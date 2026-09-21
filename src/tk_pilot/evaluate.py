"""Decision statistics for the topological-kinematics pilot (WP-1.2).

The module implements the frozen analysis of ``Pilot_Experiment_Specification.md``
section 5 and ``preregistration_draft.md`` section 7 on the raw per-trajectory
results table:

- macro balanced error within each ``(family, sigma, stride, degree)`` cell,
  with equal weight over the cells;
- a paired cluster bootstrap over whole ``(family, class, base_seed)`` clusters
  with 2000 resamples and seed 20260907 that preserves method pairing;
- simultaneous Bonferroni-adjusted family bounds over the raw families;
- the two-route GO decision for the compact representation against the
  validation-selected incumbent.

The macros and the bootstrap are pure numpy/pandas. Nothing here fits a model,
reads a file, or draws a random number outside the seeded bootstrap.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "CELL_KEYS",
    "DEFAULT_THRESHOLDS",
    "macro_balanced_error",
    "cell_table",
    "equal_weight_cell_average",
    "paired_cluster_bootstrap",
    "family_deterioration_bounds",
    "decide",
]

CELL_KEYS: tuple[str, ...] = ("family", "sigma", "stride", "degree")
CLUSTER_KEYS: tuple[str, ...] = ("family", "class", "base_seed")
TRAJECTORY_KEYS: tuple[str, ...] = (
    "family",
    "class",
    "base_seed",
    "sigma",
    "stride",
    "degree",
)

DEFAULT_THRESHOLDS: dict[str, float] = {
    "superiority_upper": -0.05,
    "noninferiority_upper": 0.02,
    "parsimony_ratio": 4.0,
    "family_deterioration": 0.05,
    "target_half_width": 0.01,
}


def macro_balanced_error(y_true, y_pred) -> float:
    """Mean over classes present in ``y_true`` of that class's error rate.

    For every label ``c`` that appears in the true labels, the per-class error
    is the fraction of true-``c`` trajectories whose prediction is not ``c``.
    Classes absent from ``y_true`` are skipped entirely, so predictions of an
    absent class only count as errors for the true class they missed.
    """
    true = np.asarray(y_true)
    pred = np.asarray(y_pred)
    if true.shape != pred.shape:
        raise ValueError(
            f"y_true and y_pred must have the same shape; got {true.shape} and {pred.shape}"
        )
    if true.size == 0:
        return float("nan")
    classes = np.unique(true)
    errors = [float(np.mean(pred[true == label] != label)) for label in classes]
    return float(np.mean(errors))


def cell_table(
    results: pd.DataFrame,
    split: str | None = "test",
    representations: Sequence[str] | None = None,
    require_status: str | None = "ok",
) -> pd.DataFrame:
    """Per-cell macro balanced error from raw per-trajectory result rows.

    One row is produced per ``(family, sigma, stride, degree, representation)``
    cell with the cell's macro balanced error, the trajectory count, and the
    mean reported ``valid_fraction``. ``split=None`` keeps every split; by
    default only rows with ``status == "ok"`` are used, so controls and failed
    extractions never enter an accuracy calculation.
    """
    df = results
    if split is not None:
        df = df[df["split"] == split]
    if require_status is not None:
        df = df[df["status"] == require_status]
    if representations is not None:
        df = df[df["representation"].isin(list(representations))]
    group_keys = list(CELL_KEYS) + ["representation"]
    rows: list[dict[str, Any]] = []
    if not df.empty:
        for key, group in df.groupby(group_keys, sort=True, dropna=False):
            cell = dict(zip(CELL_KEYS, key[:-1]))
            rows.append(
                {
                    **cell,
                    "representation": key[-1],
                    "split": split,
                    "error": macro_balanced_error(
                        group["true_label"], group["predicted_label"]
                    ),
                    "n_trajectories": int(len(group)),
                    "valid_fraction": float(np.mean(group["valid_fraction"])),
                }
            )
    columns = list(CELL_KEYS) + [
        "representation",
        "split",
        "error",
        "n_trajectories",
        "valid_fraction",
    ]
    return pd.DataFrame(rows, columns=columns)


def equal_weight_cell_average(
    table: pd.DataFrame, representation: str, split: str | None = None
) -> float:
    """Equal-weight average of the cell errors of one representation."""
    df = table[table["representation"] == representation]
    if split is not None:
        df = df[df["split"] == split]
    if df.empty:
        return float("nan")
    return float(df["error"].mean())


def _pair_methods(table: pd.DataFrame, reference: str, candidate: str) -> pd.DataFrame:
    if reference == candidate:
        raise ValueError("reference and candidate must be different representations")
    df = table
    if "status" in df.columns:
        df = df[df["status"] == "ok"]
    if "split" in df.columns and df["split"].nunique(dropna=False) > 1:
        raise ValueError(
            "filter the results table to a single split before bootstrapping; "
            "trajectory keys repeat across splits"
        )
    left = df[df["representation"] == reference]
    right = df[df["representation"] == candidate]
    if left.empty or right.empty:
        raise ValueError(
            f"both representations are required; got {len(left)} {reference} rows "
            f"and {len(right)} {candidate} rows"
        )
    paired = left.merge(
        right,
        on=list(TRAJECTORY_KEYS),
        how="inner",
        suffixes=("_ref", "_cand"),
        validate="one_to_one",
    )
    if paired.empty:
        raise ValueError("no trajectory is available for both representations")
    if not bool((paired["true_label_ref"] == paired["true_label_cand"]).all()):
        raise ValueError("paired true labels disagree between the two representations")
    return paired


def _macro_errors_from_counts(n_true: np.ndarray, n_correct: np.ndarray) -> np.ndarray:
    present = n_true > 0
    safe = np.where(present, n_true, 1.0)
    per_class = np.where(present, 1.0 - n_correct / safe, np.nan)
    totals = np.nansum(per_class, axis=-1)
    counts = present.sum(axis=-1)
    return np.where(counts > 0, totals / np.maximum(counts, 1), np.nan)


def _bootstrap_deltas(
    table: pd.DataFrame,
    reference: str,
    candidate: str,
    n_resamples: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    paired = _pair_methods(table, reference, candidate)
    cells = sorted(
        {
            (
                str(f),
                float(s),
                int(st),
                int(dg),
            )
            for f, s, st, dg in zip(
                paired["family"],
                paired["sigma"],
                paired["stride"],
                paired["degree"],
            )
        }
    )
    clusters = sorted(
        {
            (str(f), str(c), int(b))
            for f, c, b in zip(
                paired["family"], paired["class"], paired["base_seed"]
            )
        }
    )
    classes = sorted({str(label) for label in paired["true_label_ref"]})
    cell_index = {cell: i for i, cell in enumerate(cells)}
    cluster_index = {cluster: i for i, cluster in enumerate(clusters)}
    class_index = {label: i for i, label in enumerate(classes)}
    n_cells = len(cells)
    n_classes = len(classes)
    n_clusters = len(clusters)
    n_true = np.zeros((n_cells, n_classes, n_clusters), dtype=np.float64)
    n_correct_ref = np.zeros_like(n_true)
    n_correct_cand = np.zeros_like(n_true)
    families = [str(value) for value in paired["family"]]
    class_values = [str(value) for value in paired["class"]]
    seeds = [int(value) for value in paired["base_seed"]]
    sigmas = [float(value) for value in paired["sigma"]]
    strides = [int(value) for value in paired["stride"]]
    degrees = [int(value) for value in paired["degree"]]
    trues = [str(value) for value in paired["true_label_ref"]]
    preds_ref = [str(value) for value in paired["predicted_label_ref"]]
    preds_cand = [str(value) for value in paired["predicted_label_cand"]]
    for i in range(len(paired)):
        cell = (families[i], sigmas[i], strides[i], degrees[i])
        cluster = (families[i], class_values[i], seeds[i])
        ci = cell_index[cell]
        ki = cluster_index[cluster]
        yi = class_index[trues[i]]
        n_true[ci, yi, ki] += 1.0
        if preds_ref[i] == trues[i]:
            n_correct_ref[ci, yi, ki] += 1.0
        if preds_cand[i] == trues[i]:
            n_correct_cand[ci, yi, ki] += 1.0
    errors_ref = _macro_errors_from_counts(n_true.sum(axis=2), n_correct_ref.sum(axis=2))
    errors_cand = _macro_errors_from_counts(
        n_true.sum(axis=2), n_correct_cand.sum(axis=2)
    )
    delta = float(np.nanmean(errors_cand - errors_ref))
    rng = np.random.default_rng(int(seed))
    deltas = np.empty(int(n_resamples), dtype=np.float64)
    for b in range(int(n_resamples)):
        draw = rng.integers(0, n_clusters, size=n_clusters)
        sampled_true = n_true[:, :, draw].sum(axis=2)
        sampled_ref = n_correct_ref[:, :, draw].sum(axis=2)
        sampled_cand = n_correct_cand[:, :, draw].sum(axis=2)
        boot_ref = _macro_errors_from_counts(sampled_true, sampled_ref)
        boot_cand = _macro_errors_from_counts(sampled_true, sampled_cand)
        deltas[b] = np.nanmean(boot_cand - boot_ref)
    info = {
        "delta": delta,
        "cell_delta": {
            "|".join(str(value) for value in cell): float(cand - ref)
            for cell, cand, ref in zip(cells, errors_cand, errors_ref)
        },
        "n_clusters": int(n_clusters),
        "n_cells": int(n_cells),
        "n_classes": int(n_classes),
        "classes": classes,
        "cells": ["|".join(str(value) for value in cell) for cell in cells],
    }
    return deltas, info


def paired_cluster_bootstrap(
    table: pd.DataFrame,
    reference: str,
    candidate: str,
    n_resamples: int = 2000,
    seed: int = 20260907,
) -> dict:
    """Paired cluster bootstrap of ``candidate`` minus ``reference`` error.

    Whole ``(family, class, base_seed)`` clusters are resampled with
    replacement, every ``(family, sigma, stride, degree)`` cell present in the
    paired table is recomputed from the resampled clusters, and the resample
    statistic is the equal-weight average of the cell deltas. The same clusters
    enter both methods, so method pairing and all correlated noise and
    resolution variants are preserved. The reported interval is the percentile
    interval at 2.5 and 97.5 percent.
    """
    deltas, info = _bootstrap_deltas(
        table, reference, candidate, int(n_resamples), int(seed)
    )
    low, high = np.percentile(deltas, [2.5, 97.5])
    return {
        "reference": reference,
        "candidate": candidate,
        "delta": info["delta"],
        "ci_low": float(low),
        "ci_high": float(high),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "n_clusters": info["n_clusters"],
        "n_cells": info["n_cells"],
        "cell_delta": info["cell_delta"],
        "bootstrap_deltas": deltas,
    }


def family_deterioration_bounds(
    table: pd.DataFrame,
    reference: str,
    candidate: str,
    families: Sequence[str] | None = None,
    n_resamples: int = 2000,
    seed: int = 20260907,
    confidence: float = 0.95,
) -> dict:
    """Simultaneous Bonferroni-adjusted per-family delta intervals.

    With ``k`` families each family interval uses the two-sided level
    ``(1 - confidence) / k``, so the family statements hold simultaneously at
    ``confidence``. The point estimate and the bootstrap draws use the same
    seeded paired cluster bootstrap as :func:`paired_cluster_bootstrap` on the
    family-restricted table.
    """
    if families is None:
        families = sorted({str(value) for value in table["family"]})
    families = [str(value) for value in families]
    if not families:
        return {}
    alpha = (1.0 - float(confidence)) / len(families)
    bounds: dict[str, dict[str, Any]] = {}
    for family in families:
        subset = table[table["family"] == family]
        if subset.empty:
            bounds[family] = {
                "delta": float("nan"),
                "ci_low": float("nan"),
                "ci_high": float("nan"),
                "n_clusters": 0,
            }
            continue
        deltas, info = _bootstrap_deltas(
            subset, reference, candidate, int(n_resamples), int(seed)
        )
        low, high = np.percentile(
            deltas, [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)]
        )
        bounds[family] = {
            "delta": info["delta"],
            "ci_low": float(low),
            "ci_high": float(high),
            "n_clusters": info["n_clusters"],
            "family": family,
        }
    return bounds


def _interval_bounds(interval: Any) -> tuple[float, float]:
    if isinstance(interval, Mapping):
        if "lower" in interval and "upper" in interval:
            return float(interval["lower"]), float(interval["upper"])
        if "ci_low" in interval and "ci_high" in interval:
            return float(interval["ci_low"]), float(interval["ci_high"])
        raise ValueError("interval mapping must carry lower/upper or ci_low/ci_high")
    if isinstance(interval, Sequence) and len(interval) == 2:
        return float(interval[0]), float(interval[1])
    raise ValueError("interval must be a mapping or a two-element sequence")


def decide(
    delta_ci,
    parsimony_ratio: float,
    family_bounds: Mapping[str, Any] | None,
    thresholds: Mapping[str, float] | None = None,
    frozen_route: str = "superiority",
) -> dict:
    """Apply the predeclared two-route GO rule to a frozen interval set.

    Inputs are the paired interval for delta (compact minus incumbent), the
    worst-case parsimony ratio of the frozen eligible comparator set, the
    Bonferroni per-family intervals, the frozen thresholds, and the route that
    was frozen after exploration (``"superiority"`` or ``"parsimony"``).

    Route (a), superiority holds when the upper endpoint of the delta interval
    is below ``superiority_upper`` (frozen at -0.05). Route (b), parsimony holds
    when the upper endpoint is below ``noninferiority_upper`` (frozen at 0.02)
    and the parsimony ratio reaches ``parsimony_ratio`` (frozen at 4.0). GO
    requires the frozen route to hold, no family upper endpoint above
    ``family_deterioration`` (frozen at 0.05), and adequate precision
    (half-width at most ``target_half_width``, frozen at 0.01). If only the
    other route holds, the status is CONDITIONAL GO, because the claim would
    require the other route to have been frozen. If neither route holds, a
    positive lower endpoint is INCREMENTAL-ONLY (the incumbent is reliably
    better), an interval too wide to decide is INDETERMINATE, a noninferior but
    non-parsimonious result is PIVOT, and a route that holds while a family
    deteriorates above the bound is PIVOT.

    Returns ``{"status", "route", "reasons", "checks", "delta_ci",
    "parsimony_ratio", "family_bounds"}`` with status one of ``GO``,
    ``CONDITIONAL GO``, ``PIVOT``, ``INCREMENTAL-ONLY``, or ``INDETERMINATE``.
    """
    merged = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        merged.update({key: float(value) for key, value in thresholds.items()})
    if frozen_route not in ("superiority", "parsimony"):
        raise ValueError(f"frozen_route must be 'superiority' or 'parsimony'; got {frozen_route!r}")
    lower, upper = _interval_bounds(delta_ci)
    half_width = 0.5 * (upper - lower)
    superiority = bool(upper < merged["superiority_upper"])
    noninferiority = bool(upper < merged["noninferiority_upper"])
    parsimony = bool(float(parsimony_ratio) >= merged["parsimony_ratio"])
    if frozen_route == "superiority":
        route_met = superiority
        other_met = bool(noninferiority and parsimony)
        other_route = "parsimony"
    else:
        route_met = bool(noninferiority and parsimony)
        other_met = superiority
        other_route = "superiority"
    reasons: list[str] = []
    if family_bounds:
        family_upper = {
            str(family): _interval_bounds(interval)[1]
            for family, interval in family_bounds.items()
        }
        family_ok = all(
            value <= merged["family_deterioration"] for value in family_upper.values()
        )
        worst_family = max(family_upper, key=lambda key: family_upper[key])
    else:
        family_upper = {}
        family_ok = True
        worst_family = None
    precision_ok = bool(half_width <= merged["target_half_width"])
    checks = {
        "superiority": superiority,
        "noninferiority": noninferiority,
        "parsimony": parsimony,
        "route_met": route_met,
        "other_route_met": other_met,
        "family_ok": family_ok,
        "precision_ok": precision_ok,
        "half_width": float(half_width),
        "family_upper": family_upper,
    }
    if route_met and family_ok and precision_ok:
        status = "GO"
        reasons.append(
            f"frozen route {frozen_route!r} holds, every family upper endpoint is at most "
            f"{merged['family_deterioration']}, and the interval half-width is within "
            f"{merged['target_half_width']}"
        )
    elif route_met and not family_ok:
        status = "PIVOT"
        reasons.append(
            f"frozen route {frozen_route!r} holds, but family {worst_family!r} deteriorates "
            f"above {merged['family_deterioration']}"
        )
    elif route_met and not precision_ok:
        status = "INDETERMINATE"
        reasons.append(
            f"frozen route {frozen_route!r} holds but the interval half-width "
            f"{half_width:.4f} exceeds the frozen target {merged['target_half_width']}"
        )
    elif other_met and family_ok and precision_ok:
        status = "CONDITIONAL GO"
        reasons.append(
            f"the predeclared route {other_route!r} holds while the frozen route "
            f"{frozen_route!r} does not; a claim requires the other route to be frozen"
        )
    elif lower > 0.0:
        status = "INCREMENTAL-ONLY"
        reasons.append(
            "the lower endpoint of the delta interval is above zero, so the incumbent is "
            "reliably better"
        )
    elif precision_ok and noninferiority:
        status = "PIVOT"
        reasons.append(
            "the compact representation is noninferior but neither frozen route's advantage "
            "is established"
        )
    else:
        status = "INDETERMINATE"
        reasons.append(
            "the interval is too wide or otherwise unresolved while no route passes"
        )
    if superiority:
        reasons.append("superiority threshold met (upper endpoint below -0.05)")
    if noninferiority:
        reasons.append("noninferiority margin met (upper endpoint below 0.02)")
    if parsimony:
        reasons.append("parsimony ratio reaches the fourfold threshold")
    return {
        "status": status,
        "route": frozen_route,
        "reasons": reasons,
        "checks": checks,
        "delta_ci": {"lower": float(lower), "upper": float(upper)},
        "parsimony_ratio": float(parsimony_ratio),
        "family_bounds": family_bounds if family_bounds else {},
    }
