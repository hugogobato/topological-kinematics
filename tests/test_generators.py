"""Tests for the frozen trajectory generators and split namespaces (WP-1.2)."""

import csv
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from tk_pilot.generators import (
    CONTROLS,
    FAMILY_IDS,
    LABEL_IDS,
    MASTER_ORDER,
    SCIENTIFIC_CLASSES,
    build_control,
    build_trajectory,
    family_id,
    label_id,
    load_trajectory,
    save_trajectory,
    sigma_tag,
    trajectory_id,
)
from tk_pilot.splits import split_for_base_seed, write_split_manifest


def bitwise_equal(left: np.ndarray, right: np.ndarray) -> bool:
    return left.shape == right.shape and left.tobytes() == right.tobytes()


@pytest.mark.parametrize("family,point_shape", [("A", (64, 2)), ("B", (32, 32))])
def test_master_grid_and_stride_subsampling(family, point_shape):
    master = build_trajectory(family, "return", 1000, 0.0, 1)
    assert master.trajectory_id == f"{family}_return_1000_sigma0"
    assert master.family == family
    assert master.label == "return"
    assert master.base_seed == 1000
    assert master.sigma == 0.0
    assert master.stride == 1
    assert master.frames.shape == (129, *point_shape)
    assert master.frames.dtype == np.float64
    assert master.timestamps.shape == (129,)
    assert master.timestamps.dtype == np.float64
    assert master.z.shape == (129,)
    assert bitwise_equal(master.timestamps, np.arange(129, dtype=np.float64) / 128.0)
    for stride, count in ((2, 65), (4, 33)):
        subsampled = build_trajectory(family, "return", 1000, 0.0, stride)
        assert subsampled.frames.shape == (count, *point_shape)
        assert subsampled.stride == stride
        assert bitwise_equal(subsampled.frames, master.frames[::stride])
        assert bitwise_equal(subsampled.timestamps, master.timestamps[::stride])
        assert bitwise_equal(subsampled.z, master.z[::stride])
        assert subsampled.latent == master.latent


@pytest.mark.parametrize(
    "family,label,sigma,stride",
    [("A", "return", 0.05, 1), ("A", "jump", 0.0, 4), ("B", "ramp", 0.05, 2)],
)
def test_bitwise_determinism_on_rerun(family, label, sigma, stride):
    first = build_trajectory(family, label, 2024, sigma, stride)
    second = build_trajectory(family, label, 2024, sigma, stride)
    assert first.trajectory_id == second.trajectory_id
    assert bitwise_equal(first.frames, second.frames)
    assert bitwise_equal(first.timestamps, second.timestamps)
    assert bitwise_equal(first.z, second.z)
    assert first.latent == second.latent


def test_latents_differ_across_labels_at_same_seed():
    latents_a = [build_trajectory("A", name, 1000, 0.0).latent for name in SCIENTIFIC_CLASSES]
    assert latents_a[0] != latents_a[1]
    assert latents_a[1] != latents_a[2]
    assert latents_a[0] != latents_a[2]
    latents_b = [build_trajectory("B", name, 1000, 0.0).latent for name in SCIENTIFIC_CLASSES]
    assert latents_b[0] != latents_b[1]
    assert latents_b[1] != latents_b[2]
    assert latents_b[0] != latents_b[2]


def test_latent_draw_ranges():
    latent_a = build_trajectory("A", "return", 321, 0.0).latent
    for key in ("a", "b", "m", "phi", "r"):
        assert isinstance(latent_a[key], float)
    assert 0.15 <= latent_a["a"] <= 0.25
    assert 0.75 <= latent_a["b"] <= 0.85
    assert latent_a["m"] == pytest.approx(0.5 * (latent_a["a"] + latent_a["b"]))
    assert 0.9 <= latent_a["r"] <= 1.1
    assert len(latent_a["phases"]) == 2
    latent_b = build_trajectory("B", "return", 321, 0.0).latent
    assert 0.9 <= latent_b["A1"] <= 1.1
    assert 0.9 <= latent_b["A2"] <= 1.1
    assert 0.35 <= latent_b["w"] <= 0.45


def test_sigma_zero_family_a_points_stay_on_circles():
    trajectory = build_trajectory("A", "return", 1000, 0.0)
    z = trajectory.z
    phi = trajectory.latent["phi"]
    radius = trajectory.latent["r"]
    rotation = np.array(
        [[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]]
    )
    left_centers = np.column_stack([-0.5 * z, np.zeros_like(z)]) @ rotation.T
    right_centers = np.column_stack([0.5 * z, np.zeros_like(z)]) @ rotation.T
    left = np.linalg.norm(
        trajectory.frames[:, :32, :] - left_centers[:, None, :], axis=-1
    )
    right = np.linalg.norm(
        trajectory.frames[:, 32:, :] - right_centers[:, None, :], axis=-1
    )
    assert np.allclose(left, radius, rtol=0.0, atol=1e-12)
    assert np.allclose(right, radius, rtol=0.0, atol=1e-12)
    noisy = build_trajectory("A", "return", 1000, 0.05)
    noisy_left = np.linalg.norm(
        noisy.frames[:, :32, :] - left_centers[:, None, :], axis=-1
    )
    assert float(np.max(np.abs(noisy_left - radius))) > 1e-3


def test_sigma_zero_family_b_field_is_analytic():
    trajectory = build_trajectory("B", "jump", 1000, 0.0)
    axis = np.linspace(-4.0, 4.0, 32)
    grid_x, grid_y = np.meshgrid(axis, axis)
    z = trajectory.z
    width = 2.0 * trajectory.latent["w"] ** 2
    expected = trajectory.latent["A1"] * np.exp(
        -((grid_x[None] + 0.5 * z[:, None, None]) ** 2 + grid_y[None] ** 2) / width
    ) + trajectory.latent["A2"] * np.exp(
        -((grid_x[None] - 0.5 * z[:, None, None]) ** 2 + grid_y[None] ** 2) / width
    )
    assert np.allclose(trajectory.frames, expected, rtol=0.0, atol=1e-12)
    noisy = build_trajectory("B", "jump", 1000, 0.05)
    assert float(np.max(np.abs(noisy.frames - expected))) > 1e-3


@pytest.mark.parametrize("family", ["A", "B"])
@pytest.mark.parametrize("sigma", [0.0, 0.05])
def test_static_control_has_constant_z(family, sigma):
    static = build_control("static", family, 1000, sigma)
    assert static.label == "static"
    assert static.stride == 1
    assert static.frames.shape[0] == MASTER_ORDER + 1
    assert bitwise_equal(static.z, np.full(MASTER_ORDER + 1, 0.5))
    assert static.trajectory_id == f"{family}_static_1000_sigma{sigma_tag(sigma)}"


def test_translation_control_matches_static_realization():
    static = build_control("static", "A", 1000, 0.05)
    translation = build_control("translation", "A", 1000, 0.05)
    assert translation.latent == static.latent
    for key in ("phi", "r", "phases", "a", "b", "m"):
        assert translation.latent[key] == static.latent[key]
    times = static.timestamps
    tau = np.column_stack(
        [0.5 * np.sin(2.0 * np.pi * times), 0.25 * np.cos(2.0 * np.pi * times)]
    )
    assert bitwise_equal(translation.frames, static.frames + tau[:, None, :])
    assert bitwise_equal(translation.z, static.z)
    assert translation.trajectory_id == "A_translation_1000_sigma50"
    subsampled = build_control("translation", "A", 1000, 0.05, 2)
    assert subsampled.frames.shape[0] == 65
    assert bitwise_equal(subsampled.frames, translation.frames[::2])
    with pytest.raises(ValueError):
        build_control("translation", "B", 1000, 0.05)


def test_matched_controls_share_latents_and_match_steps():
    forward = build_control("matched_forward", "A", 1000, 0.05)
    folded = build_control("matched_folded", "A", 1000, 0.05)
    assert forward.frames.shape == (5, 64, 2)
    assert bitwise_equal(
        forward.timestamps, np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    )
    assert np.array_equal(forward.z, np.array([0.5, 1.0, 1.5, 1.0, 0.5]))
    assert np.array_equal(folded.z, np.array([0.5, 1.0, 0.5, 1.0, 0.5]))
    assert np.array_equal(np.abs(np.diff(forward.z)), np.abs(np.diff(folded.z)))
    assert forward.z[0] == folded.z[0]
    assert forward.z[-1] == folded.z[-1]
    assert forward.latent == folded.latent
    assert bitwise_equal(forward.frames[0], folded.frames[0])
    assert bitwise_equal(forward.frames[-1], folded.frames[-1])
    assert not np.array_equal(forward.frames[2], folded.frames[2])
    subsampled = build_control("matched_folded", "A", 1000, 0.05, 2)
    assert bitwise_equal(subsampled.frames, folded.frames[::2])
    assert bitwise_equal(subsampled.z, folded.z[::2])
    with pytest.raises(ValueError):
        build_control("matched_folded", "B", 1000, 0.05)


@pytest.mark.parametrize(
    "family,label,sigma,stride",
    [("A", "return", 0.05, 2), ("B", "jump", 0.0, 1), ("B", "ramp", 0.05, 2)],
)
def test_save_load_round_trip(tmp_path, family, label, sigma, stride):
    trajectory = build_trajectory(family, label, 1234, sigma, stride)
    directory = save_trajectory(trajectory, tmp_path)
    assert (directory / "trajectory.npz").is_file()
    assert (directory / "meta.json").is_file()
    assert (directory / "SHA256SUMS").is_file()
    loaded = load_trajectory(family, label, 1234, sigma, stride, tmp_path)
    assert loaded.trajectory_id == trajectory.trajectory_id
    assert loaded.family == family
    assert loaded.label == label
    assert loaded.base_seed == 1234
    assert loaded.sigma == sigma
    assert loaded.stride == stride
    assert loaded.latent == trajectory.latent
    assert bitwise_equal(loaded.frames, trajectory.frames)
    assert bitwise_equal(loaded.timestamps, trajectory.timestamps)
    assert bitwise_equal(loaded.z, trajectory.z)


def test_save_load_control_round_trip(tmp_path):
    translation = build_control("translation", "A", 1000, 0.05)
    save_trajectory(translation, tmp_path)
    loaded = load_trajectory("A", "translation", 1000, 0.05, 1, tmp_path)
    assert loaded.trajectory_id == translation.trajectory_id
    assert loaded.latent == translation.latent
    assert bitwise_equal(loaded.frames, translation.frames)
    assert bitwise_equal(loaded.timestamps, translation.timestamps)
    assert bitwise_equal(loaded.z, translation.z)


def test_load_missing_cache_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_trajectory("A", "return", 9999, 0.05, 1, tmp_path)


def test_generator_and_diagram_caches_coexist(tmp_path):
    from tk_pilot.persistence import load_diagram_cache, save_diagram_cache

    trajectory = build_control("matched_forward", "A", 1000, 0.05)
    directory = save_trajectory(trajectory, tmp_path)
    stride_directory = directory.parent
    assert directory.name == "trajectory"
    save_diagram_cache(trajectory, tmp_path)
    assert (stride_directory / "diagrams.npz").is_file()
    assert (stride_directory / "essential.npz").is_file()
    assert (stride_directory / "meta.json").is_file()
    assert (stride_directory / "SHA256SUMS").is_file()
    loaded = load_trajectory("A", "matched_forward", 1000, 0.05, 1, tmp_path)
    assert bitwise_equal(loaded.frames, trajectory.frames)
    cached = load_diagram_cache(trajectory, tmp_path)
    assert len(cached["diagrams"][0]) == 5
    assert len(cached["diagrams"][1]) == 5


def test_trajectory_identifiers_and_seed_ids():
    assert trajectory_id("A", "return", 1000, 0.0) == "A_return_1000_sigma0"
    assert trajectory_id("B", "jump", 2000, 0.05) == "B_jump_2000_sigma50"
    assert sigma_tag(0.0) == 0
    assert sigma_tag(0.05) == 50
    assert family_id("A") == 0
    assert family_id("B") == 1
    assert [label_id(name) for name in SCIENTIFIC_CLASSES] == [0, 1, 2]
    assert label_id("static") == 3
    assert label_id("translation") == 4
    assert label_id("matched_forward") == 5
    assert label_id("matched_folded") == 6
    assert FAMILY_IDS == {"A": 0, "B": 1}
    assert LABEL_IDS["return"] == 0
    assert CONTROLS == ("static", "translation", "matched_forward", "matched_folded")
    with pytest.raises(ValueError):
        family_id("C")
    with pytest.raises(ValueError):
        label_id("unknown")


def test_invalid_arguments_are_rejected():
    with pytest.raises(ValueError):
        build_trajectory("C", "return", 1000, 0.0)
    with pytest.raises(ValueError):
        build_trajectory("A", "translation", 1000, 0.0)
    with pytest.raises(ValueError):
        build_trajectory("A", "return", 1000, -0.05)
    with pytest.raises(ValueError):
        build_trajectory("A", "return", 1000, 0.0, 0)
    with pytest.raises(ValueError):
        build_control("unknown", "A", 1000, 0.0)
    with pytest.raises(ValueError):
        build_control("static", "C", 1000, 0.0)


def test_split_for_base_seed():
    assert split_for_base_seed(1000) == "train"
    assert split_for_base_seed(1039) == "train"
    assert split_for_base_seed(1040) is None
    assert split_for_base_seed(2000) == "validation"
    assert split_for_base_seed(2019) == "validation"
    assert split_for_base_seed(2020) is None
    assert split_for_base_seed(3000) == "test_exploratory"
    assert split_for_base_seed(3039) == "test_exploratory"
    assert split_for_base_seed(3040) is None
    assert split_for_base_seed(9999) is None
    assert split_for_base_seed(10000) == "test_confirmatory"
    assert split_for_base_seed(123456) == "test_confirmatory"
    assert split_for_base_seed(11) is None


def _manifest_config():
    return {
        "seed_namespaces": {
            "train": [1000, 1039],
            "validation": [2000, 2019],
            "test_exploratory": [3000, 3039],
            "test_confirmatory_start": 10000,
        },
        "families": ["A", "B"],
        "classes": ["return", "ramp", "jump"],
        "sigmas": [0.0, 0.05],
        "strides": [1, 2, 4],
    }


def test_write_split_manifest(tmp_path):
    config = _manifest_config()
    out_path = tmp_path / "splits" / "split_manifest.csv"
    written = write_split_manifest(config, out_path)
    assert written == out_path
    with out_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "trajectory_id",
            "base_seed",
            "family",
            "class",
            "sigma",
            "stride",
            "split",
            "cluster_id",
        ]
        rows = list(reader)
    assert len(rows) == (40 + 20 + 40) * 2 * 3 * 2 * 3
    seen: dict[str, str] = {}
    for row in rows:
        assert row["split"] == split_for_base_seed(int(row["base_seed"]))
        assert row["cluster_id"] == f"{row['family']}_{row['class']}_{row['base_seed']}"
        assert row["trajectory_id"] == trajectory_id(
            row["family"], row["class"], int(row["base_seed"]), float(row["sigma"])
        )
        previous = seen.setdefault(row["trajectory_id"], row["split"])
        assert previous == row["split"]
    assert set(seen.values()) == {"train", "validation", "test_exploratory"}
    config["seed_namespaces"]["test_confirmatory_count"] = 2
    confirmatory_path = write_split_manifest(
        config, tmp_path / "splits" / "split_manifest_confirmatory.csv"
    )
    with confirmatory_path.open(newline="", encoding="utf-8") as handle:
        expanded = list(csv.DictReader(handle))
    assert len(expanded) - len(rows) == 2 * 2 * 3 * 2 * 3
    confirmatory = [row for row in expanded if row["split"] == "test_confirmatory"]
    assert {int(row["base_seed"]) for row in confirmatory} == {10000, 10001}


def test_package_import_stays_lightweight():
    src = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import sys\n"
        "import tk_pilot\n"
        "heavy = [name for name in "
        "('gudhi', 'persim', 'sklearn', 'pandas', 'matplotlib', 'joblib', 'yaml') "
        "if name in sys.modules]\n"
        "print(','.join(heavy))\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(src)
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    assert completed.stdout.strip() == ""
