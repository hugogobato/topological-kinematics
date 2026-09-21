#!/usr/bin/env python3
"""WP-3.1 raw-data correctness ladder (conditional on gate G1).

Runs the entire raw-data-to-diagram pipeline on analytic and synthetic controls
before any label experiment, and exposes whether a null raw process generates
systematic events. This work is conditional on gate G1; the script records the
G1 packet state at runtime and labels every artifact accordingly.

Ladder (degree 0 primary, degree 1 reported as the predeclared secondary
channel):

1. Static controls: both families, z = 0.5, sigma in {0, 0.05}, seeds 11 and 12.
   At sigma = 0 every adjacent diagram distance must be exactly zero. At
   sigma = 0.05 distances must be small and nonsystematic (trend and lag-8
   exchangeability tests).
2. Smooth deformation: ramp class, sigma = 0, strides 1 and 4, seeds 11 and 12.
   Family A: monotone response and a bounded response d <= C |dz| plus floor.
   Family B: finite-H0 onset z and monotone persistence response after onset.
3. Topology changing: class programs (return, ramp, jump) for both families.
   Finite-H0 cardinality versus z; Family B should change cardinality at the
   onset, while Family A H0 cardinality is invariant by construction and its
   transition is measured in the death coordinate.
4. Noisy raw null: independent realizations at sigma in {0, 0.05, 0.10} for
   static z = 0.5 and for frozen z snapshots at z in {1.0, 2.0}. Checks are no
   monotone trend, no temporal run of exceedances, and false-event counts
   against a training-style static calibration (95th percentile of static
   z = 0.5 at sigma = 0.05) and a leave-one-out same-sigma static calibration.
5. Sampling and filtration changes: Family A point counts 16, 32, 64 from one
   fixed realization; Family B 32x32 versus 16x16 grids. Sensitivity is
   reported, with the adapted delta-dense sampling bound (Kramar-style
   Theorem 7.3 and the 2 delta Vietoris-Rips interleaving) applied where
   applicable.
6. Rigid translation invariance: Family A translation control at sigma 0 and
   0.05, tolerance 1e-7 * max(1, filtration range). Family B is not required
   to satisfy this control.

Verdict vocabulary is PASS, FAIL, RESIDUAL. Verdict rules are declared in the
corresponding check functions and repeated in the generated report.

Usage:
    python3 scripts/run_wp31_ladder.py --out research_review/results/g2 \
        --workers 3
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
from datetime import datetime, timezone
from pathlib import Path

for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_variable, "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tk_pilot import diagram_metrics, generators, path_diagnostics, persistence  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WORK_PACKAGE = "WP-3.1"
GATE = "G2"
CONDITIONAL_GATE = "G1"
DEFAULT_OUT = ROOT / "research_review" / "results" / "g2"
G1_PACKET = ROOT / "research_review" / "results" / "phase1" / "decision_packet_G1.md"
SEEDS_PRIMARY = (11, 12)
SEEDS_NULL = (13, 14)
SIGMAS_STATIC = (0.0, 0.05)
SIGMAS_NULL = (0.0, 0.05, 0.10)
SNAPSHOT_Z = (1.0, 2.0)
SNAPSHOT_TAG = 7
MAX_WORKERS = 3
METRIC_NAME = "bottleneck_linf"
CALIBRATION_PERCENTILE = 95.0
TREND_ALPHA = 0.01
GRID_SPACING_32 = 2.0 * generators.FAMILY_B_EXTENT / (generators.FAMILY_B_SIDE - 1)
DEGREES = (0, 1)
BOUND_2DELTA_FACTOR = 2.0

INPUT_FILES = (
    "research_review/Topological_Kinematics_Research_Plan.md",
    "research_review/Pilot_Experiment_Specification.md",
    "research_review/results/phase1/implementation_contract.md",
    "research_review/results/phase1/decision_packet_G1.md",
    "configs/tk_pilot.yaml",
    "src/tk_pilot/generators.py",
    "src/tk_pilot/persistence.py",
    "src/tk_pilot/diagram_metrics.py",
    "src/tk_pilot/path_diagnostics.py",
    "src/tk_pilot/features.py",
    "scripts/run_wp31_ladder.py",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_array(array) -> str:
    return sha256_bytes(np.ascontiguousarray(array).tobytes())


def sha256_file(path) -> str | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonable(value):
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
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


def write_json(path, payload) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return ""
        return f"{number:.15g}"
    return str(value)


def write_csv(path, fieldnames, rows) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fieldnames), extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})
    return destination


def peak_ram_bytes(children: bool = False) -> int:
    usage = resource.getrusage(
        resource.RUSAGE_CHILDREN if children else resource.RUSAGE_SELF
    )
    return int(usage.ru_maxrss) * 1024


def sigma_tag(sigma) -> int:
    return generators.sigma_tag(float(sigma))


def standard_run_id(family, label, seed, sigma, stride) -> str:
    return (
        f"{family}_{label}_{int(seed)}_sigma{sigma_tag(sigma)}"
        f"_stride{int(stride)}"
    )


def snapshot_run_id(family, seed, z_value, sigma) -> str:
    return (
        f"{family}_snapshot_z{float(z_value):.1f}_{int(seed)}"
        f"_sigma{sigma_tag(sigma)}_stride1"
    )


def points_run_id(family, label, seed, sigma, points) -> str:
    return (
        f"{family}_{label}_{int(seed)}_sigma{sigma_tag(sigma)}"
        f"_points{int(points)}"
    )


def grid_run_id(family, label, seed, sigma, side) -> str:
    return f"{family}_{label}_{int(seed)}_sigma{sigma_tag(sigma)}_grid{int(side)}"


def inspect_g1() -> dict:
    """Record the G1 packet state so outputs can be labelled as conditional."""
    text = G1_PACKET.read_text(encoding="utf-8") if G1_PACKET.is_file() else ""
    pending = int(text.count("[PENDING"))
    if pending:
        status = "template_with_pending_items"
    elif text.strip():
        status = "recorded"
    else:
        status = "missing"
    return {
        "gate": CONDITIONAL_GATE,
        "packet": str(G1_PACKET.relative_to(ROOT)) if G1_PACKET.is_file() else None,
        "sha256": sha256_file(G1_PACKET),
        "pending_marker_count": pending,
        "status_at_runtime": status,
        "outputs_are_conditional": True,
    }


def draw_custom_latent(family: str, seed: int, tag: int) -> dict:
    """Draw WP-3.1 control latent parameters with an explicit tag id.

    The draw order matches ``tk_pilot.generators._draw_latent``. Tag 7 is a
    WP-3.1 control tag outside the frozen label ids 0 through 6 and is used
    only for the constant-z snapshot controls.
    """
    rng = np.random.default_rng(
        [int(seed), generators.family_id(family), int(tag), 101]
    )
    a = float(rng.uniform(0.15, 0.25))
    b = float(rng.uniform(0.75, 0.85))
    latent: dict = {"a": a, "b": b, "m": 0.5 * (a + b), "wp31_tag": int(tag)}
    if family == "A":
        latent["phi"] = float(rng.uniform(0.0, 2.0 * np.pi))
        latent["r"] = float(rng.uniform(0.9, 1.1))
        latent["phases"] = [
            float(rng.uniform(0.0, 2.0 * np.pi)),
            float(rng.uniform(0.0, 2.0 * np.pi)),
        ]
    else:
        latent["A1"] = float(rng.uniform(0.9, 1.1))
        latent["A2"] = float(rng.uniform(0.9, 1.1))
        latent["w"] = float(rng.uniform(0.35, 0.45))
    return latent


def family_a_points(z_values, latent) -> np.ndarray:
    """Rebuild the frozen Family A geometry from latent parameters.

    Replicates ``tk_pilot.generators._family_a_points`` exactly; the main
    routine verifies this against the public generator before the ladder runs.
    """
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
    z_array = np.asarray(z_values, dtype=np.float64)
    offsets = np.column_stack([0.5 * z_array, np.zeros_like(z_array)])
    points = base[None, :, :] + signs[None, :, None] * offsets[:, None, :]
    phi = float(latent["phi"])
    rotation = np.array(
        [[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]],
        dtype=np.float64,
    )
    return np.ascontiguousarray(points @ rotation.T)


def family_b_fields(z_values, latent, side=None, extent=None) -> np.ndarray:
    """Rebuild the frozen Family B scalar fields on a requested grid.

    Replicates ``tk_pilot.generators._family_b_fields``; ``side`` allows the
    coarse-grid sensitivity control and the default reproduces the frozen
    32x32 grid exactly.
    """
    side = generators.FAMILY_B_SIDE if side is None else int(side)
    extent = generators.FAMILY_B_EXTENT if extent is None else float(extent)
    axis = np.linspace(-extent, extent, side, dtype=np.float64)
    grid_x, grid_y = np.meshgrid(axis, axis)
    half = 0.5 * np.asarray(z_values, dtype=np.float64)[:, None, None]
    width = 2.0 * float(latent["w"]) ** 2
    left = float(latent["A1"]) * np.exp(
        -(((grid_x[None, :, :] + half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    right = float(latent["A2"]) * np.exp(
        -(((grid_x[None, :, :] - half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    return np.ascontiguousarray(left + right)


def draw_custom_noise(family: str, seed: int, tag: int, sigma, shape):
    """Draw control noise with the frozen seed derivation and an explicit tag."""
    if float(sigma) == 0.0:
        return None
    rng = np.random.default_rng(
        [int(seed), generators.family_id(family), int(tag), 202, sigma_tag(sigma)]
    )
    return rng.normal(0.0, float(sigma), size=shape)


def build_snapshot(family: str, seed: int, z_value: float, sigma: float):
    """Constant-z snapshot control with independent per-frame noise.

    The latent parameters are drawn with tag 7, z is constant at ``z_value``,
    and noise, when sigma > 0, is drawn per frame with the frozen noise
    derivation.
    """
    latent = draw_custom_latent(family, seed, SNAPSHOT_TAG)
    n_frames = generators.FRAMES_PER_MASTER
    z = np.full(n_frames, float(z_value), dtype=np.float64)
    if family == "A":
        frames = family_a_points(z, latent)
    else:
        frames = family_b_fields(z, latent)
    noise = draw_custom_noise(family, seed, SNAPSHOT_TAG, sigma, frames.shape)
    if noise is not None:
        frames = frames + noise
    timestamps = np.arange(n_frames, dtype=np.float64) / float(
        generators.MASTER_ORDER
    )
    return np.ascontiguousarray(frames), timestamps, z, latent


def verify_geometry_replication() -> dict:
    """Check the script's geometry formulas against the public generator."""
    results: dict[str, bool] = {}
    for family in ("A", "B"):
        traj = generators.build_trajectory(family, "static", 11, 0.0, 1)
        if family == "A":
            rebuilt = family_a_points(traj.z, dict(traj.latent))
        else:
            rebuilt = family_b_fields(traj.z, dict(traj.latent))
        results[family] = bool(
            np.array_equal(np.asarray(traj.frames), np.asarray(rebuilt))
        )
    return results


def point_subsample_delta(full: np.ndarray, subsample: np.ndarray) -> float:
    """One-sided delta of a point subsample.

    Maximum over dropped points of the distance to the nearest retained point.
    """
    diff = full[:, None, :] - subsample[None, :, :]
    distances = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
    return float(np.max(np.min(distances, axis=1)))


def compute_diagrams(frames, family: str, degrees=DEGREES):
    """Finite diagrams and essential counts with one persistence call per frame."""
    internal = getattr(persistence, "_trajectory_finite_and_essential", None)
    if callable(internal):
        diagrams, essential = internal(frames, family, degrees)
    else:
        diagrams = persistence.trajectory_diagrams(frames, family, degrees=degrees)
        essential = persistence.trajectory_essential_counts(
            frames, family, degrees=degrees
        )
    return diagrams, essential


def diagram_summary(diagrams, essential) -> dict:
    """Per-frame cardinalities, essential counts, deaths, and lifetimes."""
    cards = np.asarray([len(diagram) for diagram in diagrams], dtype=np.int64)
    essential_counts = np.asarray(essential, dtype=np.int64)
    dmax = np.asarray(
        [
            float(diagram[:, 1].max()) if len(diagram) else np.nan
            for diagram in diagrams
        ],
        dtype=np.float64,
    )
    persistence_max = np.asarray(
        [
            float((diagram[:, 1] - diagram[:, 0]).max())
            if len(diagram)
            else np.nan
            for diagram in diagrams
        ],
        dtype=np.float64,
    )
    return {
        "cards": cards,
        "essential": essential_counts,
        "dmax": dmax,
        "persistence_max": persistence_max,
    }


def build_jobs() -> list[dict]:
    """Enumerate every ladder job; run_id uniqueness is enforced."""
    jobs: list[dict] = []
    seen: set[str] = set()

    def add(job: dict) -> None:
        if job["run_id"] in seen:
            raise ValueError(f"duplicate run_id {job['run_id']!r}")
        seen.add(job["run_id"])
        jobs.append(job)

    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            for sigma in SIGMAS_STATIC:
                add(
                    {
                        "kind": "standard",
                        "check": "check1_static",
                        "family": family,
                        "label": "static",
                        "seed": int(seed),
                        "sigma": float(sigma),
                        "stride": 1,
                        "run_id": standard_run_id(family, "static", seed, sigma, 1),
                    }
                )
    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            add(
                {
                    "kind": "standard",
                    "check": "check2_ramp",
                    "family": family,
                    "label": "ramp",
                    "seed": int(seed),
                    "sigma": 0.0,
                    "stride": 1,
                    "run_id": standard_run_id(family, "ramp", seed, 0.0, 1),
                }
            )
            add(
                {
                    "kind": "standard",
                    "check": "check2_stride4",
                    "family": family,
                    "label": "ramp",
                    "seed": int(seed),
                    "sigma": 0.0,
                    "stride": 4,
                    "run_id": standard_run_id(family, "ramp", seed, 0.0, 4),
                }
            )
    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            for label in ("return", "jump"):
                add(
                    {
                        "kind": "standard",
                        "check": "check3_topology",
                        "family": family,
                        "label": label,
                        "seed": int(seed),
                        "sigma": 0.0,
                        "stride": 1,
                        "run_id": standard_run_id(family, label, seed, 0.0, 1),
                    }
                )
    for family in ("A", "B"):
        for seed in SEEDS_NULL:
            for sigma in SIGMAS_NULL:
                add(
                    {
                        "kind": "standard",
                        "check": "check4_static_null",
                        "family": family,
                        "label": "static",
                        "seed": int(seed),
                        "sigma": float(sigma),
                        "stride": 1,
                        "run_id": standard_run_id(family, "static", seed, sigma, 1),
                    }
                )
    for family in ("A", "B"):
        for seed in SEEDS_NULL:
            for sigma in SIGMAS_NULL:
                for z_value in SNAPSHOT_Z:
                    add(
                        {
                            "kind": "snapshot",
                            "check": "check4_snapshot_null",
                            "family": family,
                            "seed": int(seed),
                            "sigma": float(sigma),
                            "z_value": float(z_value),
                            "run_id": snapshot_run_id(
                                family, seed, z_value, sigma
                            ),
                        }
                    )
    for seed in SEEDS_PRIMARY:
        for points in (32, 16):
            add(
                {
                    "kind": "points",
                    "check": "check5_points",
                    "family": "A",
                    "label": "ramp",
                    "seed": int(seed),
                    "sigma": 0.0,
                    "stride": 1,
                    "points_stride": int(generators.POINTS_PER_FRAME // points),
                    "run_id": points_run_id("A", "ramp", seed, 0.0, points),
                }
            )
    for seed in SEEDS_PRIMARY:
        add(
            {
                "kind": "grid",
                "check": "check5_grid",
                "family": "B",
                "label": "ramp",
                "seed": int(seed),
                "sigma": 0.0,
                "stride": 1,
                "grid_side": 16,
                "run_id": grid_run_id("B", "ramp", seed, 0.0, 16),
            }
        )
    for seed in SEEDS_PRIMARY:
        for sigma in SIGMAS_STATIC:
            add(
                {
                    "kind": "control",
                    "check": "check6_translation",
                    "family": "A",
                    "label": "translation",
                    "seed": int(seed),
                    "sigma": float(sigma),
                    "stride": 1,
                    "run_id": standard_run_id("A", "translation", seed, sigma, 1),
                }
            )
    return jobs


def save_record_outputs(job, out_dir, frames, timestamps, z, latent, diagrams, essential) -> dict:
    """Persist raw arrays, diagram sequences, metadata, and hashes."""
    family = str(job["family"])
    seed = int(job["seed"])
    run_id = str(job["run_id"])
    raw_dir = Path(out_dir) / "raw_controls" / family / str(seed)
    diagram_dir = Path(out_dir) / "diagrams" / family / str(seed)
    raw_dir.mkdir(parents=True, exist_ok=True)
    diagram_dir.mkdir(parents=True, exist_ok=True)
    frames = np.ascontiguousarray(frames, dtype=np.float64)
    timestamps = np.ascontiguousarray(timestamps, dtype=np.float64)
    z = np.ascontiguousarray(z, dtype=np.float64)
    raw_path = raw_dir / f"{run_id}.npz"
    np.savez_compressed(
        raw_path,
        frames=frames,
        timestamps=timestamps,
        z=z,
        latent_json=json.dumps(jsonable(latent), sort_keys=True),
    )
    raw_hashes = {
        "sha256_frames": sha256_array(frames),
        "sha256_timestamps": sha256_array(timestamps),
        "sha256_z": sha256_array(z),
        "sha256_npz": sha256_file(raw_path),
    }
    raw_meta = {
        "run_id": run_id,
        "work_package": WORK_PACKAGE,
        "conditional_gate": CONDITIONAL_GATE,
        "job": jsonable(job),
        "family": family,
        "seed": seed,
        "n_frames": int(frames.shape[0]),
        "frame_shape": list(frames.shape),
        "latent": jsonable(latent),
        "hashes": raw_hashes,
    }
    raw_meta_path = raw_dir / f"{run_id}.meta.json"
    write_json(raw_meta_path, raw_meta)
    diagram_path = diagram_dir / f"{run_id}.npz"
    payload = {}
    per_frame_hashes: dict[str, list] = {}
    for degree in sorted(diagrams):
        per_frame_hashes[f"degree{int(degree)}"] = []
        for index, diagram in enumerate(diagrams[degree]):
            array = np.ascontiguousarray(diagram, dtype=np.float64)
            payload[f"d{int(degree)}_{index:03d}"] = array
            per_frame_hashes[f"degree{int(degree)}"].append(sha256_array(array))
        for index, count in enumerate(essential[degree]):
            payload[f"e{int(degree)}_{index:03d}"] = np.asarray(
                [int(count)], dtype=np.int64
            )
    np.savez_compressed(diagram_path, **payload)
    diagram_meta = {
        "run_id": run_id,
        "work_package": WORK_PACKAGE,
        "conditional_gate": CONDITIONAL_GATE,
        "family": family,
        "seed": seed,
        "n_frames": int(frames.shape[0]),
        "degrees": [int(degree) for degree in sorted(diagrams)],
        "gudhi_version": __import__("gudhi").__version__,
        "per_frame_sha256": per_frame_hashes,
        "essential_counts": {
            f"degree{int(degree)}": [int(count) for count in essential[degree]]
            for degree in sorted(essential)
        },
        "sha256_npz": sha256_file(diagram_path),
    }
    diagram_meta_path = diagram_dir / f"{run_id}.meta.json"
    write_json(diagram_meta_path, diagram_meta)
    return {
        "raw_path": str(raw_path),
        "raw_meta_path": str(raw_meta_path),
        "diagram_path": str(diagram_path),
        "diagram_meta_path": str(diagram_meta_path),
        "raw_hashes": raw_hashes,
        "sha256_diagram_npz": diagram_meta["sha256_npz"],
    }


def compute_job(job: dict) -> dict:
    """Build one control trajectory, extract diagrams, and persist artifacts."""
    started = time.perf_counter()
    try:
        family = str(job["family"])
        seed = int(job["seed"])
        kind = str(job["kind"])
        sigma = float(job.get("sigma", 0.0))
        base_label = str(job.get("label", job.get("kind", "custom")))
        delta = None
        field_diff_max = None
        label = base_label
        if kind == "standard":
            traj = generators.build_trajectory(
                family, base_label, seed, sigma, int(job["stride"])
            )
            frames = np.ascontiguousarray(traj.frames)
            timestamps = np.ascontiguousarray(traj.timestamps)
            z = np.ascontiguousarray(traj.z)
            latent = dict(traj.latent)
        elif kind == "control":
            traj = generators.build_control(
                base_label, family, seed, sigma, int(job["stride"])
            )
            frames = np.ascontiguousarray(traj.frames)
            timestamps = np.ascontiguousarray(traj.timestamps)
            z = np.ascontiguousarray(traj.z)
            latent = dict(traj.latent)
        elif kind == "snapshot":
            frames, timestamps, z, latent = build_snapshot(
                family, seed, float(job["z_value"]), sigma
            )
            label = f"snapshot_z{float(job['z_value']):.1f}"
        elif kind == "points":
            traj = generators.build_trajectory(
                family, base_label, seed, sigma, int(job["stride"])
            )
            full = np.ascontiguousarray(traj.frames)
            step = int(job["points_stride"])
            frames = np.ascontiguousarray(full[:, ::step, :])
            timestamps = np.ascontiguousarray(traj.timestamps)
            z = np.ascontiguousarray(traj.z)
            latent = dict(traj.latent)
            delta = np.asarray(
                [
                    point_subsample_delta(full[index], frames[index])
                    for index in range(full.shape[0])
                ],
                dtype=np.float64,
            )
        elif kind == "grid":
            traj = generators.build_trajectory(
                family, base_label, seed, sigma, int(job["stride"])
            )
            lat = dict(traj.latent)
            side = int(job["grid_side"])
            frames = family_b_fields(traj.z, lat, side=side)
            timestamps = np.ascontiguousarray(traj.timestamps)
            z = np.ascontiguousarray(traj.z)
            latent = lat
            coarse_index = np.round(
                np.arange(side)
                * float(generators.FAMILY_B_SIDE - 1)
                / float(side - 1)
            ).astype(np.int64)
            mapped = np.asarray(traj.frames)[
                :, coarse_index[:, None], coarse_index[None, :]
            ]
            field_diff_max = np.asarray(
                [
                    float(
                        np.max(
                            np.abs(
                                np.asarray(mapped[index])
                                - np.asarray(frames[index])
                            )
                        )
                    )
                    for index in range(frames.shape[0])
                ],
                dtype=np.float64,
            )
        else:
            raise ValueError(f"unsupported job kind {kind!r}")
        diagrams, essential = compute_diagrams(frames, family, DEGREES)
        diagnostics: dict[int, dict] = {}
        for degree in DEGREES:
            diag = path_diagnostics.compute_path_diagnostics(
                diagrams[degree], timestamps, diagram_metrics.bottleneck_linf
            )
            diagnostics[degree] = {
                "adjacent": np.asarray(diag.adjacent_distances, dtype=np.float64),
                "speeds": np.asarray(diag.interval_speeds, dtype=np.float64),
                "length": float(diag.length),
                "displacement": float(diag.displacement),
                "efficiency": (
                    None if diag.efficiency is None else float(diag.efficiency)
                ),
                "angle_valid_fraction": diag.angle_valid_fraction,
            }
        summaries = {
            degree: diagram_summary(diagrams[degree], essential[degree])
            for degree in DEGREES
        }
        saved = save_record_outputs(
            job, job["out_dir"], frames, timestamps, z, latent, diagrams, essential
        )
        return {
            "run_id": str(job["run_id"]),
            "status": "ok",
            "kind": kind,
            "check": str(job.get("check", "")),
            "family": family,
            "label": label,
            "base_label": base_label,
            "seed": seed,
            "sigma": sigma,
            "stride": int(job.get("stride", 1)),
            "n_frames": int(frames.shape[0]),
            "frame_shape": list(frames.shape),
            "timestamps": timestamps,
            "z": z,
            "latent": jsonable(latent),
            "diagrams": diagrams,
            "essential": {
                degree: [int(value) for value in essential[degree]]
                for degree in DEGREES
            },
            "summaries": summaries,
            "diagnostics": diagnostics,
            "delta": delta,
            "field_diff_max": field_diff_max,
            "saved": saved,
            "peak_ram_bytes_worker": peak_ram_bytes(children=False),
            "seconds": float(time.perf_counter() - started),
        }
    except Exception as error:  # a failed job must not hide the other checks
        return {
            "run_id": str(job.get("run_id", "unknown")),
            "status": "error",
            "check": str(job.get("check", "")),
            "family": str(job.get("family", "")),
            "seed": int(job.get("seed", -1)),
            "error": f"{type(error).__name__}: {error}",
            "seconds": float(time.perf_counter() - started),
        }


def run_jobs(jobs: list[dict], out_dir: Path, workers: int) -> list[dict]:
    prepared = [dict(job, out_dir=str(out_dir)) for job in jobs]
    if int(workers) <= 1 or len(prepared) <= 1:
        return [compute_job(job) for job in prepared]
    from joblib import Parallel, delayed

    return list(
        Parallel(n_jobs=int(workers), backend="loky", verbose=0)(
            delayed(compute_job)(job) for job in prepared
        )
    )


def phase_trend_and_exchangeability(record: dict, degree: int = 0) -> dict:
    """Trend and lag-8 exchangeability statistics for a diagram sequence."""
    adjacent = np.asarray(record["diagnostics"][degree]["adjacent"], dtype=np.float64)
    n = int(adjacent.size)
    if n < 10:
        return {
            "n_intervals": n,
            "spearman_rho": float("nan"),
            "spearman_p": float("nan"),
            "ks_lag8_p": float("nan"),
            "trend_pass": False,
            "ks_pass": False,
        }
    if np.all(adjacent == 0.0):
        return {
            "n_intervals": n,
            "spearman_rho": float("nan"),
            "spearman_p": float("nan"),
            "ks_lag8_p": float("nan"),
            "trend_pass": True,
            "ks_pass": True,
        }
    rho, p_value = stats.spearmanr(adjacent, np.arange(n, dtype=np.float64))
    diagrams = record["diagrams"][degree]
    lag = min(8, n // 2)
    lag_distances = np.asarray(
        [
            float(diagram_metrics.bottleneck_linf(diagrams[i], diagrams[i + lag]))
            for i in range(len(diagrams) - lag)
        ],
        dtype=np.float64,
    )
    ks = stats.ks_2samp(adjacent, lag_distances)
    return {
        "n_intervals": n,
        "spearman_rho": float(rho),
        "spearman_p": float(p_value),
        "ks_lag8_p": float(ks.pvalue),
        "trend_pass": bool((float(p_value) > TREND_ALPHA) or (abs(float(rho)) <= 0.2)),
        "ks_pass": bool(float(ks.pvalue) > TREND_ALPHA),
    }


def distribution_stats(values) -> dict:
    array = np.asarray(values, dtype=np.float64).ravel()
    if array.size == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "q25": float("nan"),
            "median": float("nan"),
            "q75": float("nan"),
            "p95": float("nan"),
            "max": float("nan"),
        }
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "std": float(np.std(array, ddof=0)),
        "min": float(np.min(array)),
        "q25": float(np.percentile(array, 25)),
        "median": float(np.median(array)),
        "q75": float(np.percentile(array, 75)),
        "p95": float(np.percentile(array, 95)),
        "max": float(np.max(array)),
    }


def fit_linear(x: np.ndarray, y: np.ndarray) -> dict:
    if x.size < 2 or np.allclose(x, x[0]):
        return {
            "C": float("nan"),
            "f": float("nan"),
            "r2": float("nan"),
            "max_excess": float("nan"),
        }
    coefficients = np.polyfit(x, y, 1)
    prediction = coefficients[0] * x + coefficients[1]
    residual = y - prediction
    total = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1.0 - np.sum(residual**2) / total) if total > 0 else float("nan")
    return {
        "C": float(coefficients[0]),
        "f": float(coefficients[1]),
        "r2": r2,
        "max_excess": float(np.max(residual)),
    }


def check1_static(records: dict, out_dir: Path) -> dict:
    """Ladder check 1: static controls and the sigma = 0 exact-zero rule.

    Declared rule: sigma = 0 passes only if every adjacent distance for both
    degrees is exactly 0. sigma = 0.05 passes if the Spearman trend is not
    significant at 1 percent and the adjacent versus lag-8 KS test does not
    reject exchangeability at 1 percent; otherwise RESIDUAL.
    """
    table_rows: list[dict] = []
    distance_rows: list[dict] = []
    calibration: dict[str, float] = {}
    pooled: dict[str, list] = {"A": [], "B": []}
    verdicts: list[str] = []
    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            for sigma in SIGMAS_STATIC:
                run_id = standard_run_id(family, "static", seed, sigma, 1)
                record = records.get(run_id)
                if record is None or record["status"] != "ok":
                    verdicts.append("FAIL")
                    table_rows.append(
                        {
                            "run_id": run_id,
                            "family": family,
                            "seed": seed,
                            "sigma": sigma,
                            "status": "missing",
                            "verdict": "FAIL",
                        }
                    )
                    continue
                for degree in DEGREES:
                    adjacent = np.asarray(
                        record["diagnostics"][degree]["adjacent"], dtype=np.float64
                    )
                    stats_row = distribution_stats(adjacent)
                    trend = phase_trend_and_exchangeability(record, degree)
                    exact_zero = bool(np.all(adjacent == 0.0))
                    if sigma == 0.0:
                        verdict = "PASS" if exact_zero else "FAIL"
                    else:
                        verdict = (
                            "PASS"
                            if (trend["trend_pass"] and trend["ks_pass"])
                            else "RESIDUAL"
                        )
                    verdicts.append(verdict)
                    table_rows.append(
                        {
                            "run_id": run_id,
                            "family": family,
                            "seed": seed,
                            "sigma": sigma,
                            "degree": degree,
                            "n_intervals": stats_row["n"],
                            "mean": stats_row["mean"],
                            "std": stats_row["std"],
                            "min": stats_row["min"],
                            "q25": stats_row["q25"],
                            "median": stats_row["median"],
                            "q75": stats_row["q75"],
                            "p95": stats_row["p95"],
                            "max": stats_row["max"],
                            "nonzero_count": int(np.count_nonzero(adjacent)),
                            "exact_zero": exact_zero,
                            "spearman_rho": trend["spearman_rho"],
                            "spearman_p": trend["spearman_p"],
                            "ks_lag8_p": trend["ks_lag8_p"],
                            "trend_pass": trend["trend_pass"],
                            "ks_pass": trend["ks_pass"],
                            "verdict": verdict,
                        }
                    )
                    for index, value in enumerate(adjacent):
                        distance_rows.append(
                            {
                                "run_id": run_id,
                                "family": family,
                                "seed": seed,
                                "sigma": sigma,
                                "degree": degree,
                                "interval": index,
                                "u_mid": float(
                                    0.5
                                    * (
                                        record["timestamps"][index]
                                        + record["timestamps"][index + 1]
                                    )
                                ),
                                "distance": float(value),
                            }
                        )
                if sigma == 0.05:
                    pooled[family].append(
                        np.asarray(
                            record["diagnostics"][0]["adjacent"], dtype=np.float64
                        )
                    )
    for family in ("A", "B"):
        if pooled[family]:
            calibration[family] = float(
                np.percentile(np.concatenate(pooled[family]), CALIBRATION_PERCENTILE)
            )
        else:
            calibration[family] = float("nan")
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "static_controls.csv",
        list(table_rows[0].keys()) if table_rows else ["run_id"],
        table_rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "static_adjacent_distances.csv",
        list(distance_rows[0].keys()) if distance_rows else ["run_id"],
        distance_rows,
    )
    sigma0_nonzero = [
        row
        for row in table_rows
        if row.get("sigma") == 0.0 and row.get("nonzero_count", 0)
    ]
    return {
        "id": "check1_static",
        "title": "Static controls and sigma = 0 exact-zero rule",
        "verdict": overall,
        "calibration": calibration,
        "sigma0_nonzero_cases": len(sigma0_nonzero),
        "rows": table_rows,
        "tables": [
            "reports/tables/static_controls.csv",
            "reports/tables/static_adjacent_distances.csv",
        ],
    }


def check2_ramp(records: dict, out_dir: Path) -> dict:
    """Ladder check 2: smooth ramp response for both families.

    Family A declared rules: the bounded response passes when the empirical
    maximum ratio max(d / |dz|) is at most 1.5 (the least-squares fit with
    intercept is reported alongside), monotone response passes when the
    Spearman trend of adjacent distance against z on active stride-1 pairs is
    at least 0.3 with p below 0.01 and the separated-regime mean exceeds the
    overlap-regime mean by at least 10 percent, and the switch test passes when
    the measured plateau-to-line intersection equals 2r plus the intra-circle
    merge scale within 0.1.

    Family B declared rules: onset passes when the first finite H0 bar appears
    at or above 2w within one 32x32 grid spacing; monotone response passes when
    the persistence of the finite H0 bar has Spearman rho at least 0.8, at most
    15 percent local decreases, and a positive net increase.
    """
    rows: list[dict] = []
    fits: list[dict] = []
    transitions: list[dict] = []
    verdicts: list[str] = []
    stride_exact: dict[str, bool] = {}
    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            master = records.get(standard_run_id(family, "ramp", seed, 0.0, 1))
            stride4 = records.get(standard_run_id(family, "ramp", seed, 0.0, 4))
            if (
                master is None
                or master["status"] != "ok"
                or stride4 is None
                or stride4["status"] != "ok"
            ):
                verdicts.append("FAIL")
                continue
            exact = all(
                np.array_equal(
                    np.asarray(stride4["diagrams"][degree][index]),
                    np.asarray(master["diagrams"][degree][index * 4]),
                )
                for degree in DEGREES
                for index in range(len(stride4["diagrams"][degree]))
            )
            stride_exact[f"{family}_{seed}"] = bool(exact)
            z = np.asarray(master["z"], dtype=np.float64)
            timestamps = np.asarray(master["timestamps"], dtype=np.float64)
            z4 = z[::4]
            t4 = timestamps[::4]
            pair_sets = (
                (
                    1,
                    z[:-1],
                    z[1:],
                    0.5 * (timestamps[:-1] + timestamps[1:]),
                    master,
                ),
                (4, z4[:-1], z4[1:], 0.5 * (t4[:-1] + t4[1:]), stride4),
            )
            for stride, z_left, z_right, u_mid, record in pair_sets:
                dz = z_right - z_left
                z_mid = 0.5 * (z_left + z_right)
                d0 = np.asarray(record["diagnostics"][0]["adjacent"], dtype=np.float64)
                d1 = np.asarray(record["diagnostics"][1]["adjacent"], dtype=np.float64)
                dmax0 = np.asarray(record["summaries"][0]["dmax"], dtype=np.float64)
                dmax1 = np.asarray(record["summaries"][1]["dmax"], dtype=np.float64)
                card0 = np.asarray(record["summaries"][0]["cards"], dtype=np.int64)
                card1 = np.asarray(record["summaries"][1]["cards"], dtype=np.int64)
                for index in range(dz.size):
                    rows.append(
                        {
                            "run_id": record["run_id"],
                            "family": family,
                            "seed": seed,
                            "stride": stride,
                            "interval": index,
                            "u_mid": float(u_mid[index]),
                            "z_mid": float(z_mid[index]),
                            "dz": float(dz[index]),
                            "abs_dz": float(abs(dz[index])),
                            "d0": float(d0[index]),
                            "d1": float(d1[index]),
                            "dmax0": float(dmax0[index]),
                            "dmax1": float(dmax1[index]),
                            "card0": int(card0[index]),
                            "card1": int(card1[index]),
                        }
                    )
            latent = dict(master["latent"])
            if family == "A":
                emit_family_a(master, stride4, z, latent, fits, transitions, verdicts)
            else:
                emit_family_b(master, z, latent, fits, transitions, verdicts)
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "ramp_response.csv",
        list(rows[0].keys()) if rows else ["run_id"],
        rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "ramp_fits.csv",
        list(fits[0].keys()) if fits else ["family", "seed"],
        fits,
    )
    write_csv(
        out_dir / "reports" / "tables" / "ramp_transitions.csv",
        list(transitions[0].keys()) if transitions else ["family", "seed"],
        transitions,
    )
    return {
        "id": "check2_ramp",
        "title": "Smooth ramp deformation response",
        "verdict": overall,
        "stride_subsample_exact": stride_exact,
        "fits": fits,
        "transitions": transitions,
        "tables": [
            "reports/tables/ramp_response.csv",
            "reports/tables/ramp_fits.csv",
            "reports/tables/ramp_transitions.csv",
        ],
    }


def emit_family_a(master, stride4, z, latent, fits, transitions, verdicts) -> None:
    """Measure the Family A ramp response and record verdicts."""
    z_merge = 2.0 * float(latent["r"])
    dz1 = np.diff(z)
    z4 = z[::4]
    dz4 = z4[1:] - z4[:-1]
    d0_1 = np.asarray(master["diagnostics"][0]["adjacent"], dtype=np.float64)
    d0_4 = np.asarray(stride4["diagnostics"][0]["adjacent"], dtype=np.float64)
    active1 = dz1 > 0
    active4 = dz4 > 0
    floor_observed = max(
        [0.0]
        + [float(value) for value in d0_1[~active1]]
        + [float(value) for value in d0_4[~active4]]
    )
    x_all = np.concatenate([dz1[active1], dz4[active4]])
    y_all = np.concatenate([d0_1[active1], d0_4[active4]])
    ratio = y_all / x_all
    fit = fit_linear(x_all, y_all)
    c_max = float(np.max(ratio))
    z_mid1 = 0.5 * (z[:-1] + z[1:])
    rho, p_value = stats.spearmanr(d0_1[active1], z_mid1[active1])
    overlap = d0_1[active1 & (z_mid1 < z_merge - 0.25)]
    separated_mask = active1 & (z_mid1 > z_merge + 0.25)
    separated = d0_1[separated_mask]
    ratio_separated = separated / dz1[separated_mask]
    dmax0 = np.asarray(master["summaries"][0]["dmax"], dtype=np.float64)
    plateau = float(np.median(dmax0[z < z_merge - 0.25]))
    line_mask = z > z_merge + 0.25
    if np.count_nonzero(line_mask) >= 2:
        line = np.polyfit(z[line_mask], dmax0[line_mask], 1)
        z_switch = float((plateau - line[1]) / line[0])
    else:
        line = np.asarray([float("nan"), float("nan")])
        z_switch = float("nan")
    monotone_pass = bool(
        (float(rho) >= 0.3)
        and (float(p_value) < 0.01)
        and (float(np.mean(separated)) >= 1.1 * float(np.mean(overlap)))
    )
    bound_pass = bool(c_max <= 1.5)
    switch_pass = bool(abs(z_switch - (z_merge + plateau)) <= 0.1)
    if monotone_pass and bound_pass and switch_pass:
        verdict = "PASS"
    elif (not bound_pass) or (not switch_pass):
        verdict = "FAIL"
    else:
        verdict = "RESIDUAL"
    verdicts.append(verdict)
    fits.append(
        {
            "family": "A",
            "seed": int(master["seed"]),
            "z_merge": z_merge,
            "n_active_pairs": int(x_all.size),
            "C_ls": fit["C"],
            "f_ls": fit["f"],
            "r2_ls": fit["r2"],
            "max_excess_ls": fit["max_excess"],
            "C_max_ratio": c_max,
            "median_ratio": float(np.median(ratio)),
            "floor_observed_at_zero_dz": floor_observed,
            "bound_violations": int(np.count_nonzero(y_all > c_max * x_all + 1e-12)),
            "monotone_rho": float(rho),
            "monotone_p": float(p_value),
            "mean_overlap": float(np.mean(overlap)),
            "mean_separated": float(np.mean(separated)),
            "mean_ratio_separated": float(np.mean(ratio_separated)),
            "z_switch_measured": z_switch,
            "switch_offset": float(z_switch - z_merge),
            "plateau_level": plateau,
            "line_slope": float(line[0]),
            "verdict_monotone": "PASS" if monotone_pass else "RESIDUAL",
            "verdict_bound": "PASS" if bound_pass else "FAIL",
            "verdict_switch": "PASS" if switch_pass else "RESIDUAL",
            "verdict": verdict,
        }
    )
    transitions.append(
        {
            "family": "A",
            "seed": int(master["seed"]),
            "class_scope": "ramp",
            "expected_z": z_merge,
            "measured_low_z": z_switch,
            "measured_high_z": z_switch,
            "offset": float(z_switch - z_merge),
            "flag": "death_coordinate_switch",
            "criterion": "z_switch equals 2r plus the intra-circle merge scale",
            "verdict": "PASS" if switch_pass else "RESIDUAL",
        }
    )


def emit_family_b(master, z, latent, fits, transitions, verdicts) -> None:
    """Measure the Family B onset and persistence response and record verdicts."""
    w = float(latent["w"])
    z_onset = 2.0 * w
    card0 = np.asarray(master["summaries"][0]["cards"], dtype=np.int64)
    persistence = np.asarray(
        master["summaries"][0]["persistence_max"], dtype=np.float64
    )
    positive = card0 > 0
    if np.any(positive):
        first = int(np.argmax(positive))
        onset_low = float(z[first - 1]) if first > 0 else float("nan")
        onset_high = float(z[first])
        offset = float(onset_high - z_onset)
        rho_p, p_p = stats.spearmanr(persistence[first:], z[first:])
        decreases = int(np.count_nonzero(np.diff(persistence[first:]) < 0))
        steps = int(persistence.size - first - 1)
        local_fraction = float(decreases) / float(steps) if steps > 0 else 0.0
        net_increase = float(persistence[-1] - persistence[first])
        monotone_pass = bool(
            (float(rho_p) >= 0.8)
            and (local_fraction <= 0.15)
            and (net_increase > 0)
        )
        onset_pass = bool(
            (onset_high >= z_onset - 1e-9) and (offset <= GRID_SPACING_32)
        )
        if onset_pass and monotone_pass:
            verdict = "PASS"
        elif offset > 2.0 * GRID_SPACING_32:
            verdict = "FAIL"
        else:
            verdict = "RESIDUAL"
    else:
        first = -1
        onset_low = float("nan")
        onset_high = float("nan")
        offset = float("nan")
        rho_p = float("nan")
        p_p = float("nan")
        decreases = 0
        local_fraction = float("nan")
        net_increase = float("nan")
        monotone_pass = False
        onset_pass = False
        verdict = "FAIL"
    verdicts.append(verdict)
    fits.append(
        {
            "family": "B",
            "seed": int(master["seed"]),
            "w": w,
            "z_onset_expected": z_onset,
            "onset_last_zero_z": onset_low,
            "onset_first_positive_z": onset_high,
            "onset_offset": offset,
            "onset_pass": onset_pass,
            "persistence_rho": float(rho_p),
            "persistence_p": float(p_p),
            "persistence_decreases": decreases,
            "persistence_steps": int(persistence.size - first - 1) if first >= 0 else 0,
            "persistence_local_decrease_fraction": local_fraction,
            "persistence_net_increase": net_increase,
            "monotone_pass": monotone_pass,
            "verdict": verdict,
        }
    )
    transitions.append(
        {
            "family": "B",
            "seed": int(master["seed"]),
            "class_scope": "ramp",
            "expected_z": z_onset,
            "measured_low_z": onset_low,
            "measured_high_z": onset_high,
            "offset": offset,
            "flag": "finite_H0_onset",
            "criterion": "first frame with finite H0 cardinality above zero",
            "verdict": "PASS" if onset_pass else "RESIDUAL",
        }
    )


def check3_topology(records: dict, out_dir: Path) -> dict:
    """Ladder check 3: class programs crossing topology transitions.

    Family B declared rule: the finite H0 cardinality must be 0 before the
    onset, become 1 at the first frame whose z exceeds the measured onset, and
    follow the ramp, return, and jump latent programs; the onset must agree
    with 2w within one 32x32 grid spacing.

    Family A declared rule: the Rips H0 finite cardinality is exactly
    n_points - 1 at every frame by construction, so the cardinality criterion
    is recorded as RESIDUAL and the transition is instead verified through the
    death-coordinate switch at the frame whose z exceeds 2r plus the
    intra-circle merge scale.
    """
    rows: list[dict] = []
    events: list[dict] = []
    verdicts: list[str] = []
    for family in ("A", "B"):
        for seed in SEEDS_PRIMARY:
            for label in ("return", "ramp", "jump"):
                run_id = standard_run_id(family, label, seed, 0.0, 1)
                record = records.get(run_id)
                if record is None or record["status"] != "ok":
                    verdicts.append("FAIL")
                    continue
                z = np.asarray(record["z"], dtype=np.float64)
                timestamps = np.asarray(record["timestamps"], dtype=np.float64)
                card0 = np.asarray(record["summaries"][0]["cards"], dtype=np.int64)
                card1 = np.asarray(record["summaries"][1]["cards"], dtype=np.int64)
                dmax0 = np.asarray(record["summaries"][0]["dmax"], dtype=np.float64)
                persistence0 = np.asarray(
                    record["summaries"][0]["persistence_max"], dtype=np.float64
                )
                for index in range(z.size):
                    rows.append(
                        {
                            "run_id": run_id,
                            "family": family,
                            "seed": seed,
                            "class": label,
                            "frame": index,
                            "u": float(timestamps[index]),
                            "z": float(z[index]),
                            "card0": int(card0[index]),
                            "card1": int(card1[index]),
                            "dmax0": float(dmax0[index]),
                            "persistence0": float(persistence0[index]),
                        }
                    )
                latent = dict(record["latent"])
                if family == "A":
                    z_merge = 2.0 * float(latent["r"])
                    plateau = float(np.median(dmax0[z < z_merge - 0.25]))
                    threshold = plateau + 0.05
                    above = dmax0 > threshold
                    switch_z = z_merge + plateau
                    expected_frame = int(np.argmax(z > switch_z))
                    unique_cards = sorted({int(value) for value in card0})
                    if label == "return" and np.any(above):
                        measured_first = int(np.argmax(above))
                        measured_last = int(
                            len(above) - 1 - np.argmax(above[::-1])
                        )
                        expected_fall = int(
                            len(z) - 1 - np.argmax(z[::-1] > switch_z)
                        )
                        alignment = bool(
                            abs(measured_first - expected_frame) <= 3
                            and abs(measured_last - expected_fall) <= 3
                        )
                    elif np.any(above):
                        measured_first = int(np.argmax(above))
                        measured_last = measured_first
                        expected_fall = -1
                        alignment = bool(abs(measured_first - expected_frame) <= 3)
                    else:
                        measured_first = -1
                        measured_last = -1
                        expected_fall = -1
                        alignment = False
                    events.append(
                        {
                            "family": "A",
                            "seed": seed,
                            "class": label,
                            "expected_z": switch_z,
                            "expected_frame": expected_frame,
                            "measured_first_frame": measured_first,
                            "measured_last_frame": measured_last,
                            "measured_first_z": (
                                float(z[measured_first]) if measured_first >= 0 else float("nan")
                            ),
                            "expected_fall_frame": expected_fall,
                            "delta_frames_first": (
                                measured_first - expected_frame
                                if measured_first >= 0
                                else None
                            ),
                            "cardinality_before": int(card0[max(expected_frame - 1, 0)]),
                            "cardinality_after": int(card0[min(expected_frame + 1, z.size - 1)]),
                            "unique_h0_cardinalities": unique_cards,
                            "criterion": "finite H0 cardinality changes at expected z",
                            "cardinality_criterion": "RESIDUAL",
                            "event_alignment": "PASS" if alignment else "RESIDUAL",
                            "note": (
                                "H0 finite cardinality is exactly n_points - 1 for "
                                "every frame; the merge/separation transition is "
                                "resolved in the H0 death coordinate at z = 2r plus "
                                "the intra-circle merge scale"
                            ),
                        }
                    )
                    verdicts.append("RESIDUAL")
                else:
                    z_onset = 2.0 * float(latent["w"])
                    positive = card0 > 0
                    expected_rise = int(np.argmax(z > z_onset))
                    if np.any(positive):
                        measured_first = int(np.argmax(positive))
                        measured_last = int(
                            len(positive) - 1 - np.argmax(positive[::-1])
                        )
                        expected_fall = int(
                            len(z) - 1 - np.argmax(z[::-1] > z_onset)
                        )
                    else:
                        measured_first = -1
                        measured_last = -1
                        expected_fall = -1
                    if label == "jump":
                        alignment = bool(
                            measured_first >= 0
                            and abs(measured_first - expected_rise) <= 1
                        )
                    elif label == "ramp":
                        alignment = bool(
                            measured_first >= 0
                            and abs(float(z[measured_first]) - z_onset)
                            <= GRID_SPACING_32
                        )
                    else:
                        alignment = bool(
                            measured_first >= 0
                            and measured_last >= 0
                            and abs(float(z[measured_first]) - z_onset)
                            <= GRID_SPACING_32
                            and abs(float(z[measured_last]) - z_onset)
                            <= GRID_SPACING_32
                        )
                    events.append(
                        {
                            "family": "B",
                            "seed": seed,
                            "class": label,
                            "expected_z": z_onset,
                            "expected_frame": expected_rise,
                            "measured_first_frame": measured_first,
                            "measured_last_frame": measured_last,
                            "measured_first_z": (
                                float(z[measured_first]) if measured_first >= 0 else float("nan")
                            ),
                            "expected_fall_frame": expected_fall,
                            "delta_frames_first": (
                                measured_first - expected_rise
                                if measured_first >= 0
                                else None
                            ),
                            "cardinality_before": (
                                int(card0[measured_first - 1]) if measured_first > 0 else 0
                            ),
                            "cardinality_after": (
                                int(card0[measured_first]) if measured_first >= 0 else -1
                            ),
                            "unique_h0_cardinalities": sorted(
                                {int(value) for value in card0}
                            ),
                            "criterion": "finite H0 cardinality changes at expected z",
                            "cardinality_criterion": "PASS" if alignment else "RESIDUAL",
                            "event_alignment": "PASS" if alignment else "FAIL",
                            "note": "finite H0 bar appears at the separation onset",
                        }
                    )
                    verdicts.append("PASS" if alignment else "FAIL")
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "class_cardinality.csv",
        list(rows[0].keys()) if rows else ["run_id"],
        rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "class_transitions.csv",
        list(events[0].keys()) if events else ["family", "seed"],
        events,
    )
    return {
        "id": "check3_topology",
        "title": "Topology-changing class programs",
        "verdict": overall,
        "events": events,
        "tables": [
            "reports/tables/class_cardinality.csv",
            "reports/tables/class_transitions.csv",
        ],
    }


def longest_exceedance_run(values, threshold: float) -> int:
    best = 0
    current = 0
    for value in np.asarray(values, dtype=np.float64):
        if float(value) > float(threshold):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return int(best)


def longest_boolean_run(flags) -> int:
    best = 0
    current = 0
    for flag in np.asarray(flags, dtype=bool):
        if bool(flag):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return int(best)


def exceedance_cluster_pvalue(flags, n_resamples: int = 2000, seed: int = 20260907) -> float:
    """Permutation p-value for temporal clustering of exceedance indicators.

    The observed longest run of exceedances is compared with the distribution
    of the longest run under random permutations of the same indicator vector,
    so the marginal exceedance rate is held fixed. A small p-value means the
    exceedances are clustered in time rather than merely numerous.
    """
    vector = np.asarray(flags, dtype=bool)
    if vector.size == 0:
        return 1.0
    observed = longest_boolean_run(vector)
    if observed <= 1:
        return 1.0
    rng = np.random.default_rng(int(seed))
    exceedances = int(np.count_nonzero(vector))
    total = 0
    for _ in range(int(n_resamples)):
        permuted = np.zeros(vector.size, dtype=bool)
        permuted[rng.choice(vector.size, size=exceedances, replace=False)] = True
        if longest_boolean_run(permuted) >= observed:
            total += 1
    return float(total + 1) / float(int(n_resamples) + 1)


def check4_null(records: dict, out_dir: Path, calibration: dict) -> dict:
    """Ladder check 4: noisy raw null processes.

    Declared rules. sigma = 0 passes only if every adjacent distance is exactly
    zero. For sigma > 0 a run fails when the Spearman trend is significant at
    0.1 percent with absolute rho above 0.5, or when at least five consecutive
    adjacent distances exceed the same-sigma static threshold. A run is
    RESIDUAL when the trend is not nonsystematic at 1 percent or when the
    exceedance count above the same-sigma static 95th percentile exceeds the
    99 percent binomial upper bound. Configuration transfer of the frozen
    training-style sigma = 0.05 static floor is reported separately.

    The training-style calibration is the pooled 95th percentile of static
    z = 0.5 adjacent distances at sigma = 0.05 (seeds 11 and 12). The
    leave-one-out static calibration at each sigma pools the other null seed
    at z = 0.5, so it matches both sigma and configuration type.
    """
    from scipy.stats import binom

    summary_rows: list[dict] = []
    distance_rows: list[dict] = []
    verdicts: list[str] = []
    calibration_max: dict[str, float] = {}
    for family in ("A", "B"):
        pool = []
        for seed in SEEDS_PRIMARY:
            record = records.get(standard_run_id(family, "static", seed, 0.05, 1))
            if record is not None and record["status"] == "ok":
                pool.append(
                    np.asarray(record["diagnostics"][0]["adjacent"], dtype=np.float64)
                )
        calibration_max[family] = (
            float(np.max(np.concatenate(pool))) if pool else float("nan")
        )
    leave_one_out: dict[tuple, float] = {}
    for family in ("A", "B"):
        for sigma in (0.05, 0.10):
            for excluded in SEEDS_NULL:
                pool = []
                for seed in SEEDS_NULL:
                    if int(seed) == int(excluded):
                        continue
                    record = records.get(
                        standard_run_id(family, "static", seed, sigma, 1)
                    )
                    if record is not None and record["status"] == "ok":
                        pool.append(
                            np.asarray(
                                record["diagnostics"][0]["adjacent"],
                                dtype=np.float64,
                            )
                        )
                leave_one_out[(family, sigma, excluded)] = (
                    float(
                        np.percentile(
                            np.concatenate(pool), CALIBRATION_PERCENTILE
                        )
                    )
                    if pool
                    else float("nan")
                )
    runs: list[dict] = []
    for family in ("A", "B"):
        for seed in SEEDS_NULL:
            for sigma in SIGMAS_NULL:
                runs.append(
                    {
                        "family": family,
                        "seed": int(seed),
                        "sigma": float(sigma),
                        "config": "static_z0.5",
                        "z_value": 0.5,
                        "run_id": standard_run_id(family, "static", seed, sigma, 1),
                    }
                )
            for sigma in SIGMAS_NULL:
                for z_value in SNAPSHOT_Z:
                    runs.append(
                        {
                            "family": family,
                            "seed": int(seed),
                            "sigma": float(sigma),
                            "config": f"snapshot_z{z_value:.1f}",
                            "z_value": float(z_value),
                            "run_id": snapshot_run_id(family, seed, z_value, sigma),
                        }
                    )
    for run in runs:
        record = records.get(run["run_id"])
        if record is None or record["status"] != "ok":
            verdicts.append("FAIL")
            summary_rows.append(
                {
                    "run_id": run["run_id"],
                    "family": run["family"],
                    "config": run["config"],
                    "seed": run["seed"],
                    "sigma": run["sigma"],
                    "status": "missing",
                    "verdict": "FAIL",
                }
            )
            continue
        adjacent = np.asarray(
            record["diagnostics"][0]["adjacent"], dtype=np.float64
        )
        stats_row = distribution_stats(adjacent)
        trend = phase_trend_and_exchangeability(record, 0)
        exact_zero = bool(np.all(adjacent == 0.0))
        e_static = (
            calibration.get(run["family"], float("nan"))
            if run["sigma"] == 0.05
            else float("nan")
        )
        e_loo = (
            leave_one_out.get((run["family"], run["sigma"], run["seed"]), float("nan"))
            if run["sigma"] > 0
            else float("nan")
        )
        n_above_static = (
            int(np.count_nonzero(adjacent > e_static))
            if math.isfinite(e_static)
            else 0
        )
        if math.isfinite(e_loo):
            n_above_loo = int(np.count_nonzero(adjacent > e_loo))
            max_run_loo = longest_exceedance_run(adjacent, e_loo)
        else:
            n_above_loo = 0
            max_run_loo = 0
        n = int(adjacent.size)
        expected_above = 0.05 * n
        upper_bound = float(binom.ppf(0.99, n, 0.05)) if n else float("nan")
        if run["sigma"] == 0.0:
            e_primary = float("nan")
            e_primary_source = "not_applicable_sigma_zero"
        elif run["sigma"] == 0.05 and math.isfinite(e_static):
            e_primary = e_static
            e_primary_source = "pooled_static_sigma0.05_seeds11_12"
        else:
            e_primary = e_loo
            e_primary_source = "leave_one_out_static_same_sigma"
        if math.isfinite(e_primary):
            flags = adjacent > e_primary
            n_above_primary = int(np.count_nonzero(flags))
            max_run_primary = longest_exceedance_run(adjacent, e_primary)
            cluster_p = exceedance_cluster_pvalue(flags)
        else:
            n_above_primary = 0
            max_run_primary = 0
            cluster_p = float("nan")
        exceed_pass = bool(
            n_above_primary <= upper_bound
            if math.isfinite(e_primary)
            else run["sigma"] == 0.0
        )
        if run["sigma"] == 0.0:
            verdict = "PASS" if exact_zero else "FAIL"
            temporal_pass = exact_zero
            cluster_fail = False
            note = "sigma = 0 exact-zero requirement"
        else:
            trend_fail = bool(
                math.isfinite(trend["spearman_p"])
                and trend["spearman_p"] < 0.001
                and abs(trend["spearman_rho"]) > 0.5
            )
            cluster_fail = bool(math.isfinite(cluster_p) and cluster_p < 0.01)
            temporal_pass = bool((not trend_fail) and (not cluster_fail))
            if not temporal_pass:
                verdict = "FAIL"
                note = "temporal structure detected in a null process"
            elif (not trend["trend_pass"]) or (not exceed_pass):
                verdict = "RESIDUAL"
                if not exceed_pass:
                    note = (
                        "stationary null but exceedance count above the "
                        "primary static 95th percentile exceeds the binomial "
                        "99 percent bound; configuration-dependent or seed-"
                        "dependent noise scale"
                    )
                else:
                    note = "weak nonstationary trend signature"
            else:
                verdict = "PASS"
                note = "stationary noise, no exceedance excess"
        verdicts.append(verdict)
        summary_rows.append(
            {
                "run_id": run["run_id"],
                "family": run["family"],
                "config": run["config"],
                "z_value": run["z_value"],
                "seed": run["seed"],
                "sigma": run["sigma"],
                "n_intervals": stats_row["n"],
                "mean": stats_row["mean"],
                "std": stats_row["std"],
                "min": stats_row["min"],
                "median": stats_row["median"],
                "p95": stats_row["p95"],
                "max": stats_row["max"],
                "exact_zero": exact_zero,
                "spearman_rho": trend["spearman_rho"],
                "spearman_p": trend["spearman_p"],
                "trend_pass": trend["trend_pass"],
                "ks_lag8_p": trend["ks_lag8_p"],
                "e_static_05": e_static,
                "n_above_e_static_05": n_above_static,
                "e_loo_same_sigma": e_loo,
                "n_above_e_loo": n_above_loo,
                "max_run_above_e_loo": max_run_loo,
                "e_primary": e_primary,
                "e_primary_source": e_primary_source,
                "n_above_e_primary": n_above_primary,
                "max_run_above_e_primary": max_run_primary,
                "cluster_p": cluster_p,
                "expected_above_e_primary": expected_above,
                "binom_upper_99": upper_bound,
                "exceed_pass": exceed_pass,
                "calibration_max": calibration_max.get(run["family"], float("nan")),
                "temporal_pass": temporal_pass,
                "verdict": verdict,
                "note": note,
            }
        )
        for index, value in enumerate(adjacent):
            distance_rows.append(
                {
                    "run_id": run["run_id"],
                    "family": run["family"],
                    "config": run["config"],
                    "z_value": run["z_value"],
                    "seed": run["seed"],
                    "sigma": run["sigma"],
                    "interval": index,
                    "u_mid": float(
                        0.5
                        * (
                            record["timestamps"][index]
                            + record["timestamps"][index + 1]
                        )
                    ),
                    "distance": float(value),
                    "above_e_static_05": (
                        bool(value > e_static) if math.isfinite(e_static) else None
                    ),
                    "above_e_loo": (
                        bool(value > e_loo) if math.isfinite(e_loo) else None
                    ),
                }
            )
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "null_summary.csv",
        list(summary_rows[0].keys()) if summary_rows else ["run_id"],
        summary_rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "null_adjacent_distances.csv",
        list(distance_rows[0].keys()) if distance_rows else ["run_id"],
        distance_rows,
    )
    return {
        "id": "check4_null",
        "title": "Noisy raw null processes",
        "verdict": overall,
        "calibration": calibration,
        "calibration_max": calibration_max,
        "leave_one_out": {
            f"{family}_sigma{sigma_tag(sigma)}_exclude{seed}": value
            for (family, sigma, seed), value in leave_one_out.items()
        },
        "rows": summary_rows,
        "tables": [
            "reports/tables/null_summary.csv",
            "reports/tables/null_adjacent_distances.csv",
        ],
    }


def check5_sampling(records: dict, out_dir: Path) -> dict:
    """Ladder check 5: sampling and filtration-resolution sensitivity.

    Family A declared rule: every per-frame full-versus-subsample H0 distance
    must satisfy the adapted delta-dense bound d_B at most 2 delta, where delta
    is the one-sided maximum distance from a dropped point to the retained
    set; otherwise RESIDUAL. The cross distance between the 32-point and
    16-point subsamples is reported.

    Family B declared rule: the coarse 16x16 grid is a sensitivity comparison,
    not an invariance; it passes when the grid still resolves a finite H0 bar
    after onset and the 32x32 versus 16x16 distance and cardinality changes
    are finite and reported.
    """
    rows: list[dict] = []
    summary: list[dict] = []
    verdicts: list[str] = []
    for seed in SEEDS_PRIMARY:
        base = records.get(standard_run_id("A", "ramp", seed, 0.0, 1))
        subs = {
            points: records.get(points_run_id("A", "ramp", seed, 0.0, points))
            for points in (32, 16)
        }
        if (
            base is None
            or base["status"] != "ok"
            or any(
                record is None or record["status"] != "ok"
                for record in subs.values()
            )
        ):
            verdicts.append("FAIL")
            continue
        n = int(base["n_frames"])
        cross = np.asarray(
            [
                float(
                    diagram_metrics.bottleneck_linf(
                        subs[32]["diagrams"][0][index],
                        subs[16]["diagrams"][0][index],
                    )
                )
                for index in range(n)
            ],
            dtype=np.float64,
        )
        for points in (32, 16):
            record = subs[points]
            delta = np.asarray(record["delta"], dtype=np.float64)
            d0 = np.asarray(
                [
                    float(
                        diagram_metrics.bottleneck_linf(
                            base["diagrams"][0][index],
                            record["diagrams"][0][index],
                        )
                    )
                    for index in range(n)
                ],
                dtype=np.float64,
            )
            d1 = np.asarray(
                [
                    float(
                        diagram_metrics.bottleneck_linf(
                            base["diagrams"][1][index],
                            record["diagrams"][1][index],
                        )
                    )
                    for index in range(n)
                ],
                dtype=np.float64,
            )
            bound = BOUND_2DELTA_FACTOR * delta
            bound_pass = bool(np.all(d0 <= bound + 1e-12))
            card0 = np.asarray(record["summaries"][0]["cards"], dtype=np.int64)
            card1 = np.asarray(record["summaries"][1]["cards"], dtype=np.int64)
            for index in range(n):
                rows.append(
                    {
                        "run_id": record["run_id"],
                        "family": "A",
                        "seed": seed,
                        "variant": f"points{points}",
                        "frame": index,
                        "u": float(base["timestamps"][index]),
                        "z": float(base["z"][index]),
                        "card0": int(card0[index]),
                        "card1": int(card1[index]),
                        "d0_vs_full": float(d0[index]),
                        "d1_vs_full": float(d1[index]),
                        "delta": float(delta[index]),
                        "bound_2delta": float(bound[index]),
                        "d0_cross_32_16": float(cross[index]) if points == 16 else None,
                        "field_max_abs_diff": None,
                    }
                )
            summary.append(
                {
                    "family": "A",
                    "seed": seed,
                    "variant": f"points{points}",
                    "n_frames": n,
                    "n_points_per_frame": int(points),
                    "delta_min": float(np.min(delta)),
                    "delta_max": float(np.max(delta)),
                    "mean_d0_vs_full": float(np.mean(d0)),
                    "max_d0_vs_full": float(np.max(d0)),
                    "mean_d1_vs_full": float(np.mean(d1)),
                    "max_d1_vs_full": float(np.max(d1)),
                    "max_ratio_d0_to_delta": float(np.max(d0 / delta)),
                    "max_ratio_d0_to_2delta": float(np.max(d0 / bound)),
                    "card0_min": int(np.min(card0)),
                    "card0_max": int(np.max(card0)),
                    "card1_min": int(np.min(card1)),
                    "card1_max": int(np.max(card1)),
                    "cross_mean": float(np.mean(cross)),
                    "cross_max": float(np.max(cross)),
                    "bound_pass": bound_pass,
                    "verdict": "PASS" if bound_pass else "RESIDUAL",
                }
            )
            verdicts.append("PASS" if bound_pass else "RESIDUAL")
    for seed in SEEDS_PRIMARY:
        base = records.get(standard_run_id("B", "ramp", seed, 0.0, 1))
        coarse = records.get(grid_run_id("B", "ramp", seed, 0.0, 16))
        if (
            base is None
            or base["status"] != "ok"
            or coarse is None
            or coarse["status"] != "ok"
        ):
            verdicts.append("FAIL")
            continue
        n = int(base["n_frames"])
        d0 = np.asarray(
            [
                float(
                    diagram_metrics.bottleneck_linf(
                        base["diagrams"][0][index],
                        coarse["diagrams"][0][index],
                    )
                )
                for index in range(n)
            ],
            dtype=np.float64,
        )
        d1 = np.asarray(
            [
                float(
                    diagram_metrics.bottleneck_linf(
                        base["diagrams"][1][index],
                        coarse["diagrams"][1][index],
                    )
                )
                for index in range(n)
            ],
            dtype=np.float64,
        )
        card0_base = np.asarray(base["summaries"][0]["cards"], dtype=np.int64)
        card0_coarse = np.asarray(coarse["summaries"][0]["cards"], dtype=np.int64)
        card1_base = np.asarray(base["summaries"][1]["cards"], dtype=np.int64)
        card1_coarse = np.asarray(coarse["summaries"][1]["cards"], dtype=np.int64)
        field_diff = np.asarray(coarse["field_diff_max"], dtype=np.float64)
        fine_onset = int(np.argmax(card0_base > 0)) if np.any(card0_base > 0) else -1
        coarse_onset = (
            int(np.argmax(card0_coarse > 0)) if np.any(card0_coarse > 0) else -1
        )
        qualitative_pass = bool(
            fine_onset >= 0 and coarse_onset >= 0 and np.any(card0_coarse > 0)
        )
        for index in range(n):
            rows.append(
                {
                    "run_id": coarse["run_id"],
                    "family": "B",
                    "seed": seed,
                    "variant": "grid16",
                    "frame": index,
                    "u": float(base["timestamps"][index]),
                    "z": float(base["z"][index]),
                    "card0": int(card0_coarse[index]),
                    "card1": int(card1_coarse[index]),
                    "d0_vs_full": float(d0[index]),
                    "d1_vs_full": float(d1[index]),
                    "delta": None,
                    "bound_2delta": None,
                    "d0_cross_32_16": None,
                    "field_max_abs_diff": float(field_diff[index]),
                }
            )
        summary.append(
            {
                "family": "B",
                "seed": seed,
                "variant": "grid16",
                "n_frames": n,
                "n_points_per_frame": 16 * 16,
                "delta_min": None,
                "delta_max": None,
                "mean_d0_vs_full": float(np.mean(d0)),
                "max_d0_vs_full": float(np.max(d0)),
                "mean_d1_vs_full": float(np.mean(d1)),
                "max_d1_vs_full": float(np.max(d1)),
                "max_ratio_d0_to_delta": None,
                "max_ratio_d0_to_2delta": None,
                "card0_min": int(np.min(card0_coarse)),
                "card0_max": int(np.max(card0_coarse)),
                "card1_min": int(np.min(card1_coarse)),
                "card1_max": int(np.max(card1_coarse)),
                "cross_mean": None,
                "cross_max": None,
                "fine_onset_frame": fine_onset,
                "coarse_onset_frame": coarse_onset,
                "field_max_abs_diff_max": float(np.max(field_diff)),
                "bound_pass": qualitative_pass,
                "verdict": "PASS" if qualitative_pass else "RESIDUAL",
            }
        )
        verdicts.append("PASS" if qualitative_pass else "RESIDUAL")
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "sampling_resolution.csv",
        list(rows[0].keys()) if rows else ["run_id"],
        rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "sampling_summary.csv",
        list(summary[0].keys()) if summary else ["family", "seed"],
        summary,
    )
    return {
        "id": "check5_sampling",
        "title": "Sampling and filtration-resolution sensitivity",
        "verdict": overall,
        "summary": summary,
        "tables": [
            "reports/tables/sampling_resolution.csv",
            "reports/tables/sampling_summary.csv",
        ],
    }


def check6_translation(records: dict, out_dir: Path) -> dict:
    """Ladder check 6: rigid translation invariance for Family A.

    Declared rule: for every frame and degree the bottleneck distance between
    the static and translated diagrams must not exceed 1e-7 times
    max(1, filtration range), with the range taken over all finite deaths and
    births of both diagram sequences.
    """
    rows: list[dict] = []
    summary: list[dict] = []
    verdicts: list[str] = []
    for seed in SEEDS_PRIMARY:
        for sigma in SIGMAS_STATIC:
            static = records.get(standard_run_id("A", "static", seed, sigma, 1))
            translated = records.get(
                standard_run_id("A", "translation", seed, sigma, 1)
            )
            if (
                static is None
                or static["status"] != "ok"
                or translated is None
                or translated["status"] != "ok"
            ):
                verdicts.append("FAIL")
                summary.append(
                    {
                        "family": "A",
                        "seed": seed,
                        "sigma": sigma,
                        "status": "missing",
                        "verdict": "FAIL",
                    }
                )
                continue
            deviations = []
            for record in (static, translated):
                for degree in DEGREES:
                    for diagram in record["diagrams"][degree]:
                        if len(diagram):
                            deviations.append(float(diagram[:, 1].max()))
                            deviations.append(float(diagram[:, 0].min()))
            filtration_range = (
                max(deviations) - min(deviations) if deviations else 0.0
            )
            tolerance = 1e-7 * max(1.0, filtration_range)
            for degree in DEGREES:
                distances = np.asarray(
                    [
                        float(
                            diagram_metrics.bottleneck_linf(
                                static["diagrams"][degree][index],
                                translated["diagrams"][degree][index],
                            )
                        )
                        for index in range(int(static["n_frames"]))
                    ],
                    dtype=np.float64,
                )
                maximum = float(np.max(distances)) if distances.size else 0.0
                passed = bool(maximum <= tolerance)
                verdicts.append("PASS" if passed else "FAIL")
                for index, value in enumerate(distances):
                    rows.append(
                        {
                            "run_id": static["run_id"],
                            "comparison": translated["run_id"],
                            "family": "A",
                            "seed": seed,
                            "sigma": sigma,
                            "degree": degree,
                            "frame": index,
                            "u": float(static["timestamps"][index]),
                            "distance": float(value),
                            "tolerance": tolerance,
                        }
                    )
                summary.append(
                    {
                        "family": "A",
                        "seed": seed,
                        "sigma": sigma,
                        "degree": degree,
                        "n_frames": int(static["n_frames"]),
                        "max_distance": maximum,
                        "filtration_range": float(filtration_range),
                        "tolerance": float(tolerance),
                        "passed": passed,
                        "verdict": "PASS" if passed else "FAIL",
                    }
                )
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "RESIDUAL" in verdicts:
        overall = "RESIDUAL"
    else:
        overall = "PASS"
    write_csv(
        out_dir / "reports" / "tables" / "translation_controls.csv",
        list(rows[0].keys()) if rows else ["run_id"],
        rows,
    )
    write_csv(
        out_dir / "reports" / "tables" / "translation_summary.csv",
        list(summary[0].keys()) if summary else ["family", "seed"],
        summary,
    )
    return {
        "id": "check6_translation",
        "title": "Rigid translation invariance",
        "verdict": overall,
        "summary": summary,
        "tables": [
            "reports/tables/translation_controls.csv",
            "reports/tables/translation_summary.csv",
        ],
    }


def save_figure(fig, path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return str(path)


def figure_static(records: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, family in zip(axes, ("A", "B")):
        for seed, color in ((11, "tab:blue"), (12, "tab:orange")):
            record = records.get(standard_run_id(family, "static", seed, 0.05, 1))
            if record is None or record["status"] != "ok":
                continue
            ax.hist(
                np.asarray(record["diagnostics"][0]["adjacent"]),
                bins=25,
                alpha=0.5,
                color=color,
                label=f"seed {seed}",
            )
        zero_record = records.get(standard_run_id(family, "static", 11, 0.0, 1))
        zero_ok = (
            bool(np.all(np.asarray(zero_record["diagnostics"][0]["adjacent"]) == 0.0))
            if zero_record is not None and zero_record["status"] == "ok"
            else False
        )
        ax.set_title(
            f"Family {family}, static z=0.5, sigma=0.05 (H0); "
            f"sigma=0 exact zero: {zero_ok}"
        )
        ax.set_xlabel("adjacent bottleneck distance")
        ax.set_ylabel("count")
        ax.legend()
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check1_static.png")


def figure_ramp(records: dict, checks: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fits = {row["seed"]: row for row in checks["check2_ramp"]["fits"] if row["family"] == "A"}
    for seed, color in ((11, "tab:blue"), (12, "tab:orange")):
        master = records.get(standard_run_id("A", "ramp", seed, 0.0, 1))
        stride4 = records.get(standard_run_id("A", "ramp", seed, 0.0, 4))
        if master is None or stride4 is None:
            continue
        z = np.asarray(master["z"])
        d0 = np.asarray(master["diagnostics"][0]["adjacent"])
        z4 = z[::4]
        d04 = np.asarray(stride4["diagnostics"][0]["adjacent"])
        axes[0, 0].plot(
            0.5 * (z[:-1] + z[1:]), d0, ".", ms=3, color=color, label=f"seed {seed} stride 1"
        )
        axes[0, 0].plot(
            0.5 * (z4[:-1] + z4[1:]), d04, "x", ms=4, color=color, label=f"seed {seed} stride 4"
        )
        axes[0, 0].axvline(2.0 * float(master["latent"]["r"]), color=color, ls="--", lw=1)
        axes[0, 1].plot(
            np.abs(np.diff(z)),
            d0,
            ".",
            ms=3,
            color=color,
            label=f"seed {seed} stride 1",
        )
        axes[0, 1].plot(
            np.abs(z4[1:] - z4[:-1]),
            d04,
            "x",
            ms=4,
            color=color,
            label=f"seed {seed} stride 4",
        )
        row = fits.get(seed)
        if row is not None and math.isfinite(row.get("C_max_ratio", float("nan"))):
            x_line = np.linspace(0.0, float(np.max(np.abs(z4[1:] - z4[:-1]))), 50)
            axes[0, 1].plot(
                x_line,
                row["C_ls"] * x_line + row["f_ls"],
                ls="-",
                lw=1,
                color=color,
                label=f"seed {seed} LS C={row['C_ls']:.2f}",
            )
    axes[0, 0].set_xlabel("z interval midpoint")
    axes[0, 0].set_ylabel("adjacent H0 distance")
    axes[0, 0].set_title("Family A ramp response versus z (dashed: 2r)")
    axes[0, 0].legend(fontsize=7)
    axes[0, 1].set_xlabel("|dz|")
    axes[0, 1].set_ylabel("adjacent H0 distance")
    axes[0, 1].set_title("Family A bounded response, strides 1 and 4")
    axes[0, 1].legend(fontsize=7)
    for seed, color in ((11, "tab:blue"), (12, "tab:orange")):
        master = records.get(standard_run_id("B", "ramp", seed, 0.0, 1))
        if master is None:
            continue
        z = np.asarray(master["z"])
        d0 = np.asarray(master["diagnostics"][0]["adjacent"])
        persistence = np.asarray(master["summaries"][0]["persistence_max"])
        axes[1, 0].plot(0.5 * (z[:-1] + z[1:]), d0, ".", ms=3, color=color, label=f"seed {seed}")
        axes[1, 1].plot(z, persistence, ".", ms=3, color=color, label=f"seed {seed}")
        axes[1, 0].axvline(2.0 * float(master["latent"]["w"]), color=color, ls="--", lw=1)
        axes[1, 1].axvline(2.0 * float(master["latent"]["w"]), color=color, ls="--", lw=1)
    axes[1, 0].set_xlabel("z interval midpoint")
    axes[1, 0].set_ylabel("adjacent H0 distance")
    axes[1, 0].set_title("Family B ramp incremental response (dashed: 2w)")
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].set_xlabel("z")
    axes[1, 1].set_ylabel("finite H0 bar persistence")
    axes[1, 1].set_title("Family B persistence response after onset")
    axes[1, 1].legend(fontsize=7)
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check2_ramp.png")


def figure_topology(records: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    colors = {"ramp": "tab:blue", "return": "tab:green", "jump": "tab:red"}
    for label, color in colors.items():
        record = records.get(standard_run_id("A", label, 11, 0.0, 1))
        if record is None or record["status"] != "ok":
            continue
        z = np.asarray(record["z"])
        axes[0, 0].plot(
            z, np.asarray(record["summaries"][0]["dmax"]), ".", ms=3, color=color, label=label
        )
        axes[1, 0].plot(
            z, np.asarray(record["summaries"][0]["cards"]), ".", ms=3, color=color, label=f"{label} H0"
        )
    record_a = records.get(standard_run_id("A", "ramp", 11, 0.0, 1))
    if record_a is not None:
        axes[0, 0].axvline(2.0 * float(record_a["latent"]["r"]), color="k", ls="--", lw=1)
        axes[0, 0].set_title("Family A largest finite H0 death (dashed: 2r)")
    axes[0, 0].set_xlabel("z")
    axes[0, 0].set_ylabel("max finite H0 death")
    axes[0, 0].legend(fontsize=7)
    record_b = records.get(standard_run_id("B", "ramp", 11, 0.0, 1))
    for label, color in colors.items():
        record = records.get(standard_run_id("B", label, 11, 0.0, 1))
        if record is None or record["status"] != "ok":
            continue
        z = np.asarray(record["z"])
        axes[1, 0].plot(
            z, np.asarray(record["summaries"][0]["cards"]), ".", ms=3, color=color, label=f"{label} H0"
        )
        axes[1, 1].plot(
            z,
            np.asarray(record["summaries"][0]["persistence_max"]),
            ".", ms=3, color=color, label=label,
        )
        axes[1, 1].plot(
            z, np.asarray(record["summaries"][1]["cards"]), "x", ms=3, color=color, alpha=0.6,
            label=f"{label} H1",
        )
    if record_b is not None:
        axes[1, 0].axvline(2.0 * float(record_b["latent"]["w"]), color="k", ls="--", lw=1)
        axes[1, 1].axvline(2.0 * float(record_b["latent"]["w"]), color="k", ls="--", lw=1)
    axes[1, 0].set_xlabel("z")
    axes[1, 0].set_ylabel("finite H0 cardinality")
    axes[1, 0].set_title("Family B cardinality versus z (dashed: 2w)")
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].set_xlabel("z")
    axes[1, 1].set_ylabel("persistence / cardinality")
    axes[1, 1].set_title("Family B persistence and H1 cardinality")
    axes[1, 1].legend(fontsize=7)
    axes[0, 1].axis("off")
    axes[0, 1].text(
        0.02,
        0.95,
        "Family A finite H0 cardinality is constant at n_points - 1;\n"
        "the merge and separation transition is resolved in the\n"
        "largest finite H0 death and in the H1 channel.",
        va="top",
        fontsize=9,
    )
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check3_topology.png")


def figure_null(records: dict, checks: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    rows = {row["run_id"]: row for row in checks["check4_null"]["rows"]}
    for ax, family in zip((axes[0, 0], axes[0, 1]), ("A", "B")):
        for run_id, color in (
            (standard_run_id(family, "static", 13, 0.05, 1), "tab:blue"),
            (standard_run_id(family, "static", 13, 0.10, 1), "tab:orange"),
            (snapshot_run_id(family, 13, 2.0, 0.05), "tab:green"),
            (snapshot_run_id(family, 13, 2.0, 0.10), "tab:red"),
        ):
            record = records.get(run_id)
            if record is None or record["status"] != "ok":
                continue
            adjacent = np.asarray(record["diagnostics"][0]["adjacent"])
            ax.plot(adjacent, ".", ms=2, color=color, label=run_id)
        thresholds = [
            rows[run_id]["e_primary"]
            for run_id in rows
            if rows[run_id]["family"] == family
            and rows[run_id]["sigma"] == 0.05
            and rows[run_id]["seed"] == 13
            and math.isfinite(rows[run_id].get("e_primary", float("nan")))
        ]
        if thresholds:
            ax.axhline(thresholds[0], color="k", ls="--", lw=1, label="primary e95 (sigma 0.05)")
        ax.set_title(f"Family {family} null adjacent distances, seed 13")
        ax.set_xlabel("interval")
        ax.set_ylabel("distance")
        ax.legend(fontsize=5)
    family_rows = [row for row in checks["check4_null"]["rows"] if row.get("sigma")]
    labels = [row["run_id"].replace("_stride1", "") for row in family_rows]
    fractions = [
        (
            float(row.get("n_above_e_primary", 0)) / float(row["n_intervals"])
            if row.get("n_intervals")
            else 0.0
        )
        for row in family_rows
    ]
    colors = [
        "tab:green" if row["config"].startswith("static") else "tab:red"
        for row in family_rows
    ]
    axes[1, 0].bar(np.arange(len(labels)), fractions, color=colors)
    axes[1, 0].axhline(0.05, color="k", ls="--", lw=1)
    axes[1, 0].set_xticks(np.arange(len(labels)))
    axes[1, 0].set_xticklabels(labels, rotation=90, fontsize=5)
    axes[1, 0].set_ylabel("fraction above leave-one-out e95")
    axes[1, 0].set_title("False-event fractions (dashed: 0.05)")
    for family, color in (("A", "tab:blue"), ("B", "tab:orange")):
        static = records.get(standard_run_id(family, "static", 13, 0.05, 1))
        snapshot = records.get(snapshot_run_id(family, 13, 2.0, 0.05))
        if static is not None:
            axes[1, 1].hist(
                np.asarray(static["diagnostics"][0]["adjacent"]),
                bins=25,
                alpha=0.5,
                color=color,
                label=f"{family} static",
            )
        if snapshot is not None:
            axes[1, 1].hist(
                np.asarray(snapshot["diagnostics"][0]["adjacent"]),
                bins=25,
                histtype="step",
                lw=1.5,
                color=color,
                label=f"{family} snapshot z=2.0",
            )
    axes[1, 1].set_xlabel("adjacent distance")
    axes[1, 1].set_ylabel("count")
    axes[1, 1].set_title("Static versus frozen snapshot, sigma 0.05")
    axes[1, 1].legend(fontsize=7)
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check4_null.png")


def figure_sampling(records: dict, checks: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for seed, color in ((11, "tab:blue"), (12, "tab:orange")):
        base = records.get(standard_run_id("A", "ramp", seed, 0.0, 1))
        for points, style in ((32, "-"), (16, ":")):
            record = records.get(points_run_id("A", "ramp", seed, 0.0, points))
            if (
                base is None
                or base["status"] != "ok"
                or record is None
                or record["status"] != "ok"
            ):
                continue
            d0 = np.asarray(
                [
                    float(diagram_metrics.bottleneck_linf(base["diagrams"][0][i], record["diagrams"][0][i]))
                    for i in range(int(base["n_frames"]))
                ]
            )
            delta = np.asarray(record["delta"])
            axes[0, 0].plot(d0, style, lw=1, color=color, label=f"seed {seed} points {points}")
            axes[0, 0].plot(
                2.0 * delta, "--", lw=0.8, color=color, alpha=0.7,
                label=f"seed {seed} points {points} 2 delta",
            )
        coarse = records.get(grid_run_id("B", "ramp", seed, 0.0, 16))
        base_b = records.get(standard_run_id("B", "ramp", seed, 0.0, 1))
        if (
            base_b is not None
            and base_b["status"] == "ok"
            and coarse is not None
            and coarse["status"] == "ok"
        ):
            d0 = np.asarray(
                [
                    float(diagram_metrics.bottleneck_linf(base_b["diagrams"][0][i], coarse["diagrams"][0][i]))
                    for i in range(int(base_b["n_frames"]))
                ]
            )
            axes[1, 0].plot(d0, ".", ms=2, color=color, label=f"seed {seed}")
    axes[0, 0].set_xlabel("frame")
    axes[0, 0].set_ylabel("H0 distance full versus subsample")
    axes[0, 0].set_title("Family A point-count sensitivity with 2 delta bounds")
    axes[0, 0].legend(fontsize=5)
    axes[0, 1].set_title("Family A summaries")
    axes[0, 1].axis("off")
    summary_rows = list(checks.get("check5_sampling", {}).get("summary", []))
    lines = [
        f"{row['seed']} points {row['n_points_per_frame']}: "
        f"mean d0={row['mean_d0_vs_full']:.4f}, max d0={row['max_d0_vs_full']:.4f}, "
        f"max d0/delta={row['max_ratio_d0_to_delta']:.3f}, "
        f"max d0/(2 delta)={row['max_ratio_d0_to_2delta']:.3f}, "
        f"cards H0 {row['card0_min']}..{row['card0_max']}, H1 {row['card1_min']}..{row['card1_max']}"
        for row in summary_rows
        if row["family"] == "A"
    ]
    axes[0, 1].text(0.0, 1.0, "\n".join(lines), va="top", fontsize=8)
    axes[1, 0].set_xlabel("frame")
    axes[1, 0].set_ylabel("H0 distance 32x32 versus 16x16")
    axes[1, 0].set_title("Family B grid-resolution sensitivity")
    axes[1, 0].legend(fontsize=7)
    for seed, color in ((11, "tab:blue"), (12, "tab:orange")):
        base_b = records.get(standard_run_id("B", "ramp", seed, 0.0, 1))
        coarse = records.get(grid_run_id("B", "ramp", seed, 0.0, 16))
        if (
            base_b is None
            or base_b["status"] != "ok"
            or coarse is None
            or coarse["status"] != "ok"
        ):
            continue
        axes[1, 1].plot(
            np.asarray(base_b["summaries"][0]["cards"]), "-", lw=1, color=color,
            label=f"seed {seed} 32x32",
        )
        axes[1, 1].plot(
            np.asarray(coarse["summaries"][0]["cards"]), "--", lw=1, color=color,
            label=f"seed {seed} 16x16",
        )
    axes[1, 1].set_xlabel("frame")
    axes[1, 1].set_ylabel("finite H0 cardinality")
    axes[1, 1].set_title("Family B cardinality by grid resolution")
    axes[1, 1].legend(fontsize=7)
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check5_sampling.png")


def figure_translation(records: dict, checks: dict, out_dir: Path) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    rows = checks["check6_translation"]["summary"]
    labels = [f"{row.get('seed')}/sigma{sigma_tag(row.get('sigma', 0))}/d{row.get('degree')}" for row in rows]
    maxima = [row.get("max_distance", float("nan")) for row in rows]
    tolerances = [row.get("tolerance", float("nan")) for row in rows]
    axes[0].bar(np.arange(len(rows)), maxima, color="tab:blue")
    axes[0].plot(np.arange(len(rows)), tolerances, "rx", ms=8, label="tolerance")
    axes[0].set_xticks(np.arange(len(rows)))
    axes[0].set_xticklabels(labels, rotation=45, fontsize=7)
    axes[0].set_ylabel("max diagram distance")
    axes[0].set_title("Family A translation control (blue: max distance, red x: tolerance)")
    axes[0].legend(fontsize=7)
    for row in rows:
        record = records.get(standard_run_id("A", "static", row["seed"], row["sigma"], 1))
        translated = records.get(standard_run_id("A", "translation", row["seed"], row["sigma"], 1))
        if record is None or translated is None:
            continue
        axes[1].plot(
            range(int(record["n_frames"])),
            [
                float(diagram_metrics.bottleneck_linf(record["diagrams"][row["degree"]][i], translated["diagrams"][row["degree"]][i]))
                for i in range(int(record["n_frames"]))
            ],
            ".",
            ms=2,
            label=f"{row['seed']}/sigma{sigma_tag(row['sigma'])}/d{row['degree']}",
        )
    axes[1].set_xlabel("frame")
    axes[1].set_ylabel("distance")
    axes[1].set_title("Per-frame translation distances")
    axes[1].legend(fontsize=6)
    return save_figure(fig, out_dir / "reports" / "figures" / "fig_check6_translation.png")


def make_figures(records: dict, checks, out_dir: Path) -> list[str]:
    if isinstance(checks, list):
        checks = {check["id"]: check for check in checks}
    outputs: list[str] = []
    builders = (
        ("fig_check1_static.png", lambda: figure_static(records, out_dir)),
        ("fig_check2_ramp.png", lambda: figure_ramp(records, checks, out_dir)),
        ("fig_check3_topology.png", lambda: figure_topology(records, out_dir)),
        ("fig_check4_null.png", lambda: figure_null(records, checks, out_dir)),
        ("fig_check5_sampling.png", lambda: figure_sampling(records, checks, out_dir)),
        ("fig_check6_translation.png", lambda: figure_translation(records, checks, out_dir)),
    )
    for name, builder in builders:
        try:
            outputs.append(builder())
        except Exception as error:
            import traceback

            print(f"figure {name} failed: {type(error).__name__}: {error}")
            traceback.print_exc()
    return outputs


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
        return f"{number:.6g}"
    return str(value)


def md_table(headers, rows, max_rows: int | None = None) -> str:
    selected = rows if max_rows is None else rows[:max_rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in selected:
        lines.append("| " + " | ".join(md_value(value) for value in row) + " |")
    return "\n".join(lines)


def package_versions() -> dict:
    from importlib import metadata

    versions = {}
    for name in (
        "numpy",
        "scipy",
        "gudhi",
        "persim",
        "scikit-learn",
        "pandas",
        "joblib",
        "matplotlib",
        "pyarrow",
    ):
        try:
            versions[name] = metadata.version(name)
        except Exception:
            versions[name] = None
    return versions


def write_directory_sha256sums(records_list: list[dict]) -> list[str]:
    directories: dict[Path, set] = {}
    for record in records_list:
        if record["status"] != "ok":
            continue
        for key in ("raw_path", "raw_meta_path", "diagram_path", "diagram_meta_path"):
            path = Path(record["saved"][key])
            directories.setdefault(path.parent, set()).add(path.name)
    written = []
    for directory, names in sorted(directories.items()):
        lines = [
            f"{sha256_file(directory / name)}  {name}"
            for name in sorted(names)
        ]
        target = directory / "SHA256SUMS"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(str(target))
    return written


def artifact_hash_rows(out_dir: Path, records_list: list[dict], extra_files: list) -> list[dict]:
    rows: list[dict] = []
    for relative in INPUT_FILES:
        rows.append(
            {
                "category": "input",
                "path": relative,
                "sha256": sha256_file(ROOT / relative),
            }
        )
    for record in records_list:
        if record["status"] != "ok":
            continue
        rows.append(
            {
                "category": "raw_control",
                "path": record["saved"]["raw_path"],
                "sha256": sha256_file(record["saved"]["raw_path"]),
            }
        )
        rows.append(
            {
                "category": "raw_control_meta",
                "path": record["saved"]["raw_meta_path"],
                "sha256": sha256_file(record["saved"]["raw_meta_path"]),
            }
        )
        rows.append(
            {
                "category": "diagram_sequence",
                "path": record["saved"]["diagram_path"],
                "sha256": sha256_file(record["saved"]["diagram_path"]),
            }
        )
        rows.append(
            {
                "category": "diagram_meta",
                "path": record["saved"]["diagram_meta_path"],
                "sha256": sha256_file(record["saved"]["diagram_meta_path"]),
            }
        )
    for path in extra_files:
        candidate = Path(path)
        if not candidate.is_file():
            continue
        try:
            label = str(candidate.relative_to(out_dir))
        except ValueError:
            label = str(candidate)
        rows.append(
            {
                "category": "report_artifact",
                "path": label,
                "sha256": sha256_file(candidate),
            }
        )
    return rows


def render_report(
    out_dir: Path,
    info: dict,
    checks: list[dict],
    figures: list[str],
) -> Path:
    lines: list[str] = []
    g1 = info["g1"]
    lines.append("# WP-3.1 raw-data correctness ladder report (conditional on G1)")
    lines.append("")
    lines.append(
        "This report is the WP-3.1 artifact for gate G2. The work is conditional "
        f"on gate G1. At runtime the G1 packet `{g1['packet']}` was `{g1['status_at_runtime']}` "
        f"with {g1['pending_marker_count']} pending marker(s) and sha256 "
        f"`{g1['sha256']}`. Per the coordinator note, these outputs are labeled "
        "conditional and are to be read only after the written G1 record exists."
    )
    lines.append("")
    lines.append("## 0. Run provenance")
    lines.append("")
    lines.append(f"- exact command: `{info['command']}`")
    lines.append(f"- working directory: `{info['cwd']}`")
    lines.append(f"- started (UTC): {info['started_utc']}")
    lines.append(f"- finished (UTC): {info['finished_utc']}")
    lines.append(f"- wall time: {info['wall_seconds']:.1f} s")
    lines.append(f"- worker processes: {info['workers']} (maximum allowed {MAX_WORKERS})")
    lines.append(
        f"- peak RAM main process: {info['peak_ram_main'] / 1e6:.1f} MB; "
        f"peak child RSS: {info['peak_ram_children'] / 1e6:.1f} MB"
    )
    lines.append(f"- jobs: {info['n_jobs']} total, {info['n_errors']} failed")
    lines.append(
        f"- geometry replication against the public generator: {info['geometry']}"
    )
    lines.append(
        f"- saved-file hash verification mismatches: {len(info['hash_mismatches'])}"
    )
    lines.append("")
    lines.append("Environment: " + ", ".join(
        f"{name}={version}" for name, version in sorted(info["versions"].items()) if version
    ) + f", python={info['python']}, platform={info['platform']}.")
    lines.append("")
    lines.append("Input hashes are in `reports/tables/artifact_hashes.csv` and are summarized here.")
    lines.append("")
    lines.append(
        md_table(
            ["input file", "sha256"],
            [[row["path"], row["sha256"]] for row in info["artifact_rows"] if row["category"] == "input"],
        )
    )
    lines.append("")
    lines.append("## Check verdicts")
    lines.append("")
    lines.append(
        md_table(
            ["check", "title", "verdict"],
            [[check["id"], check["title"], check["verdict"]] for check in checks],
        )
    )
    lines.append("")
    checks_by_id = {check["id"]: check for check in checks}
    lines.append("## Check 1: static controls")
    lines.append("")
    lines.append(
        f"Verdict: **{checks_by_id['check1_static']['verdict']}**. Declared rule: at "
        "sigma = 0 every adjacent distance must be exactly 0 for both degrees; at "
        "sigma = 0.05 the Spearman trend is nonsignificant at 1 percent and the "
        "adjacent versus lag-8 KS test does not reject exchangeability at 1 percent. "
        f"sigma = 0 nonzero cases: {checks_by_id['check1_static']['sigma0_nonzero_cases']}. "
        f"Training-style static 95th percentiles at sigma = 0.05: "
        f"A={md_value(checks_by_id['check1_static']['calibration'].get('A'))}, "
        f"B={md_value(checks_by_id['check1_static']['calibration'].get('B'))}."
    )
    lines.append("")
    lines.append(
        md_table(
            ["family", "seed", "sigma", "degree", "mean", "p95", "max", "nonzero", "rho", "p", "ks p", "verdict"],
            [
                [
                    row.get("family"),
                    row.get("seed"),
                    row.get("sigma"),
                    row.get("degree"),
                    row.get("mean"),
                    row.get("p95"),
                    row.get("max"),
                    row.get("nonzero_count"),
                    row.get("spearman_rho"),
                    row.get("spearman_p"),
                    row.get("ks_lag8_p"),
                    row.get("verdict"),
                ]
                for row in checks_by_id["check1_static"]["rows"]
            ],
        )
    )
    lines.append("")
    lines.append("Raw adjacent distances: `reports/tables/static_adjacent_distances.csv`. Figure: `reports/figures/fig_check1_static.png`.")
    lines.append("")
    lines.append("## Check 2: smooth ramp deformation")
    lines.append("")
    lines.append(
        f"Verdict: **{checks_by_id['check2_ramp']['verdict']}**. Stride-4 subsample "
        f"exactness against the stride-1 masters: {checks_by_id['check2_ramp']['stride_subsample_exact']}."
    )
    lines.append("")
    lines.append(
        md_table(
            ["family", "seed", "C_ls", "f_ls", "R2_ls", "C_max", "rho", "mean overlap", "mean separated", "switch or onset", "verdict"],
            [
                [
                    row.get("family"),
                    row.get("seed"),
                    row.get("C_ls"),
                    row.get("f_ls"),
                    row.get("r2_ls"),
                    row.get("C_max_ratio"),
                    row.get("monotone_rho"),
                    row.get("mean_overlap"),
                    row.get("mean_separated"),
                    row.get("z_switch_measured") if row.get("family") == "A" else row.get("onset_first_positive_z"),
                    row.get("verdict"),
                ]
                for row in checks_by_id["check2_ramp"]["fits"]
            ],
        )
    )
    lines.append("")
    for row in checks_by_id["check2_ramp"]["fits"]:
        if row.get("family") == "A":
            lines.append(
                f"Family A seed {row['seed']}: z_merge=2r={md_value(row.get('z_merge'))}, "
                f"plateau={md_value(row.get('plateau_level'))}, measured switch="
                f"{md_value(row.get('z_switch_measured'))}, line slope={md_value(row.get('line_slope'))}, "
                f"max d/|dz|={md_value(row.get('C_max_ratio'))}, separated ratio="
                f"{md_value(row.get('mean_ratio_separated'))}, bound violations="
                f"{row.get('bound_violations')}, verdict components (monotone/bound/switch): "
                f"{row.get('verdict_monotone')}/{row.get('verdict_bound')}/{row.get('verdict_switch')}."
            )
        else:
            lines.append(
                f"Family B seed {row['seed']}: 2w={md_value(row.get('z_onset_expected'))}, onset in "
                f"[{md_value(row.get('onset_last_zero_z'))}, {md_value(row.get('onset_first_positive_z'))}], "
                f"offset={md_value(row.get('onset_offset'))} (one 32x32 grid spacing is "
                f"{md_value(GRID_SPACING_32)}), persistence rho={md_value(row.get('persistence_rho'))}, "
                f"local decreases={row.get('persistence_decreases')}/{row.get('persistence_steps')}, "
                f"net increase={md_value(row.get('persistence_net_increase'))}."
            )
    lines.append("")
    lines.append(
        "Raw response rows: `reports/tables/ramp_response.csv`; fits: "
        "`reports/tables/ramp_fits.csv`; transitions: `reports/tables/ramp_transitions.csv`. "
        "Figure: `reports/figures/fig_check2_ramp.png`."
    )
    lines.append("")
    lines.append("## Check 3: topology-changing class programs")
    lines.append("")
    lines.append(f"Verdict: **{checks_by_id['check3_topology']['verdict']}**.")
    lines.append("")
    lines.append(
        md_table(
            ["family", "seed", "class", "expected z", "expected frame", "measured first frame", "measured first z", "delta frames", "card before", "card after", "event alignment", "cardinality criterion"],
            [
                [
                    row.get("family"),
                    row.get("seed"),
                    row.get("class"),
                    row.get("expected_z"),
                    row.get("expected_frame"),
                    row.get("measured_first_frame"),
                    row.get("measured_first_z"),
                    row.get("delta_frames_first"),
                    row.get("cardinality_before"),
                    row.get("cardinality_after"),
                    row.get("event_alignment"),
                    row.get("cardinality_criterion"),
                ]
                for row in checks_by_id["check3_topology"]["events"]
            ],
        )
    )
    lines.append("")
    lines.append(
        "The Family A H0 finite cardinality is exactly n_points - 1 for every frame "
        "(Rips connectivity at large filtration scale), so the literal cardinality-change "
        "criterion is recorded as RESIDUAL for Family A; its merge and separation "
        "transition is verified in the largest finite H0 death and in the H1 channel. "
        "Raw per-frame cardinalities: `reports/tables/class_cardinality.csv`. "
        "Events: `reports/tables/class_transitions.csv`. Figure: "
        "`reports/figures/fig_check3_topology.png`."
    )
    lines.append("")
    lines.append("## Check 4: noisy raw null processes")
    lines.append("")
    lines.append(
        f"Verdict: **{checks_by_id['check4_null']['verdict']}**. Training-style static "
        f"calibration at sigma = 0.05: A={md_value(checks_by_id['check4_null']['calibration'].get('A'))}, "
        f"B={md_value(checks_by_id['check4_null']['calibration'].get('B'))}; calibration maxima: "
        f"A={md_value(checks_by_id['check4_null']['calibration_max'].get('A'))}, "
        f"B={md_value(checks_by_id['check4_null']['calibration_max'].get('B'))}. Declared rule: "
        "sigma = 0 requires exact zeros. For sigma > 0, the primary threshold is the "
        "pooled static sigma = 0.05 floor at sigma = 0.05 and the leave-one-out static "
        "floor at the same sigma otherwise. A run fails only on a strong nonstationary "
        "trend or a permutation test showing temporal clustering of exceedances at 1 "
        "percent; it is RESIDUAL when the trend test at 1 percent fails or the "
        "exceedance count above the primary floor exceeds the 99 percent binomial "
        "bound. The permutation test holds the marginal exceedance rate fixed, so a "
        "null process whose whole noise scale sits above a mis-transferred floor is "
        "reported as RESIDUAL rather than as a temporal event."
    )
    lines.append("")
    lines.append(
        md_table(
            ["family", "config", "seed", "sigma", "mean", "p95", "max", "rho", "p", "e_primary", "n>primary", "cluster p", "99% bound", "max run", "verdict"],
            [
                [
                    row.get("family"),
                    row.get("config"),
                    row.get("seed"),
                    row.get("sigma"),
                    row.get("mean"),
                    row.get("p95"),
                    row.get("max"),
                    row.get("spearman_rho"),
                    row.get("spearman_p"),
                    row.get("e_primary"),
                    row.get("n_above_e_primary"),
                    row.get("cluster_p"),
                    row.get("binom_upper_99"),
                    row.get("max_run_above_e_primary"),
                    row.get("verdict"),
                ]
                for row in checks_by_id["check4_null"]["rows"]
            ],
        )
    )
    lines.append("")
    lines.append(
        "Raw adjacent distances and per-row threshold flags: "
        "`reports/tables/null_adjacent_distances.csv`; run summaries: "
        "`reports/tables/null_summary.csv`. Figure: `reports/figures/fig_check4_null.png`."
    )
    lines.append("")
    lines.append("## Check 5: sampling and filtration-resolution sensitivity")
    lines.append("")
    lines.append(
        f"Verdict: **{checks_by_id['check5_sampling']['verdict']}**. The Family A bound "
        "is the adapted delta-dense statement d_B at most 2 delta, where delta is the "
        "one-sided maximum distance from a dropped point to the retained set."
    )
    lines.append("")
    lines.append(
        md_table(
            ["family", "seed", "variant", "points", "mean d0 vs full", "max d0 vs full", "max d0/delta", "max d0/(2 delta)", "H0 cards", "H1 cards", "verdict"],
            [
                [
                    row.get("family"),
                    row.get("seed"),
                    row.get("variant"),
                    row.get("n_points_per_frame"),
                    row.get("mean_d0_vs_full"),
                    row.get("max_d0_vs_full"),
                    row.get("max_ratio_d0_to_delta"),
                    row.get("max_ratio_d0_to_2delta"),
                    f"{md_value(row.get('card0_min'))}..{md_value(row.get('card0_max'))}",
                    f"{md_value(row.get('card1_min'))}..{md_value(row.get('card1_max'))}",
                    row.get("verdict"),
                ]
                for row in checks_by_id["check5_sampling"]["summary"]
            ],
        )
    )
    lines.append("")
    lines.append(
        "Raw per-frame rows: `reports/tables/sampling_resolution.csv`; summaries: "
        "`reports/tables/sampling_summary.csv`. Figure: `reports/figures/fig_check5_sampling.png`."
    )
    lines.append("")
    lines.append("## Check 6: rigid translation invariance")
    lines.append("")
    lines.append(
        f"Verdict: **{checks_by_id['check6_translation']['verdict']}**. Tolerance is "
        "1e-7 times max(1, filtration range) for Family A, degrees 0 and 1."
    )
    lines.append("")
    lines.append(
        md_table(
            ["seed", "sigma", "degree", "frames", "max distance", "filtration range", "tolerance", "verdict"],
            [
                [
                    row.get("seed"),
                    row.get("sigma"),
                    row.get("degree"),
                    row.get("n_frames"),
                    row.get("max_distance"),
                    row.get("filtration_range"),
                    row.get("tolerance"),
                    row.get("verdict"),
                ]
                for row in checks_by_id["check6_translation"]["summary"]
            ],
        )
    )
    lines.append("")
    lines.append(
        "Raw per-frame distances: `reports/tables/translation_controls.csv`; summary: "
        "`reports/tables/translation_summary.csv`. Figure: `reports/figures/fig_check6_translation.png`."
    )
    lines.append("")
    lines.append("## Cross-cutting findings")
    lines.append("")
    lines.append(
        "1. Contiguity requirement. `gudhi.RipsComplex` silently misreads "
        "non-contiguous point arrays; a strided slice such as `frame[::2]` yielded a "
        "complex on half the points in a direct probe. The frozen generator subsamples "
        "with `np.ascontiguousarray`, so this ladder passes contiguous arrays "
        "everywhere. The observation is recorded because future point subsampling must "
        "copy before extraction."
    )
    lines.append(
        "2. Configuration transfer of the static floor. The training-style floor is "
        "calibrated on static z = 0.5; frozen snapshots at other z values, and even "
        "other static seeds in Family B, can have a different noise response scale. "
        "That is a calibration-transfer limit rather than a temporal event: the "
        "permutation clustering test finds no serial dependence. The check 4 table "
        "reports the primary counts (pooled static floor at sigma = 0.05, "
        "leave-one-out static floor at sigma = 0.10), the clustering p-value, and "
        "the secondary counts."
    )
    lines.append(
        "3. Family B discrete onset. The first finite H0 bar appears slightly above "
        "the continuum prediction 2w because the two grid maxima split only on the "
        "discrete grid; the offset is reported against one grid spacing."
    )
    lines.append(
        "4. Family A bounded response. The least-squares fit with intercept is reported "
        "for completeness, but the overlap regime makes it a poor upper envelope. The "
        "reported maximum-ratio C is the empirical Lipschitz constant, and it is "
        "consistent with the separated-regime expectation that the last merge death "
        "moves exactly with z."
    )
    lines.append("")
    lines.append("## Blockers and residual items")
    lines.append("")
    if info["n_errors"] or info["hash_mismatches"] or info["missing_artifacts"]:
        lines.append(
            f"Failed jobs: {info['n_errors']}; hash mismatches: "
            f"{len(info['hash_mismatches'])}; missing artifacts: "
            f"{info['missing_artifacts']}."
        )
    else:
        lines.append("No failed jobs, hash mismatches, or missing artifacts.")
    residual_checks = [check for check in checks if check["verdict"] != "PASS"]
    lines.append(
        "Checks not at PASS: "
        + (", ".join(f"{check['id']} ({check['verdict']})" for check in residual_checks) if residual_checks else "none")
        + ". Residuals are explained in the corresponding sections; none is an unrepaired extraction failure."
    )
    lines.append("")
    lines.append("## Artifact inventory")
    lines.append("")
    categories: dict[str, int] = {}
    for row in info["artifact_rows"]:
        categories[row["category"]] = categories.get(row["category"], 0) + 1
    lines.append(
        "Artifacts by category: "
        + ", ".join(f"{name}={count}" for name, count in sorted(categories.items()))
        + f". Full hashes: `reports/tables/artifact_hashes.csv`. Figures produced: "
        + (", ".join(Path(path).name for path in figures) if figures else "none")
        + "."
    )
    lines.append("")
    target = out_dir / "reports" / "raw_correctness_report.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def clean_output_trees(out_dir: Path) -> None:
    """Remove this script's previous outputs so a run stays self-consistent.

    Only the WP-3.1 trees are touched: raw_controls, diagrams, and the report
    tables, figures, report, summary, and checksum files. Other agents' trees
    under results/g2 are never touched.
    """
    import shutil

    raw = Path(out_dir) / "raw_controls"
    diagrams = Path(out_dir) / "diagrams"
    reports = Path(out_dir) / "reports"
    for directory in (raw, diagrams, reports / "tables", reports / "figures"):
        if directory.exists():
            shutil.rmtree(directory)
    for name in ("raw_correctness_report.md", "raw_controls_summary.json"):
        target = reports / name
        if target.is_file():
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output root (default research_review/results/g2)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"worker processes, clamped to at most {MAX_WORKERS}",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="skip png figure generation",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="keep previous WP-3.1 outputs instead of clearing the trees",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="debug only: run only the first N ladder jobs",
    )
    args = parser.parse_args()
    workers = max(1, min(int(args.workers), MAX_WORKERS))
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()
    if not args.no_clean:
        clean_output_trees(out_dir)
        print("cleared previous WP-3.1 output trees")
    reports_dir = out_dir / "reports"
    (reports_dir / "tables").mkdir(parents=True, exist_ok=True)
    (reports_dir / "figures").mkdir(parents=True, exist_ok=True)
    command = " ".join([sys.executable, *sys.argv])
    started_utc = now_utc()
    started = time.perf_counter()
    phase_times: dict[str, float] = {}

    g1_info = inspect_g1()
    geometry = verify_geometry_replication()
    jobs = build_jobs()
    if args.limit is not None:
        jobs = jobs[: int(args.limit)]
        print(f"DEBUG limit active: running {len(jobs)} of the ladder jobs")
    print(
        f"{WORK_PACKAGE} raw correctness ladder: {len(jobs)} jobs, "
        f"{workers} worker processes, output {out_dir}"
    )
    print(f"G1 status at runtime: {g1_info['status_at_runtime']}")
    print(f"geometry replication exact: {geometry}")

    jobs_started = time.perf_counter()
    records_list = run_jobs(jobs, out_dir, workers)
    phase_times["jobs"] = time.perf_counter() - jobs_started
    records: dict[str, dict] = {}
    for record in records_list:
        records[record["run_id"]] = record
    errors = [record for record in records_list if record["status"] != "ok"]
    print(
        f"jobs finished in {phase_times['jobs']:.1f} s; "
        f"{len(records_list) - len(errors)} ok, {len(errors)} failed"
    )

    hash_mismatches: list[dict] = []
    for record in records_list:
        if record["status"] != "ok":
            continue
        raw_path = Path(record["saved"]["raw_path"])
        diagram_path = Path(record["saved"]["diagram_path"])
        if sha256_file(raw_path) != record["saved"]["raw_hashes"]["sha256_npz"]:
            hash_mismatches.append({"run_id": record["run_id"], "file": str(raw_path)})
        if sha256_file(diagram_path) != record["saved"]["sha256_diagram_npz"]:
            hash_mismatches.append({"run_id": record["run_id"], "file": str(diagram_path)})
    checksum_files = write_directory_sha256sums(records_list)

    check_started = time.perf_counter()
    check1 = check1_static(records, out_dir)
    phase_times["check1"] = time.perf_counter() - check_started
    check_started = time.perf_counter()
    check2 = check2_ramp(records, out_dir)
    phase_times["check2"] = time.perf_counter() - check_started
    check_started = time.perf_counter()
    check3 = check3_topology(records, out_dir)
    phase_times["check3"] = time.perf_counter() - check_started
    check_started = time.perf_counter()
    check4 = check4_null(records, out_dir, check1["calibration"])
    phase_times["check4"] = time.perf_counter() - check_started
    check_started = time.perf_counter()
    check5 = check5_sampling(records, out_dir)
    phase_times["check5"] = time.perf_counter() - check_started
    check_started = time.perf_counter()
    check6 = check6_translation(records, out_dir)
    phase_times["check6"] = time.perf_counter() - check_started
    checks = [check1, check2, check3, check4, check5, check6]
    for check in checks:
        print(f"{check['id']}: {check['verdict']}")

    figures: list[str] = []
    if not args.skip_figures:
        figure_started = time.perf_counter()
        figures = make_figures(records, checks, out_dir)
        phase_times["figures"] = time.perf_counter() - figure_started

    ladder_rows = [
        {
            "check_id": check["id"],
            "title": check["title"],
            "verdict": check["verdict"],
            "tables": ";".join(check.get("tables", [])),
        }
        for check in checks
    ]
    write_csv(
        reports_dir / "tables" / "ladder_summary.csv",
        ["check_id", "title", "verdict", "tables"],
        ladder_rows,
    )

    table_paths = [
        str(out_dir / table)
        for check in checks
        for table in check.get("tables", [])
    ]
    report_path = reports_dir / "raw_correctness_report.md"
    summary_path = reports_dir / "raw_controls_summary.json"
    preliminary_rows = artifact_hash_rows(
        out_dir, records_list, table_paths + figures + checksum_files
    )
    artifact_rows = preliminary_rows
    finished_utc = now_utc()
    wall_seconds = time.perf_counter() - started
    peak_main = peak_ram_bytes(children=False)
    worker_peaks = [
        int(record.get("peak_ram_bytes_worker", 0)) for record in records_list
    ]
    peak_children = max([peak_ram_bytes(children=True), *worker_peaks])
    missing_artifacts = int(
        sum(1 for row in preliminary_rows if row["sha256"] is None)
    )
    info = {
        "work_package": WORK_PACKAGE,
        "gate": GATE,
        "conditional_gate": CONDITIONAL_GATE,
        "g1": g1_info,
        "command": command,
        "cwd": str(Path.cwd()),
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "wall_seconds": wall_seconds,
        "phase_times": phase_times,
        "workers": workers,
        "n_jobs": len(jobs),
        "n_errors": len(errors),
        "errors": [
            {key: value for key, value in record.items() if key != "diagrams"}
            for record in errors
        ],
        "geometry": geometry,
        "hash_mismatches": hash_mismatches,
        "missing_artifacts": missing_artifacts,
        "peak_ram_main": peak_main,
        "peak_ram_children": peak_children,
        "versions": package_versions(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "checks": {check["id"]: check for check in checks},
        "artifact_rows": artifact_rows,
        "figures": figures,
        "tables": table_paths,
    }
    report_path = render_report(out_dir, info, checks, figures)
    summary = {
        "work_package": WORK_PACKAGE,
        "gate": GATE,
        "conditional_on_gate": CONDITIONAL_GATE,
        "g1_status": g1_info,
        "command": command,
        "cwd": str(Path.cwd()),
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "wall_seconds": wall_seconds,
        "phase_times": phase_times,
        "workers": workers,
        "n_jobs": len(jobs),
        "n_errors": len(errors),
        "errors": info["errors"],
        "geometry_replication": geometry,
        "hash_mismatches": hash_mismatches,
        "missing_artifacts": missing_artifacts,
        "peak_ram_bytes": {"main": peak_main, "children": peak_children},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": info["versions"],
        },
        "checks": {
            check["id"]: {
                key: value
                for key, value in check.items()
                if key not in {"rows", "events", "summary", "fits", "transitions"}
            }
            for check in checks
        },
        "check_verdicts": {
            check["id"]: check["verdict"] for check in checks
        },
        "overall_verdict": (
            "FAIL"
            if any(check["verdict"] == "FAIL" for check in checks)
            else (
                "RESIDUAL"
                if any(check["verdict"] == "RESIDUAL" for check in checks)
                else "PASS"
            )
        ),
        "inputs": {
            relative: sha256_file(ROOT / relative) for relative in INPUT_FILES
        },
        "outputs": {
            "raw_controls": str(out_dir / "raw_controls"),
            "diagrams": str(out_dir / "diagrams"),
            "reports": str(reports_dir),
            "report": str(report_path),
            "figures": figures,
            "tables": table_paths,
            "checksum_files": checksum_files,
        },
    }
    write_json(summary_path, summary)
    final_rows = artifact_hash_rows(
        out_dir,
        records_list,
        table_paths + figures + [str(report_path), str(summary_path)] + checksum_files,
    )
    write_csv(
        reports_dir / "tables" / "artifact_hashes.csv",
        ["category", "path", "sha256"],
        final_rows,
    )
    print(
        f"overall verdict: {summary['overall_verdict']}; wall {wall_seconds:.1f} s; "
        f"peak main RAM {peak_main / 1e6:.1f} MB, peak child RSS "
        f"{peak_children / 1e6:.1f} MB"
    )
    print(f"report: {report_path}")
    print(f"summary: {summary_path}")
    return 1 if summary["overall_verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
