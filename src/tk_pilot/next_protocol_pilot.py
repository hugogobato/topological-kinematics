"""Difficulty pilot for the matched-budget reversible-versus-drift protocol.

This is the pilot that the proposed post-PIVOT protocol requires before any
confirmatory seeds are opened. It reuses the frozen pipeline (exact metric,
path diagnostics, learner grid, macro balanced error) on a new two-class DGP
implemented in :mod:`tk_pilot.matched_budget`, and it sweeps the difficulty
knobs named in the report: the movement budget, the noise level, and the
sampling stride.

The pilot is deliberately outside the frozen confirmatory block: it uses its
own seed namespace (4000 to 4499) and writes its own artifacts under
``research_review/results/next_protocol/``.

Example:

    python -m tk_pilot.next_protocol_pilot \
        --budgets 0.25,0.5,1.0 --sigmas 0.05,0.1,0.2 --strides 1 \
        --train 4000:4014 --val 4020:4027 --test 4030:4044 \
        --workers 8 --tag stage1
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

import numpy as np

from . import diagram_metrics, features, generators, matched_budget, persistence
from .evaluate import macro_balanced_error
from .models import fit_select_predict
from .path_diagnostics import compute_path_diagnostics

__all__ = ["main"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTDIR = REPO_ROOT / "research_review/results/next_protocol"
PILOT_REPRESENTATIONS = (
    "compact",
    "speed_history",
    "raw_geometry_flat",
    "raw_geometry_summary",
    "moments_summary",
    "moment_signature_time",
)
METRIC = diagram_metrics.bottleneck_linf
LEARNER_SEED = 20260907


def _parse_int_range(text: str) -> list[int]:
    if ":" in str(text):
        start, end = str(text).split(":", 1)
        return list(range(int(start), int(end) + 1))
    return [int(item) for item in str(text).split(",") if item.strip()]


def _parse_float_list(text: str) -> list[float]:
    return [float(item) for item in str(text).split(",") if item.strip()]


def _parse_str_list(text: str) -> list[str]:
    return [item.strip() for item in str(text).split(",") if item.strip()]


def _cell_key(family: str, budget: float, sigma: float, stride: int) -> tuple:
    return (str(family), float(budget), float(sigma), int(stride))


def _cell_label(key: tuple) -> str:
    return f"{key[0]}|B{key[1]:g}|s{key[2]:g}|stride{key[3]}"


def _trajectory_features(job: dict[str, Any]) -> dict[str, Any]:
    """One trajectory through the frozen pipeline: diagrams, metric, features."""
    family = str(job["family"])
    class_name = str(job["class"])
    budget = float(job["budget"])
    sigma = float(job["sigma"])
    stride = int(job["stride"])
    floor = float(job["floor"])
    started = time.perf_counter()
    if str(job["kind"]) == "matched":
        traj = matched_budget.build_matched_trajectory(
            class_name, family, int(job["base_seed"]), sigma, stride, budget
        )
    else:
        traj = generators.build_trajectory(
            family, "static", int(job["base_seed"]), sigma, stride
        )
    diagram_started = time.perf_counter()
    diagrams = persistence.trajectory_diagrams(traj.frames, family, degrees=(0,))[0]
    extraction_seconds = time.perf_counter() - diagram_started
    feature_started = time.perf_counter()
    series = [features._finite_diagram(diagram) for diagram in diagrams]
    diagnostics = compute_path_diagnostics(series, traj.timestamps, METRIC)
    compact = features._compact_vector(diagnostics, floor)
    speed_history = np.concatenate(
        [
            np.asarray(diagnostics.interval_speeds, dtype=np.float64),
            compact[3:9],
        ]
    )
    geometry_rows = features._geometry_rows(family, np.asarray(traj.frames))
    moments = features.moment_path(series)
    moment_signature_time = features.signature_level2_time(
        moments, np.asarray(traj.timestamps, dtype=np.float64)
    )
    vectors = {
        "compact": compact,
        "speed_history": speed_history,
        "raw_geometry_flat": geometry_rows.ravel(),
        "raw_geometry_summary": np.concatenate(
            [geometry_rows.mean(axis=0), geometry_rows.std(axis=0)]
        ),
        "moments_summary": np.concatenate(
            [moments.mean(axis=0), moments.std(axis=0)]
        ),
        "moment_signature_time": moment_signature_time,
    }
    return {
        "kind": str(job["kind"]),
        "family": family,
        "class": class_name,
        "base_seed": int(job["base_seed"]),
        "split": str(job["split"]),
        "sigma": sigma,
        "stride": stride,
        "budget": budget,
        "valid_fraction": float(
            np.mean(
                np.asarray(
                    [
                        bool(value)
                        for value in features.angle_validity_flags(
                            np.asarray(diagnostics.adjacent_distances)[:-1],
                            np.asarray(diagnostics.adjacent_distances)[1:],
                            floor,
                        )
                    ]
                )
            )
            if np.asarray(diagnostics.adjacent_distances).size >= 2
            else float("nan")
        ),
        "vectors": {name: np.asarray(vector, dtype=np.float64) for name, vector in vectors.items()},
        "seconds": float(time.perf_counter() - started),
        "extraction_seconds": float(extraction_seconds),
        "feature_seconds": float(time.perf_counter() - feature_started),
        "n_frames": int(np.asarray(traj.frames).shape[0]),
    }


def _static_adjacent_distances(job: dict[str, Any]) -> list[float]:
    """Adjacent H0 distances of one static trajectory, for the floor sample."""
    family = str(job["family"])
    traj = generators.build_trajectory(
        family,
        "static",
        int(job["base_seed"]),
        float(job["sigma"]),
        int(job["stride"]),
    )
    diagrams = persistence.trajectory_diagrams(traj.frames, family, degrees=(0,))[0]
    series = [features._finite_diagram(diagram) for diagram in diagrams]
    if len(series) < 2:
        return []
    diagnostics = compute_path_diagnostics(series, traj.timestamps, METRIC)
    return [float(value) for value in diagnostics.adjacent_distances]


def _parallel_map(function, items, workers: int) -> list:
    entries = list(items)
    if not entries:
        return []
    if int(workers) <= 1 or len(entries) == 1:
        return [function(entry) for entry in entries]
    from joblib import Parallel, delayed

    return list(
        Parallel(n_jobs=int(workers), backend="loky")(
            delayed(function)(entry) for entry in entries
        )
    )


def _calibrate_floors(
    families: list[str],
    sigmas: list[float],
    strides: list[int],
    static_seeds: list[int],
    workers: int,
) -> dict[tuple[str, float, int], float]:
    jobs: list[dict[str, Any]] = []
    for family in families:
        for sigma in sigmas:
            if float(sigma) <= 0.0:
                continue
            for stride in strides:
                for seed in static_seeds:
                    jobs.append(
                        {
                            "family": family,
                            "sigma": float(sigma),
                            "stride": int(stride),
                            "base_seed": int(seed),
                        }
                    )
    results = _parallel_map(_static_adjacent_distances, jobs, workers)
    pooled: dict[tuple[str, float, int], list[float]] = {}
    for job, values in zip(jobs, results):
        key = (str(job["family"]), float(job["sigma"]), int(job["stride"]))
        pooled.setdefault(key, []).extend(values)
    floors: dict[tuple[str, float, int], float] = {}
    for key, values in pooled.items():
        if values:
            floors[key] = float(np.percentile(np.asarray(values), 95.0))
    return floors


def _run_cell(
    family: str,
    budget: float,
    sigma: float,
    stride: int,
    splits: dict[str, list[int]],
    floor: float,
    workers: int,
    representations: tuple[str, ...],
) -> dict[str, Any]:
    jobs = [
        {
            "kind": "matched",
            "family": family,
            "class": class_name,
            "budget": float(budget),
            "sigma": float(sigma),
            "stride": int(stride),
            "base_seed": int(seed),
            "split": split,
            "floor": float(floor),
        }
        for split, seeds in splits.items()
        for seed in seeds
        for class_name in matched_budget.MATCHED_CLASSES
    ]
    started = time.perf_counter()
    results = _parallel_map(_trajectory_features, jobs, workers)
    elapsed = time.perf_counter() - started
    data: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for result in results:
        data.setdefault(str(result["split"]), {}).setdefault(
            str(result["class"]), []
        ).append(result)
    summaries: list[dict[str, Any]] = []
    for representation in representations:
        matrices = {}
        labels = {}
        for split in ("train", "validation", "test"):
            rows = [
                result
                for class_results in data.get(split, {}).values()
                for result in class_results
            ]
            rows.sort(key=lambda item: (str(item["class"]), int(item["base_seed"])))
            matrices[split] = np.vstack(
                [item["vectors"][representation] for item in rows]
            )
            labels[split] = np.asarray([str(item["class"]) for item in rows])
        fit = fit_select_predict(
            matrices["train"],
            labels["train"],
            matrices["validation"],
            labels["validation"],
            matrices["test"],
            seed=LEARNER_SEED,
        )
        test_predictions = fit["test_predictions"]
        summaries.append(
            {
                "representation": representation,
                "learner": str(fit["learner"]),
                "val_error": float(fit["val_error"]),
                "test_error": float(
                    macro_balanced_error(labels["test"], test_predictions)
                ),
                "n_train": int(len(labels["train"])),
                "n_val": int(len(labels["validation"])),
                "n_test": int(len(labels["test"])),
                "feature_dim": int(fit["feature_dim"]),
                "valid_fraction_mean": float(
                    np.mean(
                        [
                            result["valid_fraction"]
                            for class_results in data.get("test", {}).values()
                            for result in class_results
                        ]
                    )
                ),
            }
        )
    n_frames = int(np.mean([result["n_frames"] for result in results])) if results else 0
    return {
        "family": family,
        "budget": float(budget),
        "sigma": float(sigma),
        "stride": int(stride),
        "floor": float(floor),
        "cell_seconds": float(elapsed),
        "n_frames_mean": n_frames,
        "n_trajectories": len(results),
        "summaries": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budgets", default="0.25,0.5,1.0")
    parser.add_argument("--sigmas", default="0.05,0.1,0.2")
    parser.add_argument("--strides", default="1")
    parser.add_argument("--families", default="A,B")
    parser.add_argument("--train", default="4000:4014")
    parser.add_argument("--val", default="4020:4027")
    parser.add_argument("--test", default="4030:4044")
    parser.add_argument("--static", default="4100:4114")
    parser.add_argument(
        "--representations", default=",".join(PILOT_REPRESENTATIONS)
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--tag", default="pilot")
    args = parser.parse_args(argv)

    budgets = _parse_float_list(args.budgets)
    sigmas = _parse_float_list(args.sigmas)
    strides = [int(item) for item in _parse_float_list(args.strides)]
    families = _parse_str_list(args.families)
    representations = tuple(_parse_str_list(args.representations))
    splits = {
        "train": _parse_int_range(args.train),
        "validation": _parse_int_range(args.val),
        "test": _parse_int_range(args.test),
    }
    static_seeds = _parse_int_range(args.static)
    outdir = Path(args.outdir) / str(args.tag)
    outdir.mkdir(parents=True, exist_ok=True)

    print(
        f"pilot {args.tag}: {len(families)} families x {len(budgets)} budgets x "
        f"{len(sigmas)} sigmas x {len(strides)} strides; "
        f"{len(splits['train'])}/{len(splits['validation'])}/{len(splits['test'])} "
        f"train/val/test seeds per class; workers={args.workers}"
    )
    floors = _calibrate_floors(families, sigmas, strides, static_seeds, args.workers)
    rows: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []
    for family in families:
        for budget in budgets:
            for sigma in sigmas:
                for stride in strides:
                    floor = (
                        0.0
                        if float(sigma) <= 0.0
                        else floors.get((family, float(sigma), int(stride)), float("nan"))
                    )
                    started = time.perf_counter()
                    cell = _run_cell(
                        family,
                        budget,
                        sigma,
                        stride,
                        splits,
                        floor,
                        args.workers,
                        representations,
                    )
                    cell_records.append(cell)
                    for summary in cell["summaries"]:
                        row = {
                            "family": family,
                            "budget": float(budget),
                            "sigma": float(sigma),
                            "stride": int(stride),
                            "floor": float(floor),
                            **summary,
                        }
                        rows.append(row)
                        print(
                            f"  {family} B={budget:g} sigma={sigma:g} stride={stride} "
                            f"floor={floor:.4g} {summary['representation']:>22s} "
                            f"test={summary['test_error']:.4f} "
                            f"val={summary['val_error']:.4f} "
                            f"({summary['learner']})"
                        )
                    print(
                        f"  cell wall {time.perf_counter() - started:.1f}s, "
                        f"n_frames~{cell['n_frames_mean']}"
                    )
    summary_path = outdir / "summary.csv"
    header = [
        "family",
        "budget",
        "sigma",
        "stride",
        "representation",
        "learner",
        "val_error",
        "test_error",
        "n_train",
        "n_val",
        "n_test",
        "feature_dim",
        "valid_fraction_mean",
        "floor",
    ]
    with open(summary_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in header})
    metrics_path = outdir / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "tag": str(args.tag),
                "splits": splits,
                "static_seeds": static_seeds,
                "budgets": budgets,
                "sigmas": sigmas,
                "strides": strides,
                "families": families,
                "representations": list(representations),
                "floors": {
                    f"{key[0]}|s{key[1]:g}|stride{key[2]}": value
                    for key, value in floors.items()
                },
                "cells": cell_records,
            },
            indent=2,
            sort_keys=True,
            default=float,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {summary_path} and {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
