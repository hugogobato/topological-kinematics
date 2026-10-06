"""Tests for the matched-budget reversible-versus-drift generator."""

from __future__ import annotations

import numpy as np

from src.tk_pilot import generators, matched_budget


def test_matched_budget_is_identical_across_classes() -> None:
    budget = 0.7
    for seed in (4000, 4001, 4007):
        reversible = matched_budget.build_matched_trajectory(
            "reversible", "A", seed, 0.0, budget=budget
        )
        drift = matched_budget.build_matched_trajectory(
            "drift", "A", seed, 0.0, budget=budget
        )
        steps_r = np.abs(np.diff(reversible.z))
        steps_d = np.abs(np.diff(drift.z))
        np.testing.assert_allclose(np.sort(steps_r), np.sort(steps_d))
        assert np.isclose(np.sum(steps_r), budget)
        assert np.isclose(np.sum(steps_d), budget)
        assert reversible.z[0] == drift.z[0] == matched_budget.Z_BASE
        assert np.isclose(reversible.z[-1], matched_budget.Z_BASE, atol=1e-12)
        assert np.isclose(drift.z[-1], matched_budget.Z_BASE + budget, atol=1e-12)
        # both classes change only inside the shared window
        changed_r = np.nonzero(np.abs(np.diff(reversible.z)) > 0)[0]
        changed_d = np.nonzero(np.abs(np.diff(drift.z)) > 0)[0]
        np.testing.assert_array_equal(changed_r, changed_d)


def test_stride_variants_subsample_one_master_realization() -> None:
    full = matched_budget.build_matched_trajectory(
        "drift", "B", 4010, 0.05, stride=1, budget=0.5
    )
    half = matched_budget.build_matched_trajectory(
        "drift", "B", 4010, 0.05, stride=2, budget=0.5
    )
    np.testing.assert_array_equal(half.frames, full.frames[::2])
    np.testing.assert_array_equal(half.z, full.z[::2])
    np.testing.assert_array_equal(half.timestamps, full.timestamps[::2])


def test_raw_frames_and_noise_match_frozen_generator_conventions() -> None:
    trajectory = matched_budget.build_matched_trajectory(
        "reversible", "A", 4020, 0.0, stride=1, budget=0.3
    )
    assert trajectory.frames.shape == (generators.FRAMES_PER_MASTER, 64, 2)
    assert trajectory.timestamps.shape == (generators.FRAMES_PER_MASTER,)
    # sigma = 0 draws no noise, so the realization is deterministic
    again = matched_budget.build_matched_trajectory(
        "reversible", "A", 4020, 0.0, stride=1, budget=0.3
    )
    np.testing.assert_array_equal(trajectory.frames, again.frames)
