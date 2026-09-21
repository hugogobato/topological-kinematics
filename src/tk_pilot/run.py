"""Pilot runner for the topological-kinematics stages (WP-1.2).

Command surface: ``python -m tk_pilot.run --stage smoke|exploratory|confirmatory``
with ``--config``, ``--workers``, ``--outdir``, ``--max-trajectories``,
``--degree``, and ``--seed``. The module imports ``generators``,
``persistence``, and ``features`` lazily inside the stage functions, so
``--help`` and the statistics remain usable while those modules are incomplete.

Stages:

- ``smoke``: seed 11 (or ``--seed``), both families, three classes,
  ``sigma in {0, 0.05}``, stride 1, the primary degree, and the static,
  translation, and matched-speed controls reported outside the three-class
  accuracy calculation. The first trajectory is timed alone before the rest of
  the grid, as the pilot specification requires.
- ``exploratory``: training seeds 1000-1039, validation 2000-2019, exploratory
  test 3000-3039, both families, three classes, sigmas 0 and 0.05, strides 1, 2,
  4, degree H0 primary and then H1 as a second pass through the same code path.
- ``confirmatory``: the frozen ``confirmatory`` block supplies ``n_clusters``,
  ``route``, ``incumbent``, ``shard_index``, and ``n_shards``; test clusters are
  ``(family, class, base_seed)`` triples with base seeds starting at 10000,
  ordered by ``(family, class, base_seed)``, and only clusters whose sorted
  index falls in the shard are generated.

Incumbent rule (frozen by ``results/phase1/baseline_protocol.md``): the
incumbent is the best non-compact representation by equal-weight cell-averaged
validation macro balanced error; ties break by lower validation end-to-end
cost, then lower postprocessed dimension, then contract order. The eligible
comparator set contains every non-compact representation whose validation error
is at most 0.02 above the incumbent's validation error. The worst-case
parsimony ratio over cells uses the smallest eligible postprocessed dimension
over the compact dimension and the smallest eligible end-to-end held-out cost
over the compact cost.

All artifact paths are written under the resolved output directory and the
cache directory; results are never gitignored.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import platform
import resource
import time
from collections.abc import Mapping, Sequence
from dataclasses import replace
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
import pandas as pd
import yaml

from . import diagram_metrics
from .evaluate import (
    cell_table,
    decide,
    equal_weight_cell_average,
    family_deterioration_bounds,
    macro_balanced_error,
    paired_cluster_bootstrap,
)
from .path_diagnostics import (
    angle_validity_flags,
    efficiency_validity_flag,
    noise_floor,
)

__all__ = ["build_parser", "default_config", "load_config", "main"]

REPO_ROOT = Path(__file__).resolve().parents[2]

RESULT_COLUMNS: tuple[str, ...] = (
    "run_id",
    "base_seed",
    "family",
    "class",
    "sigma",
    "stride",
    "degree",
    "metric",
    "representation",
    "learner",
    "split",
    "true_label",
    "predicted_label",
    "valid_fraction",
    "feature_dim",
    "extraction_seconds",
    "feature_seconds",
    "prediction_seconds",
    "peak_ram_bytes",
    "status",
)

REPRESENTATION_NAMES: tuple[str, ...] = (
    "compact",
    "speed_history",
    "complete_distances",
    "recurrence_summary",
    "raw_geometry_flat",
    "raw_geometry_summary",
    "moments_flat",
    "moments_summary",
    "moment_signature",
    "moment_signature_time",
)

DISTANCE_REPRESENTATIONS: frozenset[str] = frozenset(
    {
        "compact",
        "speed_history",
        "complete_distances",
        "recurrence_summary",
    }
)

RAW_GEOMETRY_REPRESENTATIONS: frozenset[str] = frozenset(
    {"raw_geometry_flat", "raw_geometry_summary"}
)

CONFIRMATORY_SIZES: tuple[int, ...] = (200, 500, 1000, 2000)


def default_config() -> dict:
    """Frozen defaults matching ``configs/tk_pilot.yaml`` and the contract."""
    return {
        "master_grid": {"n": 128},
        "strides": [1, 2, 4],
        "sigmas": [0.0, 0.05],
        "classes": ["return", "ramp", "jump"],
        "families": ["A", "B"],
        "seed_namespaces": {
            "train": [1000, 1039],
            "validation": [2000, 2019],
            "test_exploratory": [3000, 3039],
            "test_confirmatory_start": 10000,
        },
        "degrees": {"primary": 0, "secondary": 1},
        "metric": "bottleneck_linf",
        "representations": list(REPRESENTATION_NAMES),
        "learner_grids": {
            "logistic": {"C": [0.01, 0.1, 1.0, 10.0]},
            "svm_rbf": {
                "C": [0.01, 0.1, 1.0, 10.0],
                "gamma_scale": [0.1, 1.0, 10.0],
            },
        },
        "bootstrap": {"n_resamples": 2000, "seed": 20260907},
        "decision": {
            "superiority_upper": -0.05,
            "noninferiority_upper": 0.02,
            "parsimony_ratio": 4.0,
            "family_deterioration": 0.05,
            "target_half_width": 0.01,
        },
        "noise_floor": {
            "sigma_calibration": 0.05,
            "percentile": 95.0,
            "angle_factor": 2.0,
            "efficiency_factor": 2.0,
        },
        "learner_seed": 20260907,
        "smoke_seed": 11,
        "cache_dir": "research_review/results/cache",
        "controls": {
            "smoke": True,
            "exploratory": False,
            "confirmatory": False,
            "matched_family": "A",
        },
        "confirmatory": {
            "n_clusters": 500,
            "route": "superiority",
            "incumbent": "complete_distances",
            "eligible_comparators": None,
            "shard_index": 0,
            "n_shards": 1,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for the frozen stage commands."""
    parser = argparse.ArgumentParser(
        prog="tk_pilot.run",
        description=(
            "Run the topological-kinematics pilot stages (smoke, exploratory, "
            "confirmatory) from the frozen configuration."
        ),
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["smoke", "exploratory", "confirmatory"],
        help="pilot stage to execute",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="YAML configuration path; defaults to configs/tk_pilot.yaml when present",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel worker processes (default 1)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="output directory; stage defaults are used when omitted",
    )
    parser.add_argument(
        "--max-trajectories",
        type=int,
        default=None,
        dest="max_trajectories",
        help="optional cap on the number of trajectory masters",
    )
    parser.add_argument(
        "--degree",
        type=int,
        default=None,
        choices=[0, 1],
        help="restrict the run to one homological degree",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="override the smoke base seed (smoke stage only)",
    )
    return parser


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict:
    merged: dict[str, Any] = {str(key): value for key, value in base.items()}
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _sha256_file(path) -> str | None:
    if path is None or not Path(path).is_file():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path_arg: str | None) -> tuple[dict, dict]:
    """Load YAML over the built-in defaults and hash the effective config."""
    default_path = REPO_ROOT / "configs" / "tk_pilot.yaml"
    loaded: dict = {}
    path: Path | None = None
    source = "builtin"
    if path_arg is not None:
        candidate = Path(path_arg)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if not candidate.is_file():
            raise SystemExit(f"config file not found: {candidate}")
        path = candidate
        loaded = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        source = "file"
    elif default_path.is_file():
        path = default_path
        loaded = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
        source = "file"
    if not isinstance(loaded, Mapping):
        raise SystemExit("config file must contain a YAML mapping")
    merged = _deep_merge(default_config(), loaded)
    digest = hashlib.sha256(
        json.dumps(merged, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    provenance = {
        "source": source,
        "path": None if path is None else str(path),
        "file_sha256": _sha256_file(path) if path is not None else None,
        "effective_sha256": digest,
    }
    return merged, provenance


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path, payload: Any) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _read_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _peak_ram_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _sigma_tag(sigma) -> int:
    return int(round(float(sigma) * 1000.0))


def _metric_fn(name: str):
    if str(name) == "bottleneck_linf":
        return diagram_metrics.bottleneck_linf
    if str(name) == "wasserstein2_linf":
        return diagram_metrics.wasserstein2_linf
    raise ValueError(f"unsupported metric {name!r}")


def _import_stack():
    try:
        from . import features, generators, persistence
    except ImportError as exc:
        raise RuntimeError(
            "this stage requires tk_pilot.generators, tk_pilot.persistence, and "
            f"tk_pilot.features; import failed: {exc}"
        ) from exc
    return generators, persistence, features


def _parallel_map(function, items: Sequence, workers: int) -> list:
    entries = list(items)
    if not entries:
        return []
    if int(workers) <= 1 or len(entries) == 1:
        return [function(entry) for entry in entries]
    try:
        from joblib import Parallel, delayed
    except ImportError:
        return [function(entry) for entry in entries]
    return list(
        Parallel(n_jobs=int(workers), backend="loky")(
            delayed(function)(entry) for entry in entries
        )
    )


def _filtered_kwargs(function, kwargs: Mapping[str, Any]) -> dict:
    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError):
        return dict(kwargs)
    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return dict(kwargs)
    return {key: value for key, value in kwargs.items() if key in parameters}


def _resolve_path(value, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _trajectory_id(family: str, label: str, base_seed: int, sigma) -> str:
    return f"{family}_{label}_{int(base_seed)}_sigma{_sigma_tag(sigma)}"


def _diagram_cache_dir(cache_dir: Path, traj) -> Path:
    return (
        Path(cache_dir)
        / str(traj.family)
        / str(traj.label)
        / str(int(traj.base_seed))
        / f"sigma{_sigma_tag(traj.sigma)}"
        / f"stride{int(traj.stride)}"
    )


def _timing_path(cache_dir: Path, traj) -> Path:
    return (
        Path(cache_dir)
        / "runner_timings"
        / str(traj.family)
        / str(traj.label)
        / str(int(traj.base_seed))
        / f"sigma{_sigma_tag(traj.sigma)}"
        / f"stride{int(traj.stride)}.json"
    )


def _distance_cache_path(cache_dir: Path, traj, degree: int) -> Path:
    return (
        Path(cache_dir)
        / "runner_distances"
        / str(traj.family)
        / str(traj.label)
        / str(int(traj.base_seed))
        / f"sigma{_sigma_tag(traj.sigma)}"
        / f"stride{int(traj.stride)}"
        / f"degree{int(degree)}.npz"
    )


def _floor_key(family: str, degree: int, stride: int) -> str:
    return f"{family}|{int(degree)}|{int(stride)}"


def _floor_value(
    floors: Mapping[str, float], family: str, degree: int, stride: int, sigma
) -> float:
    if float(sigma) == 0.0:
        return 0.0
    key = _floor_key(family, degree, stride)
    if key not in floors:
        raise KeyError(
            f"no calibration floor for cell {key!r}; calibrate the training "
            "static-noise population before building features"
        )
    return float(floors[key])


def _load_trajectory(generators, family, label, base_seed, sigma, stride, cache_dir):
    if hasattr(generators, "load_trajectory"):
        try:
            traj = generators.load_trajectory(
                family,
                label,
                int(base_seed),
                float(sigma),
                int(stride),
                Path(cache_dir),
            )
            return traj, True
        except Exception:
            pass
    traj = generators.build_trajectory(
        family, label, int(base_seed), float(sigma), int(stride)
    )
    if hasattr(generators, "save_trajectory"):
        try:
            generators.save_trajectory(traj, Path(cache_dir))
        except OSError:
            pass
    return traj, False


def _load_control(generators, control, family, base_seed, sigma, stride, cache_dir):
    if hasattr(generators, "load_trajectory"):
        try:
            traj = generators.load_trajectory(
                family,
                control,
                int(base_seed),
                float(sigma),
                int(stride),
                Path(cache_dir),
            )
            return traj, True
        except Exception:
            pass
    traj = generators.build_control(
        control, family, int(base_seed), float(sigma), int(stride)
    )
    if hasattr(generators, "save_trajectory"):
        try:
            generators.save_trajectory(traj, Path(cache_dir))
        except OSError:
            pass
    return traj, False


def _subsample_trajectory(traj, stride: int):
    stride = int(stride)
    if stride == 1:
        return traj
    try:
        return replace(
            traj,
            stride=stride,
            timestamps=np.asarray(traj.timestamps)[::stride],
            frames=np.asarray(traj.frames)[::stride],
            z=np.asarray(traj.z)[::stride],
        )
    except (TypeError, ValueError):
        return traj


def _diagrams_for(persistence, traj, degrees, cache_dir):
    wanted = tuple(int(degree) for degree in degrees)
    if hasattr(persistence, "load_diagram_cache"):
        try:
            cached = persistence.load_diagram_cache(traj, Path(cache_dir))
            available = cached.get("diagrams", {})
            if all(degree in available for degree in wanted):
                return {degree: available[degree] for degree in wanted}, True
        except Exception:
            pass
    if hasattr(persistence, "save_diagram_cache") and hasattr(
        persistence, "load_diagram_cache"
    ):
        try:
            persistence.save_diagram_cache(traj, Path(cache_dir))
            cached = persistence.load_diagram_cache(traj, Path(cache_dir))
            available = cached.get("diagrams", {})
            if all(degree in available for degree in wanted):
                return {degree: available[degree] for degree in wanted}, False
        except Exception:
            pass
    if not hasattr(persistence, "trajectory_diagrams"):
        raise AttributeError(
            "persistence exposes neither a usable cache nor trajectory_diagrams"
        )
    computed = persistence.trajectory_diagrams(
        traj.frames, traj.family, degrees=wanted
    )
    return {degree: computed[degree] for degree in wanted}, False


def _distance_matrix_for(metric_fn, traj, diagrams, cache_dir, degree):
    path = _distance_cache_path(cache_dir, traj, degree)
    if path.is_file():
        with np.load(path) as payload:
            return np.asarray(payload["matrix"], dtype=np.float64), True
    matrix = np.asarray(
        diagram_metrics.pairwise_distance_matrix(diagrams, metric=metric_fn),
        dtype=np.float64,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, matrix=matrix)
    return matrix, False


def _extract_master(job: Mapping[str, Any]) -> dict:
    generators, persistence, features = _import_stack()
    metric_fn = _metric_fn(job["metric"])
    family = str(job["family"])
    label = str(job["label"])
    base_seed = int(job["base_seed"])
    sigma = float(job["sigma"])
    cache_dir = Path(job["cache_dir"])
    degrees = tuple(int(degree) for degree in job["degrees"])
    strides = tuple(int(stride) for stride in job["strides"])
    launched = time.perf_counter()
    if str(job["category"]) == "control":
        traj1, _ = _load_control(
            generators, label, family, base_seed, sigma, 1, cache_dir
        )
    else:
        traj1, _ = _load_trajectory(
            generators, family, label, base_seed, sigma, 1, cache_dir
        )
    timing_file = _timing_path(cache_dir, traj1)
    stored = _read_json(timing_file) if timing_file.is_file() else {}
    started = time.perf_counter()
    diagrams1, diagrams_hit = _diagrams_for(persistence, traj1, degrees, cache_dir)
    measured_extraction = time.perf_counter() - started
    if diagrams_hit and "extraction_seconds" in stored:
        extraction_seconds = float(stored["extraction_seconds"])
    else:
        extraction_seconds = float(measured_extraction)
    matrices: dict[int, np.ndarray] = {}
    distance_seconds = 0.0
    for degree in degrees:
        started = time.perf_counter()
        matrix, matrix_hit = _distance_matrix_for(
            metric_fn, traj1, diagrams1[degree], cache_dir, degree
        )
        measured_distance = time.perf_counter() - started
        key = f"distance_seconds_degree{degree}"
        if matrix_hit and key in stored:
            distance_seconds += float(stored[key])
        else:
            distance_seconds += float(measured_distance)
        matrices[degree] = matrix
    _write_json(
        timing_file,
        {
            "extraction_seconds": extraction_seconds,
            "distance_seconds": distance_seconds,
            "n_frames": int(np.asarray(traj1.frames).shape[0]),
        },
    )
    records: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    for stride in strides:
        traj_stride = _subsample_trajectory(traj1, stride)
        for degree in degrees:
            diagrams_stride = list(diagrams1[degree])[::stride]
            matrix_stride = matrices[degree][::stride, ::stride]
            floor = _floor_value(job["floors"], family, degree, stride, sigma)
            moment_scaling = (job.get("moment_scalings") or {}).get(
                _floor_key(family, degree, stride)
            )
            kwargs = _filtered_kwargs(
                features.build_representations,
                {
                    "floor_e": floor,
                    "timestamps": np.asarray(traj_stride.timestamps),
                    "distance_matrix": matrix_stride,
                    "moment_scaling": moment_scaling,
                },
            )
            started = time.perf_counter()
            built = features.build_representations(
                traj_stride, diagrams_stride, degree, metric_fn, **kwargs
            )
            feature_seconds = float(time.perf_counter() - started)
            adjacent = (
                np.diag(matrix_stride, 1)
                if matrix_stride.shape[0] > 1
                else np.empty(0, dtype=np.float64)
            )
            if adjacent.size:
                valid = angle_validity_flags(adjacent[:-1], adjacent[1:], floor)
                angle_fraction = float(np.mean(valid))
            else:
                angle_fraction = float("nan")
            coverage = (
                1.0
                if efficiency_validity_flag(
                    float(np.sum(adjacent)), int(adjacent.size), floor
                )
                else 0.0
            )
            for representation in job["representations"]:
                if representation not in built:
                    raise KeyError(
                        "features.build_representations did not return "
                        f"{representation!r}"
                    )
                vector = np.asarray(built[representation], dtype=np.float64).ravel()
                records.append(
                    {
                        "degree": degree,
                        "stride": stride,
                        "representation": str(representation),
                        "vector": vector,
                        "valid_fraction": (
                            angle_fraction
                            if str(representation) == "compact"
                            else 1.0
                        ),
                        "coverage": coverage,
                        "extraction_seconds": extraction_seconds,
                        "distance_seconds": distance_seconds,
                        "feature_seconds": feature_seconds,
                        "nominal_dim": int(vector.size),
                    }
                )
            if str(job["category"]) == "control":
                diagnostics[f"{degree}|{stride}"] = {
                    "length": float(np.sum(adjacent)) if adjacent.size else 0.0,
                    "displacement": (
                        float(matrix_stride[0, -1])
                        if matrix_stride.shape[0] > 1
                        else 0.0
                    ),
                    "adjacent_distances": [float(value) for value in adjacent],
                    "angle_valid_fraction": angle_fraction,
                    "efficiency_valid": bool(coverage),
                }
    return {
        "category": str(job["category"]),
        "split": str(job["split"]),
        "family": family,
        "label": label,
        "base_seed": base_seed,
        "sigma": sigma,
        "seconds": float(time.perf_counter() - launched),
        "records": records,
        "diagnostics": diagnostics,
        "extraction_seconds": float(extraction_seconds),
        "distance_seconds": float(distance_seconds),
        "diagram_cache_dir": str(_diagram_cache_dir(cache_dir, traj1)),
        "n_frames": int(np.asarray(traj1.frames).shape[0]),
    }


def _calibration_task(job: Mapping[str, Any]) -> dict:
    generators, persistence, features = _import_stack()
    metric_fn = _metric_fn(job["metric"])
    cache_dir = Path(job["cache_dir"])
    collected: list[np.ndarray] = []
    paths: list[np.ndarray] = []
    for seed in job["seeds"]:
        traj, _ = _load_control(
            generators,
            "static",
            str(job["family"]),
            int(seed),
            float(job["sigma"]),
            1,
            cache_dir,
        )
        diagrams, _ = _diagrams_for(
            persistence, traj, (int(job["degree"]),), cache_dir
        )
        series = diagrams[int(job["degree"])]
        adjacent = np.asarray(
            [
                float(metric_fn(series[index], series[index + 1]))
                for index in range(len(series) - 1)
            ],
            dtype=np.float64,
        )
        collected.append(adjacent[:: int(job["stride"])])
        paths.append(features.moment_path(series)[:: int(job["stride"])])
    pooled = (
        np.concatenate(collected) if collected else np.empty(0, dtype=np.float64)
    )
    value = noise_floor(pooled, percentile=float(job["percentile"]))
    path_frame = np.concatenate(paths, axis=0) if paths else np.zeros((0, 6))
    if path_frame.size:
        moment_mean = path_frame.mean(axis=0)
        moment_std = path_frame.std(axis=0, ddof=0)
    else:
        moment_mean = np.zeros(path_frame.shape[1] if path_frame.ndim == 2 else 6)
        moment_std = np.ones(moment_mean.shape[0])
    moment_std = np.where(moment_std > 0.0, moment_std, 1.0)
    return {
        "family": str(job["family"]),
        "degree": int(job["degree"]),
        "stride": int(job["stride"]),
        "e": float(value),
        "n_distances": int(pooled.size),
        "moment_mean": [float(x) for x in moment_mean],
        "moment_std": [float(x) for x in moment_std],
    }


def _run_calibration(
    cfg: Mapping[str, Any],
    seeds: Sequence[int],
    families: Sequence[str],
    degrees: Sequence[int],
    strides: Sequence[int],
    cache_dir: Path,
    workers: int,
) -> tuple[dict[str, float], dict[str, dict], dict]:
    sigma = float(cfg["noise_floor"]["sigma_calibration"])
    percentile = float(cfg["noise_floor"]["percentile"])
    jobs = [
        {
            "family": str(family),
            "degree": int(degree),
            "stride": int(stride),
            "seeds": [int(seed) for seed in seeds],
            "cache_dir": str(cache_dir),
            "sigma": sigma,
            "percentile": percentile,
            "metric": str(cfg["metric"]),
        }
        for family in families
        for degree in degrees
        for stride in strides
    ]
    jobs.sort(key=lambda item: (item["family"], item["degree"], item["stride"]))
    results = _parallel_map(_calibration_task, jobs, workers)
    floors = {
        _floor_key(item["family"], item["degree"], item["stride"]): float(item["e"])
        for item in results
    }
    moment_scalings = {
        _floor_key(item["family"], item["degree"], item["stride"]): {
            "mean": [float(x) for x in item["moment_mean"]],
            "std": [float(x) for x in item["moment_std"]],
        }
        for item in results
    }
    metadata = {
        "sigma": sigma,
        "percentile": percentile,
        "metric": str(cfg["metric"]),
        "seeds": [int(seed) for seed in seeds],
        "families": [str(family) for family in families],
        "degrees": [int(degree) for degree in degrees],
        "strides": [int(stride) for stride in strides],
        "cells": {
            _floor_key(item["family"], item["degree"], item["stride"]): float(
                item["e"]
            )
            for item in results
        },
        "n_distances": {
            _floor_key(item["family"], item["degree"], item["stride"]): int(
                item["n_distances"]
            )
            for item in results
        },
        "sigma_zero_policy": (
            "at sigma = 0 the floor is exactly 0 and only exact-zero abstention applies"
        ),
        "moment_scaling_cells": moment_scalings,
        "moment_scaling_population": (
            "training-split static-noise trajectories at sigma = 0.05, "
            "the same predeclared per-cell population as the noise floor"
        ),
    }
    return floors, moment_scalings, metadata


def _translation_check_task(job: Mapping[str, Any]) -> dict:
    generators, persistence, _ = _import_stack()
    metric_fn = _metric_fn(job["metric"])
    cache_dir = Path(job["cache_dir"])
    degree = int(job["degree"])
    static, _ = _load_control(
        generators,
        "static",
        "A",
        int(job["base_seed"]),
        float(job["sigma"]),
        1,
        cache_dir,
    )
    translation, _ = _load_control(
        generators,
        "translation",
        "A",
        int(job["base_seed"]),
        float(job["sigma"]),
        1,
        cache_dir,
    )
    static_diagrams, _ = _diagrams_for(persistence, static, (degree,), cache_dir)
    translation_diagrams, _ = _diagrams_for(
        persistence, translation, (degree,), cache_dir
    )
    distances = [
        float(metric_fn(a, b))
        for a, b in zip(static_diagrams[degree], translation_diagrams[degree])
    ]
    deaths = [
        float(np.max(diagram[:, 1]))
        for diagram in list(static_diagrams[degree])
        + list(translation_diagrams[degree])
        if np.asarray(diagram).size
    ]
    filtration_range = max(deaths) if deaths else 0.0
    tolerance = 1e-7 * max(1.0, filtration_range)
    maximum = max(distances) if distances else 0.0
    return {
        "family": "A",
        "control": "translation",
        "base_seed": int(job["base_seed"]),
        "sigma": float(job["sigma"]),
        "degree": degree,
        "n_frames": len(distances),
        "max_distance": float(maximum),
        "filtration_range": float(filtration_range),
        "tolerance": float(tolerance),
        "passed": bool(maximum <= tolerance),
    }


def _representation_cost(
    representation: str, meta: Mapping[str, Any], prediction_seconds: float
) -> float:
    name = str(representation)
    extraction = (
        0.0
        if name in RAW_GEOMETRY_REPRESENTATIONS
        else float(meta["extraction_seconds"])
    )
    distance = (
        float(meta["distance_seconds"])
        if name in DISTANCE_REPRESENTATIONS
        else 0.0
    )
    return float(
        extraction
        + distance
        + float(meta["feature_seconds"])
        + float(prediction_seconds)
    )


def _fit_cell_task(job: Mapping[str, Any]) -> dict:
    from .models import fit_select_predict

    family, sigma, stride, degree = job["cell"]
    representation = str(job["representation"])
    splits = {name: job[name] for name in ("train", "validation", "test")}
    for name, metas in splits.items():
        if not metas:
            return {
                "key": (
                    f"{family}|{sigma:g}|{int(stride)}|{int(degree)}|{representation}"
                ),
                "rows": [],
                "summary": {
                    "family": str(family),
                    "sigma": float(sigma),
                    "stride": int(stride),
                    "degree": int(degree),
                    "representation": representation,
                    "status": "skipped_empty_split",
                    "missing_split": name,
                },
                "preprocess": None,
            }
    ordered = {
        name: sorted(
            metas, key=lambda meta: (str(meta["class"]), int(meta["base_seed"]))
        )
        for name, metas in splits.items()
    }
    matrix = {
        name: np.vstack(
            [
                np.asarray(meta["vector"], dtype=np.float64).ravel()
                for meta in ordered[name]
            ]
        )
        for name in ordered
    }
    labels = {
        name: np.asarray([str(meta["class"]) for meta in ordered[name]])
        for name in ordered
    }
    result = fit_select_predict(
        matrix["train"],
        labels["train"],
        matrix["validation"],
        labels["validation"],
        matrix["test"],
        feature_costs=None,
        seed=int(job["seed"]),
    )
    per_trajectory = {
        "validation": (
            float(result["val_prediction_seconds"]) / len(ordered["validation"])
            if ordered["validation"]
            else 0.0
        ),
        "test": (
            float(result["test_prediction_seconds"] or 0.0) / len(ordered["test"])
            if ordered["test"]
            else 0.0
        ),
    }
    predictions = {
        "validation": np.asarray(result["val_predictions"]),
        "test": (
            None
            if result["test_predictions"] is None
            else np.asarray(result["test_predictions"])
        ),
    }
    rows: list[dict[str, Any]] = []
    for split_name in ("validation", "test"):
        split_predictions = predictions[split_name]
        if split_predictions is None:
            continue
        for meta, prediction in zip(ordered[split_name], split_predictions):
            rows.append(
                {
                    "run_id": str(job["run_id"]),
                    "base_seed": int(meta["base_seed"]),
                    "family": str(family),
                    "class": str(meta["class"]),
                    "sigma": float(sigma),
                    "stride": int(stride),
                    "degree": int(degree),
                    "metric": str(job["metric"]),
                    "representation": representation,
                    "learner": str(result["learner"]),
                    "split": split_name,
                    "true_label": str(meta["class"]),
                    "predicted_label": str(prediction),
                    "valid_fraction": float(meta["valid_fraction"]),
                    "feature_dim": int(result["feature_dim"]),
                    "extraction_seconds": float(meta["extraction_seconds"]),
                    "feature_seconds": float(meta["feature_seconds"]),
                    "prediction_seconds": float(per_trajectory[split_name]),
                    "peak_ram_bytes": _peak_ram_bytes(),
                    "status": "ok",
                }
            )
    validation_costs = [
        _representation_cost(representation, meta, per_trajectory["validation"])
        for meta in ordered["validation"]
    ]
    test_costs = [
        _representation_cost(representation, meta, per_trajectory["test"])
        for meta in ordered["test"]
    ]
    ranking = sorted(
        result["val_grid"],
        key=lambda row: (
            float(row["val_error"])
            if math.isfinite(float(row["val_error"]))
            else math.inf,
            float(row["prediction_seconds"]),
            str(row["learner"]),
        ),
    )
    components = {
        "extraction_seconds": float(
            np.mean([meta["extraction_seconds"] for meta in ordered["test"]])
        ),
        "distance_seconds": float(
            np.mean([meta["distance_seconds"] for meta in ordered["test"]])
        ),
        "feature_seconds": float(
            np.mean([meta["feature_seconds"] for meta in ordered["test"]])
        ),
        "prediction_seconds": float(per_trajectory["test"]),
    }
    summary = {
        "family": str(family),
        "sigma": float(sigma),
        "stride": int(stride),
        "degree": int(degree),
        "representation": representation,
        "status": "ok",
        "learner": str(result["learner"]),
        "learner_family": str(result["learner_family"]),
        "val_error": float(result["val_error"]),
        "test_error": float(
            macro_balanced_error(labels["test"], predictions["test"])
        ),
        "n_train": int(result["n_train"]),
        "n_val": int(result["n_val"]),
        "n_test": int(result["n_test"]),
        "valid_fraction_mean": float(
            np.mean([meta["valid_fraction"] for meta in ordered["test"]])
        ),
        "coverage_mean": float(
            np.mean([meta["coverage"] for meta in ordered["test"]])
        ),
        "feature_dim": int(result["feature_dim"]),
        "nominal_dim": int(result["nominal_dim"]),
        "val_prediction_seconds": float(result["val_prediction_seconds"]),
        "test_prediction_seconds": (
            None
            if result["test_prediction_seconds"] is None
            else float(result["test_prediction_seconds"])
        ),
        "fit_seconds": float(
            np.sum([row["fit_seconds"] for row in result["val_grid"]])
        ),
        "end_to_end_cost_val": (
            float(np.median(validation_costs))
            if validation_costs
            else float("nan")
        ),
        "end_to_end_cost_test": (
            float(np.median(test_costs)) if test_costs else float("nan")
        ),
        "cost_components_test": components,
        "learner_ranking": [
            {
                "learner": str(row["learner"]),
                "learner_family": str(row["learner_family"]),
                "params": dict(row["params"]),
                "val_error": float(row["val_error"]),
                "fit_seconds": float(row["fit_seconds"]),
                "prediction_seconds": float(row["prediction_seconds"]),
                "feature_cost": float(row["feature_cost"]),
                "selected": bool(row["selected"]),
            }
            for row in ranking
        ],
    }
    return {
        "key": f"{family}|{sigma:g}|{int(stride)}|{int(degree)}|{representation}",
        "rows": rows,
        "summary": summary,
        "preprocess": result["preprocess"],
    }


def _control_jobs(
    cfg: Mapping[str, Any],
    degree: int,
    cache_dir: Path,
    floors: Mapping[str, float],
    run_id: str,
    base_seed: int,
    moment_scalings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    families = [str(family) for family in cfg["families"]]
    sigmas = [float(sigma) for sigma in cfg["sigmas"]]
    matched_family = str(cfg.get("controls", {}).get("matched_family", "A"))
    specs: list[tuple[str, str, float]] = []
    for family in families:
        for sigma in sigmas:
            specs.append(("static", family, sigma))
    for sigma in sigmas:
        specs.append(("translation", "A", sigma))
        specs.append(("matched_forward", matched_family, sigma))
        specs.append(("matched_folded", matched_family, sigma))
    jobs = []
    for control, family, sigma in specs:
        jobs.append(
            {
                "category": "control",
                "split": "control",
                "family": family,
                "label": control,
                "base_seed": int(base_seed),
                "sigma": float(sigma),
                "strides": [1],
                "degrees": [int(degree)],
                "cache_dir": str(cache_dir),
                "floors": dict(floors),
                "moment_scalings": dict(moment_scalings or {}),
                "representations": [str(rep) for rep in cfg["representations"]],
                "metric": str(cfg["metric"]),
                "run_id": run_id,
            }
        )
    jobs.sort(key=lambda item: (item["family"], item["label"], item["sigma"]))
    return jobs


def _control_rows(
    result: Mapping[str, Any], run_id: str, metric: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in result["records"]:
        rows.append(
            {
                "run_id": run_id,
                "base_seed": int(result["base_seed"]),
                "family": str(result["family"]),
                "class": str(result["label"]),
                "sigma": float(result["sigma"]),
                "stride": int(record["stride"]),
                "degree": int(record["degree"]),
                "metric": metric,
                "representation": str(record["representation"]),
                "learner": "",
                "split": "control",
                "true_label": str(result["label"]),
                "predicted_label": "",
                "valid_fraction": float(record["valid_fraction"]),
                "feature_dim": int(record["nominal_dim"]),
                "extraction_seconds": float(record["extraction_seconds"]),
                "feature_seconds": float(record["feature_seconds"]),
                "prediction_seconds": 0.0,
                "peak_ram_bytes": _peak_ram_bytes(),
                "status": "control",
            }
        )
    return rows


def _split_clusters_from_namespaces(
    cfg: Mapping[str, Any],
    splits: Sequence[str] = ("train", "validation", "test"),
) -> dict[str, list[tuple[str, str, int]]]:
    namespaces = cfg["seed_namespaces"]
    mapping = {
        "train": namespaces["train"],
        "validation": namespaces["validation"],
        "test": namespaces["test_exploratory"],
    }
    families = [str(family) for family in cfg["families"]]
    classes = [str(label) for label in cfg["classes"]]
    result: dict[str, list[tuple[str, str, int]]] = {}
    for split in splits:
        start, end = mapping[split]
        triples = [
            (family, label, seed)
            for seed in range(int(start), int(end) + 1)
            for family in families
            for label in classes
        ]
        triples.sort(key=lambda item: (item[0], item[1], item[2]))
        result[split] = triples
    return result


def _split_clusters_from_seed(
    cfg: Mapping[str, Any], seed: int
) -> dict[str, list[tuple[str, str, int]]]:
    families = [str(family) for family in cfg["families"]]
    classes = [str(label) for label in cfg["classes"]]
    triples = [
        (family, label, int(seed)) for family in families for label in classes
    ]
    triples.sort(key=lambda item: (item[0], item[1], item[2]))
    return {
        "train": list(triples),
        "validation": list(triples),
        "test": list(triples),
    }


def _truncate_split_clusters(
    split_clusters: Mapping[str, list[tuple[str, str, int]]],
    max_trajectories: int | None,
    n_families: int,
    n_classes: int,
) -> dict[str, list[tuple[str, str, int]]]:
    if max_trajectories is None:
        return {split: list(items) for split, items in split_clusters.items()}
    per_split = max(
        1, int(max_trajectories) // max(1, int(n_families) * int(n_classes))
    )
    truncated: dict[str, list[tuple[str, str, int]]] = {}
    for split, triples in split_clusters.items():
        seeds = sorted({int(item[2]) for item in triples})[:per_split]
        keep = set(seeds)
        truncated[split] = [item for item in triples if int(item[2]) in keep]
    return truncated


def _confirmatory_clusters(
    n_clusters: int,
    families: Sequence[str],
    classes: Sequence[str],
    start: int,
) -> list[tuple[str, str, int]]:
    families = [str(family) for family in families]
    classes = [str(label) for label in classes]
    per_seed = len(families) * len(classes)
    n_seeds = int(math.ceil(max(int(n_clusters), 0) / max(per_seed, 1)))
    triples = [
        (family, label, int(start) + k)
        for k in range(n_seeds)
        for family in families
        for label in classes
    ]
    triples = triples[: int(n_clusters)]
    triples.sort(key=lambda item: (item[0], item[1], item[2]))
    return triples


def _run_degree_pass(
    cfg: Mapping[str, Any],
    degree: int,
    split_clusters: Mapping[str, Sequence[tuple[str, str, int]]],
    stage: str,
    cache_dir: Path,
    workers: int,
    floors: Mapping[str, float],
    run_id: str,
    probe_first: bool,
    moment_scalings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    families = [str(family) for family in cfg["families"]]
    sigmas = [float(sigma) for sigma in cfg["sigmas"]]
    strides = [int(stride) for stride in cfg["strides"]]
    representations = [str(rep) for rep in cfg["representations"]]
    metric = str(cfg["metric"])
    jobs: list[dict[str, Any]] = []
    for split in ("train", "validation", "test"):
        for family, label, seed in split_clusters.get(split, []):
            for sigma in sigmas:
                jobs.append(
                    {
                        "category": "data",
                        "split": split,
                        "family": str(family),
                        "label": str(label),
                        "base_seed": int(seed),
                        "sigma": float(sigma),
                        "strides": list(strides),
                        "degrees": [int(degree)],
                        "cache_dir": str(cache_dir),
                        "floors": dict(floors),
                        "moment_scalings": dict(moment_scalings or {}),
                        "representations": list(representations),
                        "metric": metric,
                        "run_id": run_id,
                    }
                )
    jobs.sort(
        key=lambda item: (
            item["split"],
            item["family"],
            item["label"],
            item["base_seed"],
            item["sigma"],
        )
    )
    probe: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    if probe_first and jobs:
        first = jobs[0]
        started = time.perf_counter()
        first_result = _extract_master(first)
        probe = {
            "trajectory_id": _trajectory_id(
                first["family"],
                first["label"],
                first["base_seed"],
                first["sigma"],
            ),
            "seconds": float(time.perf_counter() - started),
            "peak_ram_bytes": _peak_ram_bytes(),
            "degree": int(degree),
            "stride": 1,
        }
        results.append(first_result)
        results.extend(_parallel_map(_extract_master, jobs[1:], workers))
    else:
        results = _parallel_map(_extract_master, jobs, workers)
    control_results: list[dict[str, Any]] = []
    controls_enabled = bool(cfg.get("controls", {}).get(stage, False))
    if controls_enabled:
        control_seed = int(cfg.get("smoke_seed", 11))
        if stage != "smoke":
            train_seeds = [
                int(seed) for _, _, seed in split_clusters.get("train", [])
            ]
            if train_seeds:
                control_seed = min(train_seeds)
        control_jobs = _control_jobs(
            cfg,
            degree,
            cache_dir,
            floors,
            run_id,
            base_seed=control_seed,
            moment_scalings=moment_scalings,
        )
        control_results = _parallel_map(_extract_master, control_jobs, workers)
    buckets: dict[tuple, dict[str, list[dict[str, Any]]]] = {}
    control_rows: list[dict[str, Any]] = []
    split_manifest: list[dict[str, Any]] = []
    trajectory_seconds = 0.0
    n_trajectories = 0
    for result in results:
        trajectory_seconds += float(result["seconds"])
        n_trajectories += 1
        for record in result["records"]:
            meta = {
                "class": str(result["label"]),
                "base_seed": int(result["base_seed"]),
                "family": str(result["family"]),
                "sigma": float(result["sigma"]),
                "stride": int(record["stride"]),
                "degree": int(record["degree"]),
                "representation": str(record["representation"]),
                "vector": record["vector"],
                "valid_fraction": float(record["valid_fraction"]),
                "coverage": float(record["coverage"]),
                "extraction_seconds": float(record["extraction_seconds"]),
                "distance_seconds": float(record["distance_seconds"]),
                "feature_seconds": float(record["feature_seconds"]),
                "nominal_dim": int(record["nominal_dim"]),
            }
            key = (
                str(result["family"]),
                float(result["sigma"]),
                int(record["stride"]),
                int(record["degree"]),
                str(record["representation"]),
            )
            buckets.setdefault(key, {}).setdefault(
                str(result["split"]), []
            ).append(meta)
        split_manifest.append(
            {
                "trajectory_id": _trajectory_id(
                    result["family"],
                    result["label"],
                    result["base_seed"],
                    result["sigma"],
                ),
                "base_seed": int(result["base_seed"]),
                "family": str(result["family"]),
                "class": str(result["label"]),
                "sigma": float(result["sigma"]),
                "stride": 1,
                "degree": int(degree),
                "metric": metric,
                "split": str(result["split"]),
                "cache_path": str(result["diagram_cache_dir"]),
            }
        )
    for result in control_results:
        trajectory_seconds += float(result["seconds"])
        n_trajectories += 1
        control_rows.extend(_control_rows(result, run_id, metric))
    fit_jobs: list[dict[str, Any]] = []
    cells = sorted({key[:4] for key in buckets})
    for cell in cells:
        for representation in representations:
            key = cell + (representation,)
            if key not in buckets:
                continue
            fit_jobs.append(
                {
                    "cell": cell,
                    "representation": representation,
                    "train": buckets[key].get("train", []),
                    "validation": buckets[key].get("validation", []),
                    "test": buckets[key].get("test", []),
                    "seed": int(cfg.get("learner_seed", 20260907)),
                    "run_id": run_id,
                    "metric": metric,
                    "stage": stage,
                }
            )
    fit_results = _parallel_map(_fit_cell_task, fit_jobs, workers)
    rows = list(control_rows)
    for fit_result in fit_results:
        rows.extend(fit_result["rows"])
    return {
        "degree": int(degree),
        "rows": rows,
        "summaries": [fit_result["summary"] for fit_result in fit_results],
        "preprocessing": [
            (fit_result["key"], fit_result["preprocess"])
            for fit_result in fit_results
            if fit_result.get("preprocess")
        ],
        "split_manifest": split_manifest,
        "controls": control_results,
        "probe": probe,
        "n_trajectories": int(n_trajectories),
        "trajectory_seconds": float(trajectory_seconds),
        "n_fit_jobs": len(fit_jobs),
    }


_CELL_KEYS: tuple[str, ...] = ("family", "sigma", "stride", "degree")


def _finite_or_inf(value) -> float:
    number = float(value)
    return number if math.isfinite(number) else math.inf


def _rank_representations(
    table_validation: pd.DataFrame,
    summaries: Sequence[Mapping[str, Any]],
    representations: Sequence[str],
) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for position, representation in enumerate(representations):
        val_error = equal_weight_cell_average(
            table_validation, str(representation), "validation"
        )
        rows = [
            summary
            for summary in summaries
            if summary.get("status") == "ok"
            and str(summary["representation"]) == str(representation)
        ]
        cost = (
            float(np.mean([float(row["end_to_end_cost_val"]) for row in rows]))
            if rows
            else float("inf")
        )
        dimension = (
            float(np.mean([float(row["feature_dim"]) for row in rows]))
            if rows
            else float("inf")
        )
        if not rows and not math.isfinite(float(val_error)):
            continue
        aggregates.append(
            {
                "representation": str(representation),
                "val_error": float(val_error),
                "end_to_end_cost_val": cost,
                "feature_dim": dimension,
                "contract_order": int(position),
            }
        )
    aggregates.sort(
        key=lambda row: (
            _finite_or_inf(row["val_error"]),
            float(row["end_to_end_cost_val"]),
            float(row["feature_dim"]),
            int(row["contract_order"]),
        )
    )
    for rank, row in enumerate(aggregates, start=1):
        row["rank"] = int(rank)
    return aggregates


def _parsimony_ratio(
    summaries: Sequence[Mapping[str, Any]],
    eligible: Sequence[str],
    compact: str = "compact",
    cost_field: str = "end_to_end_cost_test",
) -> dict[str, Any]:
    eligible_names = [str(name) for name in eligible]
    by_cell: dict[tuple, dict[str, Mapping[str, Any]]] = {}
    for summary in summaries:
        if summary.get("status") != "ok":
            continue
        cell = (
            str(summary["family"]),
            float(summary["sigma"]),
            int(summary["stride"]),
            int(summary["degree"]),
        )
        by_cell.setdefault(cell, {})[str(summary["representation"])] = summary
    cell_rows: list[dict[str, Any]] = []
    worst_dimension = float("inf")
    worst_cost = float("inf")
    for cell in sorted(by_cell):
        entries = by_cell[cell]
        if compact not in entries:
            continue
        compact_entry = entries[compact]
        dimension_candidates = [
            float(entries[name]["feature_dim"])
            for name in eligible_names
            if name in entries and name != compact
        ]
        cost_candidates = [
            float(entries[name][cost_field])
            for name in eligible_names
            if name in entries
            and name != compact
            and math.isfinite(float(entries[name][cost_field]))
        ]
        if not dimension_candidates and not cost_candidates:
            continue
        compact_dimension = float(compact_entry["feature_dim"])
        compact_cost = float(compact_entry[cost_field])
        dimension_ratio = (
            min(dimension_candidates) / compact_dimension
            if dimension_candidates and compact_dimension > 0
            else float("nan")
        )
        cost_ratio = (
            min(cost_candidates) / compact_cost
            if cost_candidates and compact_cost > 0
            else float("nan")
        )
        if math.isfinite(dimension_ratio):
            worst_dimension = min(worst_dimension, dimension_ratio)
        if math.isfinite(cost_ratio):
            worst_cost = min(worst_cost, cost_ratio)
        cell_rows.append(
            {
                "family": cell[0],
                "sigma": cell[1],
                "stride": cell[2],
                "degree": cell[3],
                "dimension_ratio": dimension_ratio,
                "cost_ratio": cost_ratio,
                "compact_feature_dim": compact_dimension,
                "compact_cost": compact_cost,
                "cheapest_comparator": (
                    min(
                        (
                            name
                            for name in eligible_names
                            if name in entries
                            and name != compact
                            and math.isfinite(float(entries[name][cost_field]))
                        ),
                        key=lambda name: float(entries[name][cost_field]),
                        default=None,
                    )
                ),
            }
        )
    if not cell_rows:
        return {
            "eligible": eligible_names,
            "worst_dimension_ratio": float("nan"),
            "worst_cost_ratio": float("nan"),
            "parsimony_ratio": 0.0,
            "cells": [],
            "note": "no eligible comparator is available in the fitted cells",
        }
    parsimony_ratio = max(
        worst_dimension if math.isfinite(worst_dimension) else 0.0,
        worst_cost if math.isfinite(worst_cost) else 0.0,
    )
    return {
        "eligible": eligible_names,
        "worst_dimension_ratio": worst_dimension,
        "worst_cost_ratio": worst_cost,
        "parsimony_ratio": float(parsimony_ratio),
        "cells": cell_rows,
    }


def _recommend_size(
    half_width: float,
    n_clusters: int,
    target_half_width: float,
    allowed: Sequence[int] = CONFIRMATORY_SIZES,
) -> dict[str, Any]:
    if (
        not math.isfinite(float(half_width))
        or int(n_clusters) <= 0
        or not math.isfinite(float(target_half_width))
        or float(target_half_width) <= 0
    ):
        return {
            "n_clusters": int(allowed[0]),
            "required_clusters": None,
            "resolvable": False,
            "note": "exploratory variance is unavailable; smallest size proposed",
        }
    required = (float(half_width) / float(target_half_width)) ** 2 * int(n_clusters)
    for size in allowed:
        if float(size) >= required:
            return {
                "n_clusters": int(size),
                "required_clusters": float(required),
                "resolvable": True,
                "note": "projected half-width reaches the target at this size",
            }
    return {
        "n_clusters": int(allowed[-1]),
        "required_clusters": float(required),
        "resolvable": False,
        "note": "largest affordable size cannot resolve the margin; INDETERMINATE expected",
    }


def _analyse_pass(
    rows: pd.DataFrame,
    summaries: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    degree: int,
    incumbent_name: str | None = None,
    eligible_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    thresholds = dict(cfg.get("decision", {}))
    band = float(thresholds.get("noninferiority_upper", 0.02))
    ok_rows = rows[rows["status"] == "ok"]
    test_rows = ok_rows[ok_rows["split"] == "test"]
    validation_rows = ok_rows[ok_rows["split"] == "validation"]
    table_test = cell_table(test_rows, split="test")
    table_validation = cell_table(validation_rows, split="validation")
    fitted = sorted(
        {
            str(summary["representation"])
            for summary in summaries
            if summary.get("status") == "ok"
        }
    )
    if not fitted:
        return {
            "degree": int(degree),
            "status": "no_fitted_cells",
            "reason": "every (cell, representation) fit was skipped",
        }
    contract_order = [
        str(name) for name in cfg["representations"] if str(name) in fitted
    ]
    ranking = _rank_representations(table_validation, summaries, contract_order)
    if incumbent_name is None:
        incumbent = next(
            (
                row["representation"]
                for row in ranking
                if row["representation"] != "compact"
            ),
            None,
        )
    else:
        incumbent = str(incumbent_name)
    if incumbent is None or incumbent == "compact":
        raise ValueError(
            "a non-compact incumbent representation is required for delta"
        )
    incumbent_row = next(
        (row for row in ranking if row["representation"] == incumbent), None
    )
    incumbent_val_error = (
        float(incumbent_row["val_error"]) if incumbent_row else float("nan")
    )
    if eligible_names is None:
        eligible = [
            row["representation"]
            for row in ranking
            if row["representation"] != "compact"
            and math.isfinite(float(row["val_error"]))
            and float(row["val_error"]) <= incumbent_val_error + band
        ]
    else:
        eligible = [str(name) for name in eligible_names]
    n_resamples = int(cfg["bootstrap"]["n_resamples"])
    bootstrap_seed = int(cfg["bootstrap"]["seed"])
    delta = paired_cluster_bootstrap(
        test_rows,
        reference=incumbent,
        candidate="compact",
        n_resamples=n_resamples,
        seed=bootstrap_seed,
    )
    bounds = family_deterioration_bounds(
        test_rows,
        reference=incumbent,
        candidate="compact",
        families=[str(family) for family in cfg["families"]],
        n_resamples=n_resamples,
        seed=bootstrap_seed,
    )
    parsimony = _parsimony_ratio(summaries, eligible)
    delta_ci = {"lower": float(delta["ci_low"]), "upper": float(delta["ci_high"])}
    decision_superiority = decide(
        delta_ci, parsimony["parsimony_ratio"], bounds, thresholds, "superiority"
    )
    decision_parsimony = decide(
        delta_ci, parsimony["parsimony_ratio"], bounds, thresholds, "parsimony"
    )
    recommended_route = None
    if decision_superiority["status"] == "GO":
        recommended_route = "superiority"
    elif decision_parsimony["status"] == "GO":
        recommended_route = "parsimony"
    rule = cfg.get("decision", {})
    per_cell: list[dict[str, Any]] = []
    for cell, group in table_test.groupby(list(_CELL_KEYS), sort=True):
        compact_errors = group[group["representation"] == "compact"]["error"]
        incumbent_errors = group[group["representation"] == incumbent]["error"]
        if compact_errors.empty or incumbent_errors.empty:
            continue
        per_cell.append(
            {
                "family": str(cell[0]),
                "sigma": float(cell[1]),
                "stride": int(cell[2]),
                "degree": int(cell[3]),
                "compact_error": float(compact_errors.mean()),
                "incumbent_error": float(incumbent_errors.mean()),
                "delta": float(compact_errors.mean() - incumbent_errors.mean()),
                "n_trajectories": int(
                    group[group["representation"] == "compact"]["n_trajectories"].mean()
                ),
            }
        )
    validity: list[dict[str, Any]] = []
    costs: list[dict[str, Any]] = []
    for representation in contract_order:
        rep_rows = [
            summary
            for summary in summaries
            if summary.get("status") == "ok"
            and str(summary["representation"]) == representation
        ]
        rep_table = table_test[table_test["representation"] == representation]
        if not rep_rows:
            continue
        validity.append(
            {
                "representation": representation,
                "valid_fraction": float(rep_table["valid_fraction"].mean())
                if not rep_table.empty
                else float("nan"),
                "coverage": float(
                    np.mean(
                        [float(row.get("coverage_mean", float("nan"))) for row in rep_rows]
                    )
                ),
            }
        )
        components = {
            key: float(
                np.mean(
                    [
                        float(row["cost_components_test"][key])
                        for row in rep_rows
                        if "cost_components_test" in row
                    ]
                )
            )
            for key in (
                "extraction_seconds",
                "distance_seconds",
                "feature_seconds",
                "prediction_seconds",
            )
        }
        costs.append(
            {
                "representation": representation,
                "feature_dim": float(
                    np.mean([float(row["feature_dim"]) for row in rep_rows])
                ),
                "fit_seconds": float(
                    np.mean([float(row["fit_seconds"]) for row in rep_rows])
                ),
                "end_to_end_cost_test": float(
                    np.mean(
                        [
                            float(row["end_to_end_cost_test"])
                            for row in rep_rows
                            if math.isfinite(float(row["end_to_end_cost_test"]))
                        ]
                    )
                ),
                "end_to_end_cost_val": float(
                    np.mean(
                        [
                            float(row["end_to_end_cost_val"])
                            for row in rep_rows
                            if math.isfinite(float(row["end_to_end_cost_val"]))
                        ]
                    )
                ),
                **components,
            }
        )
    half_width = 0.5 * (delta_ci["upper"] - delta_ci["lower"])
    recommendation = _recommend_size(
        half_width,
        int(delta["n_clusters"]),
        float(rule.get("target_half_width", 0.01)),
    )
    sanitized_delta = {
        "reference": delta["reference"],
        "candidate": delta["candidate"],
        "point": float(delta["delta"]),
        "ci_low": float(delta["ci_low"]),
        "ci_high": float(delta["ci_high"]),
        "half_width": float(half_width),
        "n_resamples": int(delta["n_resamples"]),
        "seed": int(delta["seed"]),
        "n_clusters": int(delta["n_clusters"]),
        "n_cells": int(delta["n_cells"]),
        "cell_delta": dict(delta["cell_delta"]),
    }
    return {
        "degree": int(degree),
        "status": "ok",
        "validation_ranking": ranking,
        "incumbent": incumbent,
        "incumbent_val_error": float(incumbent_val_error),
        "eligible_comparators": eligible,
        "delta": sanitized_delta,
        "family_bounds": bounds,
        "parsimony": parsimony,
        "decision_superiority": decision_superiority,
        "decision_parsimony": decision_parsimony,
        "recommended_route": recommended_route,
        "size_recommendation": recommendation,
        "per_cell": per_cell,
        "validity": validity,
        "costs": costs,
        "test_equal_weight": {
            representation: equal_weight_cell_average(
                table_test, representation, "test"
            )
            for representation in contract_order
        },
        "validation_equal_weight": {
            representation: equal_weight_cell_average(
                table_validation, representation, "validation"
            )
            for representation in contract_order
        },
    }


def _write_table(df: pd.DataFrame, directory: Path, stem: str) -> tuple[Path, str]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        path = directory / f"{stem}.parquet"
        df.to_parquet(path, index=False)
        return path, "parquet"
    except (ImportError, ModuleNotFoundError, ValueError, OSError):
        path = directory / f"{stem}.csv.gz"
        df.to_csv(path, index=False, compression="gzip")
        return path, "csv.gz"


def _write_selection_table(
    summaries: Sequence[Mapping[str, Any]], directory: Path
) -> tuple[Path, str] | None:
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        if summary.get("status") != "ok":
            continue
        for rank, candidate in enumerate(summary.get("learner_ranking", []), start=1):
            rows.append(
                {
                    "family": summary["family"],
                    "sigma": summary["sigma"],
                    "stride": summary["stride"],
                    "degree": summary["degree"],
                    "representation": summary["representation"],
                    "selection_rank": rank,
                    "learner": candidate["learner"],
                    "learner_family": candidate["learner_family"],
                    "val_error": candidate["val_error"],
                    "fit_seconds": candidate["fit_seconds"],
                    "prediction_seconds": candidate["prediction_seconds"],
                    "feature_cost": candidate["feature_cost"],
                    "selected": candidate["selected"],
                }
            )
    if not rows:
        return None
    frame = pd.DataFrame(rows).sort_values(
        ["degree", "family", "sigma", "stride", "representation", "selection_rank"],
        kind="stable",
    )
    return _write_table(frame, directory, "selection_table")


def _write_preprocessing(
    preprocessing: Sequence[tuple[str, Mapping[str, Any]]], path: Path
) -> Path | None:
    arrays: dict[str, np.ndarray] = {}
    for key, pre in preprocessing:
        if not pre:
            continue
        arrays[f"{key}|median"] = np.asarray(pre["median"], dtype=np.float64)
        arrays[f"{key}|mean"] = np.asarray(pre["mean"], dtype=np.float64)
        arrays[f"{key}|std"] = np.asarray(pre["std"], dtype=np.float64)
        arrays[f"{key}|mask_columns"] = np.asarray(
            pre["mask_columns"], dtype=np.int64
        )
    if not arrays:
        return None
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **arrays)
    return destination


def _write_split_manifest(
    manifest_rows: Sequence[Mapping[str, Any]],
    directory: Path,
    filename: str = "split_manifest.csv",
) -> Path | None:
    if not manifest_rows:
        return None
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        list(manifest_rows),
        columns=[
            "trajectory_id",
            "base_seed",
            "family",
            "class",
            "sigma",
            "stride",
            "degree",
            "metric",
            "split",
            "cache_path",
        ],
    ).drop_duplicates()
    destination = directory / filename
    frame.to_csv(destination, index=False)
    return destination


def _format_value(value, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "n/a"
    if abs(number) >= 1000 or (number != 0 and abs(number) < 1e-3):
        return f"{number:.3e}"
    return f"{number:.{digits}f}"


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(str(header) for header in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _figure_stride_curves(
    table_test: pd.DataFrame, degree: int, directory: Path
) -> Path | None:
    if table_test.empty:
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    cells = sorted(
        {
            (str(family), float(sigma))
            for family, sigma in zip(table_test["family"], table_test["sigma"])
        }
    )
    if not cells:
        return None
    figure, axes = plt.subplots(
        len(cells),
        1,
        figsize=(7.5, 3.0 * len(cells)),
        squeeze=False,
        sharex=True,
    )
    representations = sorted(set(table_test["representation"]))
    for axis, (family, sigma) in zip(axes[:, 0], cells):
        subset = table_test[
            (table_test["family"] == family) & (table_test["sigma"] == sigma)
        ]
        for representation in representations:
            group = subset[subset["representation"] == representation]
            if group.empty:
                continue
            ordered = group.sort_values("stride")
            linewidth = 2.4 if representation == "compact" else 1.0
            axis.plot(
                ordered["stride"],
                ordered["error"],
                marker="o",
                linewidth=linewidth,
                label=representation,
            )
        axis.set_title(f"Family {family}, sigma = {sigma:g}")
        axis.set_ylabel("macro balanced error")
        axis.grid(True, alpha=0.3)
    axes[-1, 0].set_xlabel("stride")
    axes[0, 0].legend(fontsize=6, ncol=2)
    figure.tight_layout()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"fig_stride_curves_degree{int(degree)}.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def _figure_confusion_compact(
    table_test: pd.DataFrame, degree: int, directory: Path
) -> Path | None:
    subset = table_test[table_test["representation"] == "compact"]
    if subset.empty:
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    families = sorted(set(subset["family"]))
    classes = sorted(set(subset["true_label"]))
    figure, axes = plt.subplots(
        1, len(families), figsize=(4.5 * len(families), 4.0), squeeze=False
    )
    for axis, family in zip(axes[0], families):
        group = subset[subset["family"] == family]
        matrix = np.zeros((len(classes), len(classes)), dtype=np.float64)
        class_index = {label: index for index, label in enumerate(classes)}
        for true, predicted in zip(group["true_label"], group["predicted_label"]):
            if true in class_index and predicted in class_index:
                matrix[class_index[true], class_index[predicted]] += 1.0
        image = axis.imshow(matrix, cmap="Blues")
        axis.set_xticks(range(len(classes)), classes, rotation=45)
        axis.set_yticks(range(len(classes)), classes)
        axis.set_xlabel("predicted")
        axis.set_ylabel("true")
        axis.set_title(f"Family {family}")
        for row in range(matrix.shape[0]):
            for column in range(matrix.shape[1]):
                axis.text(
                    column,
                    row,
                    int(matrix[row, column]),
                    ha="center",
                    va="center",
                    fontsize=8,
                )
        figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.suptitle(f"Compact test confusion matrix, degree H{int(degree)}")
    figure.tight_layout()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"fig_confusion_compact_degree{int(degree)}.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def _write_exploratory_report(
    path: Path,
    cfg: Mapping[str, Any],
    analyses: Sequence[Mapping[str, Any]],
    calibration_metadata: Mapping[str, Any],
    provenance: Mapping[str, Any],
    run_id: str,
    figures: Sequence[Path],
    n_rows: int,
    wall_seconds: float,
    peak_ram_bytes: int,
) -> Path:
    lines: list[str] = []
    lines.append("# Exploratory stage report")
    lines.append("")
    lines.append(
        f"Run id `{run_id}`; config sha256 `{provenance.get('effective_sha256')}`; "
        f"config source {provenance.get('source')}; rows {n_rows}; "
        f"wall {wall_seconds:.1f} s; peak RAM {peak_ram_bytes} bytes."
    )
    lines.append("")
    lines.append(
        "The incumbent rule is frozen: the incumbent is the best non-compact "
        "representation by equal-weight cell-averaged validation macro balanced "
        "error, with ties broken by lower validation end-to-end cost, then lower "
        "postprocessed dimension, then contract order. The eligible comparator set "
        "contains every non-compact representation whose validation error is at "
        "most 0.02 above the incumbent's validation error. Delta is compact minus "
        "incumbent on the exploratory test split, with the paired cluster "
        "bootstrap over (family, class, base_seed) clusters."
    )
    lines.append("")
    lines.append("## Calibration")
    lines.append("")
    lines.append(
        f"Floors are the {calibration_metadata.get('percentile')}th percentile of "
        f"adjacent distances on training static-noise trajectories at sigma = "
        f"{calibration_metadata.get('sigma')}, stored in calibration.json. At "
        "sigma = 0 the floor is exactly zero and only exact-zero abstention applies."
    )
    lines.append("")
    for analysis in analyses:
        degree = int(analysis.get("degree", 0))
        lines.append(f"## Degree H{degree}")
        lines.append("")
        if analysis.get("status") != "ok":
            lines.append(f"Status: {analysis.get('status')} ({analysis.get('reason')}).")
            lines.append("")
            continue
        lines.append("### Validation ranking and incumbent")
        lines.append("")
        lines.append(
            _markdown_table(
                ["rank", "representation", "val_error", "feature_dim", "val_cost"],
                [
                    [
                        row["rank"],
                        row["representation"],
                        _format_value(row["val_error"]),
                        _format_value(row["feature_dim"], 2),
                        _format_value(row["end_to_end_cost_val"]),
                    ]
                    for row in analysis["validation_ranking"]
                ],
            )
        )
        lines.append("")
        lines.append(
            f"Incumbent: `{analysis['incumbent']}` with validation error "
            f"{_format_value(analysis['incumbent_val_error'])}. Eligible "
            f"comparators: {', '.join('`' + name + '`' for name in analysis['eligible_comparators']) or 'none'}."
        )
        lines.append("")
        lines.append("### Delta against the incumbent")
        lines.append("")
        delta = analysis["delta"]
        lines.append(
            f"Delta { _format_value(delta['point']) } with paired 95 percent "
            f"interval [{ _format_value(delta['ci_low']) }, "
            f"{ _format_value(delta['ci_high']) }] (half width "
            f"{ _format_value(delta['half_width']) }, "
            f"{delta['n_clusters']} clusters, {delta['n_resamples']} resamples, "
            f"seed {delta['seed']})."
        )
        lines.append("")
        lines.append(
            _markdown_table(
                ["family", "delta", "Bonferroni low", "Bonferroni high", "clusters"],
                [
                    [
                        family,
                        _format_value(bound["delta"]),
                        _format_value(bound["ci_low"]),
                        _format_value(bound["ci_high"]),
                        bound.get("n_clusters", "n/a"),
                    ]
                    for family, bound in sorted(analysis["family_bounds"].items())
                ],
            )
        )
        lines.append("")
        lines.append("### Per-cell errors")
        lines.append("")
        lines.append(
            _markdown_table(
                [
                    "family",
                    "sigma",
                    "stride",
                    "degree",
                    "compact",
                    "incumbent",
                    "delta",
                    "n",
                ],
                [
                    [
                        row["family"],
                        f"{row['sigma']:g}",
                        row["stride"],
                        row["degree"],
                        _format_value(row["compact_error"]),
                        _format_value(row["incumbent_error"]),
                        _format_value(row["delta"]),
                        row["n_trajectories"],
                    ]
                    for row in analysis["per_cell"]
                ],
            )
        )
        lines.append("")
        lines.append("### Validity and coverage")
        lines.append("")
        lines.append(
            _markdown_table(
                ["representation", "valid_fraction", "coverage"],
                [
                    [
                        row["representation"],
                        _format_value(row["valid_fraction"]),
                        _format_value(row["coverage"]),
                    ]
                    for row in analysis["validity"]
                ],
            )
        )
        lines.append("")
        lines.append("### Parsimony")
        lines.append("")
        parsimony = analysis["parsimony"]
        lines.append(
            f"Worst-case dimension ratio {_format_value(parsimony['worst_dimension_ratio'])}, "
            f"worst-case cost ratio {_format_value(parsimony['worst_cost_ratio'])}, "
            f"parsimony ratio {_format_value(parsimony['parsimony_ratio'])} "
            f"(fourfold threshold applies)."
        )
        lines.append("")
        lines.append("### Costs")
        lines.append("")
        lines.append(
            _markdown_table(
                [
                    "representation",
                    "feature_dim",
                    "extraction_s",
                    "distance_s",
                    "feature_s",
                    "prediction_s",
                    "end_to_end_test_s",
                ],
                [
                    [
                        row["representation"],
                        _format_value(row["feature_dim"], 2),
                        _format_value(row["extraction_seconds"]),
                        _format_value(row["distance_seconds"]),
                        _format_value(row["feature_seconds"]),
                        _format_value(row["prediction_seconds"]),
                        _format_value(row["end_to_end_cost_test"]),
                    ]
                    for row in analysis["costs"]
                ],
            )
        )
        lines.append("")
        lines.append("### Route recommendation")
        lines.append("")
        recommendation = analysis["size_recommendation"]
        lines.append(
            f"Recommended route: "
            f"{analysis['recommended_route'] or 'none'}. Frozen-route statuses: "
            f"superiority {analysis['decision_superiority']['status']}, "
            f"parsimony {analysis['decision_parsimony']['status']}. Size "
            f"projection: n_clusters = {recommendation['n_clusters']} "
            f"(resolvable {recommendation['resolvable']}, "
            f"{recommendation['note']})."
        )
        lines.append("")
        lines.append(
            "Superiority reasons: "
            + "; ".join(analysis["decision_superiority"]["reasons"])
            + "."
        )
        lines.append("")
        lines.append(
            "Parsimony reasons: "
            + "; ".join(analysis["decision_parsimony"]["reasons"])
            + "."
        )
        lines.append("")
    lines.append("## Figures")
    lines.append("")
    for figure in figures:
        lines.append(f"`{figure}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "Static, translation, and matched-speed controls are computed only when "
        "the stage configuration enables them; they stay outside the three-class "
        "accuracy calculation. The eligible comparator set and the route are "
        "recommendations only and must be frozen in the route freeze record before "
        "confirmatory test seeds are opened."
    )
    lines.append("")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _environment_versions() -> dict:
    import importlib

    versions: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for name in (
        "numpy",
        "scipy",
        "sklearn",
        "pandas",
        "matplotlib",
        "yaml",
        "pyarrow",
        "gudhi",
        "joblib",
    ):
        try:
            module = importlib.import_module(name)
            versions[name] = getattr(module, "__version__", None)
        except (ImportError, AttributeError):
            versions[name] = None
    return versions


def _grid_payload(
    cfg: Mapping[str, Any], degrees: Sequence[int], stage: str
) -> dict:
    return {
        "stage": stage,
        "families": [str(family) for family in cfg["families"]],
        "classes": [str(label) for label in cfg["classes"]],
        "sigmas": [float(sigma) for sigma in cfg["sigmas"]],
        "strides": [int(stride) for stride in cfg["strides"]],
        "degrees": [int(degree) for degree in degrees],
        "representations": [str(rep) for rep in cfg["representations"]],
        "seed_namespaces": dict(cfg["seed_namespaces"]),
        "metric": str(cfg["metric"]),
    }


def _write_manifest(
    outdir: Path,
    stage: str,
    run_id: str,
    provenance: Mapping[str, Any],
    cfg: Mapping[str, Any],
    workers: int,
    wall_seconds: float,
    peak_ram_bytes: int,
    grid: Mapping[str, Any],
    extras: Mapping[str, Any],
) -> Path:
    payload = {
        "run_id": run_id,
        "stage": stage,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "versions": _environment_versions(),
        "workers": int(workers),
        "wall_seconds": float(wall_seconds),
        "peak_ram_bytes": int(peak_ram_bytes),
        "config_sha256": provenance.get("effective_sha256"),
        "config_source": provenance.get("source"),
        "config_path": provenance.get("path"),
        "config_file_sha256": provenance.get("file_sha256"),
        "cache_dir": str(cfg.get("cache_dir")),
        "grid": dict(grid),
    }
    payload.update(extras)
    return _write_json(Path(outdir) / "manifest.json", payload)


def _rows_frame(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=list(RESULT_COLUMNS))
    if not frame.empty:
        frame = frame.sort_values(
            [
                "degree",
                "family",
                "sigma",
                "stride",
                "representation",
                "split",
                "class",
                "base_seed",
            ],
            kind="stable",
        ).reset_index(drop=True)
    return frame


def _smoke_controls_summary(
    control_results: Sequence[Mapping[str, Any]], degree: int
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "static": {},
        "translation": {},
        "matched": {},
        "note": (
            "controls are reported outside the three-class accuracy calculation"
        ),
    }
    for result in control_results:
        key = f"{result['family']}|sigma{_sigma_tag(result['sigma'])}"
        diagnostics = result["diagnostics"].get(f"{degree}|1", {})
        distances = [float(value) for value in diagnostics.get("adjacent_distances", [])]
        if result["label"] == "static":
            summary["static"][key] = {
                "mean_adjacent_distance": (
                    float(np.mean(distances)) if distances else None
                ),
                "max_adjacent_distance": (
                    float(np.max(distances)) if distances else None
                ),
                "angle_valid_fraction": diagnostics.get("angle_valid_fraction"),
                "efficiency_valid": diagnostics.get("efficiency_valid"),
            }
        elif result["label"] == "translation":
            summary["translation"][key] = {
                "length": diagnostics.get("length"),
                "displacement": diagnostics.get("displacement"),
                "angle_valid_fraction": diagnostics.get("angle_valid_fraction"),
            }
        else:
            summary["matched"][f"{result['label']}|{key}"] = {
                "length": diagnostics.get("length"),
                "displacement": diagnostics.get("displacement"),
            }
    return summary


def _run_smoke(
    cfg: Mapping[str, Any],
    args: argparse.Namespace,
    outdir: Path,
    cache_dir: Path,
    run_id: str,
    provenance: Mapping[str, Any],
) -> int:
    workers = int(args.workers)
    seed = (
        int(args.seed)
        if args.seed is not None
        else int(cfg.get("smoke_seed", 11))
    )
    degrees = (
        [int(args.degree)]
        if args.degree is not None
        else [int(cfg["degrees"]["primary"])]
    )
    smoke_cfg = dict(cfg)
    smoke_cfg["strides"] = [1]
    smoke_cfg["smoke_seed"] = seed
    families = [str(family) for family in smoke_cfg["families"]]
    classes = [str(label) for label in smoke_cfg["classes"]]
    split_clusters = _split_clusters_from_seed(smoke_cfg, seed)
    split_clusters = _truncate_split_clusters(
        split_clusters, args.max_trajectories, len(families), len(classes)
    )
    floors, moment_scalings, calibration_metadata = _run_calibration(
        smoke_cfg, [seed], families, degrees, smoke_cfg["strides"], cache_dir, workers
    )
    started = time.perf_counter()
    pass_result = _run_degree_pass(
        smoke_cfg,
        degrees[0],
        split_clusters,
        "smoke",
        cache_dir,
        workers,
        floors,
        run_id,
        probe_first=True,
        moment_scalings=moment_scalings,
    )
    translation_jobs = [
        {
            "family": "A",
            "control": "translation",
            "base_seed": seed,
            "sigma": float(sigma),
            "degree": int(degrees[0]),
            "cache_dir": str(cache_dir),
            "metric": str(smoke_cfg["metric"]),
        }
        for sigma in smoke_cfg["sigmas"]
    ]
    translation_checks = _parallel_map(
        _translation_check_task, translation_jobs, workers
    )
    frame = _rows_frame(pass_result["rows"])
    table_path, table_format = _write_table(frame, outdir, "metrics")
    selection = _write_selection_table(pass_result["summaries"], outdir)
    preprocessing_path = _write_preprocessing(
        pass_result["preprocessing"], outdir / "preprocessing.npz"
    )
    split_manifest_path = _write_split_manifest(
        pass_result["split_manifest"], outdir
    )
    error_rows = frame[(frame["status"] == "ok") & (frame["split"] == "test")]
    test_table = cell_table(error_rows, split="test")
    figures = [
        figure
        for figure in (
            _figure_stride_curves(test_table, degrees[0], outdir / "figures"),
            _figure_confusion_compact(error_rows, degrees[0], outdir / "figures"),
        )
        if figure is not None
    ]
    calibration_path = _write_json(
        outdir / "calibration.json", calibration_metadata
    )
    representations = sorted(
        {str(summary["representation"]) for summary in pass_result["summaries"]}
    )
    wall_seconds = float(time.perf_counter() - started)
    summary = {
        "run_id": run_id,
        "stage": "smoke",
        "seed": seed,
        "degrees": [int(degree) for degree in degrees],
        "grid": _grid_payload(smoke_cfg, degrees, "smoke"),
        "n_trajectories": int(pass_result["n_trajectories"]),
        "n_rows": int(len(frame)),
        "n_ok_rows": int((frame["status"] == "ok").sum()),
        "n_control_rows": int((frame["status"] == "control").sum()),
        "test_equal_weight": {
            representation: equal_weight_cell_average(
                test_table, representation, "test"
            )
            for representation in representations
        },
        "test_cell_table": test_table.to_dict(orient="records"),
        "controls": _smoke_controls_summary(
            pass_result["controls"], degrees[0]
        ),
        "translation_check": translation_checks,
        "probe": pass_result["probe"],
        "calibration": calibration_metadata,
        "metrics_file": table_path.name,
        "table_format": table_format,
        "calibration_file": calibration_path.name,
        "selection_table_file": None if selection is None else selection[0].name,
        "preprocessing_file": (
            None if preprocessing_path is None else preprocessing_path.name
        ),
        "split_manifest_file": (
            None if split_manifest_path is None else split_manifest_path.name
        ),
        "figures": [str(figure) for figure in figures],
        "wall_seconds": wall_seconds,
        "peak_ram_bytes": _peak_ram_bytes(),
        "workers": workers,
        "notes": [
            "trajectory generation may be cached; timings record stored cold-cache costs when available",
            "train, validation, and test use seed 11 in the smoke stage, which checks construction and cost rather than comparative accuracy",
        ],
    }
    summary_path = _write_json(outdir / "summary.json", summary)
    _write_manifest(
        outdir,
        "smoke",
        run_id,
        provenance,
        smoke_cfg,
        workers,
        wall_seconds,
        _peak_ram_bytes(),
        summary["grid"],
        {
            "metrics_file": table_path.name,
            "table_format": table_format,
            "calibration_file": calibration_path.name,
            "selection_table_file": None if selection is None else selection[0].name,
            "preprocessing_file": (
                None if preprocessing_path is None else preprocessing_path.name
            ),
            "split_manifest_file": (
                None if split_manifest_path is None else split_manifest_path.name
            ),
            "figures": [str(figure) for figure in figures],
            "summary_file": summary_path.name,
            "n_trajectories": int(pass_result["n_trajectories"]),
            "n_rows": int(len(frame)),
        },
    )
    print(
        f"smoke stage complete: {len(frame)} rows, wall {wall_seconds:.1f} s, "
        f"outputs under {outdir}"
    )
    return 0


def _run_exploratory(
    cfg: Mapping[str, Any],
    args: argparse.Namespace,
    outdir: Path,
    cache_dir: Path,
    run_id: str,
    provenance: Mapping[str, Any],
) -> int:
    workers = int(args.workers)
    families = [str(family) for family in cfg["families"]]
    classes = [str(label) for label in cfg["classes"]]
    namespaces = cfg["seed_namespaces"]
    train_seeds = list(
        range(int(namespaces["train"][0]), int(namespaces["train"][1]) + 1)
    )
    if args.degree is not None:
        degrees = [int(args.degree)]
    else:
        degrees = [
            int(cfg["degrees"]["primary"]),
            int(cfg["degrees"]["secondary"]),
        ]
    split_clusters = _split_clusters_from_namespaces(cfg)
    split_clusters = _truncate_split_clusters(
        split_clusters, args.max_trajectories, len(families), len(classes)
    )
    degree_families = {
        int(key): [str(family) for family in value]
        for key, value in dict(cfg.get("degree_families", {})).items()
    }
    floors, moment_scalings, calibration_metadata = _run_calibration(
        cfg, train_seeds, families, degrees, cfg["strides"], cache_dir, workers
    )
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_summaries: list[dict[str, Any]] = []
    all_preprocessing: list[tuple[str, Mapping[str, Any]]] = []
    manifest_rows: list[dict[str, Any]] = []
    n_trajectories = 0
    for degree in degrees:
        pass_cfg = cfg
        if degree in degree_families:
            pass_cfg = dict(cfg)
            pass_cfg["families"] = degree_families[degree]
        pass_result = _run_degree_pass(
            pass_cfg,
            degree,
            split_clusters,
            "exploratory",
            cache_dir,
            workers,
            floors,
            run_id,
            probe_first=False,
            moment_scalings=moment_scalings,
        )
        n_trajectories += int(pass_result["n_trajectories"])
        all_rows.extend(pass_result["rows"])
        all_summaries.extend(pass_result["summaries"])
        all_preprocessing.extend(pass_result["preprocessing"])
        manifest_rows.extend(pass_result["split_manifest"])
    frame = _rows_frame(all_rows)
    table_path, table_format = _write_table(frame, outdir, "metrics")
    selection = _write_selection_table(all_summaries, outdir)
    preprocessing_path = _write_preprocessing(
        all_preprocessing, outdir / "preprocessing.npz"
    )
    split_manifest_path = _write_split_manifest(manifest_rows, outdir)
    _write_split_manifest(
        manifest_rows,
        REPO_ROOT / "research_review" / "results" / "g3" / "splits",
        "exploratory_split_manifest.csv",
    )
    analyses: list[dict[str, Any]] = []
    figures: list[Path] = []
    for degree in degrees:
        degree_summaries = [
            summary
            for summary in all_summaries
            if int(summary.get("degree", -1)) == int(degree)
        ]
        analysis = _analyse_pass(
            frame[frame["degree"] == int(degree)],
            degree_summaries,
            cfg,
            int(degree),
        )
        analyses.append(analysis)
        _write_json(outdir / f"analysis_degree{int(degree)}.json", analysis)
        degree_rows = frame[
            (frame["status"] == "ok") & (frame["degree"] == int(degree))
        ]
        test_table = cell_table(degree_rows, split="test")
        test_rows = degree_rows[degree_rows["split"] == "test"]
        for figure in (
            _figure_stride_curves(test_table, int(degree), outdir / "figures"),
            _figure_confusion_compact(
                test_rows, int(degree), outdir / "figures"
            ),
        ):
            if figure is not None:
                figures.append(figure)
    route_recommendations: dict[str, Any] = {}
    for analysis in analyses:
        degree = int(analysis.get("degree", -1))
        route_recommendations[str(degree)] = {
            "recommended_route": analysis.get("recommended_route"),
            "superiority_status": analysis.get("decision_superiority", {}).get(
                "status"
            ),
            "parsimony_status": analysis.get("decision_parsimony", {}).get(
                "status"
            ),
            "size_recommendation": analysis.get("size_recommendation"),
            "incumbent": analysis.get("incumbent"),
            "eligible_comparators": analysis.get("eligible_comparators"),
            "parsimony_ratio": analysis.get("parsimony", {}).get(
                "parsimony_ratio"
            ),
        }
    primary_degree = int(cfg["degrees"]["primary"])
    primary = next(
        (
            analysis
            for analysis in analyses
            if int(analysis.get("degree", -1)) == primary_degree
        ),
        analyses[0] if analyses else None,
    )
    suggested_confirmatory = None
    if primary is not None and primary.get("status") == "ok":
        suggested_confirmatory = {
            "n_clusters": int(primary["size_recommendation"]["n_clusters"]),
            "route": primary["recommended_route"] or "superiority",
            "incumbent": primary["incumbent"],
            "eligible_comparators": primary["eligible_comparators"],
            "shard_index": 0,
            "n_shards": 1,
        }
    recommendation_payload = {
        "run_id": run_id,
        "degrees": [int(analysis.get("degree", -1)) for analysis in analyses],
        "per_degree": route_recommendations,
        "suggested_confirmatory_block": suggested_confirmatory,
        "note": (
            "recommendation only; freeze the route, incumbent, eligible comparator "
            "set, and test size in the route freeze record before opening "
            "confirmatory seeds"
        ),
    }
    recommendation_path = _write_json(
        outdir / "route_recommendation.json", recommendation_payload
    )
    calibration_path = _write_json(
        outdir / "calibration.json", calibration_metadata
    )
    wall_seconds = float(time.perf_counter() - started)
    peak_ram = _peak_ram_bytes()
    report_path = _write_exploratory_report(
        outdir / "exploratory_report.md",
        cfg,
        analyses,
        calibration_metadata,
        provenance,
        run_id,
        figures,
        int(len(frame)),
        wall_seconds,
        peak_ram,
    )
    summary = {
        "run_id": run_id,
        "stage": "exploratory",
        "degrees": [int(degree) for degree in degrees],
        "grid": _grid_payload(cfg, degrees, "exploratory"),
        "n_rows": int(len(frame)),
        "n_ok_rows": int((frame["status"] == "ok").sum()),
        "n_control_rows": int((frame["status"] == "control").sum()),
        "n_trajectory_jobs": int(n_trajectories),
        "n_master_trajectories_per_degree": (
            int(n_trajectories // len(degrees)) if degrees else 0
        ),
        "analyses": analyses,
        "recommendation": recommendation_payload,
        "calibration": calibration_metadata,
        "metrics_file": table_path.name,
        "table_format": table_format,
        "calibration_file": calibration_path.name,
        "selection_table_file": None if selection is None else selection[0].name,
        "preprocessing_file": (
            None if preprocessing_path is None else preprocessing_path.name
        ),
        "split_manifest_file": (
            None if split_manifest_path is None else split_manifest_path.name
        ),
        "report_file": report_path.name,
        "recommendation_file": recommendation_path.name,
        "figures": [str(figure) for figure in figures],
        "wall_seconds": wall_seconds,
        "peak_ram_bytes": peak_ram,
        "workers": workers,
        "notes": [
            "degree H0 is the primary channel; H1 is a predeclared secondary channel reported separately",
            "the eligible comparator set and route are recommendations until the route freeze record is written",
        ],
    }
    summary_path = _write_json(outdir / "summary.json", summary)
    _write_manifest(
        outdir,
        "exploratory",
        run_id,
        provenance,
        cfg,
        workers,
        wall_seconds,
        peak_ram,
        summary["grid"],
        {
            "metrics_file": table_path.name,
            "table_format": table_format,
            "calibration_file": calibration_path.name,
            "selection_table_file": None
            if selection is None
            else selection[0].name,
            "preprocessing_file": (
                None if preprocessing_path is None else preprocessing_path.name
            ),
            "split_manifest_file": (
                None if split_manifest_path is None else split_manifest_path.name
            ),
            "report_file": report_path.name,
            "recommendation_file": recommendation_path.name,
            "figures": [str(figure) for figure in figures],
            "summary_file": summary_path.name,
            "n_rows": int(len(frame)),
        },
    )
    print(
        f"exploratory stage complete: {len(frame)} rows, wall {wall_seconds:.1f} s, "
        f"recommendation {route_recommendations}, outputs under {outdir}"
    )
    return 0


def _run_confirmatory(
    cfg: Mapping[str, Any],
    args: argparse.Namespace,
    outdir: Path,
    cache_dir: Path,
    run_id: str,
    provenance: Mapping[str, Any],
) -> int:
    workers = int(args.workers)
    conf = dict(cfg.get("confirmatory", {}))
    if conf.get("n_clusters") is None:
        raise SystemExit(
            "confirmatory.n_clusters is required and must be one of "
            f"{CONFIRMATORY_SIZES} base-seed clusters"
        )
    n_clusters = int(conf["n_clusters"])
    route = str(conf.get("route", "superiority"))
    if route not in ("superiority", "parsimony"):
        raise SystemExit(
            f"confirmatory.route must be 'superiority' or 'parsimony'; got {route!r}"
        )
    incumbent = str(conf.get("incumbent", "complete_distances"))
    eligible_config = conf.get("eligible_comparators")
    shard_index = int(conf.get("shard_index", 0))
    n_shards = int(conf.get("n_shards", 1))
    if n_shards < 1 or shard_index < 0 or shard_index >= n_shards:
        raise SystemExit(
            f"invalid shard {shard_index} of {n_shards}; require 0 <= shard_index < n_shards"
        )
    families = [str(family) for family in cfg["families"]]
    classes = [str(label) for label in cfg["classes"]]
    start = int(cfg["seed_namespaces"]["test_confirmatory_start"])
    clusters = _confirmatory_clusters(n_clusters, families, classes, start)
    shard = [
        cluster for index, cluster in enumerate(clusters) if index % n_shards == shard_index
    ]
    if not shard:
        raise SystemExit(
            f"confirmatory shard {shard_index} of {n_shards} is empty for "
            f"{n_clusters} clusters"
        )
    if args.max_trajectories is not None:
        shard = shard[: int(args.max_trajectories)]
    base_splits = _split_clusters_from_namespaces(cfg, splits=("train", "validation"))
    split_clusters = {
        "train": base_splits["train"],
        "validation": base_splits["validation"],
        "test": shard,
    }
    degrees = (
        [int(args.degree)]
        if args.degree is not None
        else [int(cfg["degrees"]["primary"])]
    )
    train_seeds = list(
        range(
            int(cfg["seed_namespaces"]["train"][0]),
            int(cfg["seed_namespaces"]["train"][1]) + 1,
        )
    )
    floors, moment_scalings, calibration_metadata = _run_calibration(
        cfg, train_seeds, families, degrees, cfg["strides"], cache_dir, workers
    )
    started = time.perf_counter()
    pass_result = _run_degree_pass(
        cfg,
        degrees[0],
        split_clusters,
        "confirmatory",
        cache_dir,
        workers,
        floors,
        run_id,
        probe_first=False,
        moment_scalings=moment_scalings,
    )
    frame = _rows_frame(pass_result["rows"])
    table_path, table_format = _write_table(frame, outdir, "metrics")
    selection = _write_selection_table(pass_result["summaries"], outdir)
    preprocessing_path = _write_preprocessing(
        pass_result["preprocessing"], outdir / "preprocessing.npz"
    )
    split_manifest_path = _write_split_manifest(
        pass_result["split_manifest"], outdir
    )
    analysis = _analyse_pass(
        frame[frame["degree"] == int(degrees[0])],
        [
            summary
            for summary in pass_result["summaries"]
            if int(summary.get("degree", -1)) == int(degrees[0])
        ],
        cfg,
        int(degrees[0]),
        incumbent_name=incumbent,
        eligible_names=(
            [str(name) for name in eligible_config]
            if eligible_config
            else None
        ),
    )
    decision_source = (
        analysis["decision_superiority"]
        if route == "superiority"
        else analysis["decision_parsimony"]
    )
    decision_payload = {
        "run_id": run_id,
        "stage": "confirmatory",
        "route": route,
        "incumbent": incumbent,
        "n_clusters": n_clusters,
        "shard_index": shard_index,
        "n_shards": n_shards,
        "status": decision_source["status"],
        "reasons": decision_source["reasons"],
        "checks": decision_source["checks"],
        "delta": analysis["delta"],
        "family_bounds": analysis["family_bounds"],
        "parsimony": analysis["parsimony"],
        "decision": decision_source,
        "analysis_file": f"analysis_degree{int(degrees[0])}.json",
    }
    _write_json(outdir / f"analysis_degree{int(degrees[0])}.json", analysis)
    decision_path = None
    if n_shards == 1:
        decision_path = _write_json(outdir / "decision.json", decision_payload)
    degree_rows = frame[
        (frame["status"] == "ok") & (frame["degree"] == int(degrees[0]))
    ]
    test_table = cell_table(degree_rows, split="test")
    test_rows = degree_rows[degree_rows["split"] == "test"]
    figures = [
        figure
        for figure in (
            _figure_stride_curves(
                test_table, int(degrees[0]), outdir / "figures"
            ),
            _figure_confusion_compact(
                test_rows, int(degrees[0]), outdir / "figures"
            ),
        )
        if figure is not None
    ]
    calibration_path = _write_json(
        outdir / "calibration.json", calibration_metadata
    )
    wall_seconds = float(time.perf_counter() - started)
    peak_ram = _peak_ram_bytes()
    summary = {
        "run_id": run_id,
        "stage": "confirmatory",
        "route": route,
        "incumbent": incumbent,
        "n_clusters": n_clusters,
        "shard_index": shard_index,
        "n_shards": n_shards,
        "shard_clusters": len(shard),
        "degrees": [int(degree) for degree in degrees],
        "grid": _grid_payload(cfg, degrees, "confirmatory"),
        "n_rows": int(len(frame)),
        "n_ok_rows": int((frame["status"] == "ok").sum()),
        "n_control_rows": int((frame["status"] == "control").sum()),
        "analysis": analysis,
        "decision": decision_payload,
        "calibration": calibration_metadata,
        "metrics_file": table_path.name,
        "table_format": table_format,
        "calibration_file": calibration_path.name,
        "selection_table_file": None if selection is None else selection[0].name,
        "preprocessing_file": (
            None if preprocessing_path is None else preprocessing_path.name
        ),
        "split_manifest_file": (
            None if split_manifest_path is None else split_manifest_path.name
        ),
        "decision_file": None if decision_path is None else decision_path.name,
        "figures": [str(figure) for figure in figures],
        "wall_seconds": wall_seconds,
        "peak_ram_bytes": peak_ram,
        "workers": workers,
        "notes": [
            "test clusters are (family, class, base_seed) triples ordered by (family, class, base_seed)",
            "the decision is written only when n_shards equals 1; sharded runs are aggregated after all shards complete",
        ],
    }
    summary_path = _write_json(outdir / "summary.json", summary)
    _write_manifest(
        outdir,
        "confirmatory",
        run_id,
        provenance,
        cfg,
        workers,
        wall_seconds,
        peak_ram,
        summary["grid"],
        {
            "metrics_file": table_path.name,
            "table_format": table_format,
            "calibration_file": calibration_path.name,
            "selection_table_file": None
            if selection is None
            else selection[0].name,
            "preprocessing_file": (
                None if preprocessing_path is None else preprocessing_path.name
            ),
            "split_manifest_file": (
                None if split_manifest_path is None else split_manifest_path.name
            ),
            "decision_file": None if decision_path is None else decision_path.name,
            "figures": [str(figure) for figure in figures],
            "summary_file": summary_path.name,
            "n_rows": int(len(frame)),
            "shard_index": shard_index,
            "n_shards": n_shards,
        },
    )
    print(
        f"confirmatory stage complete: shard {shard_index} of {n_shards}, "
        f"status {decision_payload['status']}, wall {wall_seconds:.1f} s, "
        f"outputs under {outdir}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run the requested stage."""
    import traceback

    parser = build_parser()
    args = parser.parse_args(argv)
    if int(args.workers) < 1:
        parser.error("--workers must be at least 1")
    if args.max_trajectories is not None and int(args.max_trajectories) < 1:
        parser.error("--max-trajectories must be at least 1")
    cfg, provenance = load_config(args.config)
    stage_defaults = {
        "smoke": Path("research_review") / "results" / "phase1" / "smoke",
        "exploratory": Path("research_review") / "results" / "g3" / "exploratory",
        "confirmatory": Path("research_review") / "results" / "g3" / "confirmatory",
    }
    if args.outdir is not None:
        outdir = Path(args.outdir).resolve()
    else:
        outdir = (REPO_ROOT / stage_defaults[args.stage]).resolve()
    run_id = f"{args.stage}-{str(provenance.get('effective_sha256', ''))[:12]}"
    if args.stage == "confirmatory":
        n_shards = int(cfg.get("confirmatory", {}).get("n_shards", 1))
        shard_index = int(cfg.get("confirmatory", {}).get("shard_index", 0))
        if n_shards > 1:
            run_id = f"{run_id}-shard{shard_index:02d}of{n_shards:02d}"
            if args.outdir is None:
                outdir = outdir / f"shard_{shard_index:02d}_of_{n_shards:02d}"
    outdir.mkdir(parents=True, exist_ok=True)
    cache_dir = _resolve_path(
        cfg.get("cache_dir", "research_review/results/cache"), REPO_ROOT
    )
    _write_json(
        outdir / "config_effective.json",
        {"run_id": run_id, "config": cfg, "provenance": provenance},
    )
    try:
        if args.stage == "smoke":
            return _run_smoke(cfg, args, outdir, cache_dir, run_id, provenance)
        if args.stage == "exploratory":
            return _run_exploratory(
                cfg, args, outdir, cache_dir, run_id, provenance
            )
        return _run_confirmatory(cfg, args, outdir, cache_dir, run_id, provenance)
    except Exception as exc:
        _write_json(
            outdir / "failure.json",
            {
                "run_id": run_id,
                "stage": args.stage,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
