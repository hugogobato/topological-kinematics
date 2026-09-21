#!/usr/bin/env python3
"""WP-3.3 null, baseline-favorable, and stress controls.

This script implements the WP-3.3 falsification controls for the Topological
Kinematics pilot. Every quantity is computed with the frozen package modules
``tk_pilot.generators``, ``tk_pilot.persistence``, ``tk_pilot.path_diagnostics``,
``tk_pilot.diagram_metrics``, and the frozen compact-vector helper in
``tk_pilot.features``. The package modules are imported, never modified, and the
runner distance caches under ``research_review/results/cache/`` are never read
or written; all diagrams and distances produced here live in a private cache
directory requested on the command line.

Controls:

1. Constant-diagram null. Static ``z = 0.5`` trajectories for both families and
   ``sigma in {0, 0.05}``. At ``sigma = 0`` every adjacent distance must be
   exactly zero and every compact diagnostic must be degenerate (``L = 0``,
   ``eta`` undefined, comparison angles and triangle excess unresolved). At
   ``sigma = 0.05`` the adjacent-distance distribution and the exceedance count
   at the 95th percentile of a disjoint training static calibration are
   reported, together with trend and runs diagnostics.
2. Equal-speed ordering control. ``matched_forward`` versus ``matched_folded``
   for Family A with seeds 1000 to 1019 and both sigmas, plus an auxiliary
   Family B construction at ``sigma = 0``. Consecutive ``|dz|`` steps and
   endpoints are identical by construction; speed, ``L``, ``R``, and ``eta``
   agreement is reported, and the comparison-angle and triangle-shape
   separation is counted. This control stays outside the three-class accuracy
   calculation.
3. Time reparameterization. Ramp trajectories under ``u**1.5`` and a
   piecewise-linear warp with one fast and one slow segment. The same master
   states under warped timestamps test the local-derivative speed law exactly;
   resampled states test that ``L`` and ``R`` change only through the sampled
   sequence and that comparison angles are invariant when the same intermediate
   states are visited.
4. Raw-label-preserving transformations. A constant rigid translation and a
   fixed global rotation of an identical Family A realization. The translation
   must leave the Vietoris-Rips diagrams unchanged within
   ``1e-7 * max(1, filtration range)``; the rotation is reported against the
   same declared bound, and the observed maxima and diagnostic changes are
   reported for both degrees.
5. Very coarse sampling. Strides 8 and 16 on return, ramp, and jump
   trajectories, with compact diagnostics, efficiency coverage, angle validity,
   and a no-tuning nearest-centroid sanity check of three-class separation.
6. Adversarial full-matrix-sufficient case. A constant-diagram null with one
   injected raw realization at a single frame, at a large primary shift and at
   a near-floor shift. The full distance matrix and the compact summaries are
   both scored, their attribution, localization behaviour, and feature cost are
   reported honestly, and the construction is labeled adversarial.

Usage:
    python3 scripts/run_wp33_nulls.py \
        --out research_review/results/g3/nulls \
        --report research_review/results/g3/reports/wp33_nulls_report.md \
        --cache /tmp/opencode/wp33_cache \
        --budget-seconds 2700

The script uses a single worker process. Every table is written as CSV or JSON,
every figure as PNG, and a SHA256SUMS file covers the produced artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gudhi  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import scipy  # noqa: E402
import sklearn  # noqa: E402
from scipy import stats  # noqa: E402

from tk_pilot import generators  # noqa: E402
from tk_pilot.diagram_metrics import bottleneck_linf  # noqa: E402
from tk_pilot.features import _compact_vector  # noqa: E402
from tk_pilot.path_diagnostics import (  # noqa: E402
    compute_path_diagnostics,
    noise_floor,
)
from tk_pilot.persistence import trajectory_diagrams  # noqa: E402

WORK_PACKAGE = "WP-3.3"
DEGREE = 0
SECONDARY_DEGREE = 1
FAMILIES = ("A", "B")
SIGMAS = (0.0, 0.05)
SEEDS_CAL = tuple(range(1000, 1005))
SEEDS_EVAL = tuple(range(1005, 1020))
SEEDS_MATCHED = tuple(range(1000, 1020))
SEEDS_AUX = tuple(range(1000, 1005))
SEEDS_REPARAM = tuple(range(1000, 1010))
SEEDS_RAW = tuple(range(1000, 1005))
SEEDS_COARSE_TRAIN = tuple(range(1000, 1005))
SEEDS_COARSE_TEST = tuple(range(1005, 1015))
SEEDS_ADVERSARIAL = tuple(range(1000, 1005))
COARSE_STRIDES = (8, 16)
ADVERSARIAL_STRIDE = 8
INJECTION_INDEX = 8
INJECTION_Z_PRIMARY = 3.0
INJECTION_Z_NEAR_FLOOR = 1.5
INJECTION_Z_VALUES = (INJECTION_Z_PRIMARY, INJECTION_Z_NEAR_FLOOR)
WARP_KINK = 0.25
WARP_DERIVATIVE_MIN_U = 0.1
DERIVATIVE_REL_TOL = 0.05
ANGLE_SEPARATION_TOL = 1e-6
MATCHED_TOL = 1e-9
FIGURE_DPI = 140
CONTROL_KEYS = (
    "static_null",
    "matched_ordering",
    "time_reparam",
    "raw_preserving",
    "coarse_sampling",
    "adversarial_matrix",
)
INPUT_FILES = (
    "research_review/Topological_Kinematics_Research_Plan.md",
    "research_review/Pilot_Experiment_Specification.md",
    "research_review/results/phase1/implementation_contract.md",
    "research_review/results/g2/reports/raw_correctness_report.md",
    "src/tk_pilot/generators.py",
    "src/tk_pilot/persistence.py",
    "src/tk_pilot/features.py",
    "src/tk_pilot/path_diagnostics.py",
    "src/tk_pilot/diagram_metrics.py",
)


class BudgetExceeded(Exception):
    """Raised when the declared wall-clock budget is exhausted."""


def sigma_tag(sigma: float) -> int:
    return int(round(float(sigma) * 1000.0))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(array) -> str:
    return sha256_bytes(np.ascontiguousarray(array).tobytes())


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return repr(float(value))
    return str(value)


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    return value


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, fieldnames, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(fieldnames))
        for row in rows:
            writer.writerow([fmt(row.get(name)) for name in fieldnames])


def finite(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def nanmax_or_nan(values) -> float:
    array = finite(values)
    return float(array.max()) if array.size else float("nan")


def nanmean_or_nan(values) -> float:
    array = finite(values)
    return float(array.mean()) if array.size else float("nan")


def nanmedian_or_nan(values) -> float:
    array = finite(values)
    return float(np.median(array)) if array.size else float("nan")


def max_run_length(binary) -> int:
    best = 0
    current = 0
    for flag in np.asarray(binary, dtype=bool):
        if flag:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return int(best)


def arrays_equal_nan(first, second) -> bool:
    """Exact equality with NaN treated as equal to NaN."""
    left = np.asarray(first, dtype=np.float64)
    right = np.asarray(second, dtype=np.float64)
    if left.shape != right.shape:
        return False
    return bool(
        np.all((left == right) | (np.isnan(left) & np.isnan(right)))
    )


def runs_test(binary) -> tuple[float, float, int]:
    flags = np.asarray(binary, dtype=bool)
    n_one = int(flags.sum())
    n_zero = int(flags.size - n_one)
    if n_one == 0 or n_zero == 0:
        return float("nan"), float("nan"), 0
    runs = 1 + int(np.count_nonzero(flags[1:] != flags[:-1]))
    total = n_one + n_zero
    expected = 1.0 + 2.0 * n_one * n_zero / total
    variance = (
        2.0
        * n_one
        * n_zero
        * (2.0 * n_one * n_zero - total)
        / (total * total * (total - 1.0))
    )
    if variance <= 0.0:
        return float("nan"), float("nan"), runs
    z_value = (runs - expected) / math.sqrt(variance)
    p_value = float(2.0 * stats.norm.sf(abs(z_value)))
    return float(z_value), p_value, runs


def exceedance_cluster_pvalue(
    flags, n_resamples: int = 2000, seed: int = 20260907
) -> float:
    """G2-verified permutation p-value for temporal clustering of exceedances.

    The observed longest run of exceedances is compared with the distribution of
    the longest run under random permutations of the same indicator vector, so
    the marginal exceedance rate is held fixed. This is the statistic used by
    the verified WP-3.1 ladder and is robust to the dependence induced by
    overlapping adjacent windows, unlike an independence-based runs test.
    """
    vector = np.asarray(flags, dtype=bool)
    if vector.size == 0:
        return 1.0
    observed = max_run_length(vector)
    if observed <= 1:
        return 1.0
    rng = np.random.default_rng(int(seed))
    exceedances = int(np.count_nonzero(vector))
    total = 0
    for _ in range(int(n_resamples)):
        permuted = np.zeros(vector.size, dtype=bool)
        permuted[rng.choice(vector.size, size=exceedances, replace=False)] = True
        if max_run_length(permuted) >= observed:
            total += 1
    return float(total + 1) / float(int(n_resamples) + 1)


class DiagramCache:
    """Private diagram cache keyed by family and exact frame content.

    Frames that are bitwise identical inside a workload are computed once and
    reused, which matters for the constant-diagram null at ``sigma = 0``.
    """

    def __init__(self, cache_dir: Path):
        self.root = Path(cache_dir) / "diagrams"
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory: dict[str, dict[int, list[np.ndarray]]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, family: str, frames, degrees=(DEGREE,)):
        array = np.ascontiguousarray(np.asarray(frames, dtype=np.float64))
        content = array_sha256(array)
        degrees_key = "".join(str(int(degree)) for degree in degrees)
        key = f"{family}_{content[:20]}_d{degrees_key}_g{gudhi.__version__}"
        if key in self.memory:
            self.hits += 1
            return self.memory[key]
        path = self.root / f"{key}.npz"
        if path.is_file():
            with np.load(path) as stored:
                n_frames = int(stored["n_frames"])
                result = {
                    int(degree): [
                        np.asarray(
                            stored[f"d{int(degree)}_{index:03d}"], dtype=np.float64
                        )
                        for index in range(n_frames)
                    ]
                    for degree in degrees
                }
            self.memory[key] = result
            self.hits += 1
            return result
        unique_index: dict[str, int] = {}
        representatives: list[int] = []
        frame_map: list[int] = []
        for index, frame in enumerate(array):
            frame_key = sha256_bytes(np.ascontiguousarray(frame).tobytes())
            if frame_key not in unique_index:
                unique_index[frame_key] = len(representatives)
                representatives.append(index)
            frame_map.append(unique_index[frame_key])
        unique_frames = np.ascontiguousarray(array[representatives])
        unique_diagrams = trajectory_diagrams(unique_frames, family, degrees=degrees)
        result = {
            int(degree): [
                unique_diagrams[int(degree)][frame_map[index]]
                for index in range(array.shape[0])
            ]
            for degree in degrees
        }
        payload = {"n_frames": np.asarray(array.shape[0], dtype=np.int64)}
        for degree in degrees:
            for index, diagram in enumerate(result[int(degree)]):
                payload[f"d{int(degree)}_{index:03d}"] = diagram
        np.savez(path, **payload)
        self.memory[key] = result
        self.misses += 1
        return result


class PairCache:
    """Private pair-distance cache for one workload, degree, and variant."""

    def __init__(self, cache_dir: Path, name: str):
        self.path = Path(cache_dir) / "pairs" / f"{name}.npz"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.values: dict[tuple[int, int], float] = {}
        self.dirty = 0
        if self.path.is_file():
            with np.load(self.path) as stored:
                pairs = np.asarray(stored["pairs"], dtype=np.int64)
                values = np.asarray(stored["values"], dtype=np.float64)
            for (i, j), value in zip(pairs, values):
                self.values[(int(i), int(j))] = float(value)

    def get(self, i: int, j: int, diagrams, metric=bottleneck_linf) -> float:
        if i == j:
            return 0.0
        if i > j:
            i, j = j, i
        key = (int(i), int(j))
        if key in self.values:
            return self.values[key]
        value = float(metric(diagrams[i], diagrams[j]))
        self.values[key] = value
        self.dirty += 1
        if self.dirty >= 256:
            self.save()
        return value

    def save(self) -> None:
        if not self.dirty:
            return
        pairs = np.asarray(sorted(self.values), dtype=np.int64)
        values = np.asarray(
            [self.values[tuple(pair)] for pair in pairs], dtype=np.float64
        )
        np.savez(self.path, pairs=pairs, values=values)
        self.dirty = 0

    def metric(self, diagrams, metric=bottleneck_linf):
        index_of = {id(diagram): index for index, diagram in enumerate(diagrams)}

        def wrapped(first, second):
            i = index_of.get(id(first))
            j = index_of.get(id(second))
            if i is None or j is None:
                return float(metric(first, second))
            return self.get(i, j, diagrams, metric)

        return wrapped


class RunContext:
    def __init__(self, out_dir: Path, cache_dir: Path, budget_seconds: float):
        self.out_dir = Path(out_dir)
        self.cache_dir = Path(cache_dir)
        self.budget_seconds = float(budget_seconds)
        self.start = time.perf_counter()
        self.started_utc = utc_now()
        self.diagram_cache = DiagramCache(self.cache_dir)
        self.pair_caches: dict[str, PairCache] = {}
        self.log_lines: list[str] = []
        self.timings: dict[str, float] = {}
        self.verdicts: dict[str, dict] = {}
        self.notes: list[str] = []
        self.skipped: list[str] = []
        self.floors: dict[tuple[str, float], float] = {}
        self.figures: list[str] = []
        self.tables: list[str] = []
        log_path = self.out_dir / "run_log.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = open(log_path, "w", encoding="utf-8")

    def elapsed(self) -> float:
        return float(time.perf_counter() - self.start)

    def log(self, message: str) -> None:
        line = f"[{self.elapsed():8.1f}s] {message}"
        print(line, flush=True)
        self.log_lines.append(line)
        self.log_handle.write(line + "\n")
        self.log_handle.flush()

    def check_budget(self) -> None:
        if self.elapsed() > self.budget_seconds:
            raise BudgetExceeded(
                f"wall-clock budget {self.budget_seconds:.0f}s exceeded at "
                f"{self.elapsed():.1f}s"
            )

    def pair_cache(self, name: str) -> PairCache:
        if name not in self.pair_caches:
            self.pair_caches[name] = PairCache(self.cache_dir, name)
        return self.pair_caches[name]

    def save_pairs(self) -> None:
        for cache in self.pair_caches.values():
            cache.save()

    def register_table(self, path: Path) -> None:
        self.tables.append(str(path.relative_to(self.out_dir)))

    def register_figure(self, path: Path) -> None:
        self.figures.append(str(path.relative_to(self.out_dir)))

    def close(self) -> None:
        self.save_pairs()
        self.log_handle.close()


def family_a_points_at_z(latent: dict, z_values) -> np.ndarray:
    """Frozen Family A raw point cloud for arbitrary separations."""
    z = np.atleast_1d(np.asarray(z_values, dtype=np.float64))
    phases = latent["phases"]
    theta = np.concatenate(
        [
            generators.CIRCLE_ANGLES + float(phases[0]),
            generators.CIRCLE_ANGLES + float(phases[1]),
        ]
    )
    radius = float(latent["r"])
    base = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
    signs = np.concatenate(
        [
            -np.ones(generators.POINTS_PER_CIRCLE),
            np.ones(generators.POINTS_PER_CIRCLE),
        ]
    )
    offsets = np.column_stack([0.5 * z, np.zeros_like(z)])
    points = base[None, :, :] + signs[None, :, None] * offsets[:, None, :]
    phi = float(latent["phi"])
    rotation = np.array(
        [[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]], dtype=np.float64
    )
    return np.ascontiguousarray(points @ rotation.T, dtype=np.float64)


def family_b_fields_at_z(latent: dict, z_values) -> np.ndarray:
    """Frozen Family B scalar field for arbitrary separations."""
    z = np.atleast_1d(np.asarray(z_values, dtype=np.float64))
    axis = np.linspace(
        -generators.FAMILY_B_EXTENT,
        generators.FAMILY_B_EXTENT,
        generators.FAMILY_B_SIDE,
        dtype=np.float64,
    )
    grid_x, grid_y = np.meshgrid(axis, axis)
    half = 0.5 * z[:, None, None]
    width = 2.0 * float(latent["w"]) ** 2
    left = float(latent["A1"]) * np.exp(
        -(((grid_x[None, :, :] + half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    right = float(latent["A2"]) * np.exp(
        -(((grid_x[None, :, :] - half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    return np.ascontiguousarray(left + right, dtype=np.float64)


def raw_frames_at_z(family: str, latent: dict, z_values) -> np.ndarray:
    if family == "A":
        return family_a_points_at_z(latent, z_values)
    return family_b_fields_at_z(latent, z_values)


def custom_trajectory(base, label: str, frames, z, timestamps=None):
    return generators.Trajectory(
        trajectory_id=f"{base.trajectory_id}_{label}",
        family=base.family,
        label=base.label,
        base_seed=base.base_seed,
        sigma=base.sigma,
        stride=base.stride,
        timestamps=np.ascontiguousarray(
            base.timestamps if timestamps is None else timestamps, dtype=np.float64
        ),
        frames=np.ascontiguousarray(frames, dtype=np.float64),
        z=np.ascontiguousarray(z, dtype=np.float64),
        latent=dict(base.latent),
    )


def workload_name(family: str, label: str, seed: int, sigma: float, stride: int) -> str:
    return f"{family}_{label}_{int(seed)}_s{sigma_tag(sigma)}_str{int(stride)}"


def validate_evaluators(ctx: RunContext) -> dict:
    report: dict[str, float] = {}
    for family in FAMILIES:
        trajectory = generators.build_control("static", family, 1000, 0.0, 1)
        reproduced = raw_frames_at_z(family, trajectory.latent, trajectory.z)
        report[f"{family}_max_abs_frame_error"] = float(
            np.max(np.abs(reproduced - trajectory.frames))
        )
    ctx.log(f"evaluator validation: {report}")
    return report


def control1_static_null(ctx: RunContext) -> dict:
    ctx.log("control1 static null: start")
    rows: list[dict] = []
    distance_rows: list[dict] = []
    summary_rows: list[dict] = []
    assertions: dict[str, dict] = {}
    pooled_plot: dict[tuple[str, float], np.ndarray] = {}
    for family in FAMILIES:
        for sigma in SIGMAS:
            cal_adjacent: list[np.ndarray] = []
            for seed in SEEDS_CAL:
                ctx.check_budget()
                trajectory = generators.build_control("static", family, seed, sigma, 1)
                diagrams = ctx.diagram_cache.get(
                    family, trajectory.frames, (DEGREE, SECONDARY_DEGREE)
                )
                name = workload_name(family, "static", seed, sigma, 1)
                pairs = ctx.pair_cache(f"{name}_cal_d0")
                diagnostics = compute_path_diagnostics(
                    diagrams[DEGREE],
                    trajectory.timestamps,
                    pairs.metric(diagrams[DEGREE]),
                )
                cal_adjacent.append(np.asarray(diagnostics.adjacent_distances))
                for index, value in enumerate(diagnostics.adjacent_distances):
                    distance_rows.append(
                        {
                            "family": family,
                            "sigma": sigma,
                            "role": "calibration",
                            "seed": seed,
                            "interval_index": index,
                            "distance": float(value),
                        }
                    )
                rows.append(
                    {
                        "family": family,
                        "sigma": sigma,
                        "role": "calibration",
                        "seed": seed,
                        "n_frames": trajectory.frames.shape[0],
                        "degree": DEGREE,
                        "L": diagnostics.length,
                        "R": diagnostics.displacement,
                        "eta": diagnostics.efficiency,
                        "angle_valid_fraction": diagnostics.angle_valid_fraction,
                        "adjacent_mean": float(np.mean(diagnostics.adjacent_distances)),
                        "adjacent_p95": float(
                            np.percentile(diagnostics.adjacent_distances, 95.0)
                        ),
                        "adjacent_max": float(np.max(diagnostics.adjacent_distances)),
                        "n_above_e95": None,
                        "spearman_rho": None,
                        "spearman_p": None,
                        "runs_z": None,
                        "runs_p": None,
                        "cluster_p": None,
                        "max_run": None,
                        "h1_card_mean": float(
                            np.mean([d.shape[0] for d in diagrams[SECONDARY_DEGREE]])
                        ),
                    }
                )
                pairs.save()
            e95 = noise_floor(np.concatenate(cal_adjacent), 95.0)
            ctx.floors[(family, sigma)] = float(e95)
            eval_above: list[np.ndarray] = []
            eval_trend_p: list[float] = []
            eval_trend_rho: list[float] = []
            eval_runs_p: list[float] = []
            eval_cluster_p: list[float] = []
            pooled = np.concatenate(cal_adjacent)
            for seed in SEEDS_EVAL:
                ctx.check_budget()
                trajectory = generators.build_control("static", family, seed, sigma, 1)
                diagrams = ctx.diagram_cache.get(
                    family, trajectory.frames, (DEGREE, SECONDARY_DEGREE)
                )
                name = workload_name(family, "static", seed, sigma, 1)
                pairs = ctx.pair_cache(f"{name}_eval_d0")
                diagnostics = compute_path_diagnostics(
                    diagrams[DEGREE],
                    trajectory.timestamps,
                    pairs.metric(diagrams[DEGREE]),
                )
                distances = np.asarray(diagnostics.adjacent_distances)
                above = distances > e95
                eval_above.append(above)
                for index, value in enumerate(distances):
                    distance_rows.append(
                        {
                            "family": family,
                            "sigma": sigma,
                            "role": "evaluation",
                            "seed": seed,
                            "interval_index": index,
                            "distance": float(value),
                        }
                    )
                indices = np.arange(distances.size, dtype=np.float64)
                rho, p_value = stats.spearmanr(indices, distances)
                runs_z, runs_p, _ = runs_test(above)
                cluster_p = exceedance_cluster_pvalue(above)
                eval_trend_p.append(float(p_value))
                eval_trend_rho.append(float(rho))
                eval_runs_p.append(float(runs_p))
                eval_cluster_p.append(float(cluster_p))
                rows.append(
                    {
                        "family": family,
                        "sigma": sigma,
                        "role": "evaluation",
                        "seed": seed,
                        "n_frames": trajectory.frames.shape[0],
                        "degree": DEGREE,
                        "L": diagnostics.length,
                        "R": diagnostics.displacement,
                        "eta": diagnostics.efficiency,
                        "angle_valid_fraction": diagnostics.angle_valid_fraction,
                        "adjacent_mean": float(np.mean(distances)),
                        "adjacent_p95": float(np.percentile(distances, 95.0)),
                        "adjacent_max": float(np.max(distances)),
                        "n_above_e95": int(above.sum()),
                        "spearman_rho": float(rho),
                        "spearman_p": float(p_value),
                        "runs_z": runs_z,
                        "runs_p": runs_p,
                        "cluster_p": cluster_p,
                        "max_run": max_run_length(above),
                        "h1_card_mean": float(
                            np.mean([d.shape[0] for d in diagrams[SECONDARY_DEGREE]])
                        ),
                    }
                )
                pooled = np.concatenate([pooled, distances])
                pairs.save()
            pooled_plot[(family, sigma)] = pooled
            if sigma == 0.0:
                total_nonzero = 0
                max_abs = 0.0
                l_zero = True
                eta_none = True
                angles_unresolved = True
                excess_unresolved = True
                changes_zero = True
                efficiency_false = True
                unique_h0 = 0
                unique_h1 = 0
                for seed in SEEDS_EVAL:
                    trajectory = generators.build_control(
                        "static", family, seed, 0.0, 1
                    )
                    diagrams = ctx.diagram_cache.get(
                        family, trajectory.frames, (DEGREE, SECONDARY_DEGREE)
                    )
                    name = workload_name(family, "static", seed, 0.0, 1)
                    pairs = ctx.pair_cache(f"{name}_eval_d0")
                    diagnostics = compute_path_diagnostics(
                        diagrams[DEGREE],
                        trajectory.timestamps,
                        pairs.metric(diagrams[DEGREE]),
                    )
                    distances = np.asarray(diagnostics.adjacent_distances)
                    if float(np.max(distances)) > 0.0:
                        total_nonzero += 1
                    max_abs = max(max_abs, float(np.max(distances)))
                    l_zero = l_zero and float(diagnostics.length) == 0.0
                    eta_none = eta_none and diagnostics.efficiency is None
                    angles_unresolved = angles_unresolved and (
                        diagnostics.angle_valid_fraction == 0.0
                    )
                    excess_unresolved = excess_unresolved and (
                        not bool(np.any(diagnostics.triangle_excess_valid))
                    )
                    changes_zero = changes_zero and bool(
                        np.all(diagnostics.speed_change_rates == 0.0)
                    )
                    efficiency_false = efficiency_false and (
                        _compact_vector(diagnostics, 0.0)[11] == 0.0
                    )
                    unique_h0 = max(
                        unique_h0, len({d.tobytes() for d in diagrams[DEGREE]})
                    )
                    unique_h1 = max(
                        unique_h1,
                        len({d.tobytes() for d in diagrams[SECONDARY_DEGREE]}),
                    )
                verification_ok = (
                    total_nonzero == 0
                    and l_zero
                    and eta_none
                    and angles_unresolved
                    and excess_unresolved
                    and changes_zero
                    and efficiency_false
                    and unique_h0 == 1
                )
                assertions[f"{family}_sigma0"] = {
                    "n_evaluation_trajectories": len(SEEDS_EVAL),
                    "n_nonzero_adjacent_trajectories": int(total_nonzero),
                    "max_abs_adjacent": max_abs,
                    "L_zero_all": bool(l_zero),
                    "eta_none_all": bool(eta_none),
                    "angles_unresolved_all": bool(angles_unresolved),
                    "triangle_excess_unresolved_all": bool(excess_unresolved),
                    "speed_change_zero_all": bool(changes_zero),
                    "efficiency_flag_false_all": bool(efficiency_false),
                    "unique_h0_diagrams": int(unique_h0),
                    "unique_h1_diagrams": int(unique_h1),
                    "verdict": "PASS" if verification_ok else "FAIL",
                }
            all_above = np.concatenate(eval_above)
            n_intervals = int(all_above.size)
            n_above = int(all_above.sum())
            expected = 0.05 * n_intervals
            bound_99 = float(stats.binom.ppf(0.99, n_intervals, 0.05))
            binom_p = float(stats.binom.sf(n_above - 1, n_intervals, 0.05))
            eval_trend_p_array = np.asarray(eval_trend_p, dtype=float)
            eval_trend_rho_array = np.asarray(eval_trend_rho, dtype=float)
            eval_runs_p_array = np.asarray(eval_runs_p, dtype=float)
            eval_cluster_p_array = np.asarray(eval_cluster_p, dtype=float)
            n_trend_p01 = int(np.sum(eval_trend_p_array < 0.01))
            n_trend_fail = int(
                np.sum(
                    (eval_trend_p_array < 0.001)
                    & (np.abs(eval_trend_rho_array) > 0.5)
                )
            )
            n_runs_p01 = int(np.sum(eval_runs_p_array < 0.01))
            n_cluster_fail = int(np.sum(eval_cluster_p_array < 0.01))
            if sigma == 0.0:
                verdict = assertions[f"{family}_sigma0"]["verdict"]
                notes = "exact-zero rule and compact degeneracy"
            else:
                temporal_fail = n_trend_fail >= 1 or n_cluster_fail >= 2
                exceed_pass = n_above <= bound_99
                weak = n_trend_p01 >= 2 or n_cluster_fail == 1
                if temporal_fail:
                    verdict = "FAIL"
                elif not exceed_pass or weak:
                    verdict = "RESIDUAL"
                else:
                    verdict = "PASS"
                notes = (
                    f"e95={e95:.6g}; pooled exceedance rate="
                    f"{n_above / max(n_intervals, 1):.4f}; "
                    f"seeds with trend fail (p<0.001 and |rho|>0.5)={n_trend_fail}; "
                    f"seeds with cluster permutation p<0.01={n_cluster_fail}"
                )
            max_run_all = 0
            for row in rows:
                if (
                    row["family"] == family
                    and row["sigma"] == sigma
                    and row["role"] == "evaluation"
                    and row["max_run"] is not None
                ):
                    max_run_all = max(max_run_all, int(row["max_run"]))
            summary_rows.append(
                {
                    "family": family,
                    "sigma": sigma,
                    "e95": e95,
                    "n_calibration_trajectories": len(SEEDS_CAL),
                    "n_evaluation_trajectories": len(SEEDS_EVAL),
                    "n_intervals": n_intervals,
                    "n_above_e95": n_above,
                    "expected_above": expected,
                    "binom_bound_99": bound_99,
                    "binom_p": binom_p,
                    "exceedance_rate": n_above / max(n_intervals, 1),
                    "n_seed_trend_p01": n_trend_p01,
                    "n_seed_trend_fail": n_trend_fail,
                    "n_seed_runs_p01": n_runs_p01,
                    "n_seed_cluster_p01": n_cluster_fail,
                    "max_run": int(max_run_all),
                    "verdict": verdict,
                    "notes": notes,
                }
            )
            ctx.log(
                f"control1 {family} sigma={sigma}: e95={e95:.6g}, "
                f"above={n_above}/{n_intervals}, verdict={verdict}"
            )
    table_path = ctx.out_dir / "control1_static_null" / "per_trajectory.csv"
    write_csv(
        table_path,
        [
            "family",
            "sigma",
            "role",
            "seed",
            "n_frames",
            "degree",
            "L",
            "R",
            "eta",
            "angle_valid_fraction",
            "adjacent_mean",
            "adjacent_p95",
            "adjacent_max",
            "n_above_e95",
            "spearman_rho",
            "spearman_p",
            "runs_z",
            "runs_p",
            "cluster_p",
            "max_run",
            "h1_card_mean",
        ],
        rows,
    )
    ctx.register_table(table_path)
    distribution_path = (
        ctx.out_dir / "control1_static_null" / "adjacent_distances.csv"
    )
    write_csv(
        distribution_path,
        [
            "family",
            "sigma",
            "role",
            "seed",
            "interval_index",
            "distance",
        ],
        distance_rows,
    )
    ctx.register_table(distribution_path)
    summary_path = ctx.out_dir / "control1_static_null" / "summary.csv"
    write_csv(
        summary_path,
        [
            "family",
            "sigma",
            "e95",
            "n_calibration_trajectories",
            "n_evaluation_trajectories",
            "n_intervals",
            "n_above_e95",
            "expected_above",
            "binom_bound_99",
            "binom_p",
            "exceedance_rate",
            "n_seed_trend_p01",
            "n_seed_trend_fail",
            "n_seed_runs_p01",
            "n_seed_cluster_p01",
            "max_run",
            "verdict",
            "notes",
        ],
        summary_rows,
    )
    ctx.register_table(summary_path)
    assertions_path = (
        ctx.out_dir / "control1_static_null" / "degenerate_assertions.json"
    )
    write_json(assertions_path, assertions)
    ctx.register_table(assertions_path)

    figure_path = ctx.out_dir / "control1_static_null" / "figure_static_null.png"
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for row_index, family in enumerate(FAMILIES):
        for column_index, sigma in enumerate(SIGMAS):
            axis = axes[row_index][column_index]
            values = finite(pooled_plot[(family, sigma)])
            if sigma == 0.0:
                axis.hist(
                    np.zeros(1), bins=[-1e-6, 1e-6], color="#888888", edgecolor="black"
                )
                axis.set_title(f"Family {family}, sigma=0 (all exactly zero)")
            else:
                axis.hist(values, bins=40, color="#3b6ea5", edgecolor="white")
                axis.axvline(
                    ctx.floors[(family, sigma)],
                    color="#c1440e",
                    linestyle="--",
                    label="e95 calibration",
                )
                axis.legend(loc="upper right", fontsize=8)
                axis.set_title(
                    f"Family {family}, sigma=0.05, max={values.max():.4g}"
                )
            axis.set_xlabel("adjacent bottleneck distance")
            axis.set_ylabel("count")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)
    verdicts = {
        f"{row['family']}_sigma{sigma_tag(row['sigma'])}": row["verdict"]
        for row in summary_rows
    }
    if all(value == "PASS" for value in verdicts.values()):
        overall = "PASS"
    elif any(value == "FAIL" for value in verdicts.values()):
        overall = "FAIL"
    else:
        overall = "RESIDUAL"
    ctx.verdicts["static_null"] = {
        "verdict": overall,
        "per_cell": verdicts,
        "assertions": assertions,
    }
    ctx.log(f"control1 static null: verdict={overall}")
    return {"summary": summary_rows, "assertions": assertions, "verdict": overall}


def control2_matched_ordering(ctx: RunContext) -> dict:
    ctx.log("control2 matched ordering: start")
    condition_rows: list[dict] = []
    difference_rows: list[dict] = []
    structural: dict[str, bool] = {}
    group_stats: dict[str, dict] = {}
    for sigma in SIGMAS:
        group_key = f"A_sigma{sigma_tag(sigma)}"
        structural[group_key] = True
        separation_hits = 0
        matched_hits = 0
        matched_l_hits = 0
        matched_r_hits = 0
        matched_eta_hits = 0
        matched_speed_hits = 0
        max_angle_diffs: list[float] = []
        for seed in SEEDS_MATCHED:
            ctx.check_budget()
            forward = generators.build_control("matched_forward", "A", seed, sigma, 1)
            folded = generators.build_control("matched_folded", "A", seed, sigma, 1)
            structural[group_key] = structural[group_key] and bool(
                forward.latent == folded.latent
            )
            structural[group_key] = structural[group_key] and bool(
                np.allclose(
                    np.abs(np.diff(forward.z)),
                    np.abs(np.diff(folded.z)),
                    atol=0.0,
                    rtol=0.0,
                )
            )
            structural[group_key] = structural[group_key] and bool(
                forward.z[0] == folded.z[0] and forward.z[-1] == folded.z[-1]
            )
            name_f = workload_name("A", "matched_forward", seed, sigma, 1)
            name_d = workload_name("A", "matched_folded", seed, sigma, 1)
            diagrams_f = ctx.diagram_cache.get("A", forward.frames, (DEGREE,))
            diagrams_d = ctx.diagram_cache.get("A", folded.frames, (DEGREE,))
            pairs_f = ctx.pair_cache(f"{name_f}_d0")
            pairs_d = ctx.pair_cache(f"{name_d}_d0")
            diag_f = compute_path_diagnostics(
                diagrams_f[DEGREE],
                forward.timestamps,
                pairs_f.metric(diagrams_f[DEGREE]),
            )
            diag_d = compute_path_diagnostics(
                diagrams_d[DEGREE],
                folded.timestamps,
                pairs_d.metric(diagrams_d[DEGREE]),
            )
            compact_f = _compact_vector(diag_f, 0.0)
            compact_d = _compact_vector(diag_d, 0.0)
            for control_name, diagnostics, compact in (
                ("matched_forward", diag_f, compact_f),
                ("matched_folded", diag_d, compact_d),
            ):
                condition_rows.append(
                    {
                        "source": "frozen_family_A",
                        "family": "A",
                        "seed": seed,
                        "sigma": sigma,
                        "control": control_name,
                        "L": diagnostics.length,
                        "R": diagnostics.displacement,
                        "eta": diagnostics.efficiency,
                        "speed_mean": compact[3],
                        "speed_std": compact[4],
                        "speed_max": compact[5],
                        "speed_change_mean_signed": compact[6],
                        "speed_change_mean_abs": compact[7],
                        "speed_change_max_abs": compact[8],
                        "mean_cosine": compact[9],
                        "angle_valid_fraction": compact[10],
                        "efficiency_valid_flag": compact[11],
                        "triangle_excess_mean": nanmean_or_nan(
                            diagnostics.triangle_excess
                        ),
                    }
                )
            speed_abs_diff = nanmax_or_nan(
                np.abs(
                    np.asarray(diag_f.interval_speeds)
                    - np.asarray(diag_d.interval_speeds)
                )
            )
            angle_diff = np.abs(
                np.asarray(diag_f.comparison_angles)
                - np.asarray(diag_d.comparison_angles)
            )
            excess_diff = np.abs(
                np.asarray(diag_f.triangle_excess)
                - np.asarray(diag_d.triangle_excess)
            )
            for index in range(int(np.size(diag_f.comparison_angles))):
                difference_rows.append(
                    {
                        "source": "frozen_family_A",
                        "family": "A",
                        "seed": seed,
                        "sigma": sigma,
                        "interior_index": index,
                        "angle_forward": float(diag_f.comparison_angles[index]),
                        "angle_folded": float(diag_d.comparison_angles[index]),
                        "angle_abs_diff": float(angle_diff[index]),
                        "valid_forward": bool(diag_f.comparison_valid[index]),
                        "valid_folded": bool(diag_d.comparison_valid[index]),
                        "excess_forward": float(diag_f.triangle_excess[index]),
                        "excess_folded": float(diag_d.triangle_excess[index]),
                        "excess_abs_diff": float(excess_diff[index]),
                        "speed_forward": float(diag_f.interval_speeds[index]),
                        "speed_folded": float(diag_d.interval_speeds[index]),
                        "speed_abs_diff": float(
                            abs(
                                diag_f.interval_speeds[index]
                                - diag_d.interval_speeds[index]
                            )
                        ),
                    }
                )
            max_angle_diff = nanmax_or_nan(angle_diff)
            max_excess_diff = nanmax_or_nan(excess_diff)
            max_angle_diffs.append(max_angle_diff)
            if (
                np.isfinite(max_angle_diff) and max_angle_diff > ANGLE_SEPARATION_TOL
            ) or (
                np.isfinite(max_excess_diff)
                and max_excess_diff > ANGLE_SEPARATION_TOL
            ):
                separation_hits += 1
            matched_l = abs(diag_f.length - diag_d.length) <= MATCHED_TOL
            matched_r = (
                abs(diag_f.displacement - diag_d.displacement) <= MATCHED_TOL
            )
            if diag_f.efficiency is None and diag_d.efficiency is None:
                matched_eta = True
            elif diag_f.efficiency is None or diag_d.efficiency is None:
                matched_eta = False
            else:
                matched_eta = (
                    abs(
                        float(diag_f.efficiency)
                        - float(diag_d.efficiency)
                    )
                    <= MATCHED_TOL
                )
            matched_speed = bool(
                np.isfinite(speed_abs_diff) and speed_abs_diff <= MATCHED_TOL
            )
            matched_l_hits += int(matched_l)
            matched_r_hits += int(matched_r)
            matched_eta_hits += int(matched_eta)
            matched_speed_hits += int(matched_speed)
            if matched_l and matched_r and matched_eta and matched_speed:
                matched_hits += 1
            pairs_f.save()
            pairs_d.save()
        group_stats[group_key] = {
            "n_seeds": len(SEEDS_MATCHED),
            "separation_hits": separation_hits,
            "matched_hits_within_1e-9": matched_hits,
            "matched_L_hits": matched_l_hits,
            "matched_R_hits": matched_r_hits,
            "matched_eta_hits": matched_eta_hits,
            "matched_speed_hits": matched_speed_hits,
            "median_max_angle_diff": nanmedian_or_nan(max_angle_diffs),
            "max_max_angle_diff": nanmax_or_nan(max_angle_diffs),
            "structural_ok": structural[group_key],
        }
        ctx.log(
            f"control2 frozen family A sigma={sigma}: separation "
            f"{separation_hits}/{len(SEEDS_MATCHED)}, matched {matched_hits}"
        )

    group_key = "B_sigma0"
    structural[group_key] = True
    separation_hits = 0
    matched_hits = 0
    matched_l_hits = 0
    matched_r_hits = 0
    matched_eta_hits = 0
    matched_speed_hits = 0
    max_angle_diffs = []
    for seed in SEEDS_AUX:
        ctx.check_budget()
        rng = np.random.default_rng([int(seed), generators.FAMILY_IDS["B"], 5, 101])
        latent = {
            "a": float(rng.uniform(0.15, 0.25)),
            "b": float(rng.uniform(0.75, 0.85)),
        }
        latent["m"] = 0.5 * (latent["a"] + latent["b"])
        latent["A1"] = float(rng.uniform(0.9, 1.1))
        latent["A2"] = float(rng.uniform(0.9, 1.1))
        latent["w"] = float(rng.uniform(0.35, 0.45))
        z_forward = generators.MATCHED_Z["matched_forward"]
        z_folded = generators.MATCHED_Z["matched_folded"]
        frames_forward = family_b_fields_at_z(latent, z_forward)
        frames_folded = family_b_fields_at_z(latent, z_folded)
        structural[group_key] = structural[group_key] and bool(
            np.allclose(
                np.abs(np.diff(z_forward)),
                np.abs(np.diff(z_folded)),
                atol=0.0,
                rtol=0.0,
            )
        )
        structural[group_key] = structural[group_key] and bool(
            z_forward[0] == z_folded[0] and z_forward[-1] == z_folded[-1]
        )
        name_f = f"B_aux_matched_forward_{seed}_s0_str1"
        name_d = f"B_aux_matched_folded_{seed}_s0_str1"
        diagrams_f = ctx.diagram_cache.get("B", frames_forward, (DEGREE,))
        diagrams_d = ctx.diagram_cache.get("B", frames_folded, (DEGREE,))
        pairs_f = ctx.pair_cache(f"{name_f}_d0")
        pairs_d = ctx.pair_cache(f"{name_d}_d0")
        diag_f = compute_path_diagnostics(
            diagrams_f[DEGREE],
            generators.MATCHED_TIMES,
            pairs_f.metric(diagrams_f[DEGREE]),
        )
        diag_d = compute_path_diagnostics(
            diagrams_d[DEGREE],
            generators.MATCHED_TIMES,
            pairs_d.metric(diagrams_d[DEGREE]),
        )
        compact_f = _compact_vector(diag_f, 0.0)
        compact_d = _compact_vector(diag_d, 0.0)
        for control_name, diagnostics, compact in (
            ("matched_forward", diag_f, compact_f),
            ("matched_folded", diag_d, compact_d),
        ):
            condition_rows.append(
                {
                    "source": "aux_family_B",
                    "family": "B",
                    "seed": seed,
                    "sigma": 0.0,
                    "control": control_name,
                    "L": diagnostics.length,
                    "R": diagnostics.displacement,
                    "eta": diagnostics.efficiency,
                    "speed_mean": compact[3],
                    "speed_std": compact[4],
                    "speed_max": compact[5],
                    "speed_change_mean_signed": compact[6],
                    "speed_change_mean_abs": compact[7],
                    "speed_change_max_abs": compact[8],
                    "mean_cosine": compact[9],
                    "angle_valid_fraction": compact[10],
                    "efficiency_valid_flag": compact[11],
                    "triangle_excess_mean": nanmean_or_nan(
                        diagnostics.triangle_excess
                    ),
                }
            )
        speed_abs_diff = nanmax_or_nan(
            np.abs(
                np.asarray(diag_f.interval_speeds)
                - np.asarray(diag_d.interval_speeds)
            )
        )
        angle_diff = np.abs(
            np.asarray(diag_f.comparison_angles)
            - np.asarray(diag_d.comparison_angles)
        )
        excess_diff = np.abs(
            np.asarray(diag_f.triangle_excess)
            - np.asarray(diag_d.triangle_excess)
        )
        for index in range(int(np.size(diag_f.comparison_angles))):
            difference_rows.append(
                {
                    "source": "aux_family_B",
                    "family": "B",
                    "seed": seed,
                    "sigma": 0.0,
                    "interior_index": index,
                    "angle_forward": float(diag_f.comparison_angles[index]),
                    "angle_folded": float(diag_d.comparison_angles[index]),
                    "angle_abs_diff": float(angle_diff[index]),
                    "valid_forward": bool(diag_f.comparison_valid[index]),
                    "valid_folded": bool(diag_d.comparison_valid[index]),
                    "excess_forward": float(diag_f.triangle_excess[index]),
                    "excess_folded": float(diag_d.triangle_excess[index]),
                    "excess_abs_diff": float(excess_diff[index]),
                    "speed_forward": float(diag_f.interval_speeds[index]),
                    "speed_folded": float(diag_d.interval_speeds[index]),
                    "speed_abs_diff": float(
                        abs(
                            diag_f.interval_speeds[index]
                            - diag_d.interval_speeds[index]
                        )
                    ),
                }
            )
        max_angle_diff = nanmax_or_nan(angle_diff)
        max_excess_diff = nanmax_or_nan(excess_diff)
        max_angle_diffs.append(max_angle_diff)
        if (np.isfinite(max_angle_diff) and max_angle_diff > ANGLE_SEPARATION_TOL) or (
            np.isfinite(max_excess_diff) and max_excess_diff > ANGLE_SEPARATION_TOL
        ):
            separation_hits += 1
        matched_l = abs(diag_f.length - diag_d.length) <= MATCHED_TOL
        matched_r = abs(diag_f.displacement - diag_d.displacement) <= MATCHED_TOL
        if diag_f.efficiency is None and diag_d.efficiency is None:
            matched_eta = True
        elif diag_f.efficiency is None or diag_d.efficiency is None:
            matched_eta = False
        else:
            matched_eta = (
                abs(float(diag_f.efficiency) - float(diag_d.efficiency))
                <= MATCHED_TOL
            )
        matched_speed = bool(
            np.isfinite(speed_abs_diff) and speed_abs_diff <= MATCHED_TOL
        )
        matched_l_hits += int(matched_l)
        matched_r_hits += int(matched_r)
        matched_eta_hits += int(matched_eta)
        matched_speed_hits += int(matched_speed)
        if matched_l and matched_r and matched_eta and matched_speed:
            matched_hits += 1
        pairs_f.save()
        pairs_d.save()
    group_stats[group_key] = {
        "n_seeds": len(SEEDS_AUX),
        "separation_hits": separation_hits,
        "matched_hits_within_1e-9": matched_hits,
        "matched_L_hits": matched_l_hits,
        "matched_R_hits": matched_r_hits,
        "matched_eta_hits": matched_eta_hits,
        "matched_speed_hits": matched_speed_hits,
        "median_max_angle_diff": nanmedian_or_nan(max_angle_diffs),
        "max_max_angle_diff": nanmax_or_nan(max_angle_diffs),
        "structural_ok": structural[group_key],
    }
    ctx.log(
        f"control2 auxiliary family B sigma=0: separation {separation_hits}/"
        f"{len(SEEDS_AUX)}"
    )

    group_rows = []
    for key, stats_row in group_stats.items():
        required = max(1, int(math.ceil(0.8 * stats_row["n_seeds"])))
        separated = stats_row["separation_hits"] >= required
        group_rows.append(
            {
                "group": key,
                "n_seeds": stats_row["n_seeds"],
                "structural_ok": stats_row["structural_ok"],
                "separation_hits": stats_row["separation_hits"],
                "separation_required": required,
                "angle_or_shape_separated": separated,
                "matched_hits_within_1e-9": stats_row["matched_hits_within_1e-9"],
                "matched_L_hits": stats_row["matched_L_hits"],
                "matched_R_hits": stats_row["matched_R_hits"],
                "matched_eta_hits": stats_row["matched_eta_hits"],
                "matched_speed_hits": stats_row["matched_speed_hits"],
                "median_max_angle_diff": stats_row["median_max_angle_diff"],
                "max_max_angle_diff": stats_row["max_max_angle_diff"],
            }
        )
    condition_path = ctx.out_dir / "control2_matched_ordering" / "per_condition.csv"
    write_csv(
        condition_path,
        [
            "source",
            "family",
            "seed",
            "sigma",
            "control",
            "L",
            "R",
            "eta",
            "speed_mean",
            "speed_std",
            "speed_max",
            "speed_change_mean_signed",
            "speed_change_mean_abs",
            "speed_change_max_abs",
            "mean_cosine",
            "angle_valid_fraction",
            "efficiency_valid_flag",
            "triangle_excess_mean",
        ],
        condition_rows,
    )
    ctx.register_table(condition_path)
    difference_path = (
        ctx.out_dir / "control2_matched_ordering" / "angle_differences.csv"
    )
    write_csv(
        difference_path,
        [
            "source",
            "family",
            "seed",
            "sigma",
            "interior_index",
            "angle_forward",
            "angle_folded",
            "angle_abs_diff",
            "valid_forward",
            "valid_folded",
            "excess_forward",
            "excess_folded",
            "excess_abs_diff",
            "speed_forward",
            "speed_folded",
            "speed_abs_diff",
        ],
        difference_rows,
    )
    ctx.register_table(difference_path)
    summary_path = ctx.out_dir / "control2_matched_ordering" / "summary.csv"
    write_csv(
        summary_path,
        [
            "group",
            "n_seeds",
            "structural_ok",
            "separation_hits",
            "separation_required",
            "angle_or_shape_separated",
            "matched_hits_within_1e-9",
            "matched_L_hits",
            "matched_R_hits",
            "matched_eta_hits",
            "matched_speed_hits",
            "median_max_angle_diff",
            "max_max_angle_diff",
        ],
        group_rows,
    )
    ctx.register_table(summary_path)

    figure_path = (
        ctx.out_dir / "control2_matched_ordering" / "figure_matched_ordering.png"
    )
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    representative = SEEDS_MATCHED[0]
    for row_index, sigma in enumerate(SIGMAS):
        forward = generators.build_control(
            "matched_forward", "A", representative, sigma, 1
        )
        folded = generators.build_control("matched_folded", "A", representative, sigma, 1)
        name_f = workload_name("A", "matched_forward", representative, sigma, 1)
        name_d = workload_name("A", "matched_folded", representative, sigma, 1)
        diagrams_f = ctx.diagram_cache.get("A", forward.frames, (DEGREE,))
        diagrams_d = ctx.diagram_cache.get("A", folded.frames, (DEGREE,))
        pairs_f = ctx.pair_cache(f"{name_f}_d0")
        pairs_d = ctx.pair_cache(f"{name_d}_d0")
        diag_f = compute_path_diagnostics(
            diagrams_f[DEGREE], forward.timestamps, pairs_f.metric(diagrams_f[DEGREE])
        )
        diag_d = compute_path_diagnostics(
            diagrams_d[DEGREE], folded.timestamps, pairs_d.metric(diagrams_d[DEGREE])
        )
        axis = axes[row_index][0]
        indices = np.arange(1, int(np.size(diag_f.comparison_angles)) + 1)
        axis.plot(indices, diag_f.comparison_angles, "o-", label="forward")
        axis.plot(indices, diag_d.comparison_angles, "s--", label="folded")
        axis.set_title(f"angles, seed {representative}, sigma={sigma}")
        axis.set_xlabel("interior index")
        axis.set_ylabel("comparison angle (rad)")
        axis.legend(fontsize=8)
        axis = axes[row_index][1]
        diffs = np.abs(
            np.asarray(diag_f.interval_speeds) - np.asarray(diag_d.interval_speeds)
        )
        axis.bar(np.arange(diffs.size), np.maximum(diffs, 1e-18), color="#3b6ea5")
        axis.axhline(1e-9, color="#c1440e", linestyle="--", label="1e-9")
        axis.set_yscale("log")
        axis.set_title(f"speed difference, sigma={sigma}")
        axis.set_xlabel("interval index")
        axis.legend(fontsize=8)
        pairs_f.save()
        pairs_d.save()
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)

    structural_ok = all(structural.values())
    all_separated = all(row["angle_or_shape_separated"] for row in group_rows)
    if structural_ok and all_separated:
        overall = "PASS"
    elif structural_ok:
        overall = "RESIDUAL"
    else:
        overall = "FAIL"
    ctx.verdicts["matched_ordering"] = {
        "verdict": overall,
        "structural_ok": structural_ok,
        "groups": group_rows,
    }
    ctx.log(f"control2 matched ordering: verdict={overall}")
    return {"groups": group_rows, "verdict": overall}


WARPS = (
    (
        "u_pow_1p5",
        lambda u: np.asarray(u, dtype=np.float64) ** 1.5,
        lambda u: 1.5 * np.sqrt(np.asarray(u, dtype=np.float64)),
    ),
    (
        "piecewise_fast_slow",
        lambda u: np.where(
            np.asarray(u, dtype=np.float64) <= WARP_KINK,
            2.0 * np.asarray(u, dtype=np.float64),
            0.5 + (2.0 / 3.0) * (np.asarray(u, dtype=np.float64) - WARP_KINK),
        ),
        lambda u: np.where(
            np.asarray(u, dtype=np.float64) < WARP_KINK, 2.0, 2.0 / 3.0
        ),
    ),
)


def resample_indices(phi, n_frames: int) -> tuple[np.ndarray, np.ndarray]:
    u = np.arange(n_frames, dtype=np.float64) / float(n_frames - 1)
    mapped = np.clip(
        np.rint(phi(u) * float(n_frames - 1)).astype(np.int64), 0, n_frames - 1
    )
    mapped[0] = 0
    mapped[-1] = n_frames - 1
    keep = np.ones(mapped.size, dtype=bool)
    keep[1:] = np.diff(mapped) > 0
    positions = np.nonzero(keep)[0]
    return positions, mapped[positions]


def control3_time_reparam(ctx: RunContext) -> dict:
    ctx.log("control3 time reparameterization: start")
    speed_rows: list[dict] = []
    check_rows: list[dict] = []
    stats: dict[str, dict] = {}
    for family in FAMILIES:
        for sigma in SIGMAS:
            for seed in SEEDS_REPARAM:
                ctx.check_budget()
                trajectory = generators.build_trajectory(
                    family, "ramp", seed, sigma, 1
                )
                diagrams = ctx.diagram_cache.get(family, trajectory.frames, (DEGREE,))
                master_name = workload_name(family, "ramp", seed, sigma, 1)
                master_pairs = ctx.pair_cache(f"{master_name}_d0")
                master_metric = master_pairs.metric(diagrams[DEGREE])
                master = compute_path_diagnostics(
                    diagrams[DEGREE], trajectory.timestamps, master_metric
                )
                master_distances = np.asarray(master.adjacent_distances)
                for warp_name, phi, phi_prime in WARPS:
                    warped_times = phi(trajectory.timestamps)
                    warped = compute_path_diagnostics(
                        diagrams[DEGREE], warped_times, master_metric
                    )
                    h_master = np.diff(trajectory.timestamps)
                    h_warped = np.diff(warped_times)
                    midpoints = np.asarray(master.interval_speed_times)
                    predicted = 1.0 / phi_prime(midpoints)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ratio_observed = np.asarray(
                            warped.interval_speeds
                        ) / np.asarray(master.interval_speeds)
                        relative = (ratio_observed - predicted) / predicted
                    for index in range(int(master.n_intervals)):
                        speed_rows.append(
                            {
                                "family": family,
                                "seed": seed,
                                "sigma": sigma,
                                "warp": warp_name,
                                "variant": "clock_warp_same_states",
                                "interval_index": index,
                                "u_midpoint": float(midpoints[index]),
                                "h_master": float(h_master[index]),
                                "h_variant": float(h_warped[index]),
                                "nu_variant": float(warped.interval_speeds[index]),
                                "nu_reference": float(master.interval_speeds[index]),
                                "ratio_observed": float(ratio_observed[index]),
                                "ratio_predicted_derivative": float(predicted[index]),
                                "relative_deviation": float(relative[index]),
                                "shortcut_ratio": 1.0,
                            }
                        )
                    positions, mapped = resample_indices(
                        phi, trajectory.frames.shape[0]
                    )
                    kept_timestamps = trajectory.timestamps[positions]
                    sub_diagrams = [diagrams[DEGREE][index] for index in mapped]
                    master_ids = {
                        id(diagrams[DEGREE][index]): index for index in mapped
                    }

                    def sub_metric(
                        first,
                        second,
                        _ids=master_ids,
                        _pairs=master_pairs,
                        _all=diagrams[DEGREE],
                    ):
                        i = _ids[id(first)]
                        j = _ids[id(second)]
                        return _pairs.get(i, j, _all)

                    resampled = compute_path_diagnostics(
                        sub_diagrams, kept_timestamps, sub_metric
                    )
                    span_path = np.asarray(
                        [
                            float(
                                master_distances[
                                    int(mapped[t]) : int(mapped[t + 1])
                                ].sum()
                            )
                            for t in range(int(resampled.n_intervals))
                        ]
                    )
                    span_phi = np.diff(phi(kept_timestamps))
                    span_new = np.diff(kept_timestamps)
                    shortcut = np.where(
                        span_path > 0.0,
                        np.asarray(resampled.adjacent_distances)
                        / np.where(span_path > 0.0, span_path, 1.0),
                        1.0,
                    )
                    path_speed = span_path / span_phi
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ratio_observed_b = np.asarray(
                            resampled.interval_speeds
                        ) / np.where(path_speed > 0.0, path_speed, np.nan)
                        ratio_derivative_b = np.where(
                            shortcut > 0.0,
                            ratio_observed_b
                            / np.where(shortcut > 0.0, shortcut, 1.0),
                            np.nan,
                        )
                    midpoint_new = 0.5 * (kept_timestamps[:-1] + kept_timestamps[1:])
                    predicted_b = phi_prime(midpoint_new)
                    relative_b = (ratio_derivative_b - predicted_b) / predicted_b
                    for index in range(int(resampled.n_intervals)):
                        speed_rows.append(
                            {
                                "family": family,
                                "seed": seed,
                                "sigma": sigma,
                                "warp": warp_name,
                                "variant": "resampled_states",
                                "interval_index": index,
                                "u_midpoint": float(midpoint_new[index]),
                                "h_master": float(span_phi[index]),
                                "h_variant": float(span_new[index]),
                                "nu_variant": float(resampled.interval_speeds[index]),
                                "nu_reference": float(path_speed[index]),
                                "ratio_observed": float(ratio_observed_b[index]),
                                "ratio_predicted_derivative": float(predicted_b[index]),
                                "relative_deviation": float(relative_b[index]),
                                "shortcut_ratio": float(shortcut[index]),
                            }
                        )
                    preserved = 0
                    preserved_deviation = 0.0
                    angle_count = int(np.size(resampled.comparison_angles))
                    for index in range(angle_count):
                        left = int(mapped[index])
                        middle = int(mapped[index + 1])
                        right = int(mapped[index + 2])
                        if middle - left == 1 and right - middle == 1:
                            preserved += 1
                            reference = master.comparison_angles[middle - 1]
                            value = resampled.comparison_angles[index]
                            if np.isfinite(reference) and np.isfinite(value):
                                preserved_deviation = max(
                                    preserved_deviation, abs(value - reference)
                                )
                    fresh_indices = sorted(
                        set(
                            list(range(min(8, int(resampled.n_intervals))))
                            + list(
                                np.linspace(
                                    0,
                                    max(int(resampled.n_intervals) - 1, 0),
                                    8,
                                    dtype=int,
                                )
                            )
                            + list(
                                range(
                                    max(int(resampled.n_intervals) - 8, 0),
                                    int(resampled.n_intervals),
                                )
                            )
                        )
                    )
                    fresh_ok = True
                    fresh_max_deviation = 0.0
                    for index in fresh_indices:
                        fresh = float(
                            bottleneck_linf(
                                sub_diagrams[index], sub_diagrams[index + 1]
                            )
                        )
                        deviation = abs(
                            fresh - float(resampled.adjacent_distances[index])
                        )
                        fresh_max_deviation = max(fresh_max_deviation, deviation)
                        if deviation > 0.0:
                            fresh_ok = False
                    exact_same_states = bool(
                        arrays_equal_nan(
                            np.asarray(warped.adjacent_distances), master_distances
                        )
                        and arrays_equal_nan(
                            np.asarray(warped.comparison_angles),
                            np.asarray(master.comparison_angles),
                        )
                        and float(warped.length) == float(master.length)
                        and float(warped.displacement) == float(master.displacement)
                    )
                    exact_resampled = bool(
                        float(resampled.length) <= float(master.length) + 1e-12
                        and float(resampled.displacement)
                        == float(master.displacement)
                    )
                    check_rows.append(
                        {
                            "family": family,
                            "seed": seed,
                            "sigma": sigma,
                            "warp": warp_name,
                            "L_master": master.length,
                            "L_resampled": resampled.length,
                            "L_resampled_over_master": (
                                resampled.length / master.length
                                if master.length > 0
                                else None
                            ),
                            "R_master": master.displacement,
                            "R_resampled": resampled.displacement,
                            "eta_master": master.efficiency,
                            "eta_resampled": resampled.efficiency,
                            "n_master_states": int(trajectory.frames.shape[0]),
                            "n_resampled_states": int(kept_timestamps.size),
                            "n_duplicate_frames_dropped": int(
                                trajectory.frames.shape[0] - kept_timestamps.size
                            ),
                            "n_preserved_angle_triples": preserved,
                            "max_preserved_angle_deviation": preserved_deviation,
                            "fresh_step_checks": len(fresh_indices),
                            "fresh_step_max_deviation": fresh_max_deviation,
                            "fresh_step_all_exact": fresh_ok,
                            "exact_same_states_invariance": exact_same_states,
                            "exact_resampled_shortcut_checks": exact_resampled,
                            "kept_z_first": float(trajectory.z[positions][0]),
                            "kept_z_last": float(trajectory.z[positions][-1]),
                        }
                    )
                master_pairs.save()
        for warp_name, _, _ in WARPS:
            group_key = f"{family}_{warp_name}"
            relevant_checks = [
                row
                for row in check_rows
                if row["family"] == family and row["warp"] == warp_name
            ]
            stats[group_key] = {
                "family": family,
                "warp": warp_name,
                "same_states_exact_all": all(
                    row["exact_same_states_invariance"] for row in relevant_checks
                ),
                "resampled_exact_all": all(
                    row["exact_resampled_shortcut_checks"] for row in relevant_checks
                ),
                "fresh_exact_all": all(
                    row["fresh_step_all_exact"] for row in relevant_checks
                ),
                "preserved_angle_exact_all": all(
                    row["max_preserved_angle_deviation"] == 0.0
                    for row in relevant_checks
                ),
                "relative_deviations_qualified": [],
                "relative_deviations_low_u": [],
                "resampled_deviations_qualified": [],
                "resampled_deviations_low_u": [],
                "same_states_relative_all": [],
                "n_trajectories": len(relevant_checks),
            }
    for row in speed_rows:
        group_key = f"{row['family']}_{row['warp']}"
        if group_key not in stats:
            continue
        relative = row["relative_deviation"]
        if not np.isfinite(relative):
            continue
        if row["variant"] == "clock_warp_same_states":
            stats[group_key]["same_states_relative_all"].append(relative)
            if row["u_midpoint"] >= WARP_DERIVATIVE_MIN_U:
                stats[group_key]["relative_deviations_qualified"].append(relative)
            else:
                stats[group_key]["relative_deviations_low_u"].append(relative)
        else:
            if row["u_midpoint"] >= WARP_DERIVATIVE_MIN_U:
                stats[group_key]["resampled_deviations_qualified"].append(relative)
            else:
                stats[group_key]["resampled_deviations_low_u"].append(relative)
    summary_rows = []
    for group_key in sorted(stats):
        entry = stats[group_key]
        qualified = np.abs(
            np.asarray(entry["relative_deviations_qualified"], dtype=float)
        )
        resampled_qualified = np.abs(
            np.asarray(entry["resampled_deviations_qualified"], dtype=float)
        )
        low_u = np.abs(np.asarray(entry["relative_deviations_low_u"], dtype=float))
        all_same_states = np.abs(
            np.asarray(entry["same_states_relative_all"], dtype=float)
        )
        if entry["warp"] == "piecewise_fast_slow":
            derivative_ok = bool(
                all_same_states.size > 0
                and np.max(all_same_states) <= 1e-9
                and resampled_qualified.size > 0
                and np.max(resampled_qualified) <= 1e-9
            )
        else:
            derivative_ok = bool(
                qualified.size > 0 and np.max(qualified) <= DERIVATIVE_REL_TOL
            ) and bool(
                resampled_qualified.size > 0
                and np.max(resampled_qualified) <= DERIVATIVE_REL_TOL
            )
        exact_ok = (
            entry["same_states_exact_all"]
            and entry["resampled_exact_all"]
            and entry["fresh_exact_all"]
            and entry["preserved_angle_exact_all"]
        )
        if exact_ok and derivative_ok:
            verdict = "PASS"
        elif exact_ok:
            verdict = "RESIDUAL"
        else:
            verdict = "FAIL"
        summary_rows.append(
            {
                "group": group_key,
                "family": entry["family"],
                "warp": entry["warp"],
                "n_trajectories": entry["n_trajectories"],
                "exact_same_states_all": entry["same_states_exact_all"],
                "exact_resampled_all": entry["resampled_exact_all"],
                "fresh_step_checks_exact_all": entry["fresh_exact_all"],
                "preserved_angles_exact_all": entry["preserved_angle_exact_all"],
                "n_qualified_intervals": int(qualified.size),
                "max_abs_relative_deviation_qualified": (
                    float(np.max(qualified)) if qualified.size else None
                ),
                "median_abs_relative_deviation_qualified": (
                    float(np.median(qualified)) if qualified.size else None
                ),
                "n_low_u_intervals": int(low_u.size),
                "max_abs_relative_deviation_low_u": (
                    float(np.max(low_u)) if low_u.size else None
                ),
                "n_resampled_qualified_intervals": int(resampled_qualified.size),
                "max_abs_resampled_relative_deviation": (
                    float(np.max(resampled_qualified))
                    if resampled_qualified.size
                    else None
                ),
                "derivative_law_ok": derivative_ok,
                "verdict": verdict,
            }
        )
    speed_path = (
        ctx.out_dir / "control3_time_reparameterization" / "speed_ratios.csv"
    )
    write_csv(
        speed_path,
        [
            "family",
            "seed",
            "sigma",
            "warp",
            "variant",
            "interval_index",
            "u_midpoint",
            "h_master",
            "h_variant",
            "nu_variant",
            "nu_reference",
            "ratio_observed",
            "ratio_predicted_derivative",
            "relative_deviation",
            "shortcut_ratio",
        ],
        speed_rows,
    )
    ctx.register_table(speed_path)
    check_path = (
        ctx.out_dir / "control3_time_reparameterization" / "sequence_checks.csv"
    )
    write_csv(
        check_path,
        [
            "family",
            "seed",
            "sigma",
            "warp",
            "L_master",
            "L_resampled",
            "L_resampled_over_master",
            "R_master",
            "R_resampled",
            "eta_master",
            "eta_resampled",
            "n_master_states",
            "n_resampled_states",
            "n_duplicate_frames_dropped",
            "n_preserved_angle_triples",
            "max_preserved_angle_deviation",
            "fresh_step_checks",
            "fresh_step_max_deviation",
            "fresh_step_all_exact",
            "exact_same_states_invariance",
            "exact_resampled_shortcut_checks",
            "kept_z_first",
            "kept_z_last",
        ],
        check_rows,
    )
    ctx.register_table(check_path)
    summary_path = (
        ctx.out_dir / "control3_time_reparameterization" / "summary.csv"
    )
    write_csv(
        summary_path,
        [
            "group",
            "family",
            "warp",
            "n_trajectories",
            "exact_same_states_all",
            "exact_resampled_all",
            "fresh_step_checks_exact_all",
            "preserved_angles_exact_all",
            "n_qualified_intervals",
            "max_abs_relative_deviation_qualified",
            "median_abs_relative_deviation_qualified",
            "n_low_u_intervals",
            "max_abs_relative_deviation_low_u",
            "n_resampled_qualified_intervals",
            "max_abs_resampled_relative_deviation",
            "derivative_law_ok",
            "verdict",
        ],
        summary_rows,
    )
    ctx.register_table(summary_path)

    figure_path = (
        ctx.out_dir / "control3_time_reparameterization" / "figure_reparam.png"
    )
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for column_index, sigma in enumerate(SIGMAS):
        axis = axes[0][column_index]
        for row in speed_rows:
            if (
                row["family"] == "A"
                and row["seed"] == SEEDS_REPARAM[0]
                and row["sigma"] == sigma
                and row["variant"] == "clock_warp_same_states"
                and row["warp"] == "u_pow_1p5"
                and np.isfinite(row["ratio_predicted_derivative"])
                and np.isfinite(row["ratio_observed"])
            ):
                axis.scatter(
                    row["ratio_predicted_derivative"],
                    row["ratio_observed"],
                    s=6,
                    alpha=0.5,
                )
        axis.plot([0.05, 12.0], [0.05, 12.0], color="#c1440e", linestyle="--")
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlim([0.05, 12.0])
        axis.set_ylim([0.05, 12.0])
        axis.set_title(f"warp u^1.5, Family A, sigma={sigma}")
        axis.set_xlabel("predicted 1 / phi'(u)")
        axis.set_ylabel("observed speed ratio")
        axis = axes[1][column_index]
        for row in speed_rows:
            if (
                row["family"] == "A"
                and row["seed"] == SEEDS_REPARAM[0]
                and row["sigma"] == sigma
                and row["variant"] == "clock_warp_same_states"
                and row["warp"] == "piecewise_fast_slow"
                and np.isfinite(row["relative_deviation"])
            ):
                axis.scatter(
                    row["u_midpoint"],
                    max(abs(row["relative_deviation"]), 1e-18),
                    s=6,
                    alpha=0.6,
                )
        axis.set_yscale("log")
        axis.axhline(1e-9, color="#c1440e", linestyle="--", linewidth=1, label="1e-9")
        axis.set_title(f"piecewise warp relative deviation, sigma={sigma}")
        axis.set_xlabel("midpoint u")
        axis.set_ylabel("|relative deviation|")
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)

    if all(row["verdict"] == "PASS" for row in summary_rows):
        overall = "PASS"
    elif any(row["verdict"] == "FAIL" for row in summary_rows):
        overall = "FAIL"
    else:
        overall = "RESIDUAL"
    ctx.verdicts["time_reparam"] = {"verdict": overall, "groups": summary_rows}
    ctx.log(f"control3 time reparameterization: verdict={overall}")
    return {"summary": summary_rows, "verdict": overall}


def point_cloud_max_distance(frames) -> float:
    largest = 0.0
    for frame in frames:
        diff = frame[:, None, :] - frame[None, :, :]
        distances = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        largest = max(largest, float(distances.max()))
    return largest


def control4_raw_preserving(ctx: RunContext) -> dict:
    ctx.log("control4 raw-label-preserving transformations: start")
    frame_rows: list[dict] = []
    diagnostics_rows: list[dict] = []
    angle = 0.7
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
        dtype=np.float64,
    )
    translation = np.array([0.37, -0.21], dtype=np.float64)
    summary: dict[str, dict] = {}
    for sigma in SIGMAS:
        for seed in SEEDS_RAW:
            ctx.check_budget()
            base = generators.build_control("static", "A", seed, sigma, 4)
            translated_frames = np.ascontiguousarray(
                base.frames + translation[None, None, :]
            )
            rotated_frames = np.ascontiguousarray(base.frames @ rotation.T)
            base_diagrams = ctx.diagram_cache.get(
                "A", base.frames, (DEGREE, SECONDARY_DEGREE)
            )
            translated = custom_trajectory(
                base, "translated", translated_frames, base.z
            )
            rotated = custom_trajectory(base, "rotated", rotated_frames, base.z)
            translated_diagrams = ctx.diagram_cache.get(
                "A", translated.frames, (DEGREE, SECONDARY_DEGREE)
            )
            rotated_diagrams = ctx.diagram_cache.get(
                "A", rotated.frames, (DEGREE, SECONDARY_DEGREE)
            )
            filtration_range = point_cloud_max_distance(base.frames)
            tolerance = 1e-7 * max(1.0, filtration_range)
            variant_diagrams = {
                "translation": translated_diagrams,
                "rotation": rotated_diagrams,
            }
            for variant_name in ("translation", "rotation"):
                other_diagrams = variant_diagrams[variant_name]
                for degree in (DEGREE, SECONDARY_DEGREE):
                    max_distance = 0.0
                    argmax_frame = -1
                    for index in range(base.frames.shape[0]):
                        distance = float(
                            bottleneck_linf(
                                base_diagrams[degree][index],
                                other_diagrams[degree][index],
                            )
                        )
                        frame_rows.append(
                            {
                                "family": "A",
                                "seed": seed,
                                "sigma": sigma,
                                "variant": variant_name,
                                "degree": degree,
                                "frame": index,
                                "base_diagram_size": int(
                                    base_diagrams[degree][index].shape[0]
                                ),
                                "transformed_diagram_size": int(
                                    other_diagrams[degree][index].shape[0]
                                ),
                                "distance": distance,
                                "filtration_range": filtration_range,
                                "tolerance": tolerance,
                                "within_tolerance": distance <= tolerance,
                            }
                        )
                        if distance > max_distance:
                            max_distance = distance
                            argmax_frame = index
                    key = f"{variant_name}_degree{degree}"
                    if key not in summary:
                        summary[key] = {
                            "variant": variant_name,
                            "degree": degree,
                            "max_distance": max_distance,
                            "argmax_frame": argmax_frame,
                            "max_tolerance": tolerance,
                            "filtration_range": filtration_range,
                            "n_frames_checked": int(base.frames.shape[0]),
                            "all_within_tolerance": max_distance <= tolerance,
                        }
                    else:
                        entry = summary[key]
                        if max_distance > entry["max_distance"]:
                            entry["max_distance"] = max_distance
                            entry["argmax_frame"] = argmax_frame
                        entry["max_tolerance"] = tolerance
                        entry["filtration_range"] = filtration_range
                        entry["n_frames_checked"] += int(base.frames.shape[0])
                        entry["all_within_tolerance"] = (
                            entry["all_within_tolerance"] and max_distance <= tolerance
                        )
                base_name = f"A_static_{seed}_s{sigma_tag(sigma)}_str4_c4base_d0"
                other_name = (
                    f"A_static_{seed}_s{sigma_tag(sigma)}_str4_c4{variant_name}_d0"
                )
                pairs_base = ctx.pair_cache(base_name)
                pairs_other = ctx.pair_cache(other_name)
                diag_base = compute_path_diagnostics(
                    base_diagrams[DEGREE],
                    base.timestamps,
                    pairs_base.metric(base_diagrams[DEGREE]),
                )
                diag_other = compute_path_diagnostics(
                    other_diagrams[DEGREE],
                    translated.timestamps,
                    pairs_other.metric(other_diagrams[DEGREE]),
                )
                compact_base = _compact_vector(diag_base, 0.0)
                compact_other = _compact_vector(diag_other, 0.0)
                if (
                    diag_base.efficiency is None
                    and diag_other.efficiency is None
                ):
                    abs_delta_eta = None
                elif (
                    diag_base.efficiency is None or diag_other.efficiency is None
                ):
                    abs_delta_eta = float("nan")
                else:
                    abs_delta_eta = abs(
                        float(diag_base.efficiency) - float(diag_other.efficiency)
                    )
                diagnostics_rows.append(
                    {
                        "family": "A",
                        "seed": seed,
                        "sigma": sigma,
                        "variant": variant_name,
                        "degree": DEGREE,
                        "L_base": diag_base.length,
                        "L_variant": diag_other.length,
                        "abs_delta_L": abs(diag_base.length - diag_other.length),
                        "R_base": diag_base.displacement,
                        "R_variant": diag_other.displacement,
                        "abs_delta_R": abs(
                            diag_base.displacement - diag_other.displacement
                        ),
                        "eta_base": diag_base.efficiency,
                        "eta_variant": diag_other.efficiency,
                        "abs_delta_eta": abs_delta_eta,
                        "max_abs_delta_speed": nanmax_or_nan(
                            np.abs(
                                np.asarray(diag_base.interval_speeds)
                                - np.asarray(diag_other.interval_speeds)
                            )
                        ),
                        "max_abs_delta_angle": nanmax_or_nan(
                            np.abs(
                                np.asarray(diag_base.comparison_angles)
                                - np.asarray(diag_other.comparison_angles)
                            )
                        ),
                        "angle_valid_fraction_base": diag_base.angle_valid_fraction,
                        "angle_valid_fraction_variant": diag_other.angle_valid_fraction,
                        "compact_max_abs_difference": nanmax_or_nan(
                            np.abs(compact_base - compact_other)
                        ),
                    }
                )
                pairs_base.save()
                pairs_other.save()
        ctx.log(f"control4 sigma={sigma}: completed {len(SEEDS_RAW)} seeds")
    frame_path = ctx.out_dir / "control4_raw_preserving" / "per_frame_distances.csv"
    write_csv(
        frame_path,
        [
            "family",
            "seed",
            "sigma",
            "variant",
            "degree",
            "frame",
            "base_diagram_size",
            "transformed_diagram_size",
            "distance",
            "filtration_range",
            "tolerance",
            "within_tolerance",
        ],
        frame_rows,
    )
    ctx.register_table(frame_path)
    diagnostics_path = (
        ctx.out_dir / "control4_raw_preserving" / "diagnostic_changes.csv"
    )
    write_csv(
        diagnostics_path,
        [
            "family",
            "seed",
            "sigma",
            "variant",
            "degree",
            "L_base",
            "L_variant",
            "abs_delta_L",
            "R_base",
            "R_variant",
            "abs_delta_R",
            "eta_base",
            "eta_variant",
            "abs_delta_eta",
            "max_abs_delta_speed",
            "max_abs_delta_angle",
            "angle_valid_fraction_base",
            "angle_valid_fraction_variant",
            "compact_max_abs_difference",
        ],
        diagnostics_rows,
    )
    ctx.register_table(diagnostics_path)
    summary_rows = []
    for key in sorted(summary):
        entry = summary[key]
        verdict = "PASS" if entry["all_within_tolerance"] else "FAIL"
        if entry["max_distance"] == 0.0:
            entry = {**entry, "argmax_frame": None}
        summary_rows.append({"group": key, **entry, "verdict": verdict})
    summary_path = ctx.out_dir / "control4_raw_preserving" / "summary.csv"
    write_csv(
        summary_path,
        [
            "group",
            "variant",
            "degree",
            "max_distance",
            "argmax_frame",
            "max_tolerance",
            "filtration_range",
            "n_frames_checked",
            "all_within_tolerance",
            "verdict",
        ],
        summary_rows,
    )
    ctx.register_table(summary_path)
    figure_path = (
        ctx.out_dir / "control4_raw_preserving" / "figure_raw_preserving.png"
    )
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for column_index, variant_name in enumerate(("translation", "rotation")):
        axis = axes[column_index]
        for degree in (DEGREE, SECONDARY_DEGREE):
            values = [
                row["distance"]
                for row in frame_rows
                if row["variant"] == variant_name and row["degree"] == degree
            ]
            axis.plot(
                np.arange(len(values)),
                np.maximum(values, 1e-18),
                label=f"H{degree}",
                linewidth=1.0,
            )
        tolerance_values = [
            row["tolerance"]
            for row in frame_rows
            if row["variant"] == variant_name and row["degree"] == DEGREE
        ]
        if tolerance_values:
            axis.axhline(
                tolerance_values[0], color="#c1440e", linestyle="--", label="tolerance"
            )
        axis.set_yscale("log")
        axis.set_title(variant_name)
        axis.set_xlabel("frame")
        axis.set_ylabel("per-frame bottleneck distance")
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)
    if all(row["verdict"] == "PASS" for row in summary_rows):
        overall = "PASS"
    else:
        overall = "FAIL"
    eta_values = [
        row["abs_delta_eta"]
        for row in diagnostics_rows
        if row["abs_delta_eta"] is not None
    ]
    max_diagnostics = {
        "max_abs_delta_L": nanmax_or_nan([row["abs_delta_L"] for row in diagnostics_rows]),
        "max_abs_delta_R": nanmax_or_nan([row["abs_delta_R"] for row in diagnostics_rows]),
        "max_abs_delta_eta": nanmax_or_nan(eta_values),
        "max_abs_delta_speed": nanmax_or_nan(
            [row["max_abs_delta_speed"] for row in diagnostics_rows]
        ),
        "max_abs_delta_angle": nanmax_or_nan(
            [row["max_abs_delta_angle"] for row in diagnostics_rows]
        ),
        "max_compact_difference": nanmax_or_nan(
            [row["compact_max_abs_difference"] for row in diagnostics_rows]
        ),
    }
    ctx.verdicts["raw_preserving"] = {
        "verdict": overall,
        "groups": summary_rows,
        "max_diagnostic_changes": max_diagnostics,
    }
    ctx.log(f"control4 raw-preserving: verdict={overall}")
    return {"summary": summary_rows, "diagnostics": max_diagnostics, "verdict": overall}


def nearest_centroid(train_features, train_labels, test_features, labels) -> np.ndarray:
    median = np.nanmedian(train_features, axis=0)
    median = np.where(np.isfinite(median), median, 0.0)
    train_filled = np.where(np.isnan(train_features), median, train_features)
    test_filled = np.where(np.isnan(test_features), median, test_features)
    mean = train_filled.mean(axis=0)
    std = train_filled.std(axis=0)
    std = np.where(std > 0.0, std, 1.0)
    train_scaled = (train_filled - mean) / std
    test_scaled = (test_filled - mean) / std
    centroids = np.vstack(
        [train_scaled[train_labels == label].mean(axis=0) for label in labels]
    )
    distances = np.sum(
        (test_scaled[:, None, :] - centroids[None, :, :]) ** 2, axis=2
    )
    return np.asarray([labels[index] for index in np.argmin(distances, axis=1)])


def balanced_error(true_labels, predicted_labels, labels) -> float:
    recalls = []
    for label in labels:
        mask = true_labels == label
        if not np.any(mask):
            continue
        recalls.append(float(np.mean(predicted_labels[mask] == label)))
    if not recalls:
        return float("nan")
    return float(1.0 - np.mean(recalls))


def control5_coarse_sampling(ctx: RunContext) -> dict:
    ctx.log("control5 very coarse sampling: start")
    rows: list[dict] = []
    for family in FAMILIES:
        for sigma in SIGMAS:
            e95 = ctx.floors.get((family, sigma), 0.0)
            for stride in COARSE_STRIDES:
                for class_name in generators.SCIENTIFIC_CLASSES:
                    for seed in SEEDS_COARSE_TRAIN + SEEDS_COARSE_TEST:
                        ctx.check_budget()
                        split = (
                            "train" if seed in SEEDS_COARSE_TRAIN else "test"
                        )
                        trajectory = generators.build_trajectory(
                            family, class_name, seed, sigma, stride
                        )
                        diagrams = ctx.diagram_cache.get(
                            family, trajectory.frames, (DEGREE,)
                        )
                        name = workload_name(
                            family, class_name, seed, sigma, stride
                        )
                        pairs = ctx.pair_cache(f"{name}_c5_d0")
                        diagnostics = compute_path_diagnostics(
                            diagrams[DEGREE],
                            trajectory.timestamps,
                            pairs.metric(diagrams[DEGREE]),
                        )
                        compact = _compact_vector(diagnostics, 0.0)
                        compact_calibrated = _compact_vector(diagnostics, e95)
                        n_angles = int(np.size(diagnostics.comparison_angles))
                        n_valid = int(np.sum(diagnostics.comparison_valid))
                        rows.append(
                            {
                                "family": family,
                                "sigma": sigma,
                                "stride": stride,
                                "class": class_name,
                                "seed": seed,
                                "split": split,
                                "n_frames": int(trajectory.frames.shape[0]),
                                "L": diagnostics.length,
                                "R": diagnostics.displacement,
                                "eta": diagnostics.efficiency,
                                "speed_mean": compact[3],
                                "speed_std": compact[4],
                                "speed_max": compact[5],
                                "speed_change_mean_signed": compact[6],
                                "speed_change_mean_abs": compact[7],
                                "speed_change_max_abs": compact[8],
                                "mean_cosine": compact[9],
                                "angle_valid_fraction": compact[10],
                                "efficiency_valid_flag": compact[11],
                                "efficiency_valid_flag_calibrated": compact_calibrated[11],
                                "angle_valid_fraction_calibrated": compact_calibrated[10],
                                "n_angles": n_angles,
                                "n_angles_valid": n_valid,
                                "e95": e95,
                            }
                        )
                        pairs.save()
    table_path = ctx.out_dir / "control5_coarse_sampling" / "per_trajectory.csv"
    write_csv(
        table_path,
        [
            "family",
            "sigma",
            "stride",
            "class",
            "seed",
            "split",
            "n_frames",
            "L",
            "R",
            "eta",
            "speed_mean",
            "speed_std",
            "speed_max",
            "speed_change_mean_signed",
            "speed_change_mean_abs",
            "speed_change_max_abs",
            "mean_cosine",
            "angle_valid_fraction",
            "efficiency_valid_flag",
            "efficiency_valid_flag_calibrated",
            "angle_valid_fraction_calibrated",
            "n_angles",
            "n_angles_valid",
            "e95",
        ],
        rows,
    )
    ctx.register_table(table_path)

    feature_names = (
        "L",
        "R",
        "eta",
        "speed_mean",
        "speed_std",
        "speed_max",
        "speed_change_mean_signed",
        "speed_change_mean_abs",
        "speed_change_max_abs",
        "mean_cosine",
        "angle_valid_fraction",
        "efficiency_valid_flag",
    )
    labels = tuple(generators.SCIENTIFIC_CLASSES)
    prediction_rows = []
    confusion_rows = []
    separation_rows = []
    for family in FAMILIES:
        for sigma in SIGMAS:
            for stride in COARSE_STRIDES:
                cell = [
                    row
                    for row in rows
                    if row["family"] == family
                    and row["sigma"] == sigma
                    and row["stride"] == stride
                ]
                train = [row for row in cell if row["split"] == "train"]
                test = [row for row in cell if row["split"] == "test"]
                train_features = np.asarray(
                    [[row[name] for name in feature_names] for row in train],
                    dtype=float,
                )
                test_features = np.asarray(
                    [[row[name] for name in feature_names] for row in test],
                    dtype=float,
                )
                train_labels = np.asarray([row["class"] for row in train], dtype=object)
                test_labels = np.asarray([row["class"] for row in test], dtype=object)
                predicted = nearest_centroid(
                    train_features, train_labels, test_features, labels
                )
                error = balanced_error(test_labels, predicted, labels)
                for row, prediction in zip(test, predicted):
                    prediction_rows.append(
                        {
                            "family": family,
                            "sigma": sigma,
                            "stride": stride,
                            "seed": row["seed"],
                            "class": row["class"],
                            "predicted_class": prediction,
                            "correct": bool(row["class"] == prediction),
                            "split": row["split"],
                        }
                    )
                for true_label in labels:
                    for predicted_label in labels:
                        confusion_rows.append(
                            {
                                "family": family,
                                "sigma": sigma,
                                "stride": stride,
                                "true_class": true_label,
                                "predicted_class": predicted_label,
                                "count": int(
                                    np.sum(
                                        (test_labels == true_label)
                                        & (predicted == predicted_label)
                                    )
                                ),
                            }
                        )
                recalls = {
                    label: (
                        float(
                            np.mean(predicted[test_labels == label] == label)
                        )
                        if np.any(test_labels == label)
                        else float("nan")
                    )
                    for label in labels
                }
                efficiency_coverage = float(
                    np.mean([row["efficiency_valid_flag"] for row in test])
                )
                efficiency_coverage_calibrated = float(
                    np.mean(
                        [row["efficiency_valid_flag_calibrated"] for row in test]
                    )
                )
                angle_coverage = nanmean_or_nan(
                    [row["angle_valid_fraction"] for row in test]
                )
                angle_coverage_calibrated = nanmean_or_nan(
                    [row["angle_valid_fraction_calibrated"] for row in test]
                )
                if error < 0.5:
                    verdict = "PASS"
                elif error < 2.0 / 3.0:
                    verdict = "RESIDUAL"
                else:
                    verdict = "FAIL"
                separation_rows.append(
                    {
                        "family": family,
                        "sigma": sigma,
                        "stride": stride,
                        "n_train": len(train),
                        "n_test": len(test),
                        "balanced_error": error,
                        "recall_return": recalls["return"],
                        "recall_ramp": recalls["ramp"],
                        "recall_jump": recalls["jump"],
                        "efficiency_coverage": efficiency_coverage,
                        "efficiency_coverage_calibrated": efficiency_coverage_calibrated,
                        "angle_coverage_mean": angle_coverage,
                        "angle_coverage_calibrated": angle_coverage_calibrated,
                        "verdict": verdict,
                    }
                )
                ctx.log(
                    f"control5 {family} sigma={sigma} stride={stride}: "
                    f"balanced_error={error:.3f}, verdict={verdict}"
                )
    prediction_path = (
        ctx.out_dir / "control5_coarse_sampling" / "predictions.csv"
    )
    write_csv(
        prediction_path,
        [
            "family",
            "sigma",
            "stride",
            "seed",
            "class",
            "predicted_class",
            "correct",
            "split",
        ],
        prediction_rows,
    )
    ctx.register_table(prediction_path)
    confusion_path = ctx.out_dir / "control5_coarse_sampling" / "confusion.csv"
    write_csv(
        confusion_path,
        [
            "family",
            "sigma",
            "stride",
            "true_class",
            "predicted_class",
            "count",
        ],
        confusion_rows,
    )
    ctx.register_table(confusion_path)
    separation_path = (
        ctx.out_dir / "control5_coarse_sampling" / "separation.csv"
    )
    write_csv(
        separation_path,
        [
            "family",
            "sigma",
            "stride",
            "n_train",
            "n_test",
            "balanced_error",
            "recall_return",
            "recall_ramp",
            "recall_jump",
            "efficiency_coverage",
            "efficiency_coverage_calibrated",
            "angle_coverage_mean",
            "angle_coverage_calibrated",
            "verdict",
        ],
        separation_rows,
    )
    ctx.register_table(separation_path)

    figure_path = (
        ctx.out_dir / "control5_coarse_sampling" / "figure_coarse_sampling.png"
    )
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    colors = {"return": "#3b6ea5", "ramp": "#c1440e", "jump": "#2e7d32"}
    for column_index, stride in enumerate(COARSE_STRIDES):
        axis = axes[column_index]
        for row in rows:
            if row["family"] == "A" and row["stride"] == stride:
                axis.scatter(
                    row["L"],
                    np.maximum(row["R"], 1e-12),
                    s=14,
                    alpha=0.6,
                    color=colors[row["class"]],
                    label=row["class"],
                )
        handles, labels_seen = axis.get_legend_handles_labels()
        unique = dict(zip(labels_seen, handles))
        axis.legend(unique.values(), unique.keys(), fontsize=8)
        axis.set_yscale("log")
        axis.set_title(f"Family A, stride {stride}, all sigmas")
        axis.set_xlabel("path length L")
        axis.set_ylabel("endpoint displacement R")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)

    if all(row["verdict"] == "PASS" for row in separation_rows):
        overall = "PASS"
    elif any(row["verdict"] == "FAIL" for row in separation_rows):
        overall = "FAIL"
    else:
        overall = "RESIDUAL"
    ctx.verdicts["coarse_sampling"] = {
        "verdict": overall,
        "cells": separation_rows,
    }
    ctx.log(f"control5 coarse sampling: verdict={overall}")
    return {"cells": separation_rows, "verdict": overall}


def dense_distance_matrix(diagrams, pairs, n_frames: int) -> np.ndarray:
    matrix = np.zeros((n_frames, n_frames), dtype=np.float64)
    for i in range(n_frames):
        for j in range(i + 1, n_frames):
            value = pairs.get(i, j, diagrams)
            matrix[i, j] = value
            matrix[j, i] = value
    return matrix


def control6_adversarial_matrix(ctx: RunContext) -> dict:
    ctx.log("control6 adversarial full-matrix-sufficient: start")
    rows: list[dict] = []
    plot_payload: dict[tuple[str, float], dict] = {}
    for family in FAMILIES:
        for sigma in SIGMAS:
            for seed in SEEDS_ADVERSARIAL:
                ctx.check_budget()
                base = generators.build_control(
                    "static", family, seed, sigma, ADVERSARIAL_STRIDE
                )
                clean = raw_frames_at_z(family, base.latent, base.z)
                noise = base.frames - clean
                reconstruction_error = float(
                    np.max(np.abs(clean + noise - base.frames))
                )
                base_diagrams = ctx.diagram_cache.get(family, base.frames, (DEGREE,))
                cache_prefix = (
                    f"{family}_static_{seed}_s{sigma_tag(sigma)}"
                    f"_str{ADVERSARIAL_STRIDE}_c6"
                )
                pairs_base = ctx.pair_cache(f"{cache_prefix}_base_d0")
                n_frames = base.frames.shape[0]
                matrix_base = dense_distance_matrix(
                    base_diagrams[DEGREE], pairs_base, n_frames
                )
                off_diagonal = ~np.eye(n_frames, dtype=bool)
                full_null = float(np.max(matrix_base[off_diagonal]))
                diag_base = compute_path_diagnostics(
                    base_diagrams[DEGREE],
                    base.timestamps,
                    pairs_base.metric(base_diagrams[DEGREE]),
                )
                adjacent_null = np.asarray(diag_base.adjacent_distances)
                adj_null = float(np.max(adjacent_null))
                threshold = ctx.floors.get((family, sigma), 0.0)
                detect_full_null = bool(full_null > threshold)
                detect_compact_null = bool(adj_null > threshold)
                for injection_z in INJECTION_Z_VALUES:
                    injected_source = raw_frames_at_z(
                        family, base.latent, np.asarray([injection_z])
                    )[0]
                    injected_frames = np.array(base.frames, copy=True)
                    injected_frames[INJECTION_INDEX] = (
                        injected_source + noise[INJECTION_INDEX]
                    )
                    injected = custom_trajectory(
                        base,
                        f"injected_z{str(injection_z).replace('.', 'p')}",
                        injected_frames,
                        base.z,
                    )
                    injected_diagrams = ctx.diagram_cache.get(
                        family, injected.frames, (DEGREE,)
                    )
                    pairs_inj = ctx.pair_cache(
                        f"{cache_prefix}_inj_z{sigma_tag(injection_z)}_d0"
                    )
                    matrix_inj = dense_distance_matrix(
                        injected_diagrams[DEGREE], pairs_inj, n_frames
                    )
                    full_inj = float(np.max(matrix_inj[off_diagonal]))
                    argmax_flat = int(
                        np.argmax(np.where(off_diagonal, matrix_inj, -1.0))
                    )
                    argmax_i, argmax_j = divmod(argmax_flat, n_frames)
                    localization_full = INJECTION_INDEX in (argmax_i, argmax_j)
                    diag_inj = compute_path_diagnostics(
                        injected_diagrams[DEGREE],
                        injected.timestamps,
                        pairs_inj.metric(injected_diagrams[DEGREE]),
                    )
                    adjacent_inj = np.asarray(diag_inj.adjacent_distances)
                    adj_inj = float(np.max(adjacent_inj))
                    adj_argmax = int(np.argmax(adjacent_inj))
                    localization_compact = adj_argmax in (
                        INJECTION_INDEX - 1,
                        INJECTION_INDEX,
                    )
                    compact_null = _compact_vector(diag_base, 0.0)
                    compact_inj = _compact_vector(diag_inj, 0.0)
                    detect_full_inj = bool(full_inj > threshold)
                    detect_compact_inj = bool(adj_inj > threshold)
                    attributed_full = bool(
                        full_inj > full_null and localization_full
                    )
                    attributed_compact = bool(
                        adj_inj > adj_null and localization_compact
                    )
                    n_full_calls = n_frames * (n_frames - 1) // 2
                    n_compact_calls = int(diag_base.n_intervals) + int(
                        np.size(diag_base.comparison_angles)
                    )
                    rows.append(
                        {
                            "family": family,
                            "seed": seed,
                            "sigma": sigma,
                            "injection_z": injection_z,
                            "injection_primary": injection_z
                            == INJECTION_Z_PRIMARY,
                            "n_frames": n_frames,
                            "injection_index": INJECTION_INDEX,
                            "reconstruction_max_abs_error": reconstruction_error,
                            "threshold_e95": threshold,
                            "full_dim": n_full_calls,
                            "compact_dim": int(compact_null.size),
                            "full_distance_calls": n_full_calls,
                            "compact_distance_calls": n_compact_calls,
                            "full_max_null": full_null,
                            "full_max_injected": full_inj,
                            "full_above_null": full_inj - full_null,
                            "full_ratio": (
                                full_inj / full_null if full_null > 0.0 else None
                            ),
                            "full_argmax_i": argmax_i,
                            "full_argmax_j": argmax_j,
                            "full_localization_ok": localization_full,
                            "adjacent_max_null": adj_null,
                            "adjacent_max_injected": adj_inj,
                            "adjacent_above_null": adj_inj - adj_null,
                            "adjacent_ratio": (
                                adj_inj / adj_null if adj_null > 0.0 else None
                            ),
                            "adjacent_argmax_interval": adj_argmax,
                            "compact_localization_ok": localization_compact,
                            "detect_full_null": detect_full_null,
                            "detect_full_injected": detect_full_inj,
                            "detect_compact_null": detect_compact_null,
                            "detect_compact_injected": detect_compact_inj,
                            "attributed_full": attributed_full,
                            "attributed_compact": attributed_compact,
                            "compact_null_eta": compact_null[2],
                            "compact_injected_eta": compact_inj[2],
                        }
                    )
                    if (
                        injection_z == INJECTION_Z_PRIMARY
                        and (family, sigma) not in plot_payload
                    ):
                        plot_payload[(family, sigma)] = {
                            "matrix_null": matrix_base,
                            "matrix_injected": matrix_inj,
                            "adjacent_null": adjacent_null,
                            "adjacent_injected": adjacent_inj,
                            "seed": seed,
                            "injection_z": injection_z,
                        }
                    pairs_inj.save()
                pairs_base.save()
            ctx.log(
                f"control6 {family} sigma={sigma}: completed "
                f"{len(SEEDS_ADVERSARIAL)} seeds and "
                f"{len(INJECTION_Z_VALUES)} injections"
            )
    table_path = (
        ctx.out_dir / "control6_adversarial_matrix" / "per_trajectory.csv"
    )
    write_csv(
        table_path,
        [
            "family",
            "seed",
            "sigma",
            "injection_z",
            "injection_primary",
            "n_frames",
            "injection_index",
            "reconstruction_max_abs_error",
            "threshold_e95",
            "full_dim",
            "compact_dim",
            "full_distance_calls",
            "compact_distance_calls",
            "full_max_null",
            "full_max_injected",
            "full_above_null",
            "full_ratio",
            "full_argmax_i",
            "full_argmax_j",
            "full_localization_ok",
            "adjacent_max_null",
            "adjacent_max_injected",
            "adjacent_above_null",
            "adjacent_ratio",
            "adjacent_argmax_interval",
            "compact_localization_ok",
            "detect_full_null",
            "detect_full_injected",
            "detect_compact_null",
            "detect_compact_injected",
            "attributed_full",
            "attributed_compact",
            "compact_null_eta",
            "compact_injected_eta",
        ],
        rows,
    )
    ctx.register_table(table_path)
    summary_rows = []
    for family in FAMILIES:
        for sigma in SIGMAS:
            for injection_z in INJECTION_Z_VALUES:
                cell = [
                    row
                    for row in rows
                    if row["family"] == family
                    and row["sigma"] == sigma
                    and row["injection_z"] == injection_z
                ]
                n = len(cell)
                full_detect = sum(row["detect_full_injected"] for row in cell)
                compact_detect = sum(row["detect_compact_injected"] for row in cell)
                false_full = sum(row["detect_full_null"] for row in cell)
                false_compact = sum(row["detect_compact_null"] for row in cell)
                full_localization = sum(row["full_localization_ok"] for row in cell)
                compact_localization = sum(
                    row["compact_localization_ok"] for row in cell
                )
                attributed_full = sum(row["attributed_full"] for row in cell)
                attributed_compact = sum(row["attributed_compact"] for row in cell)
                ratio_values = [
                    row["full_ratio"]
                    for row in cell
                    if row["full_ratio"] is not None
                ]
                summary_rows.append(
                    {
                        "family": family,
                        "sigma": sigma,
                        "injection_z": injection_z,
                        "injection_primary": injection_z == INJECTION_Z_PRIMARY,
                        "n_trajectories": n,
                        "full_detected_injected": full_detect,
                        "compact_detected_injected": compact_detect,
                        "full_attributed": attributed_full,
                        "compact_attributed": attributed_compact,
                        "full_false_detections_on_null": false_full,
                        "compact_false_detections_on_null": false_compact,
                        "full_localization_ok": full_localization,
                        "compact_localization_ok": compact_localization,
                        "median_full_ratio": (
                            float(np.median(ratio_values))
                            if ratio_values
                            else None
                        ),
                        "full_dim": int(cell[0]["full_dim"]),
                        "compact_dim": int(cell[0]["compact_dim"]),
                        "full_distance_calls": int(cell[0]["full_distance_calls"]),
                        "compact_distance_calls": int(
                            cell[0]["compact_distance_calls"]
                        ),
                        "max_reconstruction_error": nanmax_or_nan(
                            [row["reconstruction_max_abs_error"] for row in cell]
                        ),
                    }
                )
    summary_path = (
        ctx.out_dir / "control6_adversarial_matrix" / "summary.csv"
    )
    write_csv(
        summary_path,
        [
            "family",
            "sigma",
            "injection_z",
            "injection_primary",
            "n_trajectories",
            "full_detected_injected",
            "compact_detected_injected",
            "full_attributed",
            "compact_attributed",
            "full_false_detections_on_null",
            "compact_false_detections_on_null",
            "full_localization_ok",
            "compact_localization_ok",
            "median_full_ratio",
            "full_dim",
            "compact_dim",
            "full_distance_calls",
            "compact_distance_calls",
            "max_reconstruction_error",
        ],
        summary_rows,
    )
    ctx.register_table(summary_path)

    figure_path = (
        ctx.out_dir / "control6_adversarial_matrix" / "figure_adversarial.png"
    )
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for row_index, family in enumerate(FAMILIES):
        payload = plot_payload[(family, 0.05)]
        axis = axes[row_index][0]
        image = axis.imshow(payload["matrix_injected"], cmap="viridis", aspect="auto")
        axis.set_title(
            f"Family {family}, sigma=0.05, injected z="
            f"{payload['injection_z']} matrix (seed {payload['seed']})"
        )
        axis.set_xlabel("frame")
        axis.set_ylabel("frame")
        figure.colorbar(image, ax=axis, fraction=0.046)
        axis = axes[row_index][1]
        axis.plot(
            np.arange(payload["adjacent_null"].size),
            np.maximum(payload["adjacent_null"], 1e-18),
            "o-",
            label="null",
            linewidth=1.0,
        )
        axis.plot(
            np.arange(payload["adjacent_injected"].size),
            np.maximum(payload["adjacent_injected"], 1e-18),
            "s--",
            label="injected",
            linewidth=1.0,
        )
        axis.axvline(
            INJECTION_INDEX - 1, color="#c1440e", linestyle=":", label="injection"
        )
        axis.set_yscale("log")
        axis.set_title(f"Family {family}: adjacent distances")
        axis.set_xlabel("interval index")
        axis.set_ylabel("distance")
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(figure_path, dpi=FIGURE_DPI)
    plt.close(figure)
    ctx.register_figure(figure_path)

    primary_cells = [row for row in summary_rows if row["injection_primary"]]
    near_cells = [row for row in summary_rows if not row["injection_primary"]]
    full_ok = all(
        row["full_attributed"] >= max(1, int(0.9 * row["n_trajectories"]))
        for row in primary_cells
    )
    compact_ok = all(
        row["compact_attributed"] >= max(1, int(0.9 * row["n_trajectories"]))
        for row in primary_cells
    )
    localization_ok = all(
        row["full_localization_ok"] >= max(1, int(0.9 * row["n_trajectories"]))
        for row in primary_cells
    )
    near_floor_ok = all(
        row["full_attributed"] >= max(1, int(0.9 * row["n_trajectories"]))
        and row["compact_attributed"] >= max(1, int(0.9 * row["n_trajectories"]))
        for row in near_cells
    )
    if full_ok and compact_ok and localization_ok and near_floor_ok:
        overall = "PASS"
    elif full_ok and compact_ok and localization_ok:
        overall = "RESIDUAL"
    else:
        overall = "FAIL"
    ctx.verdicts["adversarial_matrix"] = {
        "verdict": overall,
        "primary_full_attributed_ok": full_ok,
        "primary_compact_attributed_ok": compact_ok,
        "primary_localization_ok": localization_ok,
        "near_floor_attributed_ok": near_floor_ok,
        "cells": summary_rows,
    }
    ctx.log(f"control6 adversarial: verdict={overall}")
    return {"summary": summary_rows, "verdict": overall}


def md_value(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return "n/a"
        if number != 0.0 and (abs(number) < 1e-4 or abs(number) >= 1e6):
            return f"{number:.3e}"
        return f"{number:.6g}"
    return str(value)


def md_table(headers, rows, columns) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        values = []
        for column in columns:
            if isinstance(row, dict):
                values.append(md_value(row.get(column)))
            else:
                values.append(md_value(row))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(ctx: RunContext, results: dict, manifest: dict, report_path: Path) -> str:
    lines: list[str] = []
    lines.append("# WP-3.3 null, baseline-favorable, and stress controls")
    lines.append("")
    lines.append(
        "This report is the WP-3.3 artifact for gate G3. It contains the "
        "falsification controls requested by the research plan: constant-diagram "
        "nulls, the equal-speed ordering control, time reparameterization, "
        "raw-label-preserving transformations, very coarse sampling, and a "
        "documented adversarial full-matrix-sufficient case. All controls use "
        "the frozen package modules without modification and a private cache; "
        "the runner distance caches under `research_review/results/cache/` were "
        "not read or written."
    )
    lines.append("")
    lines.append("## 0. Provenance and verdict summary")
    lines.append("")
    lines.append(f"- exact command: `{manifest['command']}`")
    lines.append(f"- working directory: `{manifest['cwd']}`")
    lines.append(f"- started (UTC): {manifest['started_utc']}")
    lines.append(f"- finished (UTC): {manifest['finished_utc']}")
    lines.append(f"- wall time: {manifest['wall_seconds']:.1f} s")
    lines.append(
        f"- worker processes: {manifest['workers']} (budget "
        f"{manifest['budget_seconds']:.0f} s)"
    )
    lines.append(f"- peak RAM (ru_maxrss): {manifest['peak_ram_mb']:.1f} MB")
    lines.append(f"- private cache: `{manifest['cache_dir']}`")
    lines.append(f"- report file: `{report_path}`")
    lines.append("")
    verdict_rows = []
    for key in CONTROL_KEYS:
        if key in results and "verdict" in results[key]:
            verdict = results[key]["verdict"]
        elif key in results and "error" in results[key]:
            verdict = "INCOMPLETE"
        else:
            verdict = "NOT_RUN"
        verdict_rows.append(
            {
                "control": key,
                "verdict": verdict,
                "wall_seconds": ctx.timings.get(key),
            }
        )
    lines.append(
        md_table(
            ["control", "verdict", "wall time (s)"],
            verdict_rows,
            ["control", "verdict", "wall_seconds"],
        )
    )
    if ctx.skipped:
        lines.append("")
        lines.append(
            "Controls that could not be completed inside the declared budget: "
            + ", ".join(f"`{key}`" for key in ctx.skipped)
            + "."
        )
    lines.append("")

    lines.append("## 1. Constant-diagram null (static z = 0.5)")
    lines.append("")
    static = results.get("static_null", {})
    if "summary" in static:
        lines.append(
            "Calibration uses training seeds 1000 to 1004 and evaluation uses "
            "seeds 1005 to 1019, a disjoint training-namespace split. The "
            "threshold `e95` is the 95th percentile of pooled calibration "
            "adjacent distances at the same family and sigma. A cell fails when "
            "a seed shows a strong monotone trend (Spearman p below 0.001 with "
            "absolute rho above 0.5) or when two or more seeds show exceedance "
            "clustering at the G2-verified longest-run permutation p below "
            "0.01; it is RESIDUAL when the pooled exceedance count exceeds the "
            "99 percent binomial bound or when a single seed shows weaker "
            "trend or clustering signatures."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "family",
                    "sigma",
                    "e95",
                    "n above",
                    "n intervals",
                    "rate",
                    "binom p",
                    "seeds trend fail",
                    "seeds cluster p<0.01",
                    "max run",
                    "verdict",
                ],
                static["summary"],
                [
                    "family",
                    "sigma",
                    "e95",
                    "n_above_e95",
                    "n_intervals",
                    "exceedance_rate",
                    "binom_p",
                    "n_seed_trend_fail",
                    "n_seed_cluster_p01",
                    "max_run",
                    "verdict",
                ],
            )
        )
        for key in sorted(static.get("assertions", {})):
            entry = static["assertions"][key]
            lines.append("")
            lines.append(
                f"Degenerate assertions at sigma = 0 for {key}: nonzero "
                f"adjacent-distance trajectories {entry['n_nonzero_adjacent_trajectories']}, "
                f"max absolute adjacent distance {md_value(entry['max_abs_adjacent'])}, "
                f"L zero everywhere {md_value(entry['L_zero_all'])}, eta undefined "
                f"everywhere {md_value(entry['eta_none_all'])}, angles unresolved "
                f"everywhere {md_value(entry['angles_unresolved_all'])}, triangle "
                f"excess unresolved everywhere {md_value(entry['triangle_excess_unresolved_all'])}, "
                f"speed changes exactly zero {md_value(entry['speed_change_zero_all'])}, "
                f"efficiency flag false everywhere {md_value(entry['efficiency_flag_false_all'])}, "
                f"unique H0 diagrams per trajectory {entry['unique_h0_diagrams']}, "
                f"verdict {entry['verdict']}."
            )
        lines.append("")
        lines.append(
            "The full adjacent-distance samples are machine readable in "
            "`control1_static_null/adjacent_distances.csv` for the primary H0 "
            "channel; the per-trajectory summaries are in "
            "`control1_static_null/per_trajectory.csv`. Figure: "
            "`control1_static_null/figure_static_null.png`."
        )
    else:
        lines.append("Control 1 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 2. Equal-speed ordering control")
    lines.append("")
    matched = results.get("matched_ordering", {})
    if "groups" in matched:
        lines.append(
            "The frozen `matched_forward` and `matched_folded` controls share one "
            "latent and noise realization and have identical consecutive |dz| "
            "steps and identical endpoints. The speed, L, R, and eta agreement "
            "is reported as matched-hits at 1e-9; the diagnostic separation is "
            "the count of seeds whose comparison-angle or triangle-excess arrays "
            "differ by more than 1e-6. The Family B rows are an auxiliary "
            "construction at sigma = 0 built from the frozen field formula; the "
            "frozen generator defines the matched controls for Family A only."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "group",
                    "seeds",
                    "structural ok",
                    "angle/shape separated",
                    "separation hits",
                    "all four matched at 1e-9",
                    "L matched",
                    "R matched",
                    "eta matched",
                    "max speed matched",
                ],
                matched["groups"],
                [
                    "group",
                    "n_seeds",
                    "structural_ok",
                    "angle_or_shape_separated",
                    "separation_hits",
                    "matched_hits_within_1e-9",
                    "matched_L_hits",
                    "matched_R_hits",
                    "matched_eta_hits",
                    "matched_speed_hits",
                ],
            )
        )
        lines.append("")
        lines.append(
            "No seed matches L, R, eta, and the speed sequence within 1e-9. "
            "Consecutive |dz| steps are identical by construction, but the "
            "bottleneck distance is nonlinear in the separation z, so the "
            "forward ordering (0.5, 1.0, 1.5, 1.0, 0.5) and the folded ordering "
            "(0.5, 1.0, 0.5, 1.0, 0.5) produce different step distances, hence "
            "different L and different speed sequences. The endpoint "
            "displacement R is unchanged at sigma = 0 (both zero) and is noise "
            "driven at sigma = 0.05, and eta inherits R. The angle and "
            "triangle-excess sequences separate the two orderings in every "
            "seed, which is the C3 diagnostic comparison; the matched-step "
            "property alone is not sufficient to make the path summaries "
            "equal."
        )
        lines.append("")
        lines.append(
            "The comparison stays outside the three-class accuracy calculation. "
            "Figure: `control2_matched_ordering/figure_matched_ordering.png`."
        )
    else:
        lines.append("Control 2 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 3. Time reparameterization")
    lines.append("")
    reparam = results.get("time_reparam", {})
    if "summary" in reparam:
        lines.append(
            "Two monotone warps are tested: `u**1.5` and a piecewise-linear warp "
            "with a fast first quarter (slope 2) and a slow remainder (slope "
            "2/3). The clock-warp variant keeps the master states and changes "
            "the timestamps; the resampled variant selects master frames under "
            "the warped clock and re-times them uniformly. Qualified intervals "
            "restrict the derivative comparison to midpoint u at least 0.1, "
            "where the local-derivative approximation is not dominated by the "
            "vanishing derivative of `u**1.5` at zero."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "group",
                    "exact same-states",
                    "exact resampled",
                    "fresh step checks",
                    "preserved angles",
                    "max abs rel dev qualified",
                    "max abs rel dev low u",
                    "derivative ok",
                    "verdict",
                ],
                reparam["summary"],
                [
                    "group",
                    "exact_same_states_all",
                    "exact_resampled_all",
                    "fresh_step_checks_exact_all",
                    "preserved_angles_exact_all",
                    "max_abs_relative_deviation_qualified",
                    "max_abs_relative_deviation_low_u",
                    "derivative_law_ok",
                    "verdict",
                ],
            )
        )
        lines.append("")
        lines.append(
            "For the piecewise-linear warp the local derivative is constant on "
            "every grid interval (the kink sits exactly on a master grid point), "
            "so the observed ratio must match the prediction to floating-point "
            "precision; that is the sharp pass criterion. For `u**1.5` the "
            "observed error grows as the curvature term, and the low-u column is "
            "the expected degradation regime rather than a failure. Figure: "
            "`control3_time_reparameterization/figure_reparam.png`."
        )
    else:
        lines.append("Control 3 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 4. Raw-label-preserving transformations")
    lines.append("")
    raw = results.get("raw_preserving", {})
    if "summary" in raw:
        lines.append(
            "A constant rigid translation and a fixed global rotation of 0.7 "
            "radians are applied to an identical Family A static realization. "
            "The declared bound is 1e-7 times max(1, filtration range) with the "
            "range measured as the largest pairwise distance in the base "
            "realization. Diagnostic changes are reported for both degrees in "
            "the per-frame table and for degree 0 in the diagnostic table."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "group",
                    "frames checked",
                    "max distance",
                    "tolerance",
                    "argmax frame",
                    "verdict",
                ],
                raw["summary"],
                [
                    "group",
                    "n_frames_checked",
                    "max_distance",
                    "max_tolerance",
                    "argmax_frame",
                    "verdict",
                ],
            )
        )
        diagnostics = raw.get("diagnostics", {})
        lines.append("")
        lines.append(
            "Largest diagnostic changes across all seeds and sigmas: "
            f"|dL| {md_value(diagnostics.get('max_abs_delta_L'))}, "
            f"|dR| {md_value(diagnostics.get('max_abs_delta_R'))}, "
            f"|deta| {md_value(diagnostics.get('max_abs_delta_eta'))}, "
            f"|dspeed| {md_value(diagnostics.get('max_abs_delta_speed'))}, "
            f"|dangle| {md_value(diagnostics.get('max_abs_delta_angle'))}, "
            f"max compact difference "
            f"{md_value(diagnostics.get('max_compact_difference'))}. "
            "Figure: `control4_raw_preserving/figure_raw_preserving.png`."
        )
    else:
        lines.append("Control 4 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 5. Very coarse sampling")
    lines.append("")
    coarse = results.get("coarse_sampling", {})
    if "cells" in coarse:
        lines.append(
            "Strides 8 and 16 keep 17 and 9 frames on the fixed horizon. The "
            "separation check uses the 12-dimensional compact vector with "
            "nearest-centroid classification, standardization statistics fitted "
            "on training seeds only, and no hyperparameter tuning. Efficiency "
            "coverage is the fraction of test trajectories whose efficiency "
            "validity flag is one under exact-zero abstention; the calibrated "
            "columns use the control-1 e95 floor. The verdict thresholds are "
            "balanced error below 0.5 for PASS, below 2/3 for RESIDUAL, and at "
            "or above 2/3 (the three-class chance level) for FAIL."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "family",
                    "sigma",
                    "stride",
                    "balanced error",
                    "recall return",
                    "recall ramp",
                    "recall jump",
                    "efficiency coverage",
                    "angle coverage",
                    "verdict",
                ],
                coarse["cells"],
                [
                    "family",
                    "sigma",
                    "stride",
                    "balanced_error",
                    "recall_return",
                    "recall_ramp",
                    "recall_jump",
                    "efficiency_coverage",
                    "angle_coverage_mean",
                    "verdict",
                ],
            )
        )
        lines.append("")
        lines.append(
            "Coverage and performance are reported jointly in the same table so "
            "that abstention cannot manufacture robustness. Figure: "
            "`control5_coarse_sampling/figure_coarse_sampling.png`."
        )
    else:
        lines.append("Control 5 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 6. Adversarial full-matrix-sufficient case")
    lines.append("")
    adversarial = results.get("adversarial_matrix", {})
    if "summary" in adversarial:
        lines.append(
            "A single constant-diagram-null frame is replaced by a raw "
            "realization at a different separation with the same latent "
            "parameters and the same noise draw at that frame. The primary "
            "injection uses z = 3.0, where the two circles or bumps are cleanly "
            "separated and the diagram shift is large; a secondary near-floor "
            "injection uses z = 1.5. The full distance matrix and the compact "
            "maximum adjacent distance are both scored. A detection is called "
            "attributed only when the injected statistic strictly exceeds the "
            "null statistic and the argmax localizes the injected frame or its "
            "adjacent interval. The cost comparison is reported honestly: the "
            "full matrix carries T(T-1)/2 features and T(T-1)/2 distance calls "
            "against 12 compact features and roughly 2T-3 distance calls, and "
            "the full matrix localizes the injected frame exactly while the "
            "compact report localizes only the adjacent interval. This is a "
            "documented adversarial control, not a claimed win for the compact "
            "summaries."
        )
        lines.append("")
        lines.append(
            md_table(
                [
                    "family",
                    "sigma",
                    "injection z",
                    "attributed (full)",
                    "attributed (compact)",
                    "localization full",
                    "localization compact",
                    "false detections null (full)",
                    "false detections null (compact)",
                    "full dim",
                    "compact dim",
                    "full calls",
                    "compact calls",
                ],
                adversarial["summary"],
                [
                    "family",
                    "sigma",
                    "injection_z",
                    "full_attributed",
                    "compact_attributed",
                    "full_localization_ok",
                    "compact_localization_ok",
                    "full_false_detections_on_null",
                    "compact_false_detections_on_null",
                    "full_dim",
                    "compact_dim",
                    "full_distance_calls",
                    "compact_distance_calls",
                ],
            )
        )
        lines.append("")
        lines.append(
            "The per-pair e95 threshold is calibrated on adjacent distances and "
            "is a marginal, not a trajectory-level, threshold. At stride 8 the "
            "null adjacent maximum exceeds it in some seeds at sigma = 0.05 "
            "(see the false-detection columns), while the full-matrix null "
            "maximum exceeds it in nearly every seed, because the maximum over "
            "T(T-1)/2 weakly dependent entries is stochastically larger than "
            "the maximum over T-1 adjacent entries. A fair alarm comparison "
            "requires a trajectory-level calibration for both statistics; the "
            "attribution rule used here instead requires the injected "
            "statistic to exceed the paired null statistic and to localize the "
            "injection, so the detection comparison is not driven by that "
            "threshold mismatch. Figure: "
            "`control6_adversarial_matrix/figure_adversarial.png`."
        )
    else:
        lines.append("Control 6 did not complete; see `run_log.txt`.")
    lines.append("")

    lines.append("## 7. Files written")
    lines.append("")
    lines.append("Relative to the output directory:")
    lines.append("")
    for name in ctx.tables:
        lines.append(f"- `{name}`")
    for name in ctx.figures:
        lines.append(f"- `{name}`")
    lines.append("- `manifest.json`")
    lines.append("- `run_log.txt`")
    lines.append("- `SHA256SUMS`")
    lines.append("")
    lines.append(
        "The artifact manifest records input hashes, environment versions, "
        "seed namespaces, per-control verdicts, and the measured wall time and "
        "peak RAM. `SHA256SUMS` covers every file in the output directory and "
        "the report itself (listed with a `../reports/` relative path)."
    )
    lines.append("")

    lines.append("## 8. Limitations and residuals")
    lines.append("")
    lines.append(
        "Exceedance counts at e95 are binomial approximations because adjacent "
        "windows overlap; the trend, runs, and clustering diagnostics are "
        "reported alongside the count rather than replaced by it. Family B "
        "carries the larger diagram cardinalities and hence the slower "
        "bottleneck evaluations, so the coarse-sampling grid and the adversarial "
        "matrix control use strides 8 and 16. The equal-speed ordering control "
        "is defined by the frozen generator for Family A; the Family B variant "
        "at sigma = 0 is an auxiliary reproducibility construction and is "
        "labeled as such in the tables. The near-floor adversarial injection at "
        "z = 1.5 is not attributed for Family A at sigma = 0.05, where its "
        "diagram shift is comparable to the noise scale; that boundary is "
        "reported rather than hidden. The module hashes recorded in "
        "`manifest.json` differ from the hash table of the WP-3.1 "
        "raw-correctness report for `generators.py`, `persistence.py`, and "
        "`features.py`, while `diagram_metrics.py` and `path_diagnostics.py` "
        "match that table. The three listed hashes appear stale relative to "
        "the current working tree; this run used the current working-tree "
        "modules, re-verified the raw-frame evaluator against them bitwise, "
        "and re-checked the key static-null and translation-invariance "
        "properties in this work package."
    )
    lines.append("")
    for note in ctx.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_manifest(
    ctx: RunContext,
    results: dict,
    args,
    evaluator_report: dict,
    wall_seconds: float,
) -> dict:
    input_hashes = {}
    for name in INPUT_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            input_hashes[name] = sha256_file(path)
        else:
            input_hashes[name] = None
    packages = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "gudhi": gudhi.__version__,
        "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "platform": platform.platform(),
    }
    control_status = {}
    for key in CONTROL_KEYS:
        entry = results.get(key)
        if entry is None:
            status = "not_run"
            verdict = None
        elif "error" in entry:
            status = "incomplete"
            verdict = None
        else:
            status = "completed"
            verdict = entry.get("verdict")
        control_status[key] = {
            "status": status,
            "verdict": verdict,
            "wall_seconds": ctx.timings.get(key),
        }
    return {
        "work_package": WORK_PACKAGE,
        "command": " ".join([sys.executable, *sys.argv]),
        "cwd": str(Path.cwd()),
        "started_utc": ctx.started_utc,
        "finished_utc": utc_now(),
        "wall_seconds": wall_seconds,
        "peak_ram_mb": rss_mb(),
        "workers": int(args.workers),
        "budget_seconds": float(args.budget_seconds),
        "cache_dir": str(ctx.cache_dir),
        "out_dir": str(ctx.out_dir),
        "seed_namespaces": {
            "calibration": list(SEEDS_CAL),
            "evaluation": list(SEEDS_EVAL),
            "matched_family_a": list(SEEDS_MATCHED),
            "matched_aux_family_b": list(SEEDS_AUX),
            "time_reparam": list(SEEDS_REPARAM),
            "raw_preserving": list(SEEDS_RAW),
            "coarse_train": list(SEEDS_COARSE_TRAIN),
            "coarse_test": list(SEEDS_COARSE_TEST),
            "adversarial": list(SEEDS_ADVERSARIAL),
        },
        "evaluator_validation": evaluator_report,
        "floors": {
            f"{family}_sigma{sigma_tag(sigma)}": value
            for (family, sigma), value in ctx.floors.items()
        },
        "packages": packages,
        "input_hashes": input_hashes,
        "controls": control_status,
        "diagram_cache": {
            "hits": ctx.diagram_cache.hits,
            "misses": ctx.diagram_cache.misses,
        },
        "notes": ctx.notes,
        "skipped": ctx.skipped,
    }


def write_sha256sums(root: Path, extra: list[tuple[Path, str]]) -> Path:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SHA256SUMS":
            continue
        relative = str(path.relative_to(root))
        entries.append((sha256_file(path), relative))
    for path, label in extra:
        entries.append((sha256_file(path), label))
    entries.sort(key=lambda item: item[1])
    sums_path = root / "SHA256SUMS"
    sums_path.write_text(
        "\n".join(f"{digest}  {name}" for digest, name in entries) + "\n",
        encoding="utf-8",
    )
    return sums_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-3.3 null, baseline-favorable, and stress controls"
    )
    parser.add_argument(
        "--out",
        default="research_review/results/g3/nulls",
        help="output directory for tables and figures",
    )
    parser.add_argument(
        "--report",
        default="research_review/results/g3/reports/wp33_nulls_report.md",
        help="path of the Markdown report",
    )
    parser.add_argument(
        "--cache",
        default="/tmp/opencode/wp33_cache",
        help="private diagram and distance cache directory",
    )
    parser.add_argument(
        "--budget-seconds",
        type=float,
        default=2700.0,
        help="wall-clock budget in seconds",
    )
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated subset of controls to run",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="must be 1; the exploratory run reserves the remaining cores",
    )
    args = parser.parse_args(argv)
    if int(args.workers) != 1:
        parser.error("this script enforces a single worker process")
    out_dir = Path(args.out).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    cache_dir = Path(args.cache).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    selected = [
        key for key in CONTROL_KEYS if not args.only or key in args.only.split(",")
    ]
    if not selected:
        parser.error(f"--only matched no control; valid keys are {CONTROL_KEYS}")
    ctx = RunContext(out_dir, cache_dir, args.budget_seconds)
    ctx.log(f"{WORK_PACKAGE} run start; controls={selected}")
    evaluator_report = validate_evaluators(ctx)
    functions = {
        "static_null": control1_static_null,
        "matched_ordering": control2_matched_ordering,
        "time_reparam": control3_time_reparam,
        "raw_preserving": control4_raw_preserving,
        "coarse_sampling": control5_coarse_sampling,
        "adversarial_matrix": control6_adversarial_matrix,
    }
    results: dict = {}
    for key in selected:
        ctx.check_budget()
        started = time.perf_counter()
        try:
            results[key] = functions[key](ctx)
        except BudgetExceeded as exc:
            ctx.log(f"{key}: budget exceeded ({exc})")
            ctx.skipped.append(key)
            results[key] = {"error": str(exc), "verdict": "INCOMPLETE"}
        except Exception as exc:  # noqa: BLE001
            import traceback

            ctx.log(f"{key}: error {exc!r}")
            traceback.print_exc()
            results[key] = {"error": repr(exc), "verdict": "ERROR"}
        ctx.timings[key] = float(time.perf_counter() - started)
        ctx.save_pairs()
        ctx.log(f"{key}: finished in {ctx.timings[key]:.1f} s")
    wall_seconds = ctx.elapsed()
    manifest = build_manifest(ctx, results, args, evaluator_report, wall_seconds)
    write_json(out_dir / "manifest.json", manifest)
    report_text = build_report(ctx, results, manifest, report_path)
    report_path.write_text(report_text, encoding="utf-8")
    ctx.close()
    sums_path = write_sha256sums(
        out_dir,
        [(report_path, os.path.relpath(report_path, out_dir))],
    )
    print(f"wall={wall_seconds:.1f}s peak_ram={rss_mb():.1f}MB sha256={sha256_file(sums_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
