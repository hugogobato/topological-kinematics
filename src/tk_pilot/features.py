"""Feature baselines for the Topological Kinematics pilot (WP-1.1).

Each representation is a deterministic fixed-dimensional float64 vector built
from one trajectory, its finite diagrams for one homological degree, and the
frozen diagram metric. Undefined entries are NaN, never zero:

- ``compact`` and ``speed_history`` follow :mod:`tk_pilot.path_diagnostics`,
  including the training-calibrated abstention floors: efficiency is valid when
  ``L > 2 (T - 1) e`` with ``T`` the number of intervals, and an angle is valid
  when ``min(a, b) > 2 e``. ``floor_e = None`` means ``e = 0``, i.e. exact-zero
  abstention only.
- ``raw_geometry_*`` switch on the family: Family A point clouds use pairwise
  distance quantiles, covariance eigenvalues, and mean nearest-neighbor
  distance; Family B scalar fields use mean, standard deviation, maximum, and
  mean gradient energy.
- ``moments_*`` use the six frozen moment coordinates with ``p = death - birth``
  and zero for empty diagrams.
- ``moment_signature*`` use :func:`tk_pilot.signatures.signature_level2` on the
  moment polyline, with and without the timestamp as an extra coordinate.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

import numpy as np

from .diagram_metrics import pairwise_distance_matrix
from .path_diagnostics import (
    angle_validity_flags,
    compute_path_diagnostics,
    efficiency_validity_flag,
    noise_floor,
)
from .signatures import signature_level2, signature_level2_time

__all__ = [
    "REPRESENTATIONS",
    "cell_floor",
    "build_representations",
    "moment_path",
]

REPRESENTATIONS = (
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

_MOMENT_PAIRS = ((0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (0, 3))
_RECURRENCE_LAGS = (1, 2, 4, 8)
_QUANTILES = (0.1, 0.5, 0.9)
_SPEED_SUMMARIES_SLICE = slice(3, 9)


def _finite_diagram(diagram) -> np.ndarray:
    arr = np.asarray(diagram, dtype=np.float64)
    if arr.size == 0:
        return np.zeros((0, 2), dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"a finite diagram must have shape (n, 2); got {arr.shape}")
    return arr


def cell_floor(adjacent_distances_by_trajectory: Iterable) -> float:
    """Training-only floor ``e``: pooled 95th percentile of adjacent distances."""
    arrays = [
        np.asarray(values, dtype=np.float64).ravel()
        for values in adjacent_distances_by_trajectory
    ]
    if not arrays:
        raise ValueError("at least one trajectory is required to calibrate a floor")
    return noise_floor(np.concatenate(arrays))


def _compact_vector(diagnostics, floor: float) -> np.ndarray:
    speeds = np.asarray(diagnostics.interval_speeds, dtype=np.float64)
    changes = np.asarray(diagnostics.speed_change_rates, dtype=np.float64)
    distances = np.asarray(diagnostics.adjacent_distances, dtype=np.float64)
    if speeds.size:
        speed_stats = [
            float(np.mean(speeds)),
            float(np.std(speeds, ddof=0)),
            float(np.max(speeds)),
        ]
    else:
        speed_stats = [np.nan, np.nan, np.nan]
    if changes.size:
        change_stats = [
            float(np.mean(changes)),
            float(np.mean(np.abs(changes))),
            float(np.max(np.abs(changes))),
        ]
    else:
        change_stats = [np.nan, np.nan, np.nan]
    if distances.size >= 2:
        valid = np.asarray(
            angle_validity_flags(distances[:-1], distances[1:], floor), dtype=bool
        )
    else:
        valid = np.empty(0, dtype=bool)
    angle_fraction = float(np.mean(valid)) if valid.size else np.nan
    cosines = np.asarray(diagnostics.cosine_raw, dtype=np.float64)
    usable = valid & np.isfinite(cosines)
    mean_cosine = float(np.mean(cosines[usable])) if np.any(usable) else np.nan
    eta = np.nan if diagnostics.efficiency is None else float(diagnostics.efficiency)
    efficiency_flag = (
        1.0
        if efficiency_validity_flag(diagnostics.length, diagnostics.n_intervals, floor)
        else 0.0
    )
    return np.array(
        [
            float(diagnostics.length),
            float(diagnostics.displacement),
            eta,
            *speed_stats,
            *change_stats,
            mean_cosine,
            angle_fraction,
            efficiency_flag,
        ],
        dtype=np.float64,
    )


def _recurrence_vector(matrix: np.ndarray, displacement: float) -> np.ndarray:
    values: list[float] = []
    for lag in _RECURRENCE_LAGS:
        diagonal = matrix.diagonal(lag)
        if diagonal.size:
            values.extend([float(np.mean(diagonal)), float(np.min(diagonal))])
        else:
            values.extend([np.nan, np.nan])
    values.append(float(displacement))
    return np.asarray(values, dtype=np.float64)


def _point_cloud_row(points: np.ndarray) -> np.ndarray:
    row = np.full(6, np.nan, dtype=np.float64)
    n_points = points.shape[0]
    if n_points >= 2:
        diff = points[:, None, :] - points[None, :, :]
        distances = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        pairs = distances[np.triu_indices(n_points, 1)]
        row[:3] = np.quantile(pairs, _QUANTILES)
        nearest = distances.copy()
        np.fill_diagonal(nearest, np.inf)
        row[5] = float(np.mean(np.min(nearest, axis=1)))
        covariance = np.cov(points, rowvar=False)
        eigenvalues = np.linalg.eigvalsh(covariance)[::-1]
        row[3] = float(eigenvalues[0])
        row[4] = float(eigenvalues[1])
    return row


def _field_row(field: np.ndarray) -> np.ndarray:
    gradient_y, gradient_x = np.gradient(field)
    energy = float(np.mean(gradient_x * gradient_x + gradient_y * gradient_y))
    return np.array(
        [float(np.mean(field)), float(np.std(field)), float(np.max(field)), energy],
        dtype=np.float64,
    )


def _geometry_rows(family: str, frames: np.ndarray) -> np.ndarray:
    if frames.ndim != 3:
        raise ValueError(f"frames must be a 3-D array; got shape {frames.shape}")
    if family == "A":
        if frames.shape[-1] != 2:
            raise ValueError(
                "Family A frames must have shape (n, points, 2); "
                f"got {frames.shape}"
            )
        return np.vstack([_point_cloud_row(frame) for frame in frames])
    if family == "B":
        return np.vstack([_field_row(field) for field in frames])
    raise ValueError(f"unsupported family {family!r}; expected 'A' or 'B'")


def _moment_row(diagram: np.ndarray) -> np.ndarray:
    if diagram.shape[0] == 0:
        return np.zeros(len(_MOMENT_PAIRS), dtype=np.float64)
    birth = diagram[:, 0]
    lifespan = diagram[:, 1] - diagram[:, 0]
    values = [
        np.sum(birth**a * lifespan**j) for a, j in _MOMENT_PAIRS
    ]
    return np.asarray(values, dtype=np.float64)


def moment_path(series: Sequence[np.ndarray]) -> np.ndarray:
    """Per-frame six-coordinate moment path for a diagram sequence."""
    return np.vstack([_moment_row(diagram) for diagram in series])


def _apply_moment_scaling(path: np.ndarray, moment_scaling) -> np.ndarray:
    if moment_scaling is None:
        return path
    if isinstance(moment_scaling, dict):
        mean = np.asarray(moment_scaling["mean"], dtype=np.float64)
        std = np.asarray(moment_scaling["std"], dtype=np.float64)
    else:
        mean = np.asarray(moment_scaling[0], dtype=np.float64)
        std = np.asarray(moment_scaling[1], dtype=np.float64)
    if mean.shape != (path.shape[1],) or std.shape != (path.shape[1],):
        raise ValueError(
            "moment_scaling must provide one mean and std per moment coordinate; "
            f"got shapes {mean.shape} and {std.shape} for path width {path.shape[1]}"
        )
    safe_std = np.where(std > 0.0, std, 1.0)
    return (path - mean) / safe_std


def build_representations(
    traj,
    diagrams: Sequence,
    degree: int,
    metric: Callable[[object, object], float],
    floor_e: float | None = None,
    timestamps: np.ndarray | None = None,
    distance_matrix: np.ndarray | None = None,
    moment_scaling=None,
) -> dict[str, np.ndarray]:
    """Build every WP-1.1 representation for one trajectory and degree.

    ``diagrams`` is the per-frame list of finite diagrams for ``degree``; it
    must match ``traj.frames`` and the timestamps one-to-one. When
    ``distance_matrix`` is None the full symmetric pairwise matrix is computed
    with ``pairwise_distance_matrix``; a supplied stride-subsampled matrix is
    used for the distance-history representations while the compact
    diagnostics always call ``compute_path_diagnostics`` with ``metric``.
    """
    series = [_finite_diagram(diagram) for diagram in diagrams]
    frames = np.asarray(traj.frames, dtype=np.float64)
    stamps = np.asarray(
        traj.timestamps if timestamps is None else timestamps, dtype=np.float64
    )
    n_frames = len(series)
    if frames.shape[0] != n_frames:
        raise ValueError(
            f"got {n_frames} diagrams but {frames.shape[0]} frames; they must match"
        )
    if stamps.size != n_frames:
        raise ValueError(
            f"got {n_frames} diagrams but {stamps.size} timestamps; they must match"
        )
    floor = 0.0 if floor_e is None else float(floor_e)
    if not np.isfinite(floor) or floor < 0.0:
        raise ValueError("floor_e must be a finite non-negative value")
    diagnostics = compute_path_diagnostics(series, stamps, metric)
    compact = _compact_vector(diagnostics, floor)
    speed_history = np.concatenate(
        [
            np.asarray(diagnostics.interval_speeds, dtype=np.float64),
            compact[_SPEED_SUMMARIES_SLICE],
        ]
    )
    if distance_matrix is None:
        matrix = pairwise_distance_matrix(series, metric)
    else:
        matrix = np.asarray(distance_matrix, dtype=np.float64)
        if matrix.shape != (n_frames, n_frames):
            raise ValueError(
                f"distance_matrix must have shape {(n_frames, n_frames)}; "
                f"got {matrix.shape}"
            )
    complete_distances = matrix[np.triu_indices(n_frames, 1)]
    recurrence_summary = _recurrence_vector(matrix, float(diagnostics.displacement))
    geometry_rows = _geometry_rows(traj.family, frames)
    geometry_flat = geometry_rows.ravel()
    geometry_summary = np.concatenate(
        [geometry_rows.mean(axis=0), geometry_rows.std(axis=0)]
    )
    path = moment_path(series)
    moments_flat = path.ravel()
    moments_summary = np.concatenate([path.mean(axis=0), path.std(axis=0)])
    signature_path = _apply_moment_scaling(path, moment_scaling)
    moment_signature = signature_level2(signature_path)
    moment_signature_time = signature_level2_time(signature_path, stamps)
    return {
        "compact": compact,
        "speed_history": speed_history,
        "complete_distances": complete_distances,
        "recurrence_summary": recurrence_summary,
        "raw_geometry_flat": geometry_flat,
        "raw_geometry_summary": geometry_summary,
        "moments_flat": moments_flat,
        "moments_summary": moments_summary,
        "moment_signature": moment_signature,
        "moment_signature_time": moment_signature_time,
    }
