"""Tests for the persistence extraction, cache, and pooling layer (WP-2.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import gudhi
import numpy as np
import pytest

from tk_pilot.persistence import (
    diagrams_for_windows,
    family_a_diagram,
    family_b_diagram,
    finite_diagram,
    load_diagram_cache,
    pool_window,
    save_diagram_cache,
    trajectory_diagrams,
    trajectory_essential_counts,
)

SQUARE = np.array(
    [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]], dtype=float
)


@dataclass(frozen=True)
class _StubTrajectory:
    family: str
    label: str
    base_seed: int
    sigma: float
    stride: int
    timestamps: np.ndarray
    frames: np.ndarray


def _family_b_field(z: float, a1: float = 1.0, a2: float = 1.0, w: float = 0.4):
    x = np.linspace(-4.0, 4.0, 32)
    xx, yy = np.meshgrid(x, x)
    left = a1 * np.exp(-(((xx + z / 2.0) ** 2 + yy ** 2) / (2.0 * w ** 2)))
    right = a2 * np.exp(-(((xx - z / 2.0) ** 2 + yy ** 2) / (2.0 * w ** 2)))
    return left + right


def _stub(frames: np.ndarray, family: str = "A", **overrides) -> _StubTrajectory:
    n_frames = frames.shape[0]
    defaults = {
        "family": family,
        "label": "return",
        "base_seed": 1000,
        "sigma": 0.05,
        "stride": 2,
        "timestamps": np.linspace(0.0, 1.0, n_frames),
        "frames": frames,
    }
    defaults.update(overrides)
    return _StubTrajectory(**defaults)


def test_finite_diagram_empty_and_essential_stripping():
    finite, n_essential = finite_diagram([])
    assert finite.shape == (0, 2)
    assert finite.dtype == np.float64
    assert n_essential == 0

    finite, n_essential = finite_diagram([[0.0, np.inf], [1.0, np.inf]])
    assert finite.shape == (0, 2)
    assert n_essential == 2

    raw = [[1.0, 3.0], [0.0, np.inf], [0.5, 2.0], [0.5, 1.0]]
    finite, n_essential = finite_diagram(raw)
    assert n_essential == 1
    assert finite.dtype == np.float64
    assert np.array_equal(finite, np.array([[0.5, 1.0], [0.5, 2.0], [1.0, 3.0]]))


def test_finite_diagram_rejects_invalid_bars():
    for raw in ([[1.0, 0.0]], [[0.0, np.nan]], [[0.0, -np.inf]], [[np.inf, np.inf]]):
        with pytest.raises(ValueError):
            finite_diagram(raw)


def test_family_a_square_h0_analytic():
    diagram, n_essential = family_a_diagram(SQUARE, 0)
    assert n_essential == 1
    assert diagram.shape == (3, 2)
    assert np.allclose(diagram, np.array([[0.0, 1.0]] * 3), rtol=0.0, atol=1e-12)
    assert diagram[0, 1] == pytest.approx(1.0, abs=1e-12)


def test_family_a_square_h1_analytic():
    diagram, n_essential = family_a_diagram(SQUARE, 1)
    assert n_essential == 0
    assert diagram.shape == (1, 2)
    assert diagram[0, 0] == pytest.approx(1.0, abs=1e-12)
    assert diagram[0, 1] == pytest.approx(np.sqrt(2.0), abs=1e-12)


def test_family_a_h0_segment_stable_over_five_frames():
    frames = np.stack([SQUARE] * 5)
    diagrams = trajectory_diagrams(frames, "A")
    essential = trajectory_essential_counts(frames, "A")
    assert set(diagrams) == {0, 1}
    assert set(essential) == {0, 1}
    assert essential[0] == [1, 1, 1, 1, 1]
    assert essential[1] == [0, 0, 0, 0, 0]
    assert len(diagrams[0]) == 5
    assert len(diagrams[1]) == 5
    for diagram in diagrams[0]:
        assert np.array_equal(diagram, diagrams[0][0])
    for diagram in diagrams[1]:
        assert np.array_equal(diagram, diagrams[1][0])


def test_family_b_separation_limit():
    separated, n_separated = family_b_diagram(_family_b_field(3.0), 0)
    assert n_separated == 1
    assert separated.shape == (1, 2)
    persistence = float(separated[0, 1] - separated[0, 0])
    assert persistence == pytest.approx(0.927, abs=2e-2)

    merged, n_merged = family_b_diagram(_family_b_field(0.5), 0)
    assert n_merged == 1
    assert merged.shape == (0, 2)


def test_trajectory_diagrams_match_single_frame_extraction():
    frames_b = np.stack([_family_b_field(0.5), _family_b_field(3.0)])
    diagrams_b = trajectory_diagrams(frames_b, "B", degrees=(0, 1))
    for index, frame in enumerate(frames_b):
        for degree in (0, 1):
            expected, _ = family_b_diagram(frame, degree)
            assert np.array_equal(diagrams_b[degree][index], expected)

    frames_a = np.stack([SQUARE, SQUARE + 0.5])
    diagrams_a = trajectory_diagrams(frames_a, "A", degrees=(0, 1))
    for index, frame in enumerate(frames_a):
        for degree in (0, 1):
            expected, _ = family_a_diagram(frame, degree)
            assert np.array_equal(diagrams_a[degree][index], expected)


def test_invalid_family_rejected():
    with pytest.raises(ValueError):
        trajectory_diagrams([SQUARE], "C")
    with pytest.raises(ValueError):
        trajectory_essential_counts([SQUARE], "C")
    with pytest.raises(ValueError):
        pool_window([SQUARE], "C", 1, 1)


def test_cache_roundtrip_bitwise_and_layout(tmp_path):
    frames = np.stack([SQUARE, SQUARE + 0.25, SQUARE - 0.25])
    traj = _stub(frames)
    cache_dir = save_diagram_cache(traj, tmp_path)
    expected_dir = tmp_path / "A" / "return" / "1000" / "sigma50" / "stride2"
    assert cache_dir == expected_dir
    for name in ("diagrams.npz", "essential.npz", "meta.json", "SHA256SUMS"):
        assert (expected_dir / name).is_file()

    loaded = load_diagram_cache(traj, tmp_path)
    in_memory = trajectory_diagrams(frames, "A")
    counts = trajectory_essential_counts(frames, "A")
    assert set(loaded["diagrams"]) == {0, 1}
    assert set(loaded["essential"]) == {0, 1}
    for degree in (0, 1):
        assert len(loaded["diagrams"][degree]) == 3
        for stored, fresh in zip(loaded["diagrams"][degree], in_memory[degree]):
            assert stored.dtype == np.float64
            assert stored.tobytes() == fresh.tobytes()
        assert loaded["essential"][degree] == counts[degree]

    assert loaded["meta"]["frame_count"] == 3
    assert loaded["meta"]["degrees"] == [0, 1]
    assert loaded["meta"]["gudhi_version"] == gudhi.__version__
    np.testing.assert_array_equal(loaded["meta"]["timestamps"], traj.timestamps)


def test_cache_files_are_bitwise_deterministic(tmp_path):
    traj = _stub(np.stack([SQUARE, SQUARE + 0.25]))
    first = save_diagram_cache(traj, tmp_path / "one")
    second = save_diagram_cache(traj, tmp_path / "two")
    for name in ("diagrams.npz", "essential.npz", "meta.json", "SHA256SUMS"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_cache_tampering_detected(tmp_path):
    traj = _stub(np.stack([SQUARE, SQUARE + 0.25]))

    diagram_root = tmp_path / "diagram_tamper"
    cache_dir = save_diagram_cache(traj, diagram_root)
    diagram_path = cache_dir / "diagrams.npz"
    with np.load(diagram_path) as stored:
        arrays = {key: stored[key] for key in stored.files}
    arrays["d0_000"] = np.array([[0.0, 999.0]])
    np.savez(diagram_path, **arrays)
    with pytest.raises(ValueError):
        load_diagram_cache(traj, diagram_root)

    meta_root = tmp_path / "meta_tamper"
    cache_dir = save_diagram_cache(traj, meta_root)
    meta_path = cache_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["frame_count"] = 99
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError):
        load_diagram_cache(traj, meta_root)


def test_pool_window_identity_and_end_times():
    frames_a = np.arange(11 * 2 * 3, dtype=float).reshape(11, 2, 3)
    pooled, times = pool_window(frames_a, "A", 1, 1)
    assert np.array_equal(pooled, frames_a)
    np.testing.assert_array_equal(times, np.arange(11, dtype=float))

    pooled3, times3 = pool_window(frames_a, "A", 3, 2)
    assert pooled3.shape == (5, 6, 3)
    np.testing.assert_array_equal(times3, np.array([2.0, 4.0, 6.0, 8.0, 10.0]))
    assert np.array_equal(pooled3[0], frames_a[0:3].reshape(6, 3))
    assert np.array_equal(pooled3[-1], frames_a[8:11].reshape(6, 3))

    pooled5, times5 = pool_window(frames_a, "A", 5, 4)
    assert pooled5.shape[0] == 2
    np.testing.assert_array_equal(times5, np.array([4.0, 8.0]))

    frames_b = np.arange(11 * 4 * 4, dtype=float).reshape(11, 4, 4)
    pooled_b1, times_b1 = pool_window(frames_b, "B", 1, 1)
    assert np.array_equal(pooled_b1, frames_b)
    np.testing.assert_array_equal(times_b1, np.arange(11, dtype=float))
    pooled_b3, times_b3 = pool_window(frames_b, "B", 3, 2)
    assert pooled_b3.shape == (5, 4, 4)
    assert np.array_equal(pooled_b3[0], frames_b[0:3].mean(axis=0))
    assert np.array_equal(pooled_b3[-1], frames_b[8:11].mean(axis=0))
    np.testing.assert_array_equal(times_b3, times3)


def test_pool_window_rejects_unsupported_arguments():
    frames = np.zeros((5, 2, 2))
    with pytest.raises(ValueError):
        pool_window(frames, "A", 2, 1)
    with pytest.raises(ValueError):
        pool_window(frames, "A", 1, 3)
    with pytest.raises(ValueError):
        pool_window(np.zeros((1, 2, 2)), "A", 3, 1)


def test_diagrams_for_windows_length_one_matches_trajectory():
    frames_a = np.stack([SQUARE, SQUARE + 0.1, SQUARE + 0.2])
    direct = trajectory_diagrams(frames_a, "A")
    windowed = diagrams_for_windows(frames_a, "A", 1, 1)
    assert set(direct) == set(windowed) == {0, 1}
    for degree in (0, 1):
        for expected, actual in zip(direct[degree], windowed[degree]):
            assert np.array_equal(expected, actual)

    frames_b = np.stack([_family_b_field(0.5), _family_b_field(3.0)])
    direct_b = trajectory_diagrams(frames_b, "B")
    windowed_b = diagrams_for_windows(frames_b, "B", 1, 1)
    for degree in (0, 1):
        for expected, actual in zip(direct_b[degree], windowed_b[degree]):
            assert np.array_equal(expected, actual)


def test_diagrams_for_windows_pools_then_extracts():
    frames = np.stack([SQUARE, SQUARE + 0.25, SQUARE + 0.5, SQUARE + 0.75])
    windowed = diagrams_for_windows(frames, "A", 3, 1)
    assert len(windowed[0]) == 2
    assert len(windowed[1]) == 2
    pooled, _ = pool_window(frames, "A", 3, 1)
    np.testing.assert_array_equal(
        windowed[0][0], trajectory_diagrams(pooled, "A")[0][0]
    )
