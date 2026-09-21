"""Discrete metric-path diagnostics for a finite sequence of objects.

The objects may be finite persistence diagrams, but the diagnostics only ever
call the supplied metric, so arbitrary finite metric spaces are supported. The
definitions are frozen in ``assumption_ledger.yaml`` and documented in
``metric_interface.md``:

- interval speed ``nu_t = d(D_t, D_{t+1}) / h_t`` with ``h_t = t_{t+1} - t_t``,
  timestamped at the interval midpoint ``m_t = (t_t + t_{t+1}) / 2``;
- path length ``L = sum_t d(D_t, D_{t+1})``;
- endpoint displacement ``R = d(D_0, D_T)``;
- efficiency ``eta = R / L`` when ``L > 0``, otherwise undefined;
- speed-change rate ``a_t = (nu_t - nu_{t-1}) / (m_t - m_{t-1})``, never called
  physical acceleration;
- comparison angle ``theta_t = arccos(clip(z, -1, 1))`` with
  ``z = (a^2 + b^2 - c^2) / (2ab)`` for ``a = d(D_{t-1}, D_t)``,
  ``b = d(D_t, D_{t+1})``, ``c = d(D_{t-1}, D_{t+1})``, defined only when
  ``a b > 0``; the companion turn is ``pi - theta_t``;
- optional scale-free triangle excess ``q_t = (a + b - c) / (a + b)``, defined
  only when ``a + b > 0``.

Undefined quantities are represented by ``NaN`` internally and ``None`` in
:meth:`PathDiagnostics.as_json`. Undefined never means zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NamedTuple, Sequence

import numpy as np

from .diagram_metrics import bottleneck_linf

__all__ = [
    "AngleSummary",
    "PathDiagnostics",
    "validate_timestamps",
    "interval_speeds",
    "speed_change_rates",
    "comparison_angles",
    "triangle_excess",
    "path_length",
    "endpoint_displacement",
    "efficiency",
    "noise_floor",
    "angle_validity_flags",
    "efficiency_validity_flag",
    "compute_path_diagnostics",
]

_COSINE_ANOMALY_TOL = 1e-12


class AngleSummary(NamedTuple):
    """Comparison-angle outputs for interior indices ``t = 1, ..., T-1``."""

    angle: np.ndarray
    turn: np.ndarray
    valid: np.ndarray
    cosine_raw: np.ndarray
    cosine_anomaly: np.ndarray
    excess: np.ndarray
    excess_valid: np.ndarray


@dataclass(frozen=True)
class PathDiagnostics:
    """Frozen discrete path diagnostics for one trajectory."""

    timestamps: np.ndarray
    adjacent_distances: np.ndarray
    interval_speeds: np.ndarray
    interval_speed_times: np.ndarray
    length: float
    displacement: float
    efficiency: float | None
    speed_change_rates: np.ndarray
    speed_change_times: np.ndarray
    comparison_angles: np.ndarray
    comparison_turns: np.ndarray
    comparison_valid: np.ndarray
    cosine_raw: np.ndarray
    cosine_anomaly: np.ndarray
    triangle_excess: np.ndarray
    triangle_excess_valid: np.ndarray

    @property
    def n_intervals(self) -> int:
        return int(self.adjacent_distances.size)

    @property
    def angle_valid_fraction(self) -> float | None:
        if self.comparison_valid.size == 0:
            return None
        return float(np.mean(self.comparison_valid))

    def as_json(self) -> dict:
        """JSON-safe dictionary; undefined values become ``None``."""

        def row(values) -> list:
            return [None if v is None or not np.isfinite(v) else float(v) for v in values]

        return {
            "timestamps": [float(x) for x in self.timestamps],
            "adjacent_distances": row(self.adjacent_distances),
            "interval_speeds": row(self.interval_speeds),
            "interval_speed_times": row(self.interval_speed_times),
            "length": float(self.length),
            "displacement": float(self.displacement),
            "efficiency": (
                None if self.efficiency is None else float(self.efficiency)
            ),
            "speed_change_rates": row(self.speed_change_rates),
            "speed_change_times": row(self.speed_change_times),
            "comparison_angles": row(self.comparison_angles),
            "comparison_turns": row(self.comparison_turns),
            "comparison_valid": [bool(x) for x in self.comparison_valid],
            "cosine_raw": row(self.cosine_raw),
            "cosine_anomaly": [bool(x) for x in self.cosine_anomaly],
            "triangle_excess": row(self.triangle_excess),
            "triangle_excess_valid": [
                bool(x) for x in self.triangle_excess_valid
            ],
            "angle_valid_fraction": self.angle_valid_fraction,
        }


def validate_timestamps(timestamps) -> np.ndarray:
    """Return timestamps as a float array, requiring strictly increasing values."""
    t = np.asarray(timestamps, dtype=float)
    if t.ndim != 1:
        raise ValueError("timestamps must be one-dimensional")
    if t.size < 2:
        raise ValueError("at least two timestamps are required")
    if not np.all(np.isfinite(t)):
        raise ValueError("timestamps must be finite")
    if np.any(np.diff(t) <= 0):
        raise ValueError("timestamps must be strictly increasing; found h_t <= 0")
    return t


def _validate_lengths(objects: Sequence, t: np.ndarray) -> None:
    if len(objects) != t.size:
        raise ValueError(
            f"got {len(objects)} objects but {t.size} timestamps; they must match"
        )


def interval_speeds(
    objects: Sequence, timestamps, metric: Callable[[object, object], float]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(nu, adjacent_distances, midpoints)``."""
    t = validate_timestamps(timestamps)
    _validate_lengths(objects, t)
    n = t.size - 1
    distances = np.array(
        [float(metric(objects[i], objects[i + 1])) for i in range(n)]
    )
    h = np.diff(t)
    midpoints = 0.5 * (t[:-1] + t[1:])
    return distances / h, distances, midpoints


def speed_change_rates(
    speeds: np.ndarray, midpoints: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(a_t, times)`` with the midpoint-difference denominator."""
    s = np.asarray(speeds, dtype=float)
    m = np.asarray(midpoints, dtype=float)
    if s.size != m.size:
        raise ValueError("speeds and midpoints must have the same length")
    if s.size < 2:
        return np.empty(0, dtype=float), np.empty(0, dtype=float)
    steps = np.diff(m)
    if np.any(steps <= 0):
        raise ValueError("midpoint timestamps must be strictly increasing")
    return np.diff(s) / steps, m[1:]


def comparison_angles(
    objects: Sequence,
    adjacent_distances: np.ndarray,
    metric: Callable[[object, object], float],
) -> AngleSummary:
    """Comparison angle, turn, and triangle excess for each interior index.

    ``adjacent_distances`` must be the output of :func:`interval_speeds`.
    """
    d = np.asarray(adjacent_distances, dtype=float)
    n_intervals = d.size
    n_angles = max(n_intervals - 1, 0)
    angle = np.full(n_angles, np.nan)
    turn = np.full(n_angles, np.nan)
    valid = np.zeros(n_angles, dtype=bool)
    cosine_raw = np.full(n_angles, np.nan)
    anomaly = np.zeros(n_angles, dtype=bool)
    excess = np.full(n_angles, np.nan)
    excess_valid = np.zeros(n_angles, dtype=bool)
    for k in range(n_angles):
        t = k + 1
        a = d[t - 1]
        b = d[t]
        c = float(metric(objects[t - 1], objects[t + 1]))
        if a + b > 0:
            excess[k] = (a + b - c) / (a + b)
            excess_valid[k] = True
        if not (a > 0 and b > 0):
            continue
        z = (a * a + b * b - c * c) / (2.0 * a * b)
        cosine_raw[k] = z
        anomaly[k] = bool(abs(z) > 1.0 + _COSINE_ANOMALY_TOL)
        angle[k] = float(np.arccos(np.clip(z, -1.0, 1.0)))
        turn[k] = float(np.pi - angle[k])
        valid[k] = True
    return AngleSummary(
        angle=angle,
        turn=turn,
        valid=valid,
        cosine_raw=cosine_raw,
        cosine_anomaly=anomaly,
        excess=excess,
        excess_valid=excess_valid,
    )


def triangle_excess(a: float, b: float, c: float) -> float:
    """Scale-free triangle excess ``(a + b - c) / (a + b)``; NaN if a + b = 0."""
    if a + b <= 0:
        return float("nan")
    return float((a + b - c) / (a + b))


def path_length(adjacent_distances: np.ndarray) -> float:
    return float(np.sum(np.asarray(adjacent_distances, dtype=float)))


def endpoint_displacement(
    objects: Sequence, metric: Callable[[object, object], float]
) -> float:
    if len(objects) < 2:
        raise ValueError("at least two objects are required")
    return float(metric(objects[0], objects[-1]))


def efficiency(length: float, displacement: float) -> float | None:
    """``eta = R / L`` when ``L > 0``; ``None`` when the path has zero length."""
    if not np.isfinite(length) or length < 0:
        raise ValueError("length must be finite and non-negative")
    if length == 0:
        return None
    return float(displacement / length)


def noise_floor(adjacent_distances, percentile: float = 95.0) -> float:
    """Training-only static-noise calibration floor ``e``.

    The frozen policy defines ``e`` as the 95th percentile of adjacent diagram
    distances measured on the static-noise training calibration. This helper
    computes the percentile from a supplied distance sample.
    """
    d = np.asarray(adjacent_distances, dtype=float)
    if d.size == 0:
        raise ValueError("at least one distance is required to calibrate e")
    return float(np.percentile(d, percentile))


def angle_validity_flags(a, b, floor: float) -> np.ndarray:
    """``min(a, b) > 2 e``; at ``e = 0`` this is the exact-zero abstention."""
    aa = np.atleast_1d(np.asarray(a, dtype=float))
    bb = np.atleast_1d(np.asarray(b, dtype=float))
    return np.minimum(aa, bb) > 2.0 * floor


def efficiency_validity_flag(length: float, n_intervals: int, floor: float) -> bool:
    """``L > 2 (T - 1) e`` with ``T`` the number of intervals."""
    return bool(length > 2.0 * (n_intervals - 1) * floor)


def compute_path_diagnostics(
    objects: Sequence,
    timestamps,
    metric: Callable[[object, object], float] = bottleneck_linf,
) -> PathDiagnostics:
    """Compute every frozen path diagnostic for one trajectory."""
    t = validate_timestamps(timestamps)
    _validate_lengths(objects, t)
    speeds, distances, midpoints = interval_speeds(objects, t, metric)
    length = path_length(distances)
    displacement = endpoint_displacement(objects, metric)
    eta = efficiency(length, displacement)
    changes, change_times = speed_change_rates(speeds, midpoints)
    angles = comparison_angles(objects, distances, metric)
    return PathDiagnostics(
        timestamps=t,
        adjacent_distances=distances,
        interval_speeds=speeds,
        interval_speed_times=midpoints,
        length=length,
        displacement=displacement,
        efficiency=eta,
        speed_change_rates=changes,
        speed_change_times=change_times,
        comparison_angles=angles.angle,
        comparison_turns=angles.turn,
        comparison_valid=angles.valid,
        cosine_raw=angles.cosine_raw,
        cosine_anomaly=angles.cosine_anomaly,
        triangle_excess=angles.excess,
        triangle_excess_valid=angles.excess_valid,
    )
