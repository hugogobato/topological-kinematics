"""Tests for the WP-1.1 feature baselines and level-2 signatures (A4)."""

import numpy as np
import pytest

from tk_pilot.diagram_metrics import (
    bottleneck_bruteforce,
    bottleneck_linf,
    pairwise_distance_matrix,
)
from tk_pilot.features import REPRESENTATIONS, build_representations, cell_floor
from tk_pilot.path_diagnostics import (
    compute_path_diagnostics,
    efficiency_validity_flag,
)
from tk_pilot.signatures import signature_level2, signature_level2_time


class FakeTrajectory:
    def __init__(self, family, frames, timestamps, z=None, label="return"):
        self.family = family
        self.frames = np.asarray(frames, dtype=np.float64)
        self.timestamps = np.asarray(timestamps, dtype=np.float64)
        self.z = np.zeros(self.timestamps.size) if z is None else np.asarray(z)
        self.label = label


def random_diagrams(rng, n, m):
    births = rng.uniform(0.0, 2.0, size=(n, m))
    lengths = rng.uniform(0.05, 1.0, size=(n, m))
    return [np.column_stack([b, b + length]) for b, length in zip(births, lengths)]


def singleton_diagrams(n, start=0.0, step=1.0, lifespan=20.0):
    return [
        np.array([[start + step * index, start + step * index + lifespan]])
        for index in range(n)
    ]


def test_signature_straight_line_analytic():
    direction = np.array([3.0, -2.0])
    parameters = np.linspace(0.0, 1.0, 7)[:, None]
    path = parameters * direction
    sig = signature_level2(path)
    assert sig.shape == (2 + 4,)
    assert np.allclose(sig[:2], direction, atol=1e-12)
    assert np.allclose(
        sig[2:].reshape(2, 2), 0.5 * np.outer(direction, direction), atol=1e-12
    )


def test_signature_l_shape_by_hand():
    e1 = np.array([1.0, 0.0])
    e2 = np.array([0.0, 1.0])
    path = np.array([[0.0, 0.0], e1, e1 + e2])
    sig = signature_level2(path)
    expected_s2 = (
        0.5 * np.outer(e1, e1) + np.outer(e2, e1) + 0.5 * np.outer(e2, e2)
    )
    assert np.allclose(sig[:2], e1 + e2, atol=1e-12)
    assert np.allclose(sig[2:].reshape(2, 2), expected_s2, atol=1e-12)


def test_signature_dimensions_and_time_augmentation():
    rng = np.random.default_rng(7)
    path = rng.normal(size=(9, 6))
    stamps = np.linspace(0.0, 1.0, 9)
    assert signature_level2(path).size == 42
    assert signature_level2_time(path, stamps).size == 56
    augmented = signature_level2_time(path, stamps)
    assert np.allclose(augmented[:6], signature_level2(path)[:6])
    assert augmented[6] == pytest.approx(np.sum(np.diff(stamps)))


def test_signature_rejects_degenerate_paths():
    with pytest.raises(ValueError):
        signature_level2(np.zeros((1, 3)))
    with pytest.raises(ValueError):
        signature_level2(np.zeros((0, 3)))
    with pytest.raises(ValueError):
        signature_level2(np.zeros(3))
    with pytest.raises(ValueError):
        signature_level2_time(np.zeros((3, 6)), np.zeros(2))


def test_cell_floor_pooled_percentile():
    first = np.array([1.0, 2.0])
    second = np.array([3.0, 4.0])
    pooled = np.concatenate([first, second])
    assert cell_floor([first, second]) == pytest.approx(np.percentile(pooled, 95.0))
    with pytest.raises(ValueError):
        cell_floor([])


def test_compact_matches_path_diagnostics():
    rng = np.random.default_rng(11)
    diagrams = random_diagrams(rng, 3, 2)
    stamps = np.array([0.0, 0.25, 0.6])
    traj = FakeTrajectory("A", rng.normal(size=(3, 8, 2)), stamps)
    reps = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    pd = compute_path_diagnostics(diagrams, stamps, bottleneck_bruteforce)
    compact = reps["compact"]
    assert compact[0] == pytest.approx(pd.length)
    assert compact[1] == pytest.approx(pd.displacement)
    assert compact[2] == pytest.approx(pd.efficiency)
    assert compact[3] == pytest.approx(np.mean(pd.interval_speeds))
    assert compact[4] == pytest.approx(np.std(pd.interval_speeds))
    assert compact[5] == pytest.approx(np.max(pd.interval_speeds))
    assert compact[6] == pytest.approx(np.mean(pd.speed_change_rates))
    assert compact[7] == pytest.approx(np.mean(np.abs(pd.speed_change_rates)))
    assert compact[8] == pytest.approx(np.max(np.abs(pd.speed_change_rates)))
    valid_cosines = pd.cosine_raw[pd.comparison_valid]
    assert compact[9] == pytest.approx(np.mean(valid_cosines))
    assert compact[10] == pytest.approx(np.mean(pd.comparison_valid))
    assert compact[11] == pytest.approx(
        float(efficiency_validity_flag(pd.length, pd.n_intervals, 0.0))
    )
    assert np.allclose(reps["speed_history"][: pd.n_intervals], pd.interval_speeds)
    assert np.allclose(reps["speed_history"][pd.n_intervals :], compact[3:9])
    matrix = pairwise_distance_matrix(diagrams, bottleneck_bruteforce)
    assert np.allclose(
        reps["complete_distances"], matrix[np.triu_indices(3, 1)]
    )


def test_empty_diagram_moments_are_zero():
    rng = np.random.default_rng(5)
    diagrams = [np.zeros((0, 2)) for _ in range(4)]
    stamps = np.linspace(0.0, 1.0, 4)
    traj = FakeTrajectory("A", rng.normal(size=(4, 8, 2)), stamps)
    reps = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    assert np.all(reps["moments_flat"] == 0.0)
    assert np.all(reps["moments_summary"] == 0.0)
    assert np.all(reps["moment_signature"] == 0.0)


def test_complete_distances_and_recurrence_on_known_singletons():
    n = 9
    diagrams = singleton_diagrams(n, start=0.0, step=1.0, lifespan=20.0)
    stamps = np.linspace(0.0, 1.0, n)
    traj = FakeTrajectory("A", np.zeros((n, 2, 2)), stamps)
    known = np.abs(np.arange(n, dtype=float)[:, None] - np.arange(n, dtype=float))
    reps = build_representations(
        traj,
        diagrams,
        0,
        bottleneck_bruteforce,
        timestamps=stamps,
        distance_matrix=known,
    )
    assert reps["complete_distances"].size == n * (n - 1) // 2
    assert np.allclose(
        reps["complete_distances"], known[np.triu_indices(n, 1)]
    )
    expected = []
    for lag in (1, 2, 4, 8):
        values = np.array([known[i, i + lag] for i in range(n - lag)])
        expected.extend([np.mean(values), np.min(values)])
    expected.append(known[0, n - 1])
    assert np.allclose(reps["recurrence_summary"], expected)


def test_recurrence_lag_without_pairs_is_nan():
    n = 6
    diagrams = singleton_diagrams(n)
    stamps = np.linspace(0.0, 1.0, n)
    traj = FakeTrajectory("A", np.zeros((n, 2, 2)), stamps)
    known = np.abs(np.arange(n, dtype=float)[:, None] - np.arange(n, dtype=float))
    reps = build_representations(
        traj,
        diagrams,
        0,
        bottleneck_bruteforce,
        timestamps=stamps,
        distance_matrix=known,
    )
    assert np.isnan(reps["recurrence_summary"][6])
    assert np.isnan(reps["recurrence_summary"][7])
    assert np.isfinite(reps["recurrence_summary"][4])


def test_no_unexpected_nan_for_generic_case():
    rng = np.random.default_rng(20260920)
    n = 12
    diagrams = random_diagrams(rng, n, 3)
    stamps = np.linspace(0.0, 1.0, n)
    traj = FakeTrajectory("A", rng.normal(size=(n, 16, 2)), stamps)
    reps = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    assert tuple(reps.keys()) == REPRESENTATIONS
    for name in REPRESENTATIONS:
        vector = reps[name]
        assert vector.ndim == 1
        assert vector.dtype == np.float64
        assert np.all(np.isfinite(vector)), name
    assert reps["compact"][10] == pytest.approx(1.0)
    assert reps["compact"][11] == pytest.approx(1.0)


def test_zero_length_path_nan_policy():
    rng = np.random.default_rng(4)
    diagram = np.array([[0.0, 1.0], [2.0, 2.5]])
    diagrams = [diagram.copy() for _ in range(5)]
    stamps = np.linspace(0.0, 1.0, 5)
    traj = FakeTrajectory("A", rng.normal(size=(5, 6, 2)), stamps)
    reps = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    compact = reps["compact"]
    assert compact[0] == 0.0
    assert compact[1] == 0.0
    assert np.isnan(compact[2])
    assert compact[3] == 0.0
    assert compact[6] == 0.0
    assert np.isnan(compact[9])
    assert compact[10] == 0.0
    assert compact[11] == 0.0


def test_floor_semantics_and_abstention():
    rng = np.random.default_rng(13)
    diagrams = random_diagrams(rng, 6, 2)
    stamps = np.linspace(0.0, 1.0, 6)
    traj = FakeTrajectory("A", rng.normal(size=(6, 8, 2)), stamps)
    default = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    zero = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, floor_e=0.0, timestamps=stamps
    )
    assert np.allclose(default["compact"], zero["compact"], equal_nan=True)
    high = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, floor_e=10.0, timestamps=stamps
    )
    assert np.isnan(high["compact"][9])
    assert high["compact"][10] == 0.0
    assert high["compact"][11] == 0.0


def test_family_b_geometry_dimensions_and_finiteness():
    rng = np.random.default_rng(17)
    n = 10
    frames = rng.normal(size=(n, 8, 8))
    diagrams = random_diagrams(rng, n, 2)
    stamps = np.linspace(0.0, 1.0, n)
    traj = FakeTrajectory("B", frames, stamps)
    reps = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    assert reps["raw_geometry_flat"].size == 4 * n
    assert reps["raw_geometry_summary"].size == 8
    assert np.all(np.isfinite(reps["raw_geometry_flat"]))
    assert np.all(np.isfinite(reps["raw_geometry_summary"]))


def test_representation_dimensions_for_master_and_stride4():
    rng = np.random.default_rng(123)
    for n in (129, 33):
        diagrams = singleton_diagrams(n)
        stamps = np.arange(n) / 128.0
        traj = FakeTrajectory("A", rng.normal(size=(n, 8, 2)), stamps)
        known = np.zeros((n, n))
        reps = build_representations(
            traj,
            diagrams,
            0,
            bottleneck_bruteforce,
            timestamps=stamps,
            distance_matrix=known,
        )
        assert reps["compact"].size == 12
        assert reps["speed_history"].size == n - 1 + 6
        assert reps["complete_distances"].size == n * (n - 1) // 2
        assert reps["recurrence_summary"].size == 9
        assert reps["raw_geometry_flat"].size == 6 * n
        assert reps["raw_geometry_summary"].size == 12
        assert reps["moments_flat"].size == 6 * n
        assert reps["moments_summary"].size == 12
        assert reps["moment_signature"].size == 42
        assert reps["moment_signature_time"].size == 56


def test_library_metric_path_matches_bruteforce_on_small_diagrams():
    rng = np.random.default_rng(19)
    diagrams = random_diagrams(rng, 5, 1)
    stamps = np.linspace(0.0, 1.0, 5)
    traj = FakeTrajectory("A", rng.normal(size=(5, 6, 2)), stamps)
    exact = build_representations(
        traj, diagrams, 0, bottleneck_bruteforce, timestamps=stamps
    )
    library = build_representations(
        traj, diagrams, 0, bottleneck_linf, timestamps=stamps
    )
    assert np.allclose(exact["compact"], library["compact"], equal_nan=True)
    assert np.allclose(
        exact["complete_distances"], library["complete_distances"], atol=1e-9
    )
