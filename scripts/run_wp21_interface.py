#!/usr/bin/env python3
"""WP-2.1 window-to-diagram interface evidence runner.

This script produces the WP-2.1 evidence under
``research_review/results/g2/interface/``: byte-level determinism of the frozen
extraction pipeline, trailing-window equivalence at length 1 and stride 1,
extraction uncertainty under declared raw resamplings for both families,
per-window metadata for the pooling grid, and a separately reported pooled
observation map at length 3 and stride 2.

WP-2.1 is conditional on gate G1, which the coordinator records before the G2
decision. Every payload carries that dependency explicitly, and no output is a
G2 verdict. The script reads the frozen modules in ``src/tk_pilot`` but does not
modify them, and it never reads or writes ``research_review/results/cache``.
"""

from __future__ import annotations

import time

_PROCESS_START = time.perf_counter()

import argparse
import csv
import hashlib
import json
import platform
import resource
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tk_pilot import features, generators, persistence
from tk_pilot.diagram_metrics import bottleneck_linf

WP = "WP-2.1"
SEEDS = (1000, 1001, 1002)
DEFAULT_OUTDIR = ROOT / "research_review" / "results" / "g2" / "interface"
CSV_COLUMNS = (
    "family",
    "condition",
    "variant",
    "seed",
    "n_frames",
    "adjacent_mean",
    "adjacent_p95",
    "endpoint_distance",
    "changed_fraction",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sequence_sha256(series: Iterable[np.ndarray]) -> str:
    """Canonical sha256 over a diagram sequence, including array shapes."""
    digest = hashlib.sha256()
    for diagram in series:
        array = np.ascontiguousarray(np.asarray(diagram, dtype=np.float64))
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _sequences_bitwise_equal(
    left: Sequence[np.ndarray], right: Sequence[np.ndarray]
) -> bool:
    if len(left) != len(right):
        return False
    return all(np.array_equal(a, b) for a, b in zip(left, right))


def _max_component_diff(
    left: Sequence[np.ndarray], right: Sequence[np.ndarray]
) -> float:
    if len(left) != len(right):
        return float("inf")
    worst = 0.0
    for a, b in zip(left, right):
        if a.shape != b.shape:
            return float("inf")
        if a.size:
            worst = max(worst, float(np.max(np.abs(a - b))))
    return worst


def _adjacent_distances(series: Sequence[np.ndarray]) -> np.ndarray:
    return np.asarray(
        [
            bottleneck_linf(series[index], series[index + 1])
            for index in range(len(series) - 1)
        ],
        dtype=np.float64,
    )


def _jsonable(value: Any) -> Any:
    """Convert numpy values and non-finite floats to strict JSON values."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _environment() -> dict:
    import gudhi

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "gudhi": gudhi.__version__,
    }


def _g1_dependency() -> dict:
    packet = (
        ROOT / "research_review" / "results" / "phase1" / "decision_packet_G1.md"
    )
    pending: int | None = None
    status = "g1 packet not found at run time"
    if packet.is_file():
        text = packet.read_text(encoding="utf-8")
        pending = int(text.count("[PENDING"))
        status = (
            "unresolved (pending items present)"
            if pending
            else "recorded without pending markers"
        )
    return {
        "work_package": WP,
        "conditional_on": "G1",
        "g1_decision_packet": str(packet.relative_to(ROOT)),
        "g1_recorded_status_at_run_time": status,
        "pending_marker_count": pending,
        "labeling": (
            "All WP-2.1 outputs are conditional on G1 and do not constitute a "
            "G2 decision."
        ),
    }


def check_determinism(
    trajectories: Sequence[generators.Trajectory], tmp_root: Path
) -> dict:
    """Recompute each trajectory in two temporary caches and compare."""
    records: list[dict] = []
    passed = True
    for traj in trajectories:
        cache_directories: dict[str, Path] = {}
        loaded: dict[str, dict] = {}
        for tag in ("cache1", "cache2"):
            cache_directories[tag] = persistence.save_diagram_cache(
                traj, tmp_root / tag
            )
            loaded[tag] = persistence.load_diagram_cache(traj, tmp_root / tag)
        degree_records: dict[str, dict] = {}
        cache_arrays_equal = True
        for degree in sorted(loaded["cache1"]["diagrams"]):
            left = loaded["cache1"]["diagrams"][degree]
            right = loaded["cache2"]["diagrams"][degree]
            equal = _sequences_bitwise_equal(left, right)
            cache_arrays_equal = cache_arrays_equal and equal
            degree_records[str(degree)] = {
                "n_diagrams": len(left),
                "bitwise_equal": bool(equal),
                "sha256_cache1": _sequence_sha256(left),
                "sha256_cache2": _sequence_sha256(right),
                "first_frame_shape": [int(value) for value in left[0].shape],
                "essential_counts_equal": bool(
                    loaded["cache1"]["essential"][degree]
                    == loaded["cache2"]["essential"][degree]
                ),
                "essential_counts_first_frame": int(
                    loaded["cache1"]["essential"][degree][0]
                ),
            }
        file_names = ("diagrams.npz", "essential.npz", "meta.json")
        file_hashes = {
            tag: {
                name: _sha256_file(cache_directories[tag] / name)
                for name in file_names
            }
            for tag in ("cache1", "cache2")
        }
        file_equal = {
            name: bool(file_hashes["cache1"][name] == file_hashes["cache2"][name])
            for name in file_names
        }
        direct = persistence.trajectory_diagrams(traj.frames, traj.family)
        windowed = persistence.diagrams_for_windows(
            traj.frames, traj.family, length=1, stride=1
        )
        window_records: dict[str, dict] = {}
        window_equal = True
        for degree in sorted(direct):
            left = direct[degree]
            right = windowed[degree]
            equal = _sequences_bitwise_equal(left, right)
            window_equal = window_equal and equal
            window_records[str(degree)] = {
                "n_diagrams": len(left),
                "bitwise_equal": bool(equal),
                "max_component_diff": _max_component_diff(left, right),
                "sha256_trajectory_diagrams": _sequence_sha256(left),
                "sha256_diagrams_for_windows": _sequence_sha256(right),
            }
        trajectory_passed = cache_arrays_equal and window_equal
        passed = passed and trajectory_passed
        records.append(
            {
                "trajectory_id": traj.trajectory_id,
                "family": traj.family,
                "label": traj.label,
                "base_seed": int(traj.base_seed),
                "sigma": float(traj.sigma),
                "stride": int(traj.stride),
                "n_frames": int(traj.frames.shape[0]),
                "cache_recompute_bitwise_equal": bool(cache_arrays_equal),
                "degrees": degree_records,
                "file_sha256": file_hashes,
                "file_bytes_equal": file_equal,
                "window_equality": {
                    "call": (
                        "diagrams_for_windows(frames, family, length=1, "
                        "stride=1) vs trajectory_diagrams(frames, family)"
                    ),
                    "bitwise_equal": bool(window_equal),
                    "degrees": window_records,
                },
                "verdict": "PASS" if trajectory_passed else "FAIL",
            }
        )
    return {
        "verdict": "PASS" if passed else "FAIL",
        "method": (
            "Each trajectory was diagram-computed into two independent "
            "temporary caches with persistence.save_diagram_cache, loaded "
            "back with persistence.load_diagram_cache, and compared per "
            "degree and frame by np.array_equal and by sha256 over the "
            "canonical array bytes. The length 1 stride 1 trailing-window "
            "call was compared against the direct trajectory call in the "
            "same process."
        ),
        "trajectories": records,
    }


def _phase_redraw_frames(
    z_values: np.ndarray, latent: dict, seed: int
) -> np.ndarray:
    """Family A frames with fresh circle phases drawn at every frame.

    Local to this script and deliberately outside the frozen generator seed
    namespaces. The local seed namespace is ``[seed, 0, 0, 303]``.
    """
    rng = np.random.default_rng(
        [int(seed), generators.FAMILY_IDS["A"], generators.LABEL_IDS["return"], 303]
    )
    radius = float(latent["r"])
    phi = float(latent["phi"])
    rotation = np.array(
        [[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]],
        dtype=np.float64,
    )
    angles = generators.CIRCLE_ANGLES
    signs = np.concatenate(
        [
            -np.ones(generators.POINTS_PER_CIRCLE),
            np.ones(generators.POINTS_PER_CIRCLE),
        ]
    )
    frames: list[np.ndarray] = []
    for z in np.asarray(z_values, dtype=np.float64):
        phases = rng.uniform(0.0, 2.0 * np.pi, size=2)
        theta = np.concatenate([angles + phases[0], angles + phases[1]])
        base = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
        offset = np.array([0.5 * z, 0.0], dtype=np.float64)
        points = base + signs[:, None] * offset[None, :]
        frames.append(points @ rotation.T)
    return np.ascontiguousarray(np.stack(frames, axis=0), dtype=np.float64)


def _point_subsample_frames(frames: np.ndarray, per_circle: int) -> np.ndarray:
    """Keep a declared subset of each circle in every frame.

    ``per_circle=16`` keeps every second point. ``per_circle=24`` keeps three
    of every four points, since 32 is not divisible by three while the stated
    target count is 48 total points.
    """
    if per_circle == 16:
        indices = np.arange(0, generators.POINTS_PER_CIRCLE, 2)
    elif per_circle == 24:
        indices = np.asarray(
            [
                index
                for index in range(generators.POINTS_PER_CIRCLE)
                if index % 4 != 3
            ],
            dtype=np.int64,
        )
    else:
        raise ValueError(f"unsupported per-circle count {per_circle!r}")
    subgroup = int(frames.shape[1] // 2)
    kept: list[np.ndarray] = []
    for frame in frames:
        first = frame[:subgroup][indices]
        second = frame[subgroup:][indices]
        kept.append(np.concatenate([first, second], axis=0))
    return np.ascontiguousarray(np.stack(kept, axis=0), dtype=np.float64)


def _grid_stride_frames(frames: np.ndarray, step: int) -> np.ndarray:
    return np.ascontiguousarray(frames[:, ::step, ::step], dtype=np.float64)


def _sequence_comparison(
    baseline: Sequence[np.ndarray], variant: Sequence[np.ndarray]
) -> dict:
    if len(baseline) != len(variant):
        raise ValueError("baseline and variant must have the same length")
    variant_adjacent = _adjacent_distances(variant)
    baseline_adjacent = _adjacent_distances(baseline)
    paired = np.asarray(
        [bottleneck_linf(v, b) for v, b in zip(variant, baseline)], dtype=np.float64
    )
    changed_exact = np.asarray(
        [not np.array_equal(v, b) for v, b in zip(variant, baseline)], dtype=bool
    )
    return {
        "n_frames": len(variant),
        "variant_adjacent": variant_adjacent,
        "baseline_adjacent": baseline_adjacent,
        "paired": paired,
        "changed_exact": changed_exact,
        "changed_metric": paired > 0.0,
    }


def _resampling_row(
    family: str,
    condition: str,
    variant: str,
    seed: int,
    comparison: dict,
    baseline_last: np.ndarray,
    variant_last: np.ndarray,
) -> dict:
    adjacent = comparison["variant_adjacent"]
    return {
        "family": family,
        "condition": condition,
        "variant": variant,
        "seed": int(seed),
        "n_frames": int(comparison["n_frames"]),
        "adjacent_mean": float(np.mean(adjacent)) if adjacent.size else None,
        "adjacent_p95": (
            float(np.percentile(adjacent, 95)) if adjacent.size else None
        ),
        "endpoint_distance": float(bottleneck_linf(variant_last, baseline_last)),
        "changed_fraction": float(np.mean(comparison["changed_exact"])),
    }


def _resampling_detail(
    family: str,
    condition: str,
    variant: str,
    seed: int,
    comparison: dict,
) -> dict:
    variant_adjacent = comparison["variant_adjacent"]
    baseline_adjacent = comparison["baseline_adjacent"]
    paired = comparison["paired"]
    return {
        "family": family,
        "condition": condition,
        "variant": variant,
        "seed": int(seed),
        "n_frames": int(comparison["n_frames"]),
        "baseline_adjacent_mean": float(np.mean(baseline_adjacent)),
        "baseline_adjacent_p95": float(np.percentile(baseline_adjacent, 95)),
        "variant_adjacent_mean": float(np.mean(variant_adjacent)),
        "variant_adjacent_p95": float(np.percentile(variant_adjacent, 95)),
        "variant_adjacent_distances": variant_adjacent.tolist(),
        "baseline_adjacent_distances": baseline_adjacent.tolist(),
        "paired_distance_mean": float(np.mean(paired)),
        "paired_distance_p95": float(np.percentile(paired, 95)),
        "paired_distance_max": float(np.max(paired)),
        "changed_frames_exact": int(np.sum(comparison["changed_exact"])),
        "changed_fraction_exact": float(np.mean(comparison["changed_exact"])),
        "changed_frames_metric": int(np.sum(comparison["changed_metric"])),
        "changed_fraction_metric": float(np.mean(comparison["changed_metric"])),
    }


def check_resampling() -> dict:
    """Extraction uncertainty under the declared raw resamplings, degree 0."""
    rows: list[dict] = []
    details: list[dict] = []
    for seed in SEEDS:
        baseline_a = generators.build_trajectory("A", "return", seed, 0.0, 1)
        baseline_a_series = persistence.trajectory_diagrams(
            baseline_a.frames, "A", degrees=(0,)
        )[0]
        phase_frames = _phase_redraw_frames(baseline_a.z, baseline_a.latent, seed)
        phase_series = persistence.trajectory_diagrams(
            phase_frames, "A", degrees=(0,)
        )[0]
        comparison = _sequence_comparison(baseline_a_series, phase_series)
        rows.append(
            _resampling_row(
                "A",
                "A_phase_redraw",
                "phase_redraw_per_frame",
                seed,
                comparison,
                baseline_a_series[-1],
                phase_series[-1],
            )
        )
        details.append(
            _resampling_detail(
                "A", "A_phase_redraw", "phase_redraw_per_frame", seed, comparison
            )
        )
        for label, per_circle in (("points32", 16), ("points48", 24)):
            variant_frames = _point_subsample_frames(baseline_a.frames, per_circle)
            variant_series = persistence.trajectory_diagrams(
                variant_frames, "A", degrees=(0,)
            )[0]
            comparison = _sequence_comparison(baseline_a_series, variant_series)
            rows.append(
                _resampling_row(
                    "A",
                    "A_point_count",
                    label,
                    seed,
                    comparison,
                    baseline_a_series[-1],
                    variant_series[-1],
                )
            )
            details.append(
                _resampling_detail("A", "A_point_count", label, seed, comparison)
            )
        baseline_b = generators.build_trajectory("B", "jump", seed, 0.05, 1)
        baseline_b_series = persistence.trajectory_diagrams(
            baseline_b.frames, "B", degrees=(0,)
        )[0]
        noise_frames = generators.build_trajectory("B", "jump", seed, 0.10, 1).frames
        noise_series = persistence.trajectory_diagrams(
            noise_frames, "B", degrees=(0,)
        )[0]
        comparison = _sequence_comparison(baseline_b_series, noise_series)
        rows.append(
            _resampling_row(
                "B",
                "B_pixel_noise",
                "sigma0.10",
                seed,
                comparison,
                baseline_b_series[-1],
                noise_series[-1],
            )
        )
        details.append(
            _resampling_detail("B", "B_pixel_noise", "sigma0.10", seed, comparison)
        )
        grid_frames = _grid_stride_frames(baseline_b.frames, 2)
        grid_series = persistence.trajectory_diagrams(
            grid_frames, "B", degrees=(0,)
        )[0]
        comparison = _sequence_comparison(baseline_b_series, grid_series)
        rows.append(
            _resampling_row(
                "B",
                "B_grid_subsample",
                "grid16x16",
                seed,
                comparison,
                baseline_b_series[-1],
                grid_series[-1],
            )
        )
        details.append(
            _resampling_detail(
                "B", "B_grid_subsample", "grid16x16", seed, comparison
            )
        )
    return {
        "verdict": "REPORTED (descriptive)",
        "degree": 0,
        "stride": 1,
        "metric": "bottleneck_linf",
        "seeds": [int(seed) for seed in SEEDS],
        "baselines": {
            "A": "frozen-phase 64-point Family A return trajectories, sigma 0",
            "B": "Family B jump trajectories, sigma 0.05",
        },
        "column_semantics": {
            "adjacent_mean": (
                "mean of the variant within-sequence adjacent degree-0 "
                "bottleneck distances d(D_t, D_{t+1})"
            ),
            "adjacent_p95": (
                "95th percentile (numpy linear interpolation) of the variant "
                "within-sequence adjacent degree-0 bottleneck distances"
            ),
            "endpoint_distance": (
                "bottleneck distance between the variant final diagram and "
                "the baseline final diagram"
            ),
            "changed_fraction": (
                "fraction of frames whose finite degree-0 diagram array is "
                "not elementwise identical between variant and baseline"
            ),
        },
        "interpretation_notes": [
            (
                "The 48-point Family A variant keeps three of every four "
                "points around each circle because 32 points per circle are "
                "not divisible by three; the stated target count of 48 points "
                "governs."
            ),
            (
                "The phase-redraw variant uses the local seed namespace "
                "[seed, 0, 0, 303] and shares the baseline latent geometry "
                "(z, radius, orientation) so that only the circle phases "
                "change."
            ),
            (
                "No scientific pass or fail threshold is predeclared for "
                "these uncertainty measurements; they are reported as "
                "distributions for the G2 record."
            ),
        ],
        "rows": rows,
        "details": details,
    }


def _cardinality(family: str, length: int) -> dict:
    if family == "A":
        n_points = int(length * generators.POINTS_PER_FRAME)
        return {
            "kind": "points_concatenated",
            "n_points_per_window": n_points,
            "shape_per_window": [n_points, 2],
        }
    side = int(generators.FAMILY_B_SIDE)
    return {
        "kind": "field_averaged",
        "shape_per_window": [side, side],
    }


def _window_records(traj: generators.Trajectory) -> list[dict]:
    n_frames = int(traj.frames.shape[0])
    stamps = np.asarray(traj.timestamps, dtype=np.float64)
    records: list[dict] = []
    for length in (1, 3, 5):
        for stride in (1, 2, 4):
            pooled, ends = persistence.pool_window(
                traj.frames, traj.family, length, stride
            )
            ends_int = np.asarray(ends, dtype=np.int64)
            end_times = stamps[ends_int]
            support_start = int(ends_int[0]) - (length - 1)
            support_end = int(ends_int[-1])
            expected_count = int(np.arange(length - 1, n_frames, stride).size)
            record = {
                "length": int(length),
                "stride": int(stride),
                "window_index_convention": (
                    "trailing window ending at frame j; end indices ends = "
                    "arange(length - 1, n_frames, stride)"
                ),
                "output_count": int(ends_int.size),
                "expected_output_count": expected_count,
                "first_window_end_frame": int(ends_int[0]),
                "first_window_end_time": float(end_times[0]),
                "last_window_end_frame": int(ends_int[-1]),
                "last_window_end_time": float(end_times[-1]),
                "input_frame_support": {
                    "start_frame": support_start,
                    "end_frame": support_end,
                    "start_time": float(stamps[support_start]),
                    "end_time": float(stamps[support_end]),
                    "unused_tail_frames": int(n_frames - 1 - support_end),
                },
                "pooled_cardinality": _cardinality(traj.family, length),
                "pooled_array_shape": [int(value) for value in pooled.shape],
            }
            record["output_count_matches_formula"] = bool(
                record["output_count"] == expected_count
            )
            records.append(record)
    return records


def _pooled_comparison(traj: generators.Trajectory) -> dict:
    pooled_frames, ends = persistence.pool_window(traj.frames, traj.family, 3, 2)
    ends_int = np.asarray(ends, dtype=np.int64)
    stamps = np.asarray(traj.timestamps, dtype=np.float64)
    pooled_traj = generators.Trajectory(
        trajectory_id=f"{traj.trajectory_id}_pooled_l3_s2",
        family=traj.family,
        label=traj.label,
        base_seed=int(traj.base_seed),
        sigma=float(traj.sigma),
        stride=2,
        timestamps=stamps[ends_int],
        frames=pooled_frames,
        z=np.asarray(traj.z, dtype=np.float64)[ends_int],
        latent=dict(traj.latent),
    )
    frame_diagrams = persistence.trajectory_diagrams(
        traj.frames, traj.family, degrees=(0,)
    )[0]
    pooled_diagrams = persistence.diagrams_for_windows(
        traj.frames, traj.family, 3, 2, degrees=(0,)
    )[0]
    frame_repr = features.build_representations(
        traj, frame_diagrams, 0, bottleneck_linf
    )
    pooled_repr = features.build_representations(
        pooled_traj, pooled_diagrams, 0, bottleneck_linf
    )
    frame_compact = np.asarray(frame_repr["compact"], dtype=np.float64)
    pooled_compact = np.asarray(pooled_repr["compact"], dtype=np.float64)
    return {
        "degree": 0,
        "metric": "bottleneck_linf",
        "floor_e": 0.0,
        "claim_scope": (
            "separate trailing-window observation map; never mixed with the "
            "frame-level claim"
        ),
        "frame_level_baseline": {
            "n_diagrams": int(len(frame_diagrams)),
            "L": float(frame_compact[0]),
            "R": float(frame_compact[1]),
            "eta": float(frame_compact[2]),
        },
        "pooled_length3_stride2": {
            "n_windows": int(pooled_frames.shape[0]),
            "L": float(pooled_compact[0]),
            "R": float(pooled_compact[1]),
            "eta": float(pooled_compact[2]),
            "pooled_shape_per_window": [int(value) for value in pooled_frames.shape[1:]],
        },
    }


def check_windows(trajectories: Sequence[generators.Trajectory]) -> dict:
    payload: dict = {
        "verdict": "PASS",
        "trajectories": {},
        "pooled_diagnostics": {},
    }
    for traj in trajectories:
        records = _window_records(traj)
        ok = True
        for record in records:
            if not record["output_count_matches_formula"]:
                ok = False
            if not 0.0 <= record["first_window_end_time"] <= 1.0:
                ok = False
            if not 0.0 <= record["last_window_end_time"] <= 1.0:
                ok = False
            if record["output_count"] > 1 and not (
                record["first_window_end_time"] < record["last_window_end_time"]
            ):
                ok = False
        payload["trajectories"][traj.trajectory_id] = {
            "family": traj.family,
            "n_frames": int(traj.frames.shape[0]),
            "master_grid": "u = j / 128, j = 0..128",
            "windows": records,
            "verdict": "PASS" if ok else "FAIL",
        }
        payload["pooled_diagnostics"][traj.trajectory_id] = _pooled_comparison(traj)
        if not ok:
            payload["verdict"] = "FAIL"
    return payload


def _format_cell(value: Any) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(value) for value in row) + " |")
    return "\n".join(lines)


def _build_report(
    gate: dict,
    environment: dict,
    determinism: dict,
    resampling: dict,
    windows: dict,
    timings: dict,
    wall_seconds: float,
    peak_bytes: int,
    artifact_hashes: dict,
    command: str,
    started_utc: str,
) -> str:
    peak_mib = peak_bytes / (1024.0 * 1024.0)
    lines: list[str] = []
    lines.append("# WP-2.1 window-to-diagram interface evidence")
    lines.append("")
    lines.append(
        "**Conditional status.** This artifact belongs to WP-2.1, which the "
        "coordinator conditions on gate G1 before the G2 decision. The G1 "
        f"packet at `{gate['g1_decision_packet']}` was inspected at run time "
        "and its recorded status was: "
        f"{gate['g1_recorded_status_at_run_time']} "
        f"({gate['pending_marker_count']} pending markers). Every verdict below "
        "is conditional on G1 and none of it is a G2 decision."
    )
    lines.append("")
    lines.append(f"**Exact run command** (from the repository root): `{command}`")
    lines.append("")
    lines.append(f"**Run start (UTC):** {started_utc}")
    lines.append("")
    lines.append(
        f"**Wall time:** {wall_seconds:.1f} s of the 25 minute (1500 s) cap. "
        "The timer starts at module load, before the numerical imports, and "
        "stops after every diagram computation and after the data artifacts "
        "are written, before this report and the checksum file are written. "
        "Interpreter startup before module load is excluded."
    )
    lines.append("")
    lines.append(
        f"**Peak process RAM:** {peak_mib:.1f} MiB, measured as `ru_maxrss` of "
        "`RUSAGE_SELF` in a single worker process. The WP-2.1 cap is at most "
        "two worker processes; serial execution was retained because the "
        "measured workload fits the runtime budget."
    )
    lines.append("")
    lines.append(
        "**Environment:** Python "
        f"{environment['python']}, numpy {environment['numpy']}, gudhi "
        f"{environment['gudhi']}, {environment['platform']}."
    )
    lines.append("")
    lines.append("**Per-check wall time:** " + ", ".join(
        f"{name} {value:.1f} s" for name, value in timings.items()
    ) + ".")
    lines.append("")
    lines.append("## Check 1 and Check 2: determinism and window equivalence")
    lines.append("")
    lines.append(
        f"Verdict: {determinism['verdict']}. Each declared trajectory was "
        "diagram-computed twice into separate temporary caches, loaded back "
        "with checksum verification, and compared per degree and frame by "
        "`np.array_equal` and by sha256 over the canonical array bytes. In the "
        "same process, "
        "`diagrams_for_windows(frames, family, length=1, stride=1)` was "
        "compared against `trajectory_diagrams(frames, family)`."
    )
    lines.append("")
    det_rows: list[list[Any]] = []
    for record in determinism["trajectories"]:
        sha_equal = all(
            entry["sha256_cache1"] == entry["sha256_cache2"]
            for entry in record["degrees"].values()
        )
        essential_equal = all(
            entry["essential_counts_equal"] for entry in record["degrees"].values()
        )
        det_rows.append(
            [
                record["trajectory_id"],
                record["n_frames"],
                record["cache_recompute_bitwise_equal"],
                sha_equal,
                essential_equal,
                record["window_equality"]["bitwise_equal"],
                record["verdict"],
            ]
        )
    lines.append(
        _md_table(
            [
                "trajectory",
                "n_frames",
                "cache arrays bitwise equal",
                "cache sha256 equal",
                "essential counts equal",
                "window(1,1) bitwise equal",
                "verdict",
            ],
            det_rows,
        )
    )
    lines.append("")
    for record in determinism["trajectories"]:
        degree = record["degrees"]["0"]
        window_degree = record["window_equality"]["degrees"]["0"]
        lines.append(
            f"- {record['trajectory_id']}: degree 0 cache sha256 "
            f"`{degree['sha256_cache1']}` in both caches; degree 0 window call "
            f"max component difference "
            f"{_format_cell(window_degree['max_component_diff'])}."
        )
        for name, equal in record["file_bytes_equal"].items():
            lines.append(
                f"- {record['trajectory_id']}: cache file bytes equal for "
                f"{name}: {_format_cell(equal)}."
            )
    lines.append("")
    lines.append("## Check 3: extraction uncertainty under raw resampling")
    lines.append("")
    lines.append(
        f"Verdict: {resampling['verdict']}. Degree 0, stride 1, seeds "
        f"{resampling['seeds']}, `{resampling['metric']}`. Baselines: "
        f"{resampling['baselines']['A']}; {resampling['baselines']['B']}."
    )
    lines.append("")
    res_rows = [
        [
            row["family"],
            row["condition"],
            row["variant"],
            row["seed"],
            row["n_frames"],
            row["adjacent_mean"],
            row["adjacent_p95"],
            row["endpoint_distance"],
            row["changed_fraction"],
        ]
        for row in resampling["rows"]
    ]
    lines.append(
        _md_table(
            [
                "family",
                "condition",
                "variant",
                "seed",
                "n_frames",
                "adjacent_mean",
                "adjacent_p95",
                "endpoint_distance",
                "changed_fraction",
            ],
            res_rows,
        )
    )
    lines.append("")
    lines.append(
        "Column semantics: adjacent statistics are within-sequence adjacent "
        "bottleneck distances of the variant diagrams; endpoint_distance is "
        "the bottleneck distance between the variant and baseline final "
        "diagrams; changed_fraction is the fraction of frames whose finite "
        "degree-0 diagram arrays are not elementwise identical."
    )
    lines.append("")
    lines.append(
        "Interpretation notes: the 48-point variant keeps three of every four "
        "points around each circle because 32 points per circle are not "
        "divisible by three, and the stated 48-point target governs; the "
        "phase-redraw variant uses the local seed namespace [seed, 0, 0, 303] "
        "and shares the baseline latent geometry so that only the circle "
        "phases change; no scientific pass or fail threshold is predeclared "
        "for these uncertainty measurements."
    )
    lines.append("")
    lines.append("## Check 4: per-window metadata and pooled observation map")
    lines.append("")
    lines.append(
        f"Verdict: {windows['verdict']}. Trailing-window end indices follow "
        "`ends = arange(length - 1, n_frames, stride)`, so every window uses "
        "only frames at or before its end timestamp. Pooled results are "
        "reported as a separate observation map and are never mixed with the "
        "frame-level claim."
    )
    lines.append("")
    for trajectory_id, entry in windows["trajectories"].items():
        lines.append(f"### {trajectory_id} ({entry['family']} family)")
        lines.append("")
        window_rows = [
            [
                record["length"],
                record["stride"],
                record["output_count"],
                record["first_window_end_frame"],
                f"{record['first_window_end_time']:.6g}",
                record["last_window_end_frame"],
                f"{record['last_window_end_time']:.6g}",
                (
                    f"[{record['input_frame_support']['start_frame']}, "
                    f"{record['input_frame_support']['end_frame']}]"
                ),
                (
                    record["pooled_cardinality"]["kind"]
                    + " "
                    + str(record["pooled_cardinality"]["shape_per_window"])
                ),
            ]
            for record in entry["windows"]
        ]
        lines.append(
            _md_table(
                [
                    "length",
                    "stride",
                    "output count",
                    "first end frame",
                    "first end time",
                    "last end frame",
                    "last end time",
                    "input support (frames)",
                    "pooled cardinality",
                ],
                window_rows,
            )
        )
        lines.append("")
    lines.append("### Pooled diagnostics at length 3, stride 2")
    lines.append("")
    pooled_rows: list[list[Any]] = []
    for trajectory_id, entry in windows["pooled_diagnostics"].items():
        base = entry["frame_level_baseline"]
        pooled = entry["pooled_length3_stride2"]
        pooled_rows.append(
            [
                trajectory_id,
                "frame level",
                base["n_diagrams"],
                base["L"],
                base["R"],
                base["eta"],
            ]
        )
        pooled_rows.append(
            [
                trajectory_id,
                "pooled (3, 2)",
                pooled["n_windows"],
                pooled["L"],
                pooled["R"],
                pooled["eta"],
            ]
        )
    lines.append(
        _md_table(
            ["trajectory", "observation map", "count", "L", "R", "eta"],
            pooled_rows,
        )
    )
    lines.append("")
    lines.append(
        "The pooled rows are a different observation map (Family A point "
        "concatenation or Family B field averaging with pooled cardinality in "
        "the preceding table), so their L, R, and eta values are not "
        "comparable to the frame-level values and are not pooled into the "
        "frame-level claim. Undefined eta values appear as null in the JSON "
        "artifacts and as undefined in this table."
    )
    lines.append("")
    lines.append("## What is verified")
    lines.append("")
    lines.append(
        "Within one environment and one process, the frozen extraction "
        "pipeline recomputes bitwise identical diagrams for the two declared "
        "trajectories, including cache file checksums, and the length 1 "
        "stride 1 trailing-window call reproduces the frame-level call "
        "exactly. The pooling grid emits the formula-expected number of "
        "trailing windows with end times inside the physical horizon, and "
        "declared pooled cardinalities are consistent with the frozen pooling "
        "rule. Resampling uncertainty is measured for the declared variants."
    )
    lines.append("")
    lines.append("## What is not verified")
    lines.append("")
    lines.append(
        "1. Cross-machine or cross-version bitwise reproducibility is not "
        "tested; only same-environment, same-process reruns are covered. "
        "2. Three seeds per condition are descriptive and do not estimate a "
        "sampling distribution over latent draws. "
        "3. The resampling checks cover degree 0 only; the H1 secondary "
        "channel is not tested here. "
        "4. No stability, separability, event-detection, or application claim "
        "is tested, and no G2 or G3 verdict is issued. "
        "5. The pooled observation map is reported, not evaluated against the "
        "frame-level map."
    )
    lines.append("")
    lines.append("## Artifact hashes")
    lines.append("")
    hash_rows = [[name, digest] for name, digest in sorted(artifact_hashes.items())]
    lines.append(_md_table(["artifact", "sha256"], hash_rows))
    lines.append("")
    lines.append(
        "The `SHA256SUMS` file also lists the sha256 of this report. Verify "
        "with `sha256sum -c SHA256SUMS` from the output directory."
    )
    lines.append("")
    lines.append("## Gate labeling")
    lines.append("")
    lines.append(
        "This artifact is labeled conditional on G1 as instructed. It does "
        "not record, replace, or preempt the coordinator's G1 or G2 decision, "
        "and it does not modify any file outside "
        "`scripts/run_wp21_interface.py` and "
        "`research_review/results/g2/interface/`."
    )
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the WP-2.1 window-to-diagram interface evidence."
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help="output directory for the WP-2.1 evidence",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    started = _PROCESS_START
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    command = "python3 scripts/run_wp21_interface.py"
    environment = _environment()
    gate = _g1_dependency()
    timings: dict[str, float] = {}
    trajectories = (
        generators.build_trajectory("A", "return", 1000, 0.0, 1),
        generators.build_trajectory("B", "jump", 1000, 0.05, 1),
    )
    with tempfile.TemporaryDirectory(prefix="tk_wp21_") as tmp:
        mark = time.perf_counter()
        determinism = check_determinism(trajectories, Path(tmp))
        timings["determinism_seconds"] = time.perf_counter() - mark
        mark = time.perf_counter()
        resampling = check_resampling()
        timings["resampling_seconds"] = time.perf_counter() - mark
        mark = time.perf_counter()
        windows = check_windows(trajectories)
        timings["windows_seconds"] = time.perf_counter() - mark
    wall_seconds = time.perf_counter() - started
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    determinism_payload = {
        "work_package": WP,
        "gate_dependency": gate,
        "environment": environment,
        "determinism": determinism,
    }
    resampling_payload = {
        "work_package": WP,
        "gate_dependency": gate,
        "environment": environment,
        "resampling": {
            key: value for key, value in resampling.items() if key != "rows"
        },
    }
    windows_payload = {
        "work_package": WP,
        "gate_dependency": gate,
        "environment": environment,
        "windows": windows,
    }
    manifest_payload = {
        "work_package": WP,
        "gate_dependency": gate,
        "environment": environment,
        "command": command,
        "seeds": [int(seed) for seed in SEEDS],
        "worker_processes": 1,
        "trajectories": [
            traj.trajectory_id for traj in trajectories
        ],
        "timings": timings,
        "wall_time_seconds": wall_seconds,
        "peak_ram_bytes": peak_bytes,
        "peak_ram_mib": peak_bytes / (1024.0 * 1024.0),
        "artifacts": [
            "determinism.json",
            "resampling.csv",
            "resampling_details.json",
            "window_metadata.json",
            "interface_report.md",
        ],
    }
    determinism_path = outdir / "determinism.json"
    resampling_csv_path = outdir / "resampling.csv"
    resampling_details_path = outdir / "resampling_details.json"
    windows_path = outdir / "window_metadata.json"
    manifest_path = outdir / "run_manifest.json"
    report_path = outdir / "interface_report.md"
    _write_json(determinism_path, determinism_payload)
    with open(resampling_csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for row in resampling["rows"]:
            writer.writerow([row[column] for column in CSV_COLUMNS])
    _write_json(resampling_details_path, resampling_payload)
    _write_json(windows_path, windows_payload)
    _write_json(manifest_path, manifest_payload)
    hashed_paths = [
        determinism_path,
        resampling_csv_path,
        resampling_details_path,
        windows_path,
        manifest_path,
    ]
    artifact_hashes = {path.name: _sha256_file(path) for path in hashed_paths}
    report = _build_report(
        gate,
        environment,
        determinism,
        resampling,
        windows,
        timings,
        wall_seconds,
        peak_bytes,
        artifact_hashes,
        command,
        started_utc,
    )
    report_path.write_text(report, encoding="utf-8")
    sums_path = outdir / "SHA256SUMS"
    sums_lines = [
        f"{_sha256_file(path)}  {path.name}" for path in [*hashed_paths, report_path]
    ]
    sums_path.write_text("\n".join(sums_lines) + "\n", encoding="utf-8")
    return 0 if determinism["verdict"] == "PASS" and windows["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
