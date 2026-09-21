"""Tests for the frozen discrete path diagnostics (WP-0.2)."""

import json

import numpy as np
import pytest

from tk_pilot.diagram_metrics import bottleneck_bruteforce, bottleneck_linf
from tk_pilot.path_diagnostics import (
    angle_validity_flags,
    comparison_angles,
    compute_path_diagnostics,
    efficiency,
    efficiency_validity_flag,
    interval_speeds,
    noise_floor,
    path_length,
    speed_change_rates,
    triangle_excess,
    validate_timestamps,
)


def singleton(s, lifespan=10.0):
    return np.array([[float(s), float(s) + lifespan]])


def test_validate_timestamps_rejects_non_increasing():
    with pytest.raises(ValueError):
        validate_timestamps([0.0, 1.0, 1.0])
    with pytest.raises(ValueError):
        validate_timestamps([0.0, 0.5, 0.2])
    with pytest.raises(ValueError):
        validate_timestamps([0.0])


def test_interval_speeds_and_midpoints():
    objects = [singleton(s) for s in (0.0, 1.0, 0.5, 2.0, 1.0)]
    timestamps = np.array([0.0, 0.1, 0.3, 0.6, 0.7])
    speeds, distances, midpoints = interval_speeds(objects, timestamps, bottleneck_linf)
    assert np.allclose(distances, [1.0, 0.5, 1.5, 1.0])
    assert np.allclose(midpoints, [0.05, 0.2, 0.45, 0.65])
    assert np.allclose(speeds, distances / np.diff(timestamps))


def test_speed_change_rate_uses_midpoint_denominator():
    speeds = np.array([10.0, 2.5, 5.0, 10.0])
    midpoints = np.array([0.05, 0.2, 0.45, 0.65])
    changes, times = speed_change_rates(speeds, midpoints)
    assert np.allclose(times, [0.2, 0.45, 0.65])
    assert np.allclose(changes, np.diff(speeds) / np.diff(midpoints))
    assert np.allclose(changes, [-50.0, 10.0, 25.0])


def test_straight_and_reversal_angles():
    straight = compute_path_diagnostics(
        [singleton(s) for s in (0.0, 1.0, 2.0)],
        [0.0, 1.0, 2.0],
        bottleneck_bruteforce,
    )
    reversal = compute_path_diagnostics(
        [singleton(s) for s in (0.0, 1.0, 0.0)],
        [0.0, 1.0, 2.0],
        bottleneck_bruteforce,
    )
    assert straight.comparison_angles[0] == pytest.approx(np.pi)
    assert straight.comparison_turns[0] == pytest.approx(0.0)
    assert reversal.comparison_angles[0] == pytest.approx(0.0)
    assert reversal.comparison_turns[0] == pytest.approx(np.pi)


def test_library_angle_conditioning_is_bounded():
    straight_library = compute_path_diagnostics(
        [singleton(s) for s in (0.0, 1.0, 2.0)],
        [0.0, 1.0, 2.0],
        bottleneck_linf,
    )
    assert abs(straight_library.comparison_angles[0] - np.pi) <= 1e-6


def test_zero_step_undefined_angle():
    pd = compute_path_diagnostics(
        [singleton(s) for s in (0.0, 1.0, 1.0)], [0.0, 0.25, 0.5], bottleneck_linf
    )
    assert np.isnan(pd.comparison_angles[0])
    assert not bool(pd.comparison_valid[0])
    assert np.isnan(pd.comparison_turns[0])
    assert pd.triangle_excess[0] == pytest.approx(0.0)
    assert bool(pd.triangle_excess_valid[0])


def test_zero_length_path_has_no_efficiency():
    pd = compute_path_diagnostics(
        [singleton(0.0)] * 3, [0.0, 0.25, 0.5], bottleneck_linf
    )
    assert pd.length == 0.0
    assert pd.efficiency is None
    assert pd.angle_valid_fraction == 0.0
    assert np.isnan(pd.triangle_excess[0])
    assert not bool(pd.triangle_excess_valid[0])


def test_triangle_inequality_and_efficiency_bounds():
    rng = np.random.default_rng(3)
    for _ in range(50):
        dim = int(rng.choice([1, 2, 3, 5]))
        n = int(rng.integers(4, 12))
        points = rng.normal(size=(n, dim))
        metric = lambda p, q: float(np.linalg.norm(p - q))
        pd = compute_path_diagnostics(points, np.arange(n, dtype=float), metric)
        assert pd.displacement <= pd.length + 1e-9
        assert -1e-12 <= pd.efficiency <= 1 + 1e-12


def test_cosine_anomaly_flag():
    pairs = {(0, 1): 1.0, (0, 2): 3.0, (1, 2): 1.0}
    metric = lambda i, j: 0.0 if i == j else pairs[(min(i, j), max(i, j))]
    summary = comparison_angles([0, 1, 2], np.array([1.0, 1.0]), metric)
    assert bool(summary.cosine_anomaly[0])
    assert summary.angle[0] == pytest.approx(np.pi)


def test_noise_floor_and_abstention_rules():
    distances = np.array([1.0, 0.5, 1.5, 1.0])
    floor = noise_floor(distances)
    assert floor == pytest.approx(np.percentile(distances, 95.0))
    flags = angle_validity_flags(distances[:-1], distances[1:], floor)
    assert list(flags) == list(np.minimum(distances[:-1], distances[1:]) > 2 * floor)
    assert efficiency_validity_flag(4.0, 4, floor) == (4.0 > 2 * 3 * floor)
    zero_flags = angle_validity_flags(distances[:-1], distances[1:], 0.0)
    assert all(zero_flags)


def test_clock_dilation_and_relabel_invariance():
    diagrams = [singleton(s) for s in (0.0, 1.0, 0.5, 2.0, 1.0)]
    timestamps = np.array([0.0, 0.1, 0.3, 0.6, 0.7])
    pd = compute_path_diagnostics(diagrams, timestamps, bottleneck_linf)
    relabeled = compute_path_diagnostics(
        diagrams, np.array([0.0, 0.2, 0.4, 0.6, 0.8]), bottleneck_linf
    )
    stretched = compute_path_diagnostics(diagrams, 2.0 * timestamps, bottleneck_linf)
    assert pd.length == relabeled.length
    assert pd.displacement == relabeled.displacement
    assert np.allclose(stretched.interval_speeds, pd.interval_speeds / 2.0)
    assert np.allclose(stretched.speed_change_rates, pd.speed_change_rates / 4.0)


def test_efficiency_and_excess_helpers():
    assert efficiency(4.0, 1.0) == pytest.approx(0.25)
    assert efficiency(0.0, 0.0) is None
    assert triangle_excess(1.0, 1.0, 2.0) == pytest.approx(0.0)
    assert np.isnan(triangle_excess(0.0, 0.0, 0.0))


def test_as_json_is_valid_json():
    pd = compute_path_diagnostics(
        [singleton(s) for s in (0.0, 1.0, 1.0)], [0.0, 0.25, 0.5], bottleneck_linf
    )
    text = json.dumps(pd.as_json(), allow_nan=False)
    restored = json.loads(text)
    assert restored["comparison_angles"][0] is None
    assert restored["length"] == pytest.approx(1.0)
