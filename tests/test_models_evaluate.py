"""Tests for the fair learner protocol and decision statistics (WP-1.2)."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from tk_pilot.evaluate import (
    cell_table,
    decide,
    equal_weight_cell_average,
    family_deterioration_bounds,
    macro_balanced_error,
    paired_cluster_bootstrap,
)
from tk_pilot.models import (
    fit_select_predict,
    preprocess_apply,
    preprocess_fit,
    select_validation_winner,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

DECISION_THRESHOLDS = {
    "superiority_upper": -0.05,
    "noninferiority_upper": 0.02,
    "parsimony_ratio": 4.0,
    "family_deterioration": 0.05,
    "target_half_width": 0.01,
}


def synthetic_results_table(identical_predictions: bool = True) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(20260907)
    classes = ["return", "ramp", "jump"]
    for family in ["A", "B"]:
        for true_label in classes:
            for base_seed in [1000, 1001, 1002]:
                for sigma in [0.0, 0.05]:
                    for stride in [1, 2]:
                        for representation in ["compact", "complete_distances"]:
                            if identical_predictions or representation == "compact":
                                prediction = true_label
                            else:
                                prediction = str(rng.choice(classes))
                            rows.append(
                                {
                                    "run_id": "test-run",
                                    "base_seed": base_seed,
                                    "family": family,
                                    "class": true_label,
                                    "sigma": sigma,
                                    "stride": stride,
                                    "degree": 0,
                                    "metric": "bottleneck_linf",
                                    "representation": representation,
                                    "learner": "logistic(C=1)",
                                    "split": "test",
                                    "true_label": true_label,
                                    "predicted_label": prediction,
                                    "valid_fraction": 1.0,
                                    "feature_dim": 12,
                                    "extraction_seconds": 0.1,
                                    "feature_seconds": 0.01,
                                    "prediction_seconds": 0.001,
                                    "peak_ram_bytes": 1,
                                    "status": "ok",
                                }
                            )
    return pd.DataFrame(rows)


def test_macro_balanced_error_known_values():
    assert macro_balanced_error([0, 0, 1, 1], [0, 1, 1, 1]) == pytest.approx(0.25)
    assert macro_balanced_error([0, 0], [0, 1]) == pytest.approx(0.5)
    assert macro_balanced_error([1, 1], [0, 0]) == pytest.approx(1.0)
    assert macro_balanced_error([0, 1], [0, 1]) == pytest.approx(0.0)


def test_macro_balanced_error_skips_absent_classes():
    assert macro_balanced_error([0, 0, 0], [0, 1, 2]) == pytest.approx(2.0 / 3.0)
    assert macro_balanced_error([1, 1, 1], [0, 0, 0]) == pytest.approx(1.0)
    assert macro_balanced_error([2], [0]) == pytest.approx(1.0)


def test_macro_balanced_error_empty_is_nan():
    value = macro_balanced_error([], [])
    assert np.isnan(value)


def test_imputation_and_standardization_use_training_statistics_only():
    X_train = np.array([[0.0, 1.0], [2.0, 3.0], [1.0, np.nan]])
    X_test = np.array([[100.0, 5.0], [float("nan"), 9.0], [3.0, float("nan")]])
    pre = preprocess_fit(X_train)
    assert pre["n_features"] == 2
    assert pre["mask_columns"] == (1,)
    assert pre["n_output_features"] == 3
    transformed = preprocess_apply(pre, X_test)
    mean_zero = 1.0
    std_zero = float(np.sqrt(np.mean((np.array([0.0, 2.0, 1.0]) - 1.0) ** 2)))
    assert transformed[0, 0] == pytest.approx((100.0 - mean_zero) / std_zero)
    assert transformed[1, 0] == pytest.approx((mean_zero - mean_zero) / std_zero)
    assert transformed[2, 0] == pytest.approx((3.0 - mean_zero) / std_zero)
    imputed_one = 2.0
    mean_one = float(np.mean([1.0, 3.0, imputed_one]))
    std_one = float(np.std([1.0, 3.0, imputed_one]))
    assert transformed[0, 1] == pytest.approx((5.0 - mean_one) / std_one)
    assert transformed[1, 1] == pytest.approx((9.0 - mean_one) / std_one)
    assert transformed[2, 1] == pytest.approx((imputed_one - mean_one) / std_one)
    assert transformed[0, 2] == pytest.approx(0.0)
    assert transformed[1, 2] == pytest.approx(0.0)
    assert transformed[2, 2] == pytest.approx(1.0)


def test_constant_columns_map_to_zero():
    X_train = np.array([[1.0, 5.0], [1.0, 5.0], [1.0, 5.0]])
    pre = preprocess_fit(X_train)
    assert np.all(pre["std"] == 0.0)
    transformed = preprocess_apply(pre, np.array([[2.0, 7.0]]))
    assert transformed.shape == (1, 2)
    assert np.all(transformed == 0.0)


def test_learner_selection_tie_break():
    rows = [
        {"learner": "b", "val_error": 0.2, "prediction_seconds": 0.5},
        {"learner": "a", "val_error": 0.2, "prediction_seconds": 0.5},
        {"learner": "c", "val_error": 0.2, "prediction_seconds": 1.0},
        {"learner": "d", "val_error": 0.1, "prediction_seconds": 9.0},
    ]
    assert select_validation_winner(rows)["learner"] == "d"
    assert (
        select_validation_winner(
            [row for row in rows if row["learner"] != "d"]
        )["learner"]
        == "a"
    )
    nan_rows = [
        {"learner": "z", "val_error": float("nan"), "prediction_seconds": 0.0},
        {"learner": "y", "val_error": 0.9, "prediction_seconds": 5.0},
    ]
    assert select_validation_winner(nan_rows)["learner"] == "y"


def test_fit_select_predict_end_to_end_tiny_dataset():
    rng = np.random.default_rng(7)
    classes = np.array(["return", "ramp", "jump"])
    y_train = np.repeat(classes, 10)
    y_val = np.repeat(classes, 4)
    y_test = np.repeat(classes, 4)
    X_train = rng.normal(size=(30, 4)) + np.repeat([[0.0], [2.0], [4.0]], 10, axis=0)
    X_val = rng.normal(size=(12, 4)) + np.repeat([[0.0], [2.0], [4.0]], 4, axis=0)
    X_test = rng.normal(size=(12, 4)) + np.repeat([[0.0], [2.0], [4.0]], 4, axis=0)
    result = fit_select_predict(
        X_train, y_train, X_val, y_val, X_test, seed=20260907
    )
    assert result["predictions"].shape == (12,)
    assert set(result["predictions"]) <= set(classes)
    assert result["feature_dim"] == 4
    assert result["nominal_dim"] == 4
    assert len(result["val_grid"]) == 16
    assert sum(bool(row["selected"]) for row in result["val_grid"]) == 1
    assert result["learner"] in {row["learner"] for row in result["val_grid"]}
    assert result["test_prediction_seconds"] is not None
    repeated = fit_select_predict(
        X_train, y_train, X_val, y_val, X_test, seed=20260907
    )
    first_errors = {row["learner"]: row["val_error"] for row in result["val_grid"]}
    second_errors = {
        row["learner"]: row["val_error"] for row in repeated["val_grid"]
    }
    assert first_errors == second_errors
    assert result["val_error"] == pytest.approx(min(first_errors.values()))
    assert repeated["val_error"] == pytest.approx(result["val_error"])
    if result["learner"] == repeated["learner"]:
        assert np.array_equal(result["predictions"], repeated["predictions"])
    else:
        assert first_errors[result["learner"]] == pytest.approx(
            first_errors[repeated["learner"]]
        )


def test_fit_select_predict_counts_mask_columns():
    rng = np.random.default_rng(3)
    X_train = rng.normal(size=(12, 3))
    X_train[0, 1] = np.nan
    X_val = rng.normal(size=(6, 3))
    X_test = rng.normal(size=(6, 3))
    y = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2])
    result = fit_select_predict(X_train, y, X_val, y[:6], X_test)
    assert result["nominal_dim"] == 3
    assert result["feature_dim"] == 4


def test_paired_bootstrap_is_deterministic():
    table = synthetic_results_table(identical_predictions=False)
    first = paired_cluster_bootstrap(
        table, "complete_distances", "compact", n_resamples=200, seed=20260907
    )
    second = paired_cluster_bootstrap(
        table, "complete_distances", "compact", n_resamples=200, seed=20260907
    )
    assert first["delta"] == pytest.approx(second["delta"])
    assert first["ci_low"] == pytest.approx(second["ci_low"])
    assert first["ci_high"] == pytest.approx(second["ci_high"])
    assert np.array_equal(first["bootstrap_deltas"], second["bootstrap_deltas"])
    assert first["n_clusters"] == 18


def test_paired_bootstrap_zero_difference_gives_zero_interval():
    table = synthetic_results_table(identical_predictions=True)
    result = paired_cluster_bootstrap(
        table, "complete_distances", "compact", n_resamples=200, seed=20260907
    )
    assert result["delta"] == pytest.approx(0.0)
    assert result["ci_low"] == pytest.approx(0.0)
    assert result["ci_high"] == pytest.approx(0.0)
    assert np.all(result["bootstrap_deltas"] == 0.0)


def test_paired_bootstrap_drops_unpaired_trajectories():
    table = synthetic_results_table(identical_predictions=False)
    victim = table.index[table["representation"] == "complete_distances"][0]
    dropped = table.drop(victim)
    result = paired_cluster_bootstrap(
        dropped, "complete_distances", "compact", n_resamples=50, seed=1
    )
    assert result["n_clusters"] == 18
    with pytest.raises(ValueError):
        paired_cluster_bootstrap(
            table[table["representation"] == "compact"],
            "complete_distances",
            "compact",
            n_resamples=10,
            seed=1,
        )


def test_cell_table_and_equal_weight_average():
    table = synthetic_results_table(identical_predictions=True)
    cells = cell_table(table, split="test")
    assert set(cells["representation"]) == {"compact", "complete_distances"}
    assert len(cells) == 2 * 2 * 2 * 1 * 2
    assert equal_weight_cell_average(cells, "compact", "test") == pytest.approx(0.0)
    assert equal_weight_cell_average(cells, "complete_distances", "test") == pytest.approx(0.0)


def test_family_bounds_return_both_families():
    table = synthetic_results_table(identical_predictions=False)
    bounds = family_deterioration_bounds(
        table,
        "complete_distances",
        "compact",
        families=["A", "B"],
        n_resamples=100,
        seed=20260907,
    )
    assert set(bounds) == {"A", "B"}
    for bound in bounds.values():
        assert bound["ci_low"] <= bound["delta"] <= bound["ci_high"]


def test_decide_truth_table_go_superiority():
    result = decide(
        {"lower": -0.10, "upper": -0.09},
        1.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "GO"
    assert result["checks"]["superiority"] is True
    assert result["checks"]["precision_ok"] is True


def test_decide_truth_table_go_parsimony():
    result = decide(
        {"lower": -0.01, "upper": 0.01},
        5.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="parsimony",
    )
    assert result["status"] == "GO"
    assert result["checks"]["noninferiority"] is True
    assert result["checks"]["parsimony"] is True


def test_decide_truth_table_indeterminate():
    result = decide(
        {"lower": -0.05, "upper": 0.08},
        1.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "INDETERMINATE"
    assert result["checks"]["precision_ok"] is False


def test_decide_truth_table_incremental_only():
    result = decide(
        {"lower": 0.01, "upper": 0.05},
        1.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "INCREMENTAL-ONLY"


def test_decide_precision_requirement_blocks_go():
    result = decide(
        {"lower": -0.30, "upper": -0.08},
        1.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "INDETERMINATE"
    assert result["checks"]["route_met"] is True
    assert result["checks"]["precision_ok"] is False


def test_decide_other_route_is_conditional_go():
    result = decide(
        {"lower": -0.01, "upper": 0.01},
        5.0,
        {},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "CONDITIONAL GO"


def test_decide_family_deterioration_blocks_go():
    result = decide(
        {"lower": -0.10, "upper": -0.09},
        1.0,
        {"A": {"lower": -0.2, "upper": -0.06}, "B": {"lower": -0.01, "upper": 0.09}},
        DECISION_THRESHOLDS,
        frozen_route="superiority",
    )
    assert result["status"] == "PIVOT"
    assert result["checks"]["family_ok"] is False


def test_runner_help_works():
    env = dict(os.environ)
    pythonpath = str(ROOT / "src")
    env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "tk_pilot.run", "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0
    assert "smoke" in result.stdout
    assert "exploratory" in result.stdout
    assert "confirmatory" in result.stdout


def test_runner_imports_lazily():
    env = dict(os.environ)
    pythonpath = str(ROOT / "src")
    env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'src'); import tk_pilot.run; print('OK')",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=120,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout
