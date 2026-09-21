"""Merge confirmatory shard outputs and apply the frozen decision rule.

Reads every ``metrics.parquet`` produced by the sharded confirmatory stage, checks
completeness against the frozen route record, computes the paired cluster
bootstrap of the compact representation minus the frozen incumbent, applies the
Bonferroni family safeguard, and writes the merged table plus the G3 gate
inputs. It never changes the frozen route, incumbent, size, or thresholds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tk_pilot import evaluate  # noqa: E402
from tk_pilot.run import (  # noqa: E402
    _figure_confusion_compact,
    _figure_stride_curves,
    load_config,
)

CELL_KEYS = ["family", "sigma", "stride", "degree"]
TRAJECTORY_KEYS = ["family", "class", "base_seed", "sigma", "stride", "degree"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-dir", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--config", default="configs/tk_pilot_study.yaml")
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def load_shard_tables(shards_dir: Path) -> tuple[pd.DataFrame, list[Path]]:
    files = sorted(shards_dir.rglob("metrics.parquet"))
    if not files:
        files = sorted(shards_dir.rglob("metrics.csv.gz"))
    if not files:
        raise SystemExit(f"no metrics tables found under {shards_dir}")
    frames = []
    for path in files:
        frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        frame["shard_file"] = path.parent.name
        frames.append(frame)
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(
        subset=TRAJECTORY_KEYS
        + ["representation", "learner", "split", "status", "predicted_label"],
        keep="first",
    )
    return merged, files


def completeness(merged: pd.DataFrame, freeze: dict, families: list[str]) -> dict:
    test = merged[(merged["split"] == "test") & (merged["status"] == "ok")]
    report: dict[str, object] = {}
    ok = True
    for family in families:
        subset = test[test["family"] == family]
        clusters = {
            (str(row["class"]), int(row["base_seed"]))
            for _, row in subset.iterrows()
        }
        expected = int(freeze["n_clusters"])
        report[family] = {
            "n_clusters": len(clusters),
            "expected_clusters": expected,
            "n_rows": int(len(subset)),
            "complete": len(clusters) == expected,
        }
        ok = ok and len(clusters) == expected
    report["complete"] = ok
    return report


def parsimony_from_table(
    merged: pd.DataFrame, eligible: list[str], compact: str = "compact"
) -> dict:
    test = merged[(merged["split"] == "test") & (merged["status"] == "ok")]
    worst_dimension = float("inf")
    worst_cost = float("inf")
    cells: list[dict] = []
    for cell, group in test.groupby(CELL_KEYS, sort=True):
        by_rep = group.groupby("representation")
        if compact not in by_rep.groups:
            continue
        compact_rows = by_rep.get_group(compact)
        compact_dim = float(compact_rows["feature_dim"].median())
        compact_cost = float(
            (
                compact_rows["extraction_seconds"]
                + compact_rows["feature_seconds"]
                + compact_rows["prediction_seconds"]
            ).median()
        )
        dimension_candidates = []
        cost_candidates = []
        for name in eligible:
            if name == compact or name not in by_rep.groups:
                continue
            rows = by_rep.get_group(name)
            dimension_candidates.append(float(rows["feature_dim"].median()))
            cost_candidates.append(
                float(
                    (
                        rows["extraction_seconds"]
                        + rows["feature_seconds"]
                        + rows["prediction_seconds"]
                    ).median()
                )
            )
        dimension_ratio = (
            min(dimension_candidates) / compact_dim
            if dimension_candidates and compact_dim > 0
            else float("nan")
        )
        cost_ratio = (
            min(cost_candidates) / compact_cost
            if cost_candidates and compact_cost > 0
            else float("nan")
        )
        if np.isfinite(dimension_ratio):
            worst_dimension = min(worst_dimension, dimension_ratio)
        if np.isfinite(cost_ratio):
            worst_cost = min(worst_cost, cost_ratio)
        cells.append(
            {
                "cell": "|".join(str(value) for value in cell),
                "dimension_ratio": dimension_ratio,
                "cost_ratio": cost_ratio,
            }
        )
    ratio = max(
        worst_dimension if np.isfinite(worst_dimension) else 0.0,
        worst_cost if np.isfinite(worst_cost) else 0.0,
    )
    return {
        "eligible": list(eligible),
        "worst_dimension_ratio": worst_dimension,
        "worst_cost_ratio": worst_cost,
        "parsimony_ratio": float(ratio),
        "cells": cells,
    }


def main() -> int:
    args = parse_args()
    shards_dir = Path(args.shards_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    freeze = json.loads(Path(args.freeze).read_text(encoding="utf-8"))
    cfg, _ = load_config(str(REPO_ROOT / args.config))
    families = sorted({str(value) for value in freeze.get("families", cfg["families"])})
    merged, files = load_shard_tables(shards_dir)
    merged.to_parquet(outdir / "metrics_merged.parquet", index=False)

    completeness_report = completeness(merged, freeze, families)
    incumbent = str(freeze["incumbent"])
    route = str(freeze["route"])
    eligible = [str(name) for name in freeze.get("eligible_comparators") or []]
    if not eligible:
        eligible = [
            name
            for name in sorted(set(merged["representation"]))
            if name != "compact"
        ]

    test = merged[(merged["split"] == "test") & (merged["status"] == "ok")]
    table_test = evaluate.cell_table(merged, split="test")
    table_test.to_csv(outdir / "cell_table_test.csv", index=False)

    delta = evaluate.paired_cluster_bootstrap(
        test,
        reference=incumbent,
        candidate="compact",
        n_resamples=int(cfg["bootstrap"]["n_resamples"]),
        seed=int(cfg["bootstrap"]["seed"]),
    )
    family_bounds = evaluate.family_deterioration_bounds(
        test,
        reference=incumbent,
        candidate="compact",
        families=families,
        n_resamples=int(cfg["bootstrap"]["n_resamples"]),
        seed=int(cfg["bootstrap"]["seed"]),
    )
    parsimony = parsimony_from_table(merged, eligible)
    decision = evaluate.decide(
        {"ci_low": delta["ci_low"], "ci_high": delta["ci_high"]},
        parsimony_ratio=float(parsimony["parsimony_ratio"]),
        family_bounds=family_bounds,
        thresholds=cfg["decision"],
        frozen_route=route,
    )
    equal_weight = {
        representation: float(
            evaluate.equal_weight_cell_average(table_test, representation, "test")
        )
        for representation in sorted(set(table_test["representation"]))
    }
    half_width = 0.5 * (float(delta["ci_high"]) - float(delta["ci_low"]))
    payload = {
        "freeze": freeze,
        "shard_files": [str(path) for path in files],
        "completeness": completeness_report,
        "n_test_clusters": int(delta["n_clusters"]),
        "n_cells": int(delta["n_cells"]),
        "delta": {
            key: value
            for key, value in delta.items()
            if key != "bootstrap_deltas"
        },
        "half_width": half_width,
        "target_half_width": float(cfg["decision"]["target_half_width"]),
        "precision_ok": bool(half_width <= float(cfg["decision"]["target_half_width"])),
        "family_bounds": family_bounds,
        "parsimony": parsimony,
        "decision": decision,
        "test_equal_weight": equal_weight,
    }
    (outdir / "analysis.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )

    figures_dir = outdir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    degree = int(cfg["degrees"]["primary"])
    figures = []
    for figure in (
        _figure_stride_curves(table_test, degree, figures_dir),
        _figure_confusion_compact(
            test[test["degree"] == degree], degree, figures_dir
        ),
    ):
        if figure is not None:
            figures.append(str(figure))

    lines = [
        "# Confirmatory gate inputs",
        "",
        f"- Frozen route: {route}; frozen incumbent: {incumbent}",
        f"- Frozen size: {freeze['n_clusters']} base-seed clusters per family",
        f"- Merged shard tables: {len(files)}",
        f"- Completeness: {completeness_report}",
        f"- Delta (compact minus incumbent): {delta['delta']:.4f} "
        f"[{delta['ci_low']:.4f}, {delta['ci_high']:.4f}]",
        f"- Interval half-width: {half_width:.4f} "
        f"(target {cfg['decision']['target_half_width']})",
        f"- Parsimony ratio (worst case over cells): {parsimony['parsimony_ratio']:.3f} "
        f"(dimension {parsimony['worst_dimension_ratio']}, "
        f"cost {parsimony['worst_cost_ratio']})",
        f"- Family bounds: {json.dumps(family_bounds, default=str)}",
        f"- Decision status: {decision['status']}",
        f"- Reasons: {decision.get('reasons')}",
        "",
        "All thresholds are the frozen simulation thresholds, not application requirements.",
    ]
    (outdir / "gate_inputs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": decision["status"], "half_width": half_width}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
