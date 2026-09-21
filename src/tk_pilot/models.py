"""Fair learner protocol for the topological-kinematics pilot (WP-1.2).

Every representation is fitted under identical rules. Preprocessing is a
training-only per-column median imputation, a training-only mean/std
standardization with ``ddof = 0``, and one missing-mask column for every
original column that had any training missingness. Constant training columns
map to exactly zero. Validation and test data are transformed with the training
statistics only.

The learner grids are frozen:

- multinomial logistic regression with ``C`` in ``{0.01, 0.1, 1.0, 10.0}`` and
  ``max_iter = 5000`` (solver ``lbfgs``);
- RBF SVM with the same ``C`` set and ``gamma_scale`` in ``{0.1, 1.0, 10.0}``,
  evaluated at ``gamma = gamma_scale / d`` with ``d`` the postprocessed feature
  dimension, i.e. the dimension after imputation masks.

Given exactly 16 candidates per representation, the selected learner is the one
with the lowest validation macro balanced error; ties are broken by lower
measured validation prediction seconds, then by learner name, then by grid
order. The returned ``feature_dim`` is the postprocessed dimension ``d`` that
sets the SVM gamma and that the results table records, and ``nominal_dim`` is
the raw representation length before masks.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from .evaluate import macro_balanced_error

__all__ = [
    "LEARNER_GRIDS",
    "preprocess_fit",
    "preprocess_apply",
    "select_validation_winner",
    "fit_select_predict",
]

LEARNER_GRIDS: dict[str, dict[str, list[float]]] = {
    "logistic": {"C": [0.01, 0.1, 1.0, 10.0]},
    "svm_rbf": {"C": [0.01, 0.1, 1.0, 10.0], "gamma_scale": [0.1, 1.0, 10.0]},
}


def preprocess_fit(X_train) -> dict:
    """Fit training-only imputation, standardization, and missingness masks."""
    X = np.asarray(X_train, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError(f"X_train must be two-dimensional; got shape {X.shape}")
    n_features = int(X.shape[1])
    if n_features == 0:
        raise ValueError("X_train must contain at least one feature column")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        median = np.nanmedian(X, axis=0)
    median = np.where(np.isfinite(median), median, 0.0)
    mask_columns = tuple(
        int(j) for j in range(n_features) if bool(np.isnan(X[:, j]).any())
    )
    imputed = np.where(np.isnan(X), median[None, :], X)
    mean = imputed.mean(axis=0)
    std = imputed.std(axis=0)
    return {
        "median": np.asarray(median, dtype=np.float64),
        "mean": np.asarray(mean, dtype=np.float64),
        "std": np.asarray(std, dtype=np.float64),
        "mask_columns": mask_columns,
        "n_features": n_features,
        "n_output_features": int(n_features + len(mask_columns)),
    }


def preprocess_apply(pre: Mapping[str, Any], X) -> np.ndarray:
    """Apply fitted preprocessing with training statistics only."""
    values = np.asarray(X, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"X must be two-dimensional; got shape {values.shape}")
    if int(values.shape[1]) != int(pre["n_features"]):
        raise ValueError(
            f"X has {values.shape[1]} columns but preprocessing was fitted on "
            f"{pre['n_features']} columns"
        )
    median = np.asarray(pre["median"], dtype=np.float64)
    mean = np.asarray(pre["mean"], dtype=np.float64)
    std = np.asarray(pre["std"], dtype=np.float64)
    imputed = np.where(np.isnan(values), median[None, :], values)
    safe = np.where(std > 0.0, std, 1.0)
    standardized = (imputed - mean[None, :]) / safe[None, :]
    if standardized.shape[1]:
        standardized[:, std <= 0.0] = 0.0
    mask_columns = tuple(int(j) for j in pre["mask_columns"])
    if mask_columns:
        masks = np.isnan(values[:, mask_columns]).astype(np.float64)
        transformed = np.concatenate([standardized, masks], axis=1)
    else:
        transformed = standardized
    return np.ascontiguousarray(transformed, dtype=np.float64)


def _candidate_key(row: Mapping[str, Any]) -> tuple[float, float, str]:
    val_error = float(row["val_error"])
    if not np.isfinite(val_error):
        val_error = float("inf")
    return (val_error, float(row["prediction_seconds"]), str(row["learner"]))


def select_validation_winner(rows: Sequence[Mapping[str, Any]]) -> dict:
    """Lowest validation error, then lower prediction seconds, then learner name."""
    if not rows:
        raise ValueError("at least one candidate is required")
    return min(rows, key=_candidate_key)


def _build_estimator(family: str, params: Mapping[str, float], dim: int, seed: int):
    if family == "logistic":
        return LogisticRegression(
            C=float(params["C"]),
            max_iter=5000,
            solver="lbfgs",
            random_state=int(seed),
        )
    if family == "svm_rbf":
        return SVC(
            kernel="rbf",
            C=float(params["C"]),
            gamma=float(params["gamma_scale"]) / float(max(dim, 1)),
            random_state=int(seed),
        )
    raise ValueError(f"unsupported learner family {family!r}")


def _candidate_rows(dim: int) -> list[tuple[str, dict[str, float], str]]:
    rows: list[tuple[str, dict[str, float], str]] = []
    for c in LEARNER_GRIDS["logistic"]["C"]:
        rows.append(("logistic", {"C": float(c)}, f"logistic(C={c:g})"))
    for c in LEARNER_GRIDS["svm_rbf"]["C"]:
        for gamma_scale in LEARNER_GRIDS["svm_rbf"]["gamma_scale"]:
            rows.append(
                (
                    "svm_rbf",
                    {"C": float(c), "gamma_scale": float(gamma_scale)},
                    f"svm_rbf(C={c:g},gamma_scale={gamma_scale:g})",
                )
            )
    return rows


def fit_select_predict(
    X_train,
    y_train,
    X_val,
    y_val,
    X_test=None,
    feature_costs: Mapping[str, float] | None = None,
    seed: int = 20260907,
) -> dict:
    """Fit the frozen learner grid, select on validation, predict.

    All candidates are fitted on the training split only with preprocessing
    fitted on the training split only. Selection is :func:`select_validation_winner`
    over the 16 ``(learner, hyperparameter)`` candidates. The returned
    ``predictions`` are the test predictions when ``X_test`` is supplied,
    otherwise the validation predictions; ``val_predictions`` and
    ``test_predictions`` expose both. ``prediction_seconds`` is the measured
    prediction time for the returned split, while ``val_prediction_seconds`` and
    ``test_prediction_seconds`` are the totals used for cost accounting.
    Optional ``feature_costs`` are recorded per candidate as the representation
    feature cost and never influence selection, which is frozen to validation
    error, then prediction seconds, then learner name.
    """
    Xtr_raw = np.asarray(X_train, dtype=np.float64)
    Xva_raw = np.asarray(X_val, dtype=np.float64)
    if Xtr_raw.ndim != 2 or Xva_raw.ndim != 2:
        raise ValueError("X_train and X_val must be two-dimensional")
    if Xtr_raw.shape[1] != Xva_raw.shape[1]:
        raise ValueError("X_train and X_val must have the same feature count")
    ytr = np.asarray(y_train)
    yva = np.asarray(y_val)
    if ytr.shape[0] != Xtr_raw.shape[0] or yva.shape[0] != Xva_raw.shape[0]:
        raise ValueError("labels and feature rows must have matching lengths")
    if np.unique(ytr).size < 2:
        raise ValueError("at least two training classes are required")
    cost_map: dict[str, float] = {}
    if feature_costs:
        cost_map = {str(key): float(value) for key, value in feature_costs.items()}
    pre = preprocess_fit(Xtr_raw)
    Xtr = preprocess_apply(pre, Xtr_raw)
    Xva = preprocess_apply(pre, Xva_raw)
    postprocessed_dim = int(Xtr.shape[1])
    candidates = _candidate_rows(postprocessed_dim)
    grid: list[dict[str, Any]] = []
    fitted: dict[str, Any] = {}
    for family, params, label in candidates:
        estimator = _build_estimator(family, params, postprocessed_dim, seed)
        start = time.perf_counter()
        estimator.fit(Xtr, ytr)
        fitted_at = time.perf_counter()
        val_predictions = np.asarray(estimator.predict(Xva))
        predicted_at = time.perf_counter()
        grid.append(
            {
                "learner": label,
                "learner_family": family,
                "params": dict(params),
                "val_error": float(macro_balanced_error(yva, val_predictions)),
                "fit_seconds": float(fitted_at - start),
                "prediction_seconds": float(predicted_at - fitted_at),
                "feature_cost": float(cost_map.get(label, cost_map.get(family, 0.0))),
                "selected": False,
            }
        )
        fitted[label] = (estimator, val_predictions)
    winner = select_validation_winner(grid)
    winner["selected"] = True
    winner_label = str(winner["learner"])
    model, winner_val_predictions = fitted[winner_label]
    if X_test is not None:
        Xte_raw = np.asarray(X_test, dtype=np.float64)
        if Xte_raw.ndim != 2 or Xte_raw.shape[1] != Xtr_raw.shape[1]:
            raise ValueError("X_test must be two-dimensional with the training feature count")
        Xte = preprocess_apply(pre, Xte_raw)
        started = time.perf_counter()
        test_predictions = np.asarray(model.predict(Xte))
        test_seconds = float(time.perf_counter() - started)
        predictions = test_predictions
        prediction_seconds = test_seconds
        n_test = int(Xte_raw.shape[0])
    else:
        test_predictions = None
        test_seconds = None
        predictions = winner_val_predictions
        prediction_seconds = float(winner["prediction_seconds"])
        n_test = 0
    return {
        "predictions": predictions,
        "learner": winner_label,
        "learner_family": str(winner["learner_family"]),
        "val_error": float(winner["val_error"]),
        "feature_dim": postprocessed_dim,
        "nominal_dim": int(Xtr_raw.shape[1]),
        "prediction_seconds": float(prediction_seconds),
        "val_prediction_seconds": float(winner["prediction_seconds"]),
        "test_prediction_seconds": test_seconds,
        "n_train": int(Xtr_raw.shape[0]),
        "n_val": int(Xva_raw.shape[0]),
        "n_test": n_test,
        "model": model,
        "preprocess": pre,
        "val_grid": grid,
        "val_predictions": winner_val_predictions,
        "test_predictions": test_predictions,
        "classes": [str(label) for label in np.unique(ytr)],
    }
