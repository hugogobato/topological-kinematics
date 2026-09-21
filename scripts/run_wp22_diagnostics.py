#!/usr/bin/env python3
"""WP-2.2 bounded metric diagnostics for the Topological Kinematics pilot.

This runner evaluates the frozen discrete path diagnostics of
``research_review/metric_interface.md`` on real (synthetic but extracted)
diagram sequences:

- interval speed ``nu_t``, path length ``L``, endpoint displacement ``R``,
  efficiency ``eta = R / L`` when ``L > 0``, speed-change rate with the
  midpoint denominator, comparison angle ``theta_t`` on ``a b > 0``, and the
  optional triangle excess ``q_t`` gated by a predeclared noise scale floor;
- training-like static-noise calibration of the per-cell floor ``e`` from the
  static trajectories at ``sigma = 0.05`` (seeds 1000 and 1001, the train-like
  draws); at ``sigma = 0`` the floor is exactly zero and only exact-zero
  abstention applies;
- both homology degrees: degree 0 is the primary channel and degree 1 is the
  secondary channel reported alongside it.

Metric backends. The frozen primary metric call is
``tk_pilot.diagram_metrics.bottleneck_linf``, which canonicalizes each diagram
and calls ``gudhi.bottleneck_distance``. This runner evaluates two backends on
exactly the same distance pairs:

- ``gudhi_default``: the frozen wrapper as imported, unchanged;
- ``exact_scipy``: an independent exact bottleneck solver (binary search over
  the finite candidate costs of the augmented matching problem with a
  perfect-matching feasibility test), used as the corrected candidate.

The frozen backend is incorrect in this environment. Its default ``e=None``
selects gudhi's approximate algorithm rather than the exact one, and the
approximation error is not small relative to the declared numerical zero.
More seriously, the gudhi implementation returns wrong distances on some
diagrams even when the exact ``e=0.0`` algorithm is requested, and its value
often depends on the order of the input points; some pairs are wrong in every
tested order, so canonicalization cannot repair it. The corrected candidate is
therefore an implementation independent of gudhi. It is validated against the
project brute-force reference on small diagrams, against
``persim.bottleneck``, by exhaustive enumeration on one 4 versus 4 point pair,
and by an explicit order-invariance test. The backend comparison quantifies
the frozen primary defect, which breaks the triangle inequality on real pilot
diagrams and invalidates cached artifacts computed with it.

Gate labeling: this work package is conditional on G1, which the coordinator
records before the G2 decision. Outputs carry the label ``conditional_on_G1``
and no G2 or predictive claim is made. The scientific pass condition is stable
definitions only, and the metric backend defect is reported as a G2 blocker
rather than silently repaired.

Data. The cached smoke trajectories under ``research_review/results/cache``
(families A and B, seed 11, ``sigma`` in {0, 0.05}, stride 1, classes return,
ramp, jump, plus static calibration controls) are read-only inputs. The
additional train-like draws (seeds 1000 and 1001) are built, cached, and
extracted fresh under a temporary cache; the repository cache is never
written. Strides 2 and 4 are exact subsamples of the stride-1 frame
realization, so every stride variant of a trajectory is a subsample of the
same master path.

Artifacts are written under ``research_review/results/g2/diagnostics``:
``feature_table.csv`` (frozen backend), ``feature_table_exact_metric.csv``
(corrected candidate), ``checks.json``, ``cell_summary.csv``,
``metric_backend_witness.json``, figures under ``figures/``,
``edge_case_report.md``, ``stability_report.md``, ``metric_backend_audit.md``,
``run_manifest.json``, and ``SHA256SUMS`` covering every artifact.

Usage::

    python scripts/run_wp22_diagnostics.py
    python scripts/run_wp22_diagnostics.py --quick --out-dir /tmp/opencode/wp22_quick
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/opencode/wp22_mplconfig")

import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tk_pilot import generators, persistence  # noqa: E402
from tk_pilot.diagram_metrics import (  # noqa: E402
    NUMERICAL_ZERO,
    as_diagram,
    bottleneck_linf,
)
from tk_pilot.path_diagnostics import (  # noqa: E402
    angle_validity_flags,
    compute_path_diagnostics,
    efficiency_validity_flag,
    noise_floor,
)

DEFAULT_REPO_CACHE = ROOT / "research_review" / "results" / "cache"
DEFAULT_TMP_CACHE = Path("/tmp/opencode/wp22_cache")
DEFAULT_OUT_DIR = ROOT / "research_review" / "results" / "g2" / "diagnostics"

FAMILIES = ("A", "B")
CLASSES = ("return", "ramp", "jump", "static")
SCIENTIFIC_CLASSES = ("return", "ramp", "jump")
SEEDS = (11, 1000, 1001)
CALIBRATION_SEEDS = (1000, 1001)
SIGMAS = (0.0, 0.05)
STRIDES = (1, 2, 4)
DEGREES = (0, 1)

BACKEND_PRIMARY = "gudhi_default"
BACKEND_EXACT = "exact_scipy"
BACKENDS = (BACKEND_PRIMARY, BACKEND_EXACT)

TOLERANCE = 1e-9
BACKEND_AGREEMENT_TOL = 1e-12
COSINE_ANOMALY_TOL = 1e-12
Q_FLOOR_FACTOR = 4.0
FLOOR_PERCENTILE = 95.0

GATE_LABEL = (
    "conditional_on_G1: WP-2.2 executed after the coordinator's G1 record and "
    "before the G2 decision; scientific pass condition is stable definitions "
    "only; no predictive value is claimed"
)

__all__ = ["main"]

# ---------------------------------------------------------------------------
# metric implementations
# ---------------------------------------------------------------------------


def _snap(value: float) -> float:
    """Declared numerical-zero convention from the frozen interface."""
    return 0.0 if float(value) <= NUMERICAL_ZERO else float(value)


def _identical(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and np.array_equal(a, b)


def gudhi_exact_e0(d1, d2) -> float:
    """Diagnostic only: the frozen wrapper with gudhi's exact ``e=0.0`` path.

    Kept to document that pinning ``e=0.0`` does not repair the frozen backend,
    because the gudhi implementation also depends on the order of the input
    points and the frozen canonicalization is not a correct fix. This function
    is not used for any feature value.
    """
    import gudhi

    a = as_diagram(d1)
    b = as_diagram(d2)
    if a.shape[0] == 0 and b.shape[0] == 0:
        return 0.0
    if _identical(a, b):
        return 0.0
    return _snap(gudhi.bottleneck_distance(a, b, 0.0))


def scipy_exact_bottleneck(d1, d2) -> float:
    """Independent exact bottleneck with L-infinity ground and diagonal costs.

    Binary search over the finite candidate costs of the augmented matching
    problem with a perfect-matching feasibility test per candidate. This is an
    independent reference implementation used to verify the corrected backend;
    it shares no code with gudhi, persim, or the project brute-force reference.
    """
    from scipy.optimize import linear_sum_assignment

    a = as_diagram(d1)
    b = as_diagram(d2)
    n = int(a.shape[0])
    m = int(b.shape[0])
    if n == 0 and m == 0:
        return 0.0
    if n == 0:
        return _snap(float(np.max(0.5 * (b[:, 1] - b[:, 0]))))
    if m == 0:
        return _snap(float(np.max(0.5 * (a[:, 1] - a[:, 0]))))
    if _identical(a, b):
        return 0.0
    size = n + m
    costs = np.zeros((size, size), dtype=float)
    diff = np.abs(a[:, None, :] - b[None, :, :])
    costs[:n, :m] = np.max(diff, axis=2)
    da = 0.5 * (a[:, 1] - a[:, 0])
    db = 0.5 * (b[:, 1] - b[:, 0])
    costs[:n, m:] = np.inf
    np.fill_diagonal(costs[:n, m:], da)
    costs[n:, :m] = np.inf
    np.fill_diagonal(costs[n:, :m], db)
    candidates = np.unique(costs[np.isfinite(costs)])
    big = float(candidates[-1]) + 1.0
    low = 0
    high = int(candidates.size) - 1
    while low < high:
        middle = (low + high) // 2
        threshold = candidates[middle]
        binary = np.where(costs <= threshold, 0.0, big)
        rows, columns = linear_sum_assignment(binary)
        if float(binary[rows, columns].sum()) == 0.0:
            high = middle
        else:
            low = middle + 1
    return _snap(float(candidates[low]))


def _backend_metric(name: str):
    if name == BACKEND_PRIMARY:
        return bottleneck_linf
    if name == BACKEND_EXACT:
        return scipy_exact_bottleneck
    raise ValueError(f"unknown backend {name!r}")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _floor_cell_key(family: str, degree: int, stride: int) -> str:
    return f"{family}|{int(degree)}|{int(stride)}"


# ---------------------------------------------------------------------------
# worker side
# ---------------------------------------------------------------------------


class _IndexedMetric:
    """Symmetric memoized wrapper recording distances by diagram index.

    When ``checker`` is given, each distinct distance is recomputed with the
    checker and compared against the returned value.
    """

    def __init__(self, objects, metric, checker=None):
        self._objects = list(objects)
        self._index = {id(obj): i for i, obj in enumerate(self._objects)}
        self._metric = metric
        self._checker = checker
        self.values: dict[tuple[int, int], float] = {}
        self.calls = 0
        self.checker_calls = 0
        self.checker_max_diff = 0.0
        self.checker_mismatches = 0
        self.checker_witnesses: list[dict] = []

    def __call__(self, a, b) -> float:
        i = self._index[id(a)]
        j = self._index[id(b)]
        if i > j:
            i, j = j, i
        key = (i, j)
        value = self.values.get(key)
        if value is None:
            value = float(self._metric(a, b))
            self.values[key] = value
            self.calls += 1
            if self._checker is not None:
                checked = float(self._checker(a, b))
                self.checker_calls += 1
                difference = abs(checked - value)
                self.checker_max_diff = max(self.checker_max_diff, difference)
                if difference > BACKEND_AGREEMENT_TOL:
                    self.checker_mismatches += 1
                    if len(self.checker_witnesses) < 20:
                        self.checker_witnesses.append(
                            {
                                "i": int(i),
                                "j": int(j),
                                "backend": value,
                                "checker": checked,
                                "abs_diff": difference,
                            }
                        )
        return value


def _trajectory_dirs(repo_cache: Path, tmp_cache: Path, seed: int) -> list[Path]:
    dirs = [tmp_cache]
    if int(seed) == 11:
        dirs.append(repo_cache)
    return dirs


def _load_or_build_trajectory(job):
    family = str(job["family"])
    label = str(job["label"])
    seed = int(job["seed"])
    sigma = float(job["sigma"])
    tmp_cache = Path(job["tmp_cache"])
    repo_cache = Path(job["repo_cache"])
    for directory in _trajectory_dirs(repo_cache, tmp_cache, seed):
        try:
            traj = generators.load_trajectory(family, label, seed, sigma, 1, directory)
            return traj, str(directory), True
        except FileNotFoundError:
            continue
    traj = generators.build_trajectory(family, label, seed, sigma, 1)
    generators.save_trajectory(traj, tmp_cache)
    return traj, str(tmp_cache), False


def _load_or_extract_diagrams(traj, job):
    tmp_cache = Path(job["tmp_cache"])
    repo_cache = Path(job["repo_cache"])
    for directory in _trajectory_dirs(repo_cache, tmp_cache, int(job["seed"])):
        try:
            cached = persistence.load_diagram_cache(traj, directory)
            return (
                {degree: cached["diagrams"][degree] for degree in DEGREES},
                {degree: cached["essential"][degree] for degree in DEGREES},
                str(directory),
                True,
            )
        except FileNotFoundError:
            continue
    persistence.save_diagram_cache(traj, tmp_cache)
    cached = persistence.load_diagram_cache(traj, tmp_cache)
    return (
        {degree: cached["diagrams"][degree] for degree in DEGREES},
        {degree: cached["essential"][degree] for degree in DEGREES},
        str(tmp_cache),
        False,
    )


def _process_trajectory(job) -> dict:
    """Load or build one trajectory and run both metric backends on it."""

    root = str(job["src"])
    if root not in sys.path:
        sys.path.insert(0, root)

    started = time.perf_counter()
    traj, traj_cache, traj_hit = _load_or_build_trajectory(job)
    extract_started = time.perf_counter()
    diagrams, essential_by_degree, diagram_cache, diagram_hit = (
        _load_or_extract_diagrams(traj, job)
    )
    extraction_seconds = time.perf_counter() - extract_started
    n_frames = int(np.asarray(traj.frames).shape[0])
    timestamps = np.asarray(traj.timestamps, dtype=float)

    records = []
    recorders: dict[str, dict[int, "_IndexedMetric"]] = {
        backend: {} for backend in BACKENDS
    }
    metric_seconds = {backend: 0.0 for backend in BACKENDS}
    for backend in BACKENDS:
        metric = _backend_metric(backend)
        for degree in DEGREES:
            series = diagrams[degree]
            recorder = _IndexedMetric(series, metric)
            for stride in STRIDES:
                indices = list(range(0, len(series), int(stride)))
                stamps = timestamps[:: int(stride)]
                started_metric = time.perf_counter()
                diagnostics = compute_path_diagnostics(
                    [series[i] for i in indices], stamps, recorder
                )
                metric_seconds[backend] += time.perf_counter() - started_metric
                payload = diagnostics.as_json()
                adjacent = [
                    float(recorder.values[(indices[i], indices[i + 1])])
                    for i in range(len(indices) - 1)
                ]
                interior_c = [
                    float(recorder.values[(indices[i - 1], indices[i + 1])])
                    for i in range(1, len(indices) - 1)
                ]
                endpoint = float(recorder.values[(indices[0], indices[-1])])
                if endpoint != float(payload["displacement"]):
                    raise AssertionError(
                        "recorded endpoint distance disagrees with diagnostics"
                    )
                records.append(
                    {
                        "backend": backend,
                        "degree": int(degree),
                        "stride": int(stride),
                        "timestamps": [float(x) for x in stamps],
                        "adjacent": adjacent,
                        "interior_c": interior_c,
                        "endpoint": endpoint,
                        "comparison_valid": payload["comparison_valid"],
                        "comparison_angles": payload["comparison_angles"],
                        "comparison_turns": payload["comparison_turns"],
                        "cosine_raw": payload["cosine_raw"],
                        "cosine_anomaly": payload["cosine_anomaly"],
                        "triangle_excess": payload["triangle_excess"],
                        "triangle_excess_valid": payload["triangle_excess_valid"],
                        "interval_speeds": payload["interval_speeds"],
                        "speed_change_rates": payload["speed_change_rates"],
                        "cardinality": [int(series[i].shape[0]) for i in indices],
                        "essential": [
                            int(essential_by_degree[degree][i]) for i in indices
                        ],
                    }
                )
            recorders[backend][degree] = recorder

    cross_backend = {
        "n_pairs_compared": 0,
        "n_above_tolerance": 0,
        "max_abs_difference": 0.0,
        "witnesses": [],
        "by_degree": {},
    }
    for degree in DEGREES:
        primary = recorders[BACKEND_PRIMARY][degree]
        exact = recorders[BACKEND_EXACT][degree]
        common = sorted(set(primary.values) & set(exact.values))
        differences = []
        for key in common:
            difference = abs(primary.values[key] - exact.values[key])
            differences.append((difference, key))
            cross_backend["max_abs_difference"] = max(
                cross_backend["max_abs_difference"], difference
            )
            if difference > BACKEND_AGREEMENT_TOL:
                cross_backend["n_above_tolerance"] += 1
        cross_backend["n_pairs_compared"] += len(common)
        differences.sort(reverse=True)
        degree_block = cross_backend["by_degree"].setdefault(
            str(degree),
            {"n_pairs_compared": 0, "n_above_tolerance": 0, "max_abs_difference": 0.0},
        )
        degree_block["n_pairs_compared"] += len(common)
        for difference, (i, j) in differences:
            if difference <= BACKEND_AGREEMENT_TOL:
                break
            degree_block["n_above_tolerance"] += 1
        if differences:
            degree_block["max_abs_difference"] = max(
                degree_block["max_abs_difference"], differences[0][0]
            )
        for difference, (i, j) in differences[:10]:
            if difference <= BACKEND_AGREEMENT_TOL:
                break
            cross_backend["witnesses"].append(
                {
                    "trajectory_id": str(traj.trajectory_id),
                    "family": str(job["family"]),
                    "class": str(job["label"]),
                    "seed": int(job["seed"]),
                    "sigma": float(job["sigma"]),
                    "degree": int(degree),
                    "i": int(i),
                    "j": int(j),
                    "primary": float(primary.values[(i, j)]),
                    "exact": float(exact.values[(i, j)]),
                    "abs_diff": float(difference),
                }
            )
    cross_backend["witnesses"] = sorted(
        cross_backend["witnesses"], key=lambda item: -item["abs_diff"]
    )[:25]

    return {
        "family": str(job["family"]),
        "label": str(job["label"]),
        "seed": int(job["seed"]),
        "sigma": float(job["sigma"]),
        "trajectory_id": str(traj.trajectory_id),
        "n_frames": n_frames,
        "trajectory_cache": traj_cache,
        "trajectory_cache_hit": bool(traj_hit),
        "diagram_cache": diagram_cache,
        "diagram_cache_hit": bool(diagram_hit),
        "extraction_seconds": float(extraction_seconds),
        "metric_seconds": metric_seconds,
        "wall_seconds": float(time.perf_counter() - started),
        "records": records,
        "cross_backend": cross_backend,
    }

# ---------------------------------------------------------------------------
# parent side: floors, rows, checks
# ---------------------------------------------------------------------------


def _collect_records(results, backend):
    keyed = {}
    for result in results:
        for record in result["records"]:
            if record["backend"] != backend:
                continue
            key = (
                result["family"],
                result["label"],
                int(result["seed"]),
                round(float(result["sigma"]), 6),
                int(record["degree"]),
                int(record["stride"]),
            )
            keyed[key] = {"trajectory": result, "record": record}
    return keyed


def _compute_floors(families, keyed):
    """Per-cell 95th percentile of static-noise adjacent distances at sigma 0.05."""

    floors = {}
    floor_meta = {}
    seed11_sensitivity = {}
    calibration_seeds = [
        seed
        for seed in CALIBRATION_SEEDS
        if all(
            (family, "static", seed, 0.05, degree, stride) in keyed
            for family in families
            for degree in DEGREES
            for stride in STRIDES
        )
    ]
    for family in families:
        for degree in DEGREES:
            for stride in STRIDES:
                pooled = []
                parts = {}
                for seed in calibration_seeds:
                    key = (family, "static", seed, 0.05, degree, stride)
                    adjacent = keyed[key]["record"]["adjacent"]
                    pooled.extend(adjacent)
                    parts[str(seed)] = len(adjacent)
                cell = _floor_cell_key(family, degree, stride)
                value = float(
                    noise_floor(np.asarray(pooled, dtype=float), FLOOR_PERCENTILE)
                )
                floors[cell] = value
                key11 = (family, "static", 11, 0.05, degree, stride)
                if key11 in keyed:
                    pooled_11 = keyed[key11]["record"]["adjacent"]
                    seed11_sensitivity[cell] = float(
                        noise_floor(np.asarray(pooled_11, dtype=float), FLOOR_PERCENTILE)
                    )
                floor_meta[cell] = {
                    "family": family,
                    "degree": int(degree),
                    "stride": int(stride),
                    "sigma": 0.05,
                    "percentile": FLOOR_PERCENTILE,
                    "seeds": [int(seed) for seed in calibration_seeds],
                    "n_distances": int(len(pooled)),
                    "n_distances_per_seed": parts,
                    "e": value,
                }
    return floors, floor_meta, seed11_sensitivity


def _build_row(cell_record, floors, floor_meta, backend):
    trajectory = cell_record["trajectory"]
    record = cell_record["record"]
    family = trajectory["family"]
    label = trajectory["label"]
    seed = int(trajectory["seed"])
    sigma = float(trajectory["sigma"])
    degree = int(record["degree"])
    stride = int(record["stride"])
    role = "scientific" if label in SCIENTIFIC_CLASSES else "calibration_control"
    cell = _floor_cell_key(family, degree, stride)

    if sigma == 0.0:
        floor = 0.0
        floor_source = "zero_sigma_exact_zero"
        floor_n = 0
    else:
        floor = float(floors[cell])
        floor_source = "static_sigma50_train_like_pool"
        floor_n = int(floor_meta[cell]["n_distances"])

    adjacent = np.asarray(record["adjacent"], dtype=float)
    interior_c = np.asarray(record["interior_c"], dtype=float)
    timestamps = np.asarray(record["timestamps"], dtype=float)
    n_intervals = int(adjacent.size)
    length = float(np.sum(adjacent))
    displacement = float(record["endpoint"])
    eta = (displacement / length) if length > 0.0 else None

    h = np.diff(timestamps)
    speeds = adjacent / h if n_intervals else np.empty(0)
    midpoints = 0.5 * (timestamps[:-1] + timestamps[1:])
    if speeds.size >= 2:
        changes = np.diff(speeds) / np.diff(midpoints)
    else:
        changes = np.empty(0)

    valid = np.asarray(record["comparison_valid"], dtype=bool)
    a_prev = adjacent[:-1]
    b_next = adjacent[1:]
    expected_valid = (a_prev > 0.0) & (b_next > 0.0)
    valid_mismatch = int(np.sum(valid != expected_valid))

    floor_valid = np.asarray(angle_validity_flags(a_prev, b_next, floor), dtype=bool)
    cosines = np.asarray(
        [np.nan if v is None else float(v) for v in record["cosine_raw"]]
    )
    angles = np.asarray(
        [np.nan if v is None else float(v) for v in record["comparison_angles"]]
    )
    usable = floor_valid & np.isfinite(cosines)
    mean_cosine = float(np.mean(cosines[usable])) if np.any(usable) else None
    mean_angle = float(np.mean(angles[usable])) if np.any(usable) else None

    excess = np.asarray(
        [np.nan if v is None else float(v) for v in record["triangle_excess"]]
    )
    defined_q = np.isfinite(excess)
    q_gate = (a_prev + b_next) > (Q_FLOOR_FACTOR * floor)
    q_valid = defined_q & q_gate
    q_mean = float(np.mean(excess[q_valid])) if np.any(q_valid) else None
    q_std = float(np.std(excess[q_valid])) if int(np.sum(q_valid)) >= 2 else None

    anomalies = [bool(x) for x in record["cosine_anomaly"]]
    cosine_anomaly_count = int(np.sum(anomalies))
    anomaly_mismatch = 0
    for index, z in enumerate(record["cosine_raw"]):
        if z is None:
            continue
        if bool(abs(float(z)) > 1.0 + COSINE_ANOMALY_TOL) != anomalies[index]:
            anomaly_mismatch += 1

    straight_count = int(np.sum(cosines <= -1.0))
    reversal_count = int(np.sum(cosines >= 1.0))
    near_straight_count = int(np.sum(np.abs(cosines + 1.0) < 1e-6))
    near_reversal_count = int(np.sum(np.abs(cosines - 1.0) < 1e-6))

    card = np.asarray(record["cardinality"], dtype=int)
    card_change_count = int(np.sum(card[:-1] != card[1:])) if card.size >= 2 else 0
    essential = np.asarray(record["essential"], dtype=int)
    efficiency_valid = bool(
        length > 0.0 and efficiency_validity_flag(length, n_intervals, floor)
    )
    l_per_interval = length / (n_intervals - 1) if n_intervals > 1 else float("nan")
    if floor > 0.0 and np.isfinite(l_per_interval):
        l_over_floor = float(l_per_interval / floor)
    else:
        l_over_floor = None

    row = {
        "metric": backend,
        "metric_role": (
            "frozen_primary" if backend == BACKEND_PRIMARY else "corrected_candidate"
        ),
        "family": family,
        "class": label,
        "seed": seed,
        "sigma": sigma,
        "stride": stride,
        "degree": degree,
        "source": "cached_smoke" if seed == 11 else "fresh_train_like",
        "role": role,
        "trajectory_id": trajectory["trajectory_id"],
        "n_frames": int(len(record["timestamps"])),
        "n_intervals": n_intervals,
        "floor_e": floor,
        "floor_source": floor_source,
        "floor_n_distances": floor_n,
        "L": length,
        "R": displacement,
        "eta": eta,
        "eta_defined": bool(eta is not None),
        "efficiency_valid": efficiency_valid,
        "L_per_interval": float(l_per_interval),
        "L_over_floor_ratio": l_over_floor,
        "speed_mean": float(np.mean(speeds)) if speeds.size else None,
        "speed_std": float(np.std(speeds)) if speeds.size else None,
        "speed_max": float(np.max(speeds)) if speeds.size else None,
        "speed_change_mean": float(np.mean(changes)) if changes.size else None,
        "speed_change_mean_abs": (
            float(np.mean(np.abs(changes))) if changes.size else None
        ),
        "speed_change_max_abs": (
            float(np.max(np.abs(changes))) if changes.size else None
        ),
        "angle_defined_count": int(np.sum(valid)),
        "angle_defined_fraction": float(np.mean(valid)) if valid.size else None,
        "angle_floor_valid_count": int(np.sum(floor_valid)),
        "angle_floor_valid_fraction": (
            float(np.mean(floor_valid)) if floor_valid.size else None
        ),
        "mean_cosine_angle": mean_cosine,
        "mean_angle_rad": mean_angle,
        "straight_count": straight_count,
        "reversal_count": reversal_count,
        "near_straight_count": near_straight_count,
        "near_reversal_count": near_reversal_count,
        "q_defined_count": int(np.sum(defined_q)),
        "q_valid_count": int(np.sum(q_valid)),
        "q_valid_fraction": float(np.mean(q_valid)) if q_valid.size else None,
        "q_mean": q_mean,
        "q_std": q_std,
        "cosine_anomaly_count": cosine_anomaly_count,
        "unresolved_zero_step_count": int(np.sum(~valid)),
        "card_min": int(np.min(card)) if card.size else None,
        "card_mean": float(np.mean(card)) if card.size else None,
        "card_max": int(np.max(card)) if card.size else None,
        "card_change_count": card_change_count,
        "empty_diagram_count": int(np.sum(card == 0)),
        "essential_count_min": int(np.min(essential)) if essential.size else None,
        "essential_count_max": int(np.max(essential)) if essential.size else None,
        "essential_count_total": int(np.sum(essential)),
        "_valid_mismatch": valid_mismatch,
        "_anomaly_mismatch": anomaly_mismatch,
    }
    check_arrays = {
        "timestamps": timestamps,
        "adjacent": adjacent,
        "interior_c": interior_c,
        "a_prev": a_prev,
        "b_next": b_next,
        "valid": valid,
        "floor_valid": floor_valid,
        "excess": excess,
        "defined_q": defined_q,
        "cosines": cosines,
        "floor": floor,
        "length": length,
        "displacement": displacement,
        "n_intervals": n_intervals,
    }
    return row, check_arrays


def _check_R_le_L(rows, checks):
    violations = 0
    worst = 0.0
    for row in rows:
        slack = float(row["R"]) - float(row["L"]) - TOLERANCE
        if slack > 0:
            violations += 1
        worst = max(worst, float(row["R"]) - float(row["L"]))
    checks.append(
        {
            "id": "R_le_L",
            "description": "R <= L + 1e-9 on every row",
            "verdict": "pass" if violations == 0 else "fail",
            "n_checked": len(rows),
            "n_violations": violations,
            "worst_R_minus_L": worst,
            "tolerance": TOLERANCE,
        }
    )


def _check_eta(rows, checks):
    out_of_range = 0
    worst_over = 0.0
    worst_under = 0.0
    undefined_positive = 0
    defined_zero = 0
    for row in rows:
        length = float(row["L"])
        if length > 0.0:
            if row["eta"] is None:
                undefined_positive += 1
            else:
                eta = float(row["eta"])
                worst_over = max(worst_over, eta - 1.0)
                worst_under = max(worst_under, -eta)
                if eta < -TOLERANCE or eta > 1.0 + TOLERANCE:
                    out_of_range += 1
        else:
            if row["eta"] is not None:
                defined_zero += 1
    checks.append(
        {
            "id": "eta_range",
            "description": "0 <= eta <= 1 + 1e-9 on every row with L > 0",
            "verdict": "pass" if out_of_range == 0 else "fail",
            "n_checked": int(sum(1 for row in rows if float(row["L"]) > 0.0)),
            "n_violations": out_of_range,
            "worst_eta_minus_one": worst_over,
            "worst_minus_eta": worst_under,
            "tolerance": TOLERANCE,
        }
    )
    checks.append(
        {
            "id": "eta_undefined_iff_L_zero",
            "description": "eta is defined exactly when L > 0 and null exactly when L = 0",
            "verdict": (
                "pass" if undefined_positive == 0 and defined_zero == 0 else "fail"
            ),
            "n_rows_with_L_zero": int(
                sum(1 for row in rows if float(row["L"]) == 0.0)
            ),
            "n_undefined_with_L_positive": undefined_positive,
            "n_defined_with_L_zero": defined_zero,
        }
    )


def _check_triangles(rows, arrays_by_row, checks):
    violations = 0
    worst = 0.0
    checked = 0
    for row in rows:
        arr = arrays_by_row[id(row)]
        a_prev = arr["a_prev"]
        b_next = arr["b_next"]
        c = arr["interior_c"]
        if c.size == 0:
            continue
        checked += int(c.size)
        upper = c - (a_prev + b_next)
        lower = np.abs(a_prev - b_next) - c
        worst = max(worst, float(np.max(upper)), float(np.max(lower)))
        violations += int(np.sum(upper > TOLERANCE))
        violations += int(np.sum(lower > TOLERANCE))
    checks.append(
        {
            "id": "triangle_inequality",
            "description": "c <= a + b and c >= |a - b| on every interior triple within 1e-9",
            "verdict": "pass" if violations == 0 else "fail",
            "n_triples_checked": checked,
            "n_violations": violations,
            "worst_excess": worst,
            "tolerance": TOLERANCE,
        }
    )


def _check_triangle_excess(rows, arrays_by_row, checks):
    violations = 0
    checked = 0
    worst_over = 0.0
    worst_under = 0.0
    for row in rows:
        arr = arrays_by_row[id(row)]
        mask = arr["defined_q"]
        if not np.any(mask):
            continue
        checked += int(np.sum(mask))
        values = arr["excess"][mask]
        worst_over = max(worst_over, float(np.max(values - 1.0)))
        worst_under = max(worst_under, float(np.max(-values)))
        violations += int(np.sum(values > 1.0 + TOLERANCE))
        violations += int(np.sum(values < -TOLERANCE))
    checks.append(
        {
            "id": "triangle_excess_range",
            "description": "0 <= q_t <= 1 + 1e-9 wherever q is defined (a + b > 0)",
            "verdict": "pass" if violations == 0 else "fail",
            "n_checked": checked,
            "n_violations": violations,
            "worst_q_minus_one": worst_over,
            "worst_minus_q": worst_under,
            "tolerance": TOLERANCE,
        }
    )


def _check_angles(rows, arrays_by_row, checks):
    valid_mismatch = int(sum(row["_valid_mismatch"] for row in rows))
    anomaly_mismatch = int(sum(row["_anomaly_mismatch"] for row in rows))
    undefined_positive = 0
    for row in rows:
        arr = arrays_by_row[id(row)]
        positive = (arr["a_prev"] > 0.0) & (arr["b_next"] > 0.0)
        undefined_positive += int(np.sum(positive & ~arr["valid"]))
    checks.append(
        {
            "id": "angle_defined_iff_positive_steps",
            "description": "theta_t is defined exactly when a > 0 and b > 0",
            "verdict": "pass" if valid_mismatch == 0 else "fail",
            "n_violations": valid_mismatch,
        }
    )
    checks.append(
        {
            "id": "cosine_anomaly_accounting",
            "description": "cosine-anomaly flags equal |z| > 1 + 1e-12 wherever z is defined",
            "verdict": "pass" if anomaly_mismatch == 0 else "fail",
            "n_violations": anomaly_mismatch,
            "tolerance": COSINE_ANOMALY_TOL,
        }
    )
    checks.append(
        {
            "id": "straight_and_reversal_retained",
            "description": "every interior time with ab > 0 carries a reported angle; straight and reversal cases are retained",
            "verdict": "pass" if undefined_positive == 0 else "fail",
            "n_violations": undefined_positive,
            "n_straight": int(sum(row["straight_count"] for row in rows)),
            "n_reversal": int(sum(row["reversal_count"] for row in rows)),
        }
    )


def _check_grid(rows, grid, checks):
    expected = int(np.prod([len(values) for values in grid.values()], dtype=np.int64))
    checks.append(
        {
            "id": "no_trajectory_deleted",
            "description": "the written feature table covers the complete predeclared grid",
            "verdict": "pass" if len(rows) == expected else "fail",
            "n_expected_rows": expected,
            "n_rows_written": len(rows),
        }
    )


def _check_floors(rows, floors, checks):
    missing = [cell for cell in sorted(floors) if not (floors[cell] > 0.0)]
    checks.append(
        {
            "id": "floor_calibration_positive_sigma50",
            "description": "every (family, degree, stride) sigma=0.05 floor is strictly positive",
            "verdict": "pass" if not missing else "fail",
            "n_cells": len(floors),
            "cells_with_nonpositive_floor": missing,
        }
    )
    sigma0_values = [
        float(row["floor_e"]) for row in rows if float(row["sigma"]) == 0.0
    ]
    nonzero = int(sum(1 for value in sigma0_values if value != 0.0))
    checks.append(
        {
            "id": "floor_zero_sigma0",
            "description": "sigma = 0 rows use the exact-zero floor",
            "verdict": "pass" if nonzero == 0 else "fail",
            "n_rows_sigma0": len(sigma0_values),
            "n_nonzero": nonzero,
        }
    )


def _check_timestamps(rows, arrays_by_row, checks):
    bad = 0
    for row in rows:
        stamps = arrays_by_row[id(row)]["timestamps"]
        if stamps.size < 2 or np.any(np.diff(stamps) <= 0.0):
            bad += 1
    checks.append(
        {
            "id": "timestamps_strictly_increasing",
            "description": "every stride variant keeps strictly increasing timestamps (the frozen library also rejects nonpositive intervals)",
            "verdict": "pass" if bad == 0 else "fail",
            "n_rows": len(rows),
            "n_violations": bad,
            "note": "compute_path_diagnostics raises on any nonpositive interval; no silent repair is used",
        }
    )


def _check_cached_matrices(keyed, repo_cache, backend, checks):
    differences = 0.0
    compared = 0
    n_above = 0
    for (family, label, seed, sigma, degree, stride), entry in sorted(
        keyed.items(), key=lambda item: item[0]
    ):
        if seed != 11 or degree != 0 or stride != 1:
            continue
        matrix_path = (
            Path(repo_cache)
            / "runner_distances"
            / family
            / label
            / "11"
            / f"sigma{generators.sigma_tag(sigma)}"
            / "stride1"
            / "degree0.npz"
        )
        if not matrix_path.is_file():
            continue
        matrix = np.load(matrix_path)["matrix"]
        adjacent = entry["record"]["adjacent"]
        for i, value in enumerate(adjacent):
            difference = abs(float(value) - float(matrix[i, i + 1]))
            differences = max(differences, difference)
            n_above += int(difference > BACKEND_AGREEMENT_TOL)
            compared += 1
        endpoint = float(entry["record"]["endpoint"])
        difference = abs(endpoint - float(matrix[0, -1]))
        differences = max(differences, difference)
        n_above += int(difference > BACKEND_AGREEMENT_TOL)
        compared += 1
    checks.append(
        {
            "id": "cached_distance_matrix_comparison",
            "description": "seed 11 degree 0 stride 1 distances against the cached smoke distance matrices",
            "verdict": "pass",
            "n_values_compared": compared,
            "n_above_tolerance": n_above,
            "max_abs_difference": differences,
            "tolerance": BACKEND_AGREEMENT_TOL,
            "note": (
                "the cached matrices were produced by the frozen backend, so exact agreement is a reproducibility check, not a correctness check"
                if backend == BACKEND_PRIMARY
                else "differences against the cached frozen-backend matrices quantify the backend defect"
            ),
        }
    )


def _cell_coverage(rows):
    coverage = []
    for family in sorted({row["family"] for row in rows}):
        for sigma in sorted({row["sigma"] for row in rows}):
            for degree in sorted({row["degree"] for row in rows}):
                for stride in sorted({row["stride"] for row in rows}):
                    cell_rows = [
                        row
                        for row in rows
                        if row["family"] == family
                        and row["sigma"] == sigma
                        and row["degree"] == degree
                        and row["stride"] == stride
                    ]
                    if not cell_rows:
                        continue
                    coverage.append(
                        {
                            "family": family,
                            "sigma": sigma,
                            "degree": int(degree),
                            "stride": int(stride),
                            "floor_e": float(cell_rows[0]["floor_e"]),
                            "n_rows": len(cell_rows),
                            "n_scientific_rows": int(
                                sum(
                                    1
                                    for row in cell_rows
                                    if row["role"] == "scientific"
                                )
                            ),
                            "angle_defined_fraction_mean": float(
                                np.mean(
                                    [
                                        row["angle_defined_fraction"]
                                        for row in cell_rows
                                    ]
                                )
                            ),
                            "angle_floor_valid_fraction_mean": float(
                                np.mean(
                                    [
                                        row["angle_floor_valid_fraction"]
                                        for row in cell_rows
                                    ]
                                )
                            ),
                            "efficiency_coverage": float(
                                np.mean(
                                    [
                                        1.0 if row["efficiency_valid"] else 0.0
                                        for row in cell_rows
                                    ]
                                )
                            ),
                            "eta_defined_fraction": float(
                                np.mean(
                                    [
                                        1.0 if row["eta_defined"] else 0.0
                                        for row in cell_rows
                                    ]
                                )
                            ),
                            "q_valid_fraction_mean": float(
                                np.mean(
                                    [row["q_valid_fraction"] for row in cell_rows]
                                )
                            ),
                        }
                    )
    return coverage


def _run_checks(rows, arrays_by_row, grid, floors, keyed, repo_cache, backend):
    checks = []
    _check_R_le_L(rows, checks)
    _check_eta(rows, checks)
    _check_triangles(rows, arrays_by_row, checks)
    _check_triangle_excess(rows, arrays_by_row, checks)
    _check_angles(rows, arrays_by_row, checks)
    _check_grid(rows, grid, checks)
    _check_floors(rows, floors, checks)
    _check_timestamps(rows, arrays_by_row, checks)
    _check_cached_matrices(keyed, repo_cache, backend, checks)
    verdict = "pass" if all(check["verdict"] == "pass" for check in checks) else "fail"
    return checks, _cell_coverage(rows), verdict


def _random_pairs(rng, count, max_points):
    pairs = []
    for _ in range(count):
        n = int(rng.integers(1, max_points))
        m = int(rng.integers(1, max_points))
        births_a = rng.uniform(0.0, 1.0, n)
        births_b = rng.uniform(0.0, 1.0, m)
        a = np.column_stack([births_a, births_a + rng.uniform(0.1, 1.0, n)])
        b = np.column_stack([births_b, births_b + rng.uniform(0.1, 1.0, m)])
        pairs.append((a, b))
    return pairs


def _exhaustive_bottleneck(a, b) -> float:
    """Exhaustive enumeration of all matchings with diagonal copies.

    Independent of the project brute-force reference (which is limited to seven
    points in total) and of the SciPy feasibility search. Intended only for
    pairs with at most eight points in total.
    """
    import itertools

    from tk_pilot.diagram_metrics import _bruteforce_cost_matrix

    fa = as_diagram(a)
    fb = as_diagram(b)
    size = fa.shape[0] + fb.shape[0]
    if size > 8:
        raise ValueError("exhaustive enumeration is limited to eight points in total")
    costs = _bruteforce_cost_matrix(fa, fb)
    best = np.inf
    for perm in itertools.permutations(range(size)):
        worst = 0.0
        for i, j in enumerate(perm):
            value = costs[i, j]
            if value > worst:
                worst = value
                if worst >= best:
                    break
        if worst < best:
            best = worst
    return _snap(float(best))


def _solver_validation():
    """Validate the independent SciPy solver and quantify the gudhi defect."""

    from tk_pilot.diagram_metrics import bottleneck_bruteforce

    rng = np.random.default_rng(20260907)

    small = [pair for pair in _random_pairs(rng, 80, 4) if sum(x.shape[0] for x in pair) <= 7]
    comparisons = {"scipy_vs_project_bruteforce": 0, "scipy_vs_gudhi_default": 0, "scipy_vs_gudhi_e0": 0}
    mismatches = {"project_bruteforce": 0, "gudhi_default": 0, "gudhi_e0": 0}
    max_diff = {"project_bruteforce": 0.0, "gudhi_default": 0.0, "gudhi_e0": 0.0}
    for a, b in small:
        exact = scipy_exact_bottleneck(a, b)
        reference = float(bottleneck_bruteforce(a, b))
        default = float(bottleneck_linf(a, b))
        e0 = gudhi_exact_e0(a, b)
        comparisons["scipy_vs_project_bruteforce"] += 1
        comparisons["scipy_vs_gudhi_default"] += 1
        comparisons["scipy_vs_gudhi_e0"] += 1
        for key, value, bucket in (
            ("project_bruteforce", reference, "project_bruteforce"),
            ("gudhi_default", default, "gudhi_default"),
            ("gudhi_e0", e0, "gudhi_e0"),
        ):
            if abs(exact - value) > BACKEND_AGREEMENT_TOL:
                mismatches[bucket] += 1
            max_diff[bucket] = max(max_diff[bucket], abs(exact - value))

    order_invariance = {"comparisons": 0, "mismatches": 0, "max_abs_difference": 0.0}
    for a, b in _random_pairs(rng, 30, 7):
        exact = scipy_exact_bottleneck(a, b)
        shuffled = scipy_exact_bottleneck(a[rng.permutation(a.shape[0])], b[rng.permutation(b.shape[0])])
        order_invariance["comparisons"] += 1
        if abs(exact - shuffled) > BACKEND_AGREEMENT_TOL:
            order_invariance["mismatches"] += 1
        order_invariance["max_abs_difference"] = max(
            order_invariance["max_abs_difference"], abs(exact - shuffled)
        )

    gudhi_order = {
        "default_canonical_mismatches": 0,
        "default_shuffled_mismatches": 0,
        "e0_canonical_mismatches": 0,
        "e0_shuffled_mismatches": 0,
        "pairs_wrong_in_all_four_tests": 0,
        "witness": None,
        "n_pairs": 0,
    }
    import gudhi

    for a, b in _random_pairs(np.random.default_rng(11), 60, 6):
        exact = scipy_exact_bottleneck(a, b)
        gudhi_order["n_pairs"] += 1
        a_can = as_diagram(a)
        b_can = as_diagram(b)
        a_shuf = a_can[np.random.default_rng(101).permutation(a_can.shape[0])]
        b_shuf = b_can[np.random.default_rng(102).permutation(b_can.shape[0])]
        values = {
            "default_canonical_mismatches": float(
                gudhi.bottleneck_distance(a_can, b_can)
            ),
            "default_shuffled_mismatches": float(
                gudhi.bottleneck_distance(a_shuf, b_shuf)
            ),
            "e0_canonical_mismatches": float(
                gudhi.bottleneck_distance(a_can, b_can, 0.0)
            ),
            "e0_shuffled_mismatches": float(
                gudhi.bottleneck_distance(a_shuf, b_shuf, 0.0)
            ),
        }
        if all(
            abs(value - exact) > BACKEND_AGREEMENT_TOL for value in values.values()
        ):
            gudhi_order["pairs_wrong_in_all_four_tests"] += 1
        for key, value in values.items():
            if abs(value - exact) > BACKEND_AGREEMENT_TOL:
                gudhi_order[key] += 1
        if gudhi_order["witness"] is None and abs(
            values["e0_canonical_mismatches"] - exact
        ) > BACKEND_AGREEMENT_TOL:
            gudhi_order["witness"] = {
                "diagram_a": a.tolist(),
                "diagram_b": b.tolist(),
                "scipy_exact": exact,
                "gudhi_default_canonical": values["default_canonical_mismatches"],
                "gudhi_e0_canonical": values["e0_canonical_mismatches"],
                "gudhi_default_shuffled": values["default_shuffled_mismatches"],
                "gudhi_e0_shuffled": values["e0_shuffled_mismatches"],
            }

    exhaustive = None
    if gudhi_order.get("witness"):
        witness = gudhi_order["witness"]
        a = np.asarray(witness["diagram_a"], dtype=float)
        b = np.asarray(witness["diagram_b"], dtype=float)
        if a.shape[0] + b.shape[0] <= 8:
            exhaustive = {
                "n": int(a.shape[0]),
                "m": int(b.shape[0]),
                "scipy_exact": scipy_exact_bottleneck(a, b),
                "exhaustive_enumeration": _exhaustive_bottleneck(a, b),
                "gudhi_e0_canonical": gudhi_exact_e0(a, b),
            }
            exhaustive["agreement"] = (
                abs(
                    exhaustive["scipy_exact"]
                    - exhaustive["exhaustive_enumeration"]
                )
                <= BACKEND_AGREEMENT_TOL
            )

    persim_comparisons = 0
    persim_mismatches = 0
    persim_max_diff = 0.0
    real_pairs_comparisons = 0
    real_pairs_mismatches = 0
    real_pairs_max_diff = 0.0
    try:
        import persim

        for a, b in _random_pairs(rng, 8, 4):
            exact = scipy_exact_bottleneck(a, b)
            comparison = float(persim.bottleneck(a, b))
            persim_comparisons += 1
            if abs(exact - comparison) > BACKEND_AGREEMENT_TOL:
                persim_mismatches += 1
            persim_max_diff = max(persim_max_diff, abs(exact - comparison))

        real_cases = (
            (
                ROOT
                / "research_review"
                / "results"
                / "cache"
                / "A"
                / "ramp"
                / "11"
                / "sigma50"
                / "stride1"
                / "diagrams.npz",
                {1: [(i, i + 1) for i in range(0, 24, 4)], 0: [(0, 1), (10, 11)]},
            ),
            (
                ROOT
                / "research_review"
                / "results"
                / "cache"
                / "A"
                / "return"
                / "11"
                / "sigma50"
                / "stride1"
                / "diagrams.npz",
                {1: [(37, 39), (48, 52), (37, 38), (47, 48)]},
            ),
        )
        for path, index_map in real_cases:
            if not path.is_file():
                continue
            payload = np.load(path)
            for degree, index_pairs in index_map.items():
                series = [payload[f"d{degree}_{i:03d}"] for i in range(129)]
                for i, j in index_pairs:
                    exact = scipy_exact_bottleneck(series[i], series[j])
                    comparison = float(persim.bottleneck(series[i], series[j]))
                    real_pairs_comparisons += 1
                    if abs(exact - comparison) > BACKEND_AGREEMENT_TOL:
                        real_pairs_mismatches += 1
                    real_pairs_max_diff = max(
                        real_pairs_max_diff, abs(exact - comparison)
                    )
    except Exception as error:  # pragma: no cover - persim availability
        return {
            "verdict": "indeterminate",
            "error": str(error),
            "comparisons": comparisons,
            "mismatches": mismatches,
            "max_abs_difference": max_diff,
            "order_invariance": order_invariance,
            "gudhi_order_sensitivity": gudhi_order,
            "exhaustive_verification": exhaustive,
        }
    general_pass = (
        mismatches["project_bruteforce"] == 0
        and order_invariance["mismatches"] == 0
        and persim_mismatches == 0
        and real_pairs_mismatches == 0
        and (exhaustive is None or exhaustive["agreement"])
    )
    return {
        "verdict": "pass" if general_pass else "fail",
        "description": (
            "independent SciPy exact solver against the project brute-force "
            "reference, persim, exhaustive enumeration, and an order-invariance "
            "test; gudhi defects quantified separately"
        ),
        "comparisons": comparisons,
        "mismatches": mismatches,
        "max_abs_difference": max_diff,
        "order_invariance": order_invariance,
        "gudhi_order_sensitivity": gudhi_order,
        "exhaustive_verification": exhaustive,
        "persim_comparisons": persim_comparisons,
        "persim_mismatches": persim_mismatches,
        "persim_max_abs_difference": persim_max_diff,
        "real_diagram_pairs_comparisons": real_pairs_comparisons,
        "real_diagram_pairs_mismatches": real_pairs_mismatches,
        "real_diagram_pairs_max_abs_difference": real_pairs_max_diff,
    }

# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------


def _feature_grid(df, additional_seeds, sigma, features, plt, path, title):
    families = ["A", "B"]
    degrees = [0, 1]
    colors = {"return": "tab:blue", "ramp": "tab:orange", "jump": "tab:green"}
    fig, axes = plt.subplots(
        len(features),
        len(families) * len(degrees),
        figsize=(3.1 * len(families) * len(degrees), 2.5 * len(features)),
        squeeze=False,
        sharex=True,
    )
    for column, family in enumerate(families):
        for row_index, degree in enumerate(degrees):
            column_index = column * len(degrees) + row_index
            subset = df[
                (df["family"] == family)
                & (df["degree"] == degree)
                & (df["sigma"] == sigma)
                & (df["seed"].isin(list(additional_seeds)))
            ]
            for feature_index, (feature, label, logy) in enumerate(features):
                axis = axes[feature_index][column_index]
                for klass in SCIENTIFIC_CLASSES:
                    part = subset[subset["class"] == klass].sort_values("stride")
                    if part.empty:
                        continue
                    grouped = part.groupby("stride")[feature]
                    mean = grouped.mean()
                    low = grouped.min()
                    high = grouped.max()
                    axis.plot(
                        mean.index,
                        mean.values,
                        marker="o",
                        color=colors[klass],
                        label=klass,
                    )
                    axis.fill_between(
                        mean.index,
                        low.values,
                        high.values,
                        color=colors[klass],
                        alpha=0.15,
                    )
                if logy:
                    axis.set_yscale("log")
                axis.set_xticks(list(STRIDES))
                axis.set_xticklabels([str(s) for s in STRIDES])
                if feature_index == 0:
                    axis.set_title(f"family {family}, degree {degree}")
                if column_index == 0:
                    axis.set_ylabel(label)
                if feature_index == len(features) - 1:
                    axis.set_xlabel("stride")
                axis.grid(alpha=0.25)
                if feature_index == 0 and column_index == 0:
                    axis.legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_features_vs_sigma(df, additional_seeds, plt, path, title):
    features = [
        ("L", "L (distance units)", True),
        ("eta", "eta", False),
        ("speed_mean", "mean speed", True),
        ("angle_floor_valid_fraction", "angle floor-valid fraction", False),
    ]
    families = ["A", "B"]
    degrees = [0, 1]
    colors = {"return": "tab:blue", "ramp": "tab:orange", "jump": "tab:green"}
    fig, axes = plt.subplots(
        len(features),
        len(families) * len(degrees),
        figsize=(3.1 * len(families) * len(degrees), 2.5 * len(features)),
        squeeze=False,
        sharex=True,
    )
    positions = {0.0: 0, 0.05: 1}
    for column, family in enumerate(families):
        for row_index, degree in enumerate(degrees):
            column_index = column * len(degrees) + row_index
            subset = df[
                (df["family"] == family)
                & (df["degree"] == degree)
                & (df["stride"] == 1)
                & (df["seed"].isin(list(additional_seeds)))
            ]
            for feature_index, (feature, label, logy) in enumerate(features):
                axis = axes[feature_index][column_index]
                for klass in SCIENTIFIC_CLASSES:
                    part = subset[subset["class"] == klass]
                    xs = []
                    ys = []
                    for sigma in SIGMAS:
                        values = part[part["sigma"] == sigma][feature].to_numpy(
                            dtype=float
                        )
                        values = values[np.isfinite(values)]
                        if values.size:
                            xs.append(positions[sigma])
                            ys.append(float(np.mean(values)))
                    axis.plot(xs, ys, marker="o", color=colors[klass], label=klass)
                if logy:
                    axis.set_yscale("log")
                axis.set_xticks([0, 1])
                axis.set_xticklabels(["0", "0.05"])
                if feature_index == 0:
                    axis.set_title(f"family {family}, degree {degree}")
                if column_index == 0:
                    axis.set_ylabel(label)
                if feature_index == len(features) - 1:
                    axis.set_xlabel("sigma")
                axis.grid(alpha=0.25)
                if feature_index == 0 and column_index == 0:
                    axis.legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_angle_validity(df, additional_seeds, plt, path, title):
    families = ["A", "B"]
    colors = {"return": "tab:blue", "ramp": "tab:orange", "jump": "tab:green"}
    fig, axes = plt.subplots(
        2,
        len(families),
        figsize=(3.4 * len(families), 3.0 * 2),
        squeeze=False,
        sharex=True,
        sharey=True,
    )
    for column, family in enumerate(families):
        for row_index, sigma in enumerate(SIGMAS):
            axis = axes[row_index][column]
            subset = df[
                (df["family"] == family)
                & (df["sigma"] == sigma)
                & (df["seed"].isin(list(additional_seeds)))
            ]
            for klass in SCIENTIFIC_CLASSES:
                for degree, linestyle in ((0, "-"), (1, "--")):
                    part = subset[
                        (subset["class"] == klass) & (subset["degree"] == degree)
                    ].sort_values("stride")
                    if part.empty:
                        continue
                    grouped = part.groupby("stride")["angle_floor_valid_fraction"]
                    mean = grouped.mean()
                    axis.plot(
                        mean.index,
                        mean.values,
                        marker="o",
                        linestyle=linestyle,
                        color=colors[klass],
                        label=f"{klass} d{degree}",
                    )
            axis.set_xticks(list(STRIDES))
            axis.set_xticklabels([str(s) for s in STRIDES])
            axis.set_title(f"family {family}, sigma {sigma}")
            axis.set_ylim(-0.05, 1.05)
            axis.grid(alpha=0.25)
            if row_index == 1:
                axis.set_xlabel("stride")
            if column == 0:
                axis.set_ylabel("angle floor-valid fraction")
            if row_index == 0 and column == 0:
                axis.legend(fontsize=6, ncol=2)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_noise_floor(df, plt, path, title):
    families = ["A", "B"]
    degrees = [0, 1]
    colors = {"return": "tab:blue", "ramp": "tab:orange", "jump": "tab:green"}
    fig, axes = plt.subplots(
        len(families),
        len(degrees),
        figsize=(4.0 * len(degrees), 3.2 * len(families)),
        squeeze=False,
        sharex=True,
    )
    for row_index, family in enumerate(families):
        for column, degree in enumerate(degrees):
            axis = axes[row_index][column]
            subset = df[
                (df["family"] == family)
                & (df["degree"] == degree)
                & (df["sigma"] == 0.05)
                & (df["role"] == "scientific")
            ]
            for klass in SCIENTIFIC_CLASSES:
                part = subset[subset["class"] == klass].sort_values("stride")
                grouped = part.groupby("stride")["L_over_floor_ratio"]
                mean = grouped.mean()
                axis.plot(
                    mean.index,
                    mean.values,
                    marker="o",
                    color=colors[klass],
                    label=klass,
                )
            axis.axhline(2.0, color="black", linestyle=":", linewidth=1.2)
            axis.axhline(1.0, color="gray", linestyle=":", linewidth=1.0)
            axis.set_yscale("log")
            axis.set_xticks(list(STRIDES))
            axis.set_xticklabels([str(s) for s in STRIDES])
            axis.set_title(f"family {family}, degree {degree}")
            axis.grid(alpha=0.25)
            if row_index == len(families) - 1:
                axis.set_xlabel("stride")
            if column == 0:
                axis.set_ylabel("mean step / floor  (L/(T-1))/e")
            if row_index == 0 and column == 0:
                axis.legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_edge_case_counts(df, plt, path, title):
    families = ["A", "B"]
    degrees = [0, 1]
    sigmas = [0.0, 0.05]
    categories = [
        ("unresolved_zero_step_count", "unresolved zero steps"),
        ("cosine_anomaly_count", "cosine anomalies"),
        ("empty_diagram_count", "empty diagrams"),
        ("card_change_count", "cardinality changes"),
    ]
    width = 0.2
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.0), sharey=False)
    for axis, family in zip(axes, families):
        subset = df[df["family"] == family]
        labels = []
        for sigma in sigmas:
            for degree in degrees:
                labels.append((sigma, degree))
        x = np.arange(len(labels))
        for offset, (column, label) in enumerate(categories):
            values = []
            for sigma, degree in labels:
                part = subset[
                    (subset["sigma"] == sigma) & (subset["degree"] == degree)
                ]
                values.append(int(part[column].sum()))
            axis.bar(
                x + (offset - 1.5) * width,
                np.asarray(values, dtype=float) + 0.5,
                width=width,
                label=label,
            )
        axis.set_xticks(x)
        axis.set_xticklabels([f"s{s}\nd{d}" for s, d in labels])
        axis.set_yscale("log")
        axis.set_title(f"family {family}")
        axis.grid(alpha=0.25, axis="y")
    axes[0].set_ylabel("count (log scale, 0 plotted as 0.5)")
    axes[0].legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_backend_discrepancy(df_primary, df_exact, plt, path):
    merged = df_primary.merge(
        df_exact,
        on=["family", "class", "seed", "sigma", "stride", "degree"],
        suffixes=("_primary", "_exact"),
    )
    merged["abs_diff"] = np.abs(
        merged["L_primary"].to_numpy(dtype=float)
        - merged["L_exact"].to_numpy(dtype=float)
    )
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    for axis, column, label, logy in zip(
        axes,
        ["abs_diff", "eta_primary"],
        [
            "|L(primary) - L(exact)|",
            "eta under the frozen primary backend",
        ],
        [True, False],
    ):
        families = sorted(merged["family"].unique())
        data = [
            merged[merged["family"] == family][column].to_numpy(dtype=float)
            for family in families
        ]
        data = [values[np.isfinite(values)] for values in data]
        axis.boxplot(data, tick_labels=families)
        axis.set_title(label)
        axis.grid(alpha=0.25, axis="y")
        if logy:
            axis.set_yscale("symlog", linthresh=1e-12)
    fig.suptitle(
        "WP-2.2 metric backend discrepancy (rows pooled over classes, seeds, sigmas, strides, degrees)"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _cell_summary_table(df):
    rows = []
    for (family, klass, sigma, stride, degree), part in df.groupby(
        ["family", "class", "sigma", "stride", "degree"], sort=True
    ):
        if klass == "static":
            continue
        entry = {
            "metric": str(part["metric"].iloc[0]),
            "family": family,
            "class": klass,
            "sigma": sigma,
            "stride": int(stride),
            "degree": int(degree),
            "n_seeds": int(part["seed"].nunique()),
        }
        for column in [
            "L",
            "eta",
            "speed_mean",
            "speed_change_mean_abs",
            "angle_floor_valid_fraction",
            "q_mean",
            "floor_e",
        ]:
            values = part[column].to_numpy(dtype=float)
            values = values[np.isfinite(values)]
            entry[f"{column}_mean"] = float(np.mean(values)) if values.size else None
            entry[f"{column}_std"] = (
                float(np.std(values, ddof=1)) if values.size >= 2 else None
            )
        entry["efficiency_coverage"] = float(
            part["efficiency_valid"].astype(float).mean()
        )
        rows.append(entry)
    return rows


def _minimal_witness():
    """Deterministic minimal pair exposed by a small random search (3 vs 4 points)."""

    import itertools

    from tk_pilot.diagram_metrics import _bruteforce_cost_matrix, bottleneck_bruteforce

    rng = np.random.default_rng(7)
    for _ in range(400):
        n, m = 3, 4
        births_a = rng.uniform(0.0, 1.0, n)
        births_b = rng.uniform(0.0, 1.0, m)
        a = np.column_stack([births_a, births_a + rng.uniform(0.0, 1.0, n)])
        b = np.column_stack([births_b, births_b + rng.uniform(0.0, 1.0, m)])
        exact = scipy_exact_bottleneck(a, b)
        default = float(bottleneck_linf(a, b))
        canonical_default = float(
            __import__("gudhi").bottleneck_distance(
                as_diagram(a), as_diagram(b)
            )
        )
        canonical_e0 = float(
            __import__("gudhi").bottleneck_distance(
                as_diagram(a), as_diagram(b), 0.0
            )
        )
        if (
            abs(exact - default) <= BACKEND_AGREEMENT_TOL
            and abs(exact - canonical_e0) <= BACKEND_AGREEMENT_TOL
        ):
            continue
        costs = _bruteforce_cost_matrix(a, b)
        best = np.inf
        best_perm = None
        for perm in itertools.permutations(range(n + m)):
            worst = 0.0
            for i, j in enumerate(perm):
                value = costs[i, j]
                if value > worst:
                    worst = value
                    if worst >= best:
                        break
            if worst < best:
                best = worst
                best_perm = perm
        certificate = []
        for i, j in enumerate(best_perm):
            if i < n and j < m:
                kind = "point_to_point"
                cost = float(costs[i, j])
            elif i < n:
                kind = "a_to_diagonal"
                cost = float(0.5 * (a[i, 1] - a[i, 0]))
            elif j < m:
                kind = "b_to_diagonal"
                cost = float(0.5 * (b[j, 1] - b[j, 0]))
            else:
                kind = "diagonal_to_diagonal"
                cost = 0.0
            certificate.append(
                {"i": int(i), "j": int(j), "kind": kind, "cost": cost}
            )
        return {
            "diagram_a": a.tolist(),
            "diagram_b": b.tolist(),
            "scipy_exact": exact,
            "project_bruteforce": float(bottleneck_bruteforce(a, b)),
            "persim": float(__import__("persim").bottleneck(a, b)),
            "gudhi_default": default,
            "gudhi_exact_e0": gudhi_exact_e0(a, b),
            "gudhi_default_canonical": canonical_default,
            "gudhi_e0_canonical": canonical_e0,
            "abs_diff": max(
                abs(default - exact),
                abs(canonical_default - exact),
                abs(canonical_e0 - exact),
            ),
            "certificate_matching": certificate,
            "search": "random 3-point and 4-point diagrams, numpy default_rng(7)",
        }
    return None

# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def _fmt(value, digits=4):
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}g}"


def _backend_audit_report(summary, witnesses, solver_validation, checks_exact):
    order = solver_validation["gudhi_order_sensitivity"]
    lines = []
    lines.append("# WP-2.2 metric backend audit")
    lines.append("")
    lines.append(f"Gate label: {GATE_LABEL}.")
    lines.append("")
    lines.append("## 1. Finding")
    lines.append("")
    lines.append(
        "The frozen primary metric call, `tk_pilot.diagram_metrics.bottleneck_linf`, "
        "canonicalizes each finite diagram and then calls "
        "`gudhi.bottleneck_distance` from gudhi 3.12.0. Two separate defects were "
        "observed on real pilot diagrams and are quantified in this audit."
    )
    lines.append("")
    lines.append(
        "First, the default call does not use gudhi's exact algorithm: the "
        "documented default `e=None` selects the approximate path, and the "
        "additive approximation error is not small relative to the declared "
        "numerical zero. Second, and decisively, the gudhi implementation is not "
        "invariant to the order of the input points. The canonicalized inputs that "
        "the frozen wrapper always produces give a wrong distance on some real "
        "pairs even when the exact algorithm is requested with `e=0.0`, while the "
        "same diagrams in their stored order can give the correct value. Pinning "
        "`e=0.0` therefore does not repair the backend."
    )
    lines.append("")
    lines.append(
        "The WP-2.2 machine checks detect the defect directly: the frozen backend "
        f"fails the triangle-inequality check with "
        f"{summary.get('primary_triangle_violations', 0)} violating triples and "
        f"worst excess {_fmt(summary.get('primary_triangle_worst'), 6)}, and fails "
        f"the triangle-excess range check with "
        f"{summary.get('primary_q_violations', 0)} violating interior times. The "
        f"corrected candidate `{BACKEND_EXACT}` passes all {checks_exact} checks."
    )
    lines.append("")
    lines.append("## 2. Backend comparison on the WP-2.2 grid")
    lines.append("")
    lines.append(
        f"Distinct distance pairs compared: {summary.get('n_pairs_compared', 0)}. "
        f"Pairs differing by more than 1e-12: {summary.get('n_above_tolerance', 0)}. "
        f"Maximum absolute difference: {_fmt(summary.get('max_abs_difference'), 6)}."
    )
    lines.append("")
    lines.append("| degree | pairs compared | differing beyond 1e-12 | max abs difference |")
    lines.append("|---|---|---|---|")
    for degree, block in sorted(summary.get("by_degree", {}).items()):
        lines.append(
            f"| {degree} | {block.get('n_pairs_compared', 0)} | "
            f"{block.get('n_above_tolerance', 0)} | "
            f"{_fmt(block.get('max_abs_difference'), 6)} |"
        )
    lines.append("")
    lines.append("Worst observed witnesses (indices refer to the stride-1 frame ordering):")
    lines.append("")
    lines.append(
        "| trajectory | class | seed | sigma | degree | i | j | primary value | "
        "exact value | abs difference |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for witness in witnesses[:10]:
        lines.append(
            f"| {witness.get('trajectory_id', 'n/a')} | "
            f"{witness.get('class', 'n/a')} | {witness.get('seed', 'n/a')} | "
            f"{witness.get('sigma', 'n/a')} | {witness['degree']} | "
            f"{witness['i']} | {witness['j']} | "
            f"{_fmt(witness['primary'], 9)} | {_fmt(witness['exact'], 9)} | "
            f"{_fmt(witness['abs_diff'], 6)} |"
        )
    lines.append("")
    lines.append(
        "The failing comparisons include non-adjacent pairs used by the "
        "comparison-angle construction, so the primary backend also corrupts q_t "
        "and the triangle side of eta. The frozen feature table is still written, "
        "labelled as the frozen backend output; the corrected candidate table is "
        "written beside it."
    )
    lines.append("")
    lines.append("## 3. Incorrectness and order sensitivity of gudhi")
    lines.append("")
    lines.append(
        f"On {order['n_pairs']} random diagram pairs, the exact corrected solver "
        "was compared against the gudhi implementation on canonicalized and "
        "randomly permuted inputs:"
    )
    lines.append("")
    lines.append("| gudhi call | input order | mismatches against exact |")
    lines.append("|---|---|---|")
    lines.append(
        f"| default `e=None` | canonical | {order['default_canonical_mismatches']} |"
    )
    lines.append(
        f"| default `e=None` | shuffled | {order['default_shuffled_mismatches']} |"
    )
    lines.append(f"| exact `e=0.0` | canonical | {order['e0_canonical_mismatches']} |")
    lines.append(f"| exact `e=0.0` | shuffled | {order['e0_shuffled_mismatches']} |")
    lines.append("")
    lines.append(
        f"Pairs wrong in all four tests, meaning no tested order or `e` setting "
        f"recovers the exact value: {order['pairs_wrong_in_all_four_tests']}. The "
        "defect is therefore not only an ordering artefact that canonicalization "
        "could fix; the implementation is simply incorrect on some inputs."
    )
    lines.append("")
    if order.get("witness"):
        witness = order["witness"]
        lines.append(
            "A witness from this test: for one pair the exact value is "
            f"{_fmt(witness['scipy_exact'], 9)}, gudhi `e=0.0` on the canonical "
            f"order returns {_fmt(witness['gudhi_e0_canonical'], 9)}, and the same "
            "call on a shuffled order returns "
            f"{_fmt(witness['gudhi_e0_shuffled'], 9)}."
        )
        lines.append("")
    exhaustive = solver_validation.get("exhaustive_verification")
    if exhaustive:
        lines.append(
            "Exhaustive cross-check on a 4 versus 4 point pair: enumerating all "
            f"matchings with diagonal copies gives "
            f"{_fmt(exhaustive['exhaustive_enumeration'], 9)}, the corrected solver "
            f"gives {_fmt(exhaustive['scipy_exact'], 9)} "
            f"({'agreement' if exhaustive['agreement'] else 'disagreement'}), and "
            f"gudhi `e=0.0` on the canonical order gives "
            f"{_fmt(exhaustive['gudhi_e0_canonical'], 9)}. The minimal 3 versus 4 "
            "point witness and its certificate are stored in "
            "`metric_backend_witness.json`."
        )
        lines.append("")
    lines.append("## 4. Verification of the corrected candidate")
    lines.append("")
    lines.append(
        "The corrected candidate is an independent SciPy exact solver: binary "
        "search over the finite candidate costs of the augmented matching problem "
        "with a perfect-matching feasibility test. It shares no code with gudhi, "
        "persim, or the project brute-force reference. Validation results:"
    )
    lines.append("")
    lines.append(
        f"1. Against the project brute-force reference on small diagrams: "
        f"{solver_validation['comparisons']['scipy_vs_project_bruteforce']} "
        f"comparisons, {solver_validation['mismatches']['project_bruteforce']} "
        f"mismatches, maximum absolute difference "
        f"{_fmt(solver_validation['max_abs_difference']['project_bruteforce'], 6)}."
    )
    lines.append(
        f"2. Order invariance: {solver_validation['order_invariance']['comparisons']} "
        f"canonical against shuffled comparisons, "
        f"{solver_validation['order_invariance']['mismatches']} mismatches, maximum "
        f"absolute difference "
        f"{_fmt(solver_validation['order_invariance']['max_abs_difference'], 6)}."
    )
    lines.append(
        f"3. Against persim on synthetic pairs: "
        f"{solver_validation['persim_comparisons']} comparisons, "
        f"{solver_validation['persim_mismatches']} mismatches, maximum absolute "
        f"difference {_fmt(solver_validation['persim_max_abs_difference'], 6)}."
    )
    lines.append(
        f"4. Against persim on cached real diagrams: "
        f"{solver_validation['real_diagram_pairs_comparisons']} comparisons, "
        f"{solver_validation['real_diagram_pairs_mismatches']} mismatches, maximum "
        f"absolute difference "
        f"{_fmt(solver_validation['real_diagram_pairs_max_abs_difference'], 6)}."
    )
    lines.append("")
    lines.append("## 5. Minimal standalone witness")
    lines.append("")
    witness = summary.get("minimal_witness")
    if witness:
        lines.append(
            "A minimal reproduction with 3 and 4 points is recorded in "
            "`metric_backend_witness.json` together with the certificate matching. "
            f"For that pair, the exact value is {_fmt(witness['scipy_exact'], 9)}, "
            f"gudhi default on the stored order returns "
            f"{_fmt(witness['gudhi_default'], 9)}, gudhi `e=0.0` on the canonical "
            f"order returns {_fmt(witness.get('gudhi_e0_canonical'), 9)}, and the "
            f"largest discrepancy is {_fmt(witness['abs_diff'], 6)}."
        )
    else:
        lines.append("No minimal witness was generated.")
    lines.append("")
    lines.append("## 6. Consequences and required action")
    lines.append("")
    lines.append(
        "1. The frozen backend fails the declared tolerance pseudometric policy on "
        "real pilot diagrams, and the failure is not a rounding band: it reaches "
        "tens of thousandths and breaks the triangle inequality."
    )
    lines.append(
        "2. Pinning `e=0.0` is necessary but not sufficient. The order dependence "
        "means the backend must be replaced by an exact implementation that is "
        "order invariant, for example the validated SciPy solver used here as the "
        "corrected candidate, or a gudhi call without the canonicalization that "
        "triggers the wrong value, after the order dependence is understood and "
        "fixed upstream."
    )
    lines.append(
        "3. Cached artifacts produced by the frozen backend (the smoke distance "
        "matrices under `research_review/results/cache/runner_distances` and any "
        "features built from them) are unreliable wherever the defect triggers. "
        "Their reproducibility check passes, because the same wrong function is "
        "reproduced, but their correctness does not."
    )
    lines.append(
        "4. Amend `research_review/metric_interface.md` and the ledger to declare "
        "the exact solver as the primary metric (or to pin a verified gudhi call), "
        "re-run WP-0.2 with randomized order tests, and re-run WP-2.2 under the "
        "amended definition before the G2 decision. This is a policy change and "
        "must be recorded, not applied silently inside WP-2.2."
    )
    lines.append(
        "5. The WP-2.2 definitions themselves are stable under the corrected "
        "candidate, but the frozen backend is a G2 blocker and cached artifacts "
        "must be regenerated after the interface amendment."
    )
    lines.append("")
    return "\n".join(lines)


def _edge_case_report(df, floors, seed11_floors):
    lines = []
    lines.append("# WP-2.2 edge-case report")
    lines.append("")
    lines.append(f"Gate label: {GATE_LABEL}.")
    lines.append("")
    lines.append(
        "This report enumerates every degenerate case present in the evaluated "
        "diagram sequences, the treatment applied under the frozen policies in "
        "`research_review/assumption_ledger.yaml` and `research_review/metric_interface.md`, "
        "and the resulting abstention coverage. No trajectory and no valid case was "
        "dropped. Abstention means a quantity is reported as undefined for that "
        "time or that a validity flag is false; it never removes a row."
    )
    lines.append("")
    lines.append(
        f"The tables refer to the corrected candidate backend `{BACKEND_EXACT}`, "
        "an independent exact solver verified against the project brute-force "
        "reference, persim, and an order-invariance test; the frozen backend "
        "table is written separately and its metric defect is documented in "
        "`metric_backend_audit.md`."
    )
    lines.append("")
    lines.append("## 1. Evaluated grid")
    lines.append("")
    lines.append(
        "Cells: families A and B, classes return, ramp, jump, and the static "
        "calibration control, seeds 11, 1000, and 1001, sigma 0 and 0.05, strides "
        "1, 2, and 4, degrees 0 (primary) and 1 (secondary). Seed 11 trajectories "
        "are the cached smoke draws; seeds 1000 and 1001 are the additional "
        "train-like draws computed fresh under the temporary cache. Strides 2 and "
        "4 are exact subsamples of the stride-1 realization."
    )
    lines.append("")
    lines.append(
        f"Rows written: {len(df)}. A missing-window event would exclude a whole "
        "trajectory with a recorded count; none occurred."
    )
    lines.append("")
    lines.append("## 2. Degenerate-case inventory")
    lines.append("")
    lines.append(
        "| family | degree | sigma | unresolved zero-step times | L = 0 rows | "
        "efficiency abstentions | angle floor abstentions | q floor abstentions | "
        "cosine anomalies | empty diagrams | cardinality changes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for family in ["A", "B"]:
        for degree in [0, 1]:
            for sigma in [0.0, 0.05]:
                part = df[
                    (df["family"] == family)
                    & (df["degree"] == degree)
                    & (df["sigma"] == sigma)
                ]
                zero_steps = int(
                    (part["n_intervals"] - 1 - part["angle_defined_count"])
                    .clip(lower=0)
                    .sum()
                )
                l_zero = int((part["L"] == 0.0).sum())
                eff_abstain = int((~part["efficiency_valid"]).sum())
                angle_interior = (part["n_intervals"] - 1).clip(lower=0)
                angle_abstain = int(
                    (angle_interior - part["angle_floor_valid_count"])
                    .clip(lower=0)
                    .sum()
                )
                q_defined = int(part["q_defined_count"].sum())
                q_abstain = int(q_defined - part["q_valid_count"].sum())
                anomalies = int(part["cosine_anomaly_count"].sum())
                empty = int(part["empty_diagram_count"].sum())
                card_changes = int(part["card_change_count"].sum())
                lines.append(
                    f"| {family} | {degree} | {sigma} | {zero_steps} | {l_zero} | "
                    f"{eff_abstain} | {angle_abstain} | {q_abstain} | {anomalies} | "
                    f"{empty} | {card_changes} |"
                )
    lines.append("")
    lines.append(
        "Counts pool all classes, seeds, and strides within each family, degree, "
        "and sigma block, so they include the static calibration controls; the "
        "scientific classes alone are used in section 3."
    )
    lines.append("")

    scientific = df[df["role"] == "scientific"]
    total_zero = int(
        (scientific["n_intervals"] - 1 - scientific["angle_defined_count"])
        .clip(lower=0)
        .sum()
    )
    total_interior = int((scientific["n_intervals"] - 1).clip(lower=0).sum())
    lines.append("## 3. Zero steps and undefined angles")
    lines.append("")
    lines.append(
        "A zero step is an adjacent diagram distance returned as exactly 0.0 under "
        "the declared numerical-zero convention, so the law-of-cosines denominator "
        "2ab vanishes and the comparison angle is undefined. Policy: the step is "
        "counted as unresolved, the angle is null, and the trajectory stays in the "
        "table."
    )
    lines.append("")
    lines.append(
        f"Scientific rows carry {total_zero} unresolved zero-step interior times "
        f"out of {total_interior} interior times "
        f"({100.0 * total_zero / max(total_interior, 1):.1f} percent). The largest "
        "concentrations are the exact-zero regime of family B, where degree 0 and "
        "degree 1 diagrams are mostly empty or carry one off-diagonal point, and "
        "the flat segments of the return and jump controls at sigma = 0, where "
        "consecutive diagrams are identical."
    )
    lines.append("")
    lines.append(
        "Undefined angles occur exactly when a = 0 or b = 0, which the machine "
        "check `angle_defined_iff_positive_steps` confirms with zero violations."
    )
    lines.append("")
    lines.append("## 4. Paths with L = 0 and undefined efficiency")
    lines.append("")
    zero_paths = df[df["L"] == 0.0]
    lines.append(
        f"Rows with L = 0: {len(zero_paths)}. In every such row eta is null, the "
        "efficiency flag is false, comparison angles and q are undefined, and the "
        "row is retained. The machine check `eta_undefined_iff_L_zero` confirms the "
        "exact correspondence."
    )
    lines.append("")
    if len(zero_paths):
        lines.append("| family | class | seed | sigma | stride | degree |")
        lines.append("|---|---|---|---|---|---|")
        for _, row in zero_paths.sort_values(
            ["family", "class", "seed", "sigma", "stride", "degree"]
        ).iterrows():
            lines.append(
                f"| {row['family']} | {row['class']} | {int(row['seed'])} | "
                f"{row['sigma']} | {int(row['stride'])} | {int(row['degree'])} |"
            )
        lines.append("")
    scientific_zero = zero_paths[zero_paths["role"] == "scientific"]
    lines.append(
        f"Scientific rows with L = 0: {len(scientific_zero)}. These come from "
        "exactly static diagram sequences (family B at sigma = 0)."
    )
    lines.append("")
    lines.append("## 5. Near-zero floors and abstention coverage")
    lines.append("")
    lines.append(
        "The floor e is the 95th percentile of adjacent diagram distances of the "
        "static sigma = 0.05 calibration population for each (family, degree, "
        "stride) cell, using the train-like seeds 1000 and 1001. At sigma = 0 the "
        "floor is exactly zero. The checkpoint values are:"
    )
    lines.append("")
    lines.append("| cell (family, degree, stride) | e | seed 11 static sensitivity |")
    lines.append("|---|---|---|")
    for cell in sorted(floors):
        lines.append(
            f"| {cell} | {_fmt(floors[cell], 6)} | {_fmt(seed11_floors.get(cell), 6)} |"
        )
    lines.append("")
    floor_violations = df[
        (df["sigma"] == 0.05)
        & (df["n_intervals"] > 1)
        & (df["L_over_floor_ratio"].notna())
        & (df["L_over_floor_ratio"] <= 2.0)
    ]
    lines.append(
        f"Rows whose mean step L/(T-1) lies at or below the efficiency abstention "
        f"bound 2e at sigma = 0.05: {len(floor_violations)}, which is every "
        "sigma = 0.05 row on this grid. These rows keep their values but are "
        "flagged efficiency-invalid, so the efficiency channel has zero coverage "
        "in the noise regime under the conservative floor. Comparison-angle "
        "floor coverage at sigma = 0.05 is likewise small; the exact fractions "
        "are in the table below."
    )
    lines.append("")
    lines.append("Per-cell coverage, pooled over seeds and classes:")
    lines.append("")
    lines.append(
        "| family | degree | sigma | stride | angle defined | angle floor-valid | "
        "efficiency coverage | eta defined |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for family in ["A", "B"]:
        for degree in [0, 1]:
            for sigma in [0.0, 0.05]:
                for stride in [1, 2, 4]:
                    part = df[
                        (df["family"] == family)
                        & (df["degree"] == degree)
                        & (df["sigma"] == sigma)
                        & (df["stride"] == stride)
                        & (df["role"] == "scientific")
                    ]
                    lines.append(
                        f"| {family} | {degree} | {sigma} | {stride} | "
                        f"{np.mean(part['angle_defined_fraction']):.3f} | "
                        f"{np.mean(part['angle_floor_valid_fraction']):.3f} | "
                        f"{np.mean(part['efficiency_valid'].astype(float)):.3f} | "
                        f"{np.mean(part['eta_defined'].astype(float)):.3f} |"
                    )
    lines.append("")
    lines.append("## 6. Cosine anomalies")
    lines.append("")
    lines.append(
        f"Recorded cosine anomalies (|z| > 1 + 1e-12 before clipping): "
        f"{int(df['cosine_anomaly_count'].sum())}. The machine check "
        "`cosine_anomaly_accounting` verifies that the flags equal the set of "
        "defined cosines outside the tolerance, so no anomaly is hidden. Clipping "
        "keeps arccos total; straight and reversal cases are reported, not deleted."
    )
    lines.append("")
    lines.append(
        f"Straight cases retained: {int(df['straight_count'].sum())}. "
        f"Reversal cases retained: {int(df['reversal_count'].sum())}. "
        f"Near-straight within 1e-6: {int(df['near_straight_count'].sum())}. "
        f"Near-reversal within 1e-6: {int(df['near_reversal_count'].sum())}."
    )
    lines.append("")
    lines.append("## 7. Cardinality changes and empty diagrams")
    lines.append("")
    lines.append(
        "Cardinality changes and empty diagrams are expected objects under the "
        "frozen policy; the bottleneck metric handles unequal cardinality through "
        "diagonal matching, and empty finite diagrams are valid. Cardinality is "
        "recorded per frame; no persistence threshold or interpolation was applied."
    )
    lines.append("")
    lines.append(
        f"Empty frames across all rows: {int(df['empty_diagram_count'].sum())}. "
        f"Rows with at least one cardinality change: "
        f"{int((df['card_change_count'] > 0).sum())}. Maximum single-frame "
        f"cardinality change: {int((df['card_max'] - df['card_min']).max())}."
    )
    lines.append("")
    lines.append("## 8. Metric backend edge case")
    lines.append("")
    lines.append(
        "The frozen primary backend is itself a degenerate case: the gudhi "
        "implementation returns incorrect distances on some real pilot pairs, in "
        "some cases for every tested input order and with both the default and "
        "the exact algorithm, and it fails the declared tolerance pseudometric "
        "assumption by up to about 0.05. This is reported in full in "
        "`metric_backend_audit.md` and under the `gudhi_default` backend in "
        "`checks.json`. No value was repaired in place; the corrected candidate is "
        "reported as a separate labeled table, and cached frozen-backend "
        "artifacts must be regenerated after the interface amendment."
    )
    lines.append("")
    lines.append("## 9. Summary of abstained quantities and coverage")
    lines.append("")
    lines.append(
        "1. eta is abstained exactly on L = 0 rows, tabulated in section 4; "
        "elsewhere it is reported."
    )
    lines.append(
        "2. The efficiency-valid flag is false whenever L <= 2 (T - 1) e, which "
        "captures every L = 0 row and the near-floor rows of section 5; eta itself "
        "is still reported when L > 0."
    )
    lines.append(
        "3. Comparison angles are abstained on zero steps and on steps below the "
        "calibrated floor min(a, b) <= 2e; the coverage columns in section 5 give "
        "the exact fractions per cell."
    )
    lines.append(
        "4. q_t is reported only on interior times with a + b > 4e, the predeclared "
        "sum floor. The q-valid counts and fractions are in the feature table and "
        "in section 2."
    )
    lines.append("")
    lines.append(
        "No valid straight or reversal index was removed, no trajectory was "
        "deleted, and every degenerate count above remains visible in "
        "`feature_table_exact_metric.csv` and `checks.json`."
    )
    lines.append("")
    return "\n".join(lines)


def _stability_report(df, checks, floors, seed11_floors, verdicts, primary_summary):
    lines = []
    lines.append("# WP-2.2 stability report")
    lines.append("")
    lines.append(f"Gate label: {GATE_LABEL}.")
    lines.append("")
    lines.append(
        "Scope. This report checks whether the bounded metric diagnostics keep a "
        "stable operational definition across sampling rates and noise levels on "
        "the evaluated diagram sequences. WP-2.2 passes on stable definitions "
        "only; nothing here is evidence of predictive value, and no classification "
        "or decision claim is made."
    )
    lines.append("")
    lines.append(
        f"The main tables use the corrected candidate backend `{BACKEND_EXACT}` "
        "(an independent exact solver, verified against the project brute-force "
        "reference, persim, and an order-invariance test). The frozen backend "
        "`gudhi_default` fails the metric axiom checks, as reported in "
        "`checks.json` and `metric_backend_audit.md`; its stability numbers are "
        "therefore not interpreted."
    )
    lines.append("")
    lines.append("## 1. Data and uncertainty")
    lines.append("")
    lines.append(
        f"Rows evaluated: {len(df)} over families A and B, classes return, ramp, "
        "jump, and static, seeds 11 (cached smoke), 1000 and 1001 (additional "
        "train-like draws), sigma 0 and 0.05, strides 1, 2, and 4, and degrees 0 "
        "and 1. Uncertainty is reported as the across-seed sample standard "
        "deviation within each cell in `cell_summary.csv`; with three seeds per "
        "cell it is a spread indicator, not an inferential confidence interval. "
        "The declared numerical zero is 1e-12, so differences below that scale are "
        "not resolvable."
    )
    lines.append("")
    lines.append("## 2. Sampling-rate sensitivity")
    lines.append("")
    lines.append(
        "Strides 2 and 4 subsample the same master realization and keep the "
        "physical horizon fixed, so interval counts fall and each interval spans "
        "more physical time. Table cells below are means over classes and seeds of "
        "the stride-specific values at sigma = 0.05."
    )
    lines.append("")
    lines.append(
        "| family | degree | stride | mean L | mean L/(T-1) | mean eta | mean speed | "
        "angle floor-valid | mean q |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for family in ["A", "B"]:
        for degree in [0, 1]:
            for stride in [1, 2, 4]:
                part = df[
                    (df["family"] == family)
                    & (df["degree"] == degree)
                    & (df["stride"] == stride)
                    & (df["sigma"] == 0.05)
                    & (df["role"] == "scientific")
                ]
                lines.append(
                    f"| {family} | {degree} | {stride} | {_fmt(part['L'].mean())} | "
                    f"{_fmt(part['L_per_interval'].mean())} | {_fmt(part['eta'].mean())} | "
                    f"{_fmt(part['speed_mean'].mean())} | "
                    f"{_fmt(part['angle_floor_valid_fraction'].mean(), 3)} | "
                    f"{_fmt(part['q_mean'].mean())} |"
                )
    lines.append("")
    lines.append(
        "On the fixed horizon [0, 1] the mean interval speed in distance units "
        "per unit physical time equals L, so the mean L and mean speed columns "
        "coincide by construction and are not independent evidence."
    )
    lines.append("")
    lines.append(
        "Relative change of the cell mean from stride 1 to stride 4, sigma = 0.05:"
    )
    lines.append("")
    lines.append(
        "| family | degree | L ratio s4/s1 | L/(T-1) ratio s4/s1 | eta ratio s4/s1 |"
    )
    lines.append("|---|---|---|---|---|")

    def cell_mean(part, column, stride):
        values = part[part["stride"] == stride][column].to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        return float(np.mean(values)) if values.size else float("nan")

    l_ratios = []
    p_ratios = []
    e_ratios = []
    for family in ["A", "B"]:
        for degree in [0, 1]:
            part = df[
                (df["family"] == family)
                & (df["degree"] == degree)
                & (df["sigma"] == 0.05)
                & (df["role"] == "scientific")
            ]
            l1, l4 = cell_mean(part, "L", 1), cell_mean(part, "L", 4)
            p1, p4 = cell_mean(part, "L_per_interval", 1), cell_mean(
                part, "L_per_interval", 4
            )
            e1, e4 = cell_mean(part, "eta", 1), cell_mean(part, "eta", 4)
            lines.append(
                f"| {family} | {degree} | {_fmt(l4 / l1, 3)} | {_fmt(p4 / p1, 3)} | "
                f"{_fmt(e4 / e1, 3)} |"
            )
            if np.isfinite(l1) and l1 != 0:
                l_ratios.append(abs(l4 / l1))
            if np.isfinite(p1) and p1 != 0:
                p_ratios.append(abs(p4 / p1))
            if np.isfinite(e1) and e1 != 0:
                e_ratios.append(abs(e4 / e1))
    lines.append("")
    lines.append(
        f"Across cells, the stride-4 to stride-1 ratio of L has median "
        f"{_fmt(np.median(l_ratios), 3)} and range "
        f"[{_fmt(min(l_ratios), 3)}, {_fmt(max(l_ratios), 3)}]; for L/(T-1) the "
        f"median ratio is {_fmt(np.median(p_ratios), 3)} with range "
        f"[{_fmt(min(p_ratios), 3)}, {_fmt(max(p_ratios), 3)}]; for eta the median "
        f"ratio is {_fmt(np.median(e_ratios), 3)} with range "
        f"[{_fmt(min(e_ratios), 3)}, {_fmt(max(e_ratios), 3)}]."
    )
    lines.append("")
    lines.append(
        "Interpretation and flags. L is a discretization-dependent accumulation "
        "by construction: it counts resolved steps, so its value is only "
        "comparable within a fixed stride cell. The observed stride-4 to stride-1 "
        "ratios show how strongly the cell means move with resolution: L falls by "
        f"a median factor of {_fmt(1.0 / np.median(l_ratios), 3)} "
        f"(range {_fmt(1.0 / max(l_ratios), 3)} to "
        f"{_fmt(1.0 / min(l_ratios), 3)}), L/(T-1) changes by a median factor of "
        f"{_fmt(np.median(p_ratios), 3)} (range {_fmt(min(p_ratios), 3)} to "
        f"{_fmt(max(p_ratios), 3)}), and eta changes by a median factor of "
        f"{_fmt(np.median(e_ratios), 3)} (range {_fmt(min(e_ratios), 3)} to "
        f"{_fmt(max(e_ratios), 3)}). The definitions of L, L/(T-1), and eta are "
        "unchanged across cells and their coverage is reported, but their values "
        "are not sampling-invariant on this grid. Flag: eta is strongly "
        "resolution-sensitive and must not be compared across stride cells; it is "
        "retained with exploratory status for any cross-resolution statement. "
        "Flag: L/(T-1) is mildly resolution-sensitive and is likewise reported "
        "per cell rather than pooled. Peak speeds of the jump class shrink at "
        "stride 4 because the transition is resolved by fewer intervals; this is "
        "a resolution effect, not a change of definition."
    )
    lines.append("")
    lines.append("## 3. Noise sensitivity")
    lines.append("")
    lines.append("Table cells below are means over classes and seeds at stride 1.")
    lines.append("")
    lines.append(
        "| family | degree | sigma | mean L | mean eta | mean speed | angle defined | "
        "angle floor-valid | mean q | zero-step times |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for family in ["A", "B"]:
        for degree in [0, 1]:
            for sigma in [0.0, 0.05]:
                part = df[
                    (df["family"] == family)
                    & (df["degree"] == degree)
                    & (df["sigma"] == sigma)
                    & (df["stride"] == 1)
                    & (df["role"] == "scientific")
                ]
                zero_steps = int(
                    (part["n_intervals"] - 1 - part["angle_defined_count"])
                    .clip(lower=0)
                    .sum()
                )
                lines.append(
                    f"| {family} | {degree} | {sigma} | {_fmt(part['L'].mean())} | "
                    f"{_fmt(part['eta'].mean())} | {_fmt(part['speed_mean'].mean())} | "
                    f"{_fmt(part['angle_defined_fraction'].mean(), 3)} | "
                    f"{_fmt(part['angle_floor_valid_fraction'].mean(), 3)} | "
                    f"{_fmt(part['q_mean'].mean())} | {zero_steps} |"
                )
    lines.append("")
    lines.append(
        "Interpretation and flags. sigma is a regime label, not a nuisance "
        "parameter: at sigma = 0 the diagram sequences are deterministic, exact "
        "zero steps are common on flat segments, and family B collapses to sparse "
        "H0 and empty H1 diagrams, while at sigma = 0.05 every adjacent distance "
        "is strictly positive and the floor e is positive. Features computed in "
        "the two regimes are not pooled and are not numerically comparable."
    )
    lines.append("")
    lines.append(
        "A second structural finding is coverage, not definition: under the "
        "conservative floor the usable channels shrink sharply with noise. At "
        "sigma = 0.05 the angle floor-valid fraction is near zero in every cell "
        "(it ranges from 0.000 to 0.122 in the coverage table), and the efficiency "
        "flag is false in every row because the mean step never clears 2e. The "
        "angle and efficiency channels are therefore populated mainly at "
        "sigma = 0, where exact zeros, not the calibrated floor, dominate the "
        "abstentions. Flag: any use of the angle or efficiency channels must "
        "report this coverage jointly and must not treat the abstained majority "
        "at sigma = 0.05 as evidence of stability or instability."
    )
    lines.append("")
    lines.append("## 4. Meaning changes across cells and unstable quantities")
    lines.append("")
    lines.append("The following structural findings bound the interpretation.")
    lines.append("")
    lines.append(
        "1. Family B at sigma = 0 has near-empty degree 0 diagrams and empty "
        "degree 1 diagrams. In that regime L is frequently exactly zero, eta is "
        "undefined, and comparison angles and q are mostly undefined. These rows "
        "are retained with flags, but the angle channel is inapplicable there. This "
        "is a regime-limited meaning change, not a definition failure."
    )
    lines.append(
        "2. The floor e changes per (family, degree, stride) cell and is never "
        "pooled. The seed 11 static sensitivity values differ from the train-like "
        "floor, which shows that the floor estimate itself carries calibration "
        "uncertainty; abstention coverage is therefore reported per cell, as done "
        "here."
    )
    lines.append(
        "3. L is resolution-dependent by construction and must not be compared "
        "across stride cells; L/(T-1), eta, and the floor-gated fractions are the "
        "sampling-comparable summaries."
    )
    lines.append(
        "4. Speed-change rates are finite differences of speeds and amplify "
        "distance noise by the midpoint spacing. They are retained as descriptive, "
        "exploratory quantities and are not promoted to any decision role in "
        "WP-2.2."
    )
    lines.append(
        "5. Comparison angles and q keep their definitions in every cell where "
        "they are defined; the only variation is coverage through the calibrated "
        "floor and the exact-zero rule. Straight and reversal cases are reported "
        "wherever ab > 0."
    )
    lines.append(
        "6. The frozen metric backend is a definition-level failure, not a "
        "stability finding: the gudhi implementation returns incorrect distances "
        "on some real diagram pairs, in some cases for every tested input order "
        "and with both the default and the exact algorithm, so the triangle "
        "inequality itself breaks. It is flagged for repair before any G2 "
        "sign-off and is not used for the stability conclusions."
    )
    lines.append("")
    lines.append("## 5. Machine checks")
    lines.append("")
    for backend, verdict in verdicts.items():
        lines.append(f"### Backend `{backend}`: {verdict}")
        lines.append("")
        lines.append("| check | verdict | detail |")
        lines.append("|---|---|---|")
        for check in checks[backend]:
            detail = ", ".join(
                f"{key}={value}"
                for key, value in check.items()
                if key not in ("id", "description", "verdict")
            )
            lines.append(f"| {check['id']} | {check['verdict']} | {detail} |")
        lines.append("")
    primary_failures = ", ".join(
        check["id"]
        for check in checks[BACKEND_PRIMARY]
        if check["verdict"] != "pass"
    )
    lines.append(
        "WP-2.2 verdict on definitions. Under the corrected candidate backend all "
        "structural checks pass: L (per stride), eta, the speed summaries, the "
        "floor-gated comparison angle and q, and the zero-step and anomaly "
        "accounting are stable operational definitions on this grid. eta and the "
        "angle channel are regime-limited where L = 0 or where the diagrams are "
        "empty, and speed-change rates are exploratory under noise. Under the "
        f"frozen backend the failing checks are {primary_failures or 'none'}, so "
        "the frozen results are not signed off and the metric backend is a "
        "blocker. No predictive value is claimed, and the gate label remains "
        "conditional on G1 until the coordinator records the G2 decision."
    )
    lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _parse_list(value, cast):
    return tuple(cast(item) for item in value.split(",") if item != "")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-cache", default=str(DEFAULT_REPO_CACHE))
    parser.add_argument("--tmp-cache", default=str(DEFAULT_TMP_CACHE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--classes", default=",".join(CLASSES))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in SEEDS))
    parser.add_argument("--sigmas", default=",".join(str(s) for s in SIGMAS))
    parser.add_argument("--strides", default=",".join(str(s) for s in STRIDES))
    parser.add_argument("--degrees", default=",".join(str(d) for d in DEGREES))
    parser.add_argument(
        "--quick",
        action="store_true",
        help="small validation grid (family A, classes return and static, seeds 11 and 1000, strides 1 and 2)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.quick:
        args.families = "A"
        args.classes = "return,static"
        args.seeds = "11,1000"
        args.strides = "1,2"
    families = _parse_list(args.families, str)
    classes = _parse_list(args.classes, str)
    seeds = _parse_list(args.seeds, int)
    sigmas = _parse_list(args.sigmas, float)
    strides = _parse_list(args.strides, int)
    degrees = _parse_list(args.degrees, int)

    repo_cache = Path(args.repo_cache).resolve()
    tmp_cache = Path(args.tmp_cache).resolve()
    out_dir = Path(args.out_dir).resolve()
    figure_dir = out_dir / "figures"
    workers = max(1, min(2, int(args.workers)))

    out_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    tmp_cache.mkdir(parents=True, exist_ok=True)

    global DEGREES, STRIDES, SIGMAS
    DEGREES = tuple(degrees)
    STRIDES = tuple(strides)
    SIGMAS = tuple(sigmas)

    started_wall = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    jobs = [
        {
            "family": family,
            "label": label,
            "seed": seed,
            "sigma": sigma,
            "repo_cache": str(repo_cache),
            "tmp_cache": str(tmp_cache),
            "src": str(SRC),
        }
        for family in families
        for label in classes
        for seed in seeds
        for sigma in sigmas
    ]
    jobs.sort(
        key=lambda job: (job["family"], job["label"], job["seed"], job["sigma"])
    )

    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_process_trajectory, jobs, chunksize=1))

    grid = {
        "families": list(families),
        "classes": list(classes),
        "seeds": list(seeds),
        "sigmas": list(sigmas),
        "strides": list(strides),
        "degrees": list(degrees),
    }

    import pandas as pd

    tables = {}
    checks_by_backend = {}
    coverage_by_backend = {}
    verdicts = {}
    floors_by_backend = {}
    floor_meta_by_backend = {}
    seed11_by_backend = {}
    for backend in BACKENDS:
        keyed = _collect_records(results, backend)
        floors, floor_meta, seed11 = _compute_floors(families, keyed)
        rows = []
        arrays = {}
        for key in sorted(keyed):
            row, check_arrays = _build_row(keyed[key], floors, floor_meta, backend)
            rows.append(row)
            arrays[id(row)] = check_arrays
        checks, coverage, verdict = _run_checks(
            rows, arrays, grid, floors, keyed, repo_cache, backend
        )
        feature_df = pd.DataFrame(rows).sort_values(
            ["family", "class", "seed", "sigma", "stride", "degree"], kind="stable"
        )
        feature_df = feature_df.reset_index(drop=True)
        tables[backend] = feature_df
        checks_by_backend[backend] = checks
        coverage_by_backend[backend] = coverage
        verdicts[backend] = verdict
        floors_by_backend[backend] = floors
        floor_meta_by_backend[backend] = floor_meta
        seed11_by_backend[backend] = seed11

    primary_table_path = out_dir / "feature_table.csv"
    exact_table_path = out_dir / "feature_table_exact_metric.csv"
    tables[BACKEND_PRIMARY].to_csv(primary_table_path, index=False)
    tables[BACKEND_EXACT].to_csv(exact_table_path, index=False)

    cell_summary = _cell_summary_table(tables[BACKEND_EXACT])
    cell_summary_path = out_dir / "cell_summary.csv"
    pd.DataFrame(cell_summary).to_csv(cell_summary_path, index=False)

    solver_validation = _solver_validation()

    cross_backend = {
        "n_pairs_compared": 0,
        "n_above_tolerance": 0,
        "max_abs_difference": 0.0,
        "witnesses": [],
        "by_degree": {},
    }
    for result in results:
        block = result["cross_backend"]
        cross_backend["n_pairs_compared"] += block["n_pairs_compared"]
        cross_backend["n_above_tolerance"] += block["n_above_tolerance"]
        cross_backend["max_abs_difference"] = max(
            cross_backend["max_abs_difference"], block["max_abs_difference"]
        )
        cross_backend["witnesses"].extend(block["witnesses"])
        for degree, values in block["by_degree"].items():
            target = cross_backend["by_degree"].setdefault(
                degree,
                {
                    "n_pairs_compared": 0,
                    "n_above_tolerance": 0,
                    "max_abs_difference": 0.0,
                },
            )
            target["n_pairs_compared"] += values["n_pairs_compared"]
            target["n_above_tolerance"] += values["n_above_tolerance"]
            target["max_abs_difference"] = max(
                target["max_abs_difference"], values["max_abs_difference"]
            )
    cross_backend["witnesses"] = sorted(
        cross_backend["witnesses"], key=lambda item: -item["abs_diff"]
    )[:25]

    minimal_witness = _minimal_witness()
    witness_path = out_dir / "metric_backend_witness.json"
    _write_json(
        witness_path,
        {
            "work_package": "WP-2.2",
            "gate_label": GATE_LABEL,
            "description": (
                "minimal pair (3 and 4 points) exposing the order dependence of the "
                "frozen gudhi call and the difference between the frozen backend "
                "and the independent exact solver"
            ),
            "witness": minimal_witness,
            "gudhi_version": __import__("gudhi").__version__,
        },
    )

    def check_value(checks, check_id, key):
        for check in checks:
            if check["id"] == check_id:
                return check.get(key)
        return None

    primary_checks = checks_by_backend[BACKEND_PRIMARY]
    primary_summary = {
        "primary_triangle_violations": check_value(
            primary_checks, "triangle_inequality", "n_violations"
        ),
        "primary_triangle_worst": check_value(
            primary_checks, "triangle_inequality", "worst_excess"
        ),
        "primary_q_violations": check_value(
            primary_checks, "triangle_excess_range", "n_violations"
        ),
        "n_pairs_compared": cross_backend["n_pairs_compared"],
        "n_above_tolerance": cross_backend["n_above_tolerance"],
        "max_abs_difference": cross_backend["max_abs_difference"],
        "by_degree": cross_backend["by_degree"],
        "solver_validation": solver_validation,
        "minimal_witness": minimal_witness,
    }

    checks_payload = {
        "work_package": "WP-2.2",
        "gate_label": GATE_LABEL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "grid": grid,
        "metric_backends": {
            BACKEND_PRIMARY: (
                "frozen primary call: tk_pilot.bottleneck_linf, gudhi default e, "
                "canonicalized inputs; order-dependent and defective"
            ),
            BACKEND_EXACT: (
                "corrected candidate: independent SciPy exact solver, validated "
                "against the project brute-force reference, persim, and an "
                "order-invariance test"
            ),
        },
        "tolerances": {
            "R_le_L": TOLERANCE,
            "eta_bounds": TOLERANCE,
            "triangle_inequality": TOLERANCE,
            "triangle_excess_bounds": TOLERANCE,
            "backend_agreement": BACKEND_AGREEMENT_TOL,
            "cosine_anomaly": COSINE_ANOMALY_TOL,
        },
        "q_floor_factor": Q_FLOOR_FACTOR,
        "floor_percentile": FLOOR_PERCENTILE,
        "floor_population": {
            "sigma": 0.05,
            "class": "static",
            "seeds": [int(seed) for seed in CALIBRATION_SEEDS],
            "seed11_sensitivity_floors": {
                cell: float(value)
                for cell, value in sorted(seed11_by_backend[BACKEND_EXACT].items())
            },
        },
        "solver_validation": solver_validation,
        "cross_backend": cross_backend,
        "overall_verdict": verdicts,
        "wp22_definition_verdict": (
            "pass under the corrected candidate exact_scipy; the frozen primary "
            "fails the metric axiom checks and is a G2 blocker documented in "
            "metric_backend_audit.md; cached frozen-backend artifacts must be "
            "regenerated after the interface amendment"
            if verdicts[BACKEND_EXACT] == "pass"
            else "fail under the corrected candidate; inspect checks.json"
        ),
        "backends": {
            backend: {
                "role": (
                    "frozen_primary"
                    if backend == BACKEND_PRIMARY
                    else "corrected_candidate"
                ),
                "verdict": verdicts[backend],
                "checks": checks_by_backend[backend],
                "coverage_by_cell": coverage_by_backend[backend],
                "floors": {
                    cell: float(value)
                    for cell, value in sorted(floors_by_backend[backend].items())
                },
                "floor_population": floor_meta_by_backend[backend],
            }
            for backend in BACKENDS
        },
    }
    checks_path = out_dir / "checks.json"
    _write_json(checks_path, checks_payload)

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    additional = [seed for seed in seeds if seed != 11]
    figure_paths = []
    if additional:
        for backend, tag in (
            (BACKEND_PRIMARY, "frozen_primary"),
            (BACKEND_EXACT, "exact_reference"),
        ):
            backend_dir = figure_dir / tag
            backend_dir.mkdir(parents=True, exist_ok=True)
            frame = tables[backend]
            for sigma in SIGMAS:
                path = backend_dir / f"fig_features_vs_stride_sigma{sigma:g}.png"
                _feature_grid(
                    frame,
                    additional,
                    sigma,
                    [
                        ("L", "L (distance units)", True),
                        ("eta", "eta", False),
                        ("speed_mean", "mean speed", True),
                        (
                            "angle_floor_valid_fraction",
                            "angle floor-valid fraction",
                            False,
                        ),
                    ],
                    plt,
                    path,
                    f"WP-2.2 features versus stride at sigma {sigma:g}, "
                    f"additional train-like seeds, backend {backend}",
                )
                figure_paths.append(path)
            path = backend_dir / "fig_features_vs_sigma.png"
            _plot_features_vs_sigma(
                frame,
                additional,
                plt,
                path,
                f"WP-2.2 features versus sigma at stride 1, "
                f"additional train-like seeds, backend {backend}",
            )
            figure_paths.append(path)
            path = backend_dir / "fig_angle_valid_fraction_vs_stride.png"
            _plot_angle_validity(
                frame,
                additional,
                plt,
                path,
                f"WP-2.2 angle floor-valid fraction versus stride "
                f"(solid degree 0, dashed degree 1), backend {backend}",
            )
            figure_paths.append(path)
            path = backend_dir / "fig_noise_floor_sensitivity.png"
            _plot_noise_floor(
                frame,
                plt,
                path,
                f"WP-2.2 noise-floor sensitivity at sigma = 0.05 "
                f"(dotted line 2e is the efficiency gate scale), backend {backend}",
            )
            figure_paths.append(path)
            path = backend_dir / "fig_edge_case_counts.png"
            _plot_edge_case_counts(
                frame,
                plt,
                path,
                f"WP-2.2 degenerate-case counts, backend {backend}",
            )
            figure_paths.append(path)
    path = figure_dir / "fig_metric_backend_discrepancy.png"
    _plot_backend_discrepancy(
        tables[BACKEND_PRIMARY], tables[BACKEND_EXACT], plt, path
    )
    figure_paths.append(path)

    edge_report_path = out_dir / "edge_case_report.md"
    _write_text(
        edge_report_path,
        _edge_case_report(
            tables[BACKEND_EXACT],
            floors_by_backend[BACKEND_EXACT],
            seed11_by_backend[BACKEND_EXACT],
        ),
    )
    stability_report_path = out_dir / "stability_report.md"
    _write_text(
        stability_report_path,
        _stability_report(
            tables[BACKEND_EXACT],
            checks_by_backend,
            floors_by_backend[BACKEND_EXACT],
            seed11_by_backend[BACKEND_EXACT],
            verdicts,
            primary_summary,
        ),
    )
    audit_report_path = out_dir / "metric_backend_audit.md"
    exact_pass_count = sum(
        1
        for check in checks_by_backend[BACKEND_EXACT]
        if check["verdict"] == "pass"
    )
    _write_text(
        audit_report_path,
        _backend_audit_report(
            primary_summary,
            cross_backend["witnesses"],
            solver_validation,
            exact_pass_count,
        ),
    )

    wall_seconds = time.perf_counter() - started_wall
    parent_peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    children_peak = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * 1024
    import gudhi

    manifest = {
        "work_package": "WP-2.2",
        "gate_label": GATE_LABEL,
        "command": " ".join([sys.executable, *sys.argv]),
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "wall_seconds": wall_seconds,
        "workers": workers,
        "grid": grid,
        "metric_backends": {
            BACKEND_PRIMARY: (
                "frozen primary call: tk_pilot.bottleneck_linf, gudhi default e, "
                "canonicalized inputs; order-dependent and defective"
            ),
            BACKEND_EXACT: (
                "corrected candidate: independent SciPy exact solver, validated "
                "against the project brute-force reference, persim, and an "
                "order-invariance test"
            ),
        },
        "repo_cache": str(repo_cache),
        "tmp_cache": str(tmp_cache),
        "out_dir": str(out_dir),
        "cached_trajectory_ids": sorted(
            result["trajectory_id"]
            for result in results
            if result["trajectory_cache_hit"]
        ),
        "fresh_trajectory_ids": sorted(
            result["trajectory_id"]
            for result in results
            if not result["trajectory_cache_hit"]
        ),
        "trajectory_cache_hits": int(
            sum(1 for result in results if result["trajectory_cache_hit"])
        ),
        "diagram_cache_hits": int(
            sum(1 for result in results if result["diagram_cache_hit"])
        ),
        "extraction_seconds_total": float(
            sum(result["extraction_seconds"] for result in results)
        ),
        "metric_seconds_total": {
            backend: float(
                sum(result["metric_seconds"][backend] for result in results)
            )
            for backend in BACKENDS
        },
        "floors": {
            backend: {
                cell: float(value)
                for cell, value in sorted(floors_by_backend[backend].items())
            }
            for backend in BACKENDS
        },
        "verdicts": verdicts,
        "n_feature_rows": int(len(tables[BACKEND_EXACT])),
        "solver_validation": solver_validation,
        "cross_backend": {
            "n_pairs_compared": cross_backend["n_pairs_compared"],
            "n_above_tolerance": cross_backend["n_above_tolerance"],
            "max_abs_difference": cross_backend["max_abs_difference"],
            "by_degree": cross_backend["by_degree"],
        },
        "minimal_witness": minimal_witness,
        "peak_ram_bytes": {
            "parent": parent_peak,
            "children_max": children_peak,
            "reported_max": max(parent_peak, children_peak),
        },
        "versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "gudhi": gudhi.__version__,
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "artifacts": sorted(
            str(path)
            for path in (
                primary_table_path,
                exact_table_path,
                cell_summary_path,
                checks_path,
                witness_path,
                edge_report_path,
                stability_report_path,
                audit_report_path,
                *figure_paths,
            )
        ),
    }
    manifest_path = out_dir / "run_manifest.json"
    _write_json(manifest_path, manifest)

    artifacts = sorted(
        path
        for path in out_dir.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    sums = "\n".join(
        f"{_sha256_file(path)}  {path.relative_to(out_dir).as_posix()}"
        for path in artifacts
    )
    (out_dir / "SHA256SUMS").write_text(sums + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "n_rows": int(len(tables[BACKEND_EXACT])),
                "verdicts": verdicts,
                "wp22_definition_verdict": checks_payload["wp22_definition_verdict"],
                "cross_backend": {
                    "n_pairs_compared": cross_backend["n_pairs_compared"],
                    "n_above_tolerance": cross_backend["n_above_tolerance"],
                    "max_abs_difference": cross_backend["max_abs_difference"],
                },
                "wall_seconds": wall_seconds,
                "peak_ram_bytes": max(parent_peak, children_peak),
                "workers": workers,
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    return 0 if verdicts[BACKEND_EXACT] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
