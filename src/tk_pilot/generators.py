"""Synthetic trajectory generators for the Topological Kinematics pilot.

Frozen conventions (``Pilot_Experiment_Specification.md`` section 1 and the
Phase-1 implementation contract sections 3 and 4):

- master clock ``u = j / 128`` for ``j = 0, ..., 128`` (129 frames); strides
  1, 2, 4 return the exact subsamples ``frames[::stride]`` of the master
  realization while the horizon ``[0, 1]`` stays fixed;
- latent RNG ``np.random.default_rng([base_seed, family_id, label_id, 101])``
  and noise RNG
  ``np.random.default_rng([base_seed, family_id, label_id, 202, sigma_tag])``
  with ``sigma_tag = int(round(sigma * 1000))``; at ``sigma = 0`` no noise is
  drawn or added;
- three scientific classes (return, ramp, jump) with ``z(u) = 0.5 + 2.5 g(u)``
  and, outside the three-class accuracy calculation, the controls static,
  translation, matched_forward, and matched_folded;
- Family A: two circles of 32 equally spaced points each with fixed phases,
  centers ``(-z/2, 0)`` and ``(z/2, 0)``, radius ``r``, entire configuration
  rotated by ``phi``, isotropic Gaussian coordinate noise;
- Family B: a fixed ``32 x 32`` grid on ``[-4, 4]^2`` and two Gaussian bumps
  separated by ``z``, additive pixel noise;
- every array is ``float64`` and every stochastic draw is reproducible from
  the seed alone.

The translation control is the identical static Family A realization plus the
time-dependent offset ``tau(u) = (0.5 sin(2 pi u), 0.25 cos(2 pi u))``. Both
matched controls share one latent and noise realization keyed by
``matched_forward`` (label id 5) so that ``matched_forward`` and
``matched_folded`` differ only in the order of the explicit ``z`` sequence;
label id 6 stays assigned to ``matched_folded`` for identifiers and split
bookkeeping.

Cache layout:
``{cache_dir}/{family}/{label}/{base_seed}/sigma{tag}/stride{stride}/trajectory/``
holding ``trajectory.npz`` (keys ``frames``, ``timestamps``, ``z``, and
``latent_json``), ``meta.json``, and ``SHA256SUMS``. The extra ``trajectory``
level keeps these files disjoint from the frozen diagram cache written by
:mod:`tk_pilot.persistence` in the parent stride directory.
"""

from __future__ import annotations

import hashlib
import json
import fcntl
import contextlib
import random
import time
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = [
    "CONTROLS",
    "FAMILY_B_EXTENT",
    "FAMILY_B_SIDE",
    "FAMILY_IDS",
    "FRAMES_PER_MASTER",
    "LABEL_IDS",
    "MASTER_ORDER",
    "POINTS_PER_FRAME",
    "SCIENTIFIC_CLASSES",
    "Trajectory",
    "build_control",
    "build_trajectory",
    "family_id",
    "label_id",
    "load_trajectory",
    "save_trajectory",
    "sigma_tag",
    "trajectory_id",
]

MASTER_ORDER = 128
FRAMES_PER_MASTER = MASTER_ORDER + 1
POINTS_PER_CIRCLE = 32
POINTS_PER_FRAME = 2 * POINTS_PER_CIRCLE
FAMILY_B_SIDE = 32
FAMILY_B_EXTENT = 4.0

FAMILY_IDS = {"A": 0, "B": 1}
LABEL_IDS = {
    "return": 0,
    "ramp": 1,
    "jump": 2,
    "static": 3,
    "translation": 4,
    "matched_forward": 5,
    "matched_folded": 6,
}
SCIENTIFIC_CLASSES = ("return", "ramp", "jump")
CONTROLS = ("static", "translation", "matched_forward", "matched_folded")
MATCHED_TIMES = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float64)
MATCHED_Z = {
    "matched_forward": np.array([0.5, 1.0, 1.5, 1.0, 0.5], dtype=np.float64),
    "matched_folded": np.array([0.5, 1.0, 0.5, 1.0, 0.5], dtype=np.float64),
}
CIRCLE_ANGLES = (
    (2.0 * np.pi)
    * np.arange(POINTS_PER_CIRCLE, dtype=np.float64)
    / float(POINTS_PER_CIRCLE)
)
TRAJECTORY_NPZ = "trajectory.npz"
META_JSON = "meta.json"
SHA256SUMS = "SHA256SUMS"


@dataclass(frozen=True)
class Trajectory:
    """One synthetic trajectory with its frozen latent parameters.

    ``frames`` is ``(n, 64, 2)`` for Family A and ``(n, 32, 32)`` for Family B,
    ``timestamps`` and ``z`` are ``(n,)``, and ``latent`` is a JSON-safe dict of
    the seed-driven parameters shared by every sigma and stride variant.
    """

    trajectory_id: str
    family: str
    label: str
    base_seed: int
    sigma: float
    stride: int
    timestamps: np.ndarray
    frames: np.ndarray
    z: np.ndarray
    latent: dict


def sigma_tag(sigma: float) -> int:
    """Frozen noise tag ``int(round(sigma * 1000))`` used in seeds and paths."""
    return int(round(float(sigma) * 1000.0))


def family_id(family: str) -> int:
    """Family seed id: A=0, B=1."""
    key = str(family)
    if key not in FAMILY_IDS:
        raise ValueError(f"family must be one of {tuple(FAMILY_IDS)}; got {family!r}")
    return FAMILY_IDS[key]


def label_id(label: str) -> int:
    """Label seed id: return=0 through matched_folded=6."""
    key = str(label)
    if key not in LABEL_IDS:
        raise ValueError(f"label must be one of {tuple(LABEL_IDS)}; got {label!r}")
    return LABEL_IDS[key]


def trajectory_id(family: str, label: str, base_seed: int, sigma: float) -> str:
    """Frozen trajectory identifier ``{family}_{label}_{seed}_sigma{tag}``."""
    family_id(family)
    label_id(label)
    return f"{family}_{label}_{int(base_seed)}_sigma{sigma_tag(sigma)}"


def _validate_stride(stride: int) -> int:
    step = int(stride)
    if step < 1:
        raise ValueError(f"stride must be a positive integer; got {stride!r}")
    return step


def _validate_sigma(sigma: float) -> float:
    value = float(sigma)
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"sigma must be finite and non-negative; got {sigma!r}")
    return value


def _latent_rng(base_seed: int, family: str, label: str) -> np.random.Generator:
    return np.random.default_rng(
        [int(base_seed), FAMILY_IDS[family], LABEL_IDS[label], 101]
    )


def _draw_latent(family: str, rng: np.random.Generator) -> dict:
    a = float(rng.uniform(0.15, 0.25))
    b = float(rng.uniform(0.75, 0.85))
    latent: dict = {"a": a, "b": b, "m": 0.5 * (a + b)}
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


def _control_program(label: str, u: np.ndarray, latent: dict) -> np.ndarray:
    a = float(latent["a"])
    b = float(latent["b"])
    m = float(latent["m"])
    if label == "return":
        g = np.zeros_like(u)
        rising = (u >= a) & (u <= m)
        falling = (u > m) & (u <= b)
        g[rising] = (u[rising] - a) / (m - a)
        g[falling] = (b - u[falling]) / (b - m)
        return g
    if label == "ramp":
        return np.clip((u - a) / (b - a), 0.0, 1.0)
    if label == "jump":
        return (u >= m).astype(np.float64)
    if label == "static":
        return np.zeros_like(u)
    raise ValueError(f"no control program for label {label!r}")


def _master_timestamps() -> np.ndarray:
    return np.arange(FRAMES_PER_MASTER, dtype=np.float64) / float(MASTER_ORDER)


def _family_a_points(z_values: np.ndarray, latent: dict) -> np.ndarray:
    phases = latent["phases"]
    theta = np.concatenate(
        [
            CIRCLE_ANGLES + float(phases[0]),
            CIRCLE_ANGLES + float(phases[1]),
        ]
    )
    radius = float(latent["r"])
    base = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
    signs = np.concatenate([-np.ones(POINTS_PER_CIRCLE), np.ones(POINTS_PER_CIRCLE)])
    offsets = np.column_stack([0.5 * z_values, np.zeros_like(z_values)])
    points = base[None, :, :] + signs[None, :, None] * offsets[:, None, :]
    phi = float(latent["phi"])
    rotation = np.array(
        [[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]],
        dtype=np.float64,
    )
    return points @ rotation.T


def _family_b_fields(z_values: np.ndarray, latent: dict) -> np.ndarray:
    axis = np.linspace(
        -FAMILY_B_EXTENT, FAMILY_B_EXTENT, FAMILY_B_SIDE, dtype=np.float64
    )
    grid_x, grid_y = np.meshgrid(axis, axis)
    half = 0.5 * np.asarray(z_values, dtype=np.float64)[:, None, None]
    width = 2.0 * float(latent["w"]) ** 2
    left = float(latent["A1"]) * np.exp(
        -(((grid_x[None, :, :] + half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    right = float(latent["A2"]) * np.exp(
        -(((grid_x[None, :, :] - half) ** 2) + grid_y[None, :, :] ** 2) / width
    )
    return left + right


def _draw_noise(
    family: str,
    n_frames: int,
    sigma: float,
    base_seed: int,
    family_key: int,
    label_key: int,
) -> np.ndarray | None:
    if sigma == 0.0:
        return None
    rng = np.random.default_rng(
        [int(base_seed), family_key, label_key, 202, sigma_tag(sigma)]
    )
    if family == "A":
        return rng.normal(0.0, sigma, size=(n_frames, POINTS_PER_FRAME, 2))
    return rng.normal(0.0, sigma, size=(n_frames, FAMILY_B_SIDE, FAMILY_B_SIDE))


def _master_frames(
    family: str,
    label: str,
    z_values: np.ndarray,
    latent: dict,
    sigma: float,
    base_seed: int,
) -> np.ndarray:
    if family == "A":
        frames = _family_a_points(z_values, latent)
    else:
        frames = _family_b_fields(z_values, latent)
    noise = _draw_noise(
        family,
        int(z_values.size),
        sigma,
        base_seed,
        FAMILY_IDS[family],
        LABEL_IDS[label],
    )
    if noise is not None:
        frames = frames + noise
    return np.ascontiguousarray(frames, dtype=np.float64)


def _subsample(
    frames: np.ndarray, timestamps: np.ndarray, z: np.ndarray, stride: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.ascontiguousarray(frames[::stride], dtype=np.float64),
        np.ascontiguousarray(timestamps[::stride], dtype=np.float64),
        np.ascontiguousarray(z[::stride], dtype=np.float64),
    )


def _make_trajectory(
    family: str,
    label: str,
    base_seed: int,
    sigma: float,
    stride: int,
    timestamps: np.ndarray,
    frames: np.ndarray,
    z: np.ndarray,
    latent: dict,
) -> Trajectory:
    return Trajectory(
        trajectory_id=trajectory_id(family, label, base_seed, sigma),
        family=family,
        label=label,
        base_seed=int(base_seed),
        sigma=float(sigma),
        stride=int(stride),
        timestamps=timestamps,
        frames=frames,
        z=z,
        latent=latent,
    )


def build_trajectory(
    family: str, label: str, base_seed: int, sigma: float, stride: int = 1
) -> Trajectory:
    """Build a scientific-class trajectory (return, ramp, jump) or static.

    The master realization is generated on the 129-frame clock and only then
    subsampled, so every stride variant is an exact subsample of the same
    realization for a fixed ``(base_seed, family, label, sigma)``.
    """
    family_id(family)
    name = str(label)
    if name not in SCIENTIFIC_CLASSES and name != "static":
        raise ValueError(
            f"build_trajectory supports {SCIENTIFIC_CLASSES + ('static',)}; "
            f"got {label!r}"
        )
    step = _validate_stride(stride)
    sig = _validate_sigma(sigma)
    seed = int(base_seed)
    latent = _draw_latent(family, _latent_rng(seed, family, name))
    timestamps = _master_timestamps()
    z = 0.5 + 2.5 * _control_program(name, timestamps, latent)
    frames = _master_frames(family, name, z, latent, sig, seed)
    frames, timestamps, z = _subsample(frames, timestamps, z, step)
    return _make_trajectory(family, name, seed, sig, step, timestamps, frames, z, latent)


def build_control(
    control: str, family: str, base_seed: int, sigma: float, stride: int = 1
) -> Trajectory:
    """Build one frozen control trajectory outside the three-class accuracy set.

    ``static`` keeps ``z = 0.5`` for both families. ``translation`` (Family A
    only) is the identical static realization plus the time-dependent offset
    ``tau(u) = (0.5 sin(2 pi u), 0.25 cos(2 pi u))``. ``matched_forward`` and
    ``matched_folded`` (Family A only) share one latent and noise realization
    and differ only in the order of the explicit five-frame ``z`` sequence.
    """
    family_id(family)
    if control not in CONTROLS:
        raise ValueError(f"control must be one of {CONTROLS}; got {control!r}")
    step = _validate_stride(stride)
    sig = _validate_sigma(sigma)
    seed = int(base_seed)
    if control == "static":
        return build_trajectory(family, "static", seed, sig, step)
    if control == "translation":
        if family != "A":
            raise ValueError("the translation control exists only for family A")
        static = build_trajectory("A", "static", seed, sig, 1)
        times = static.timestamps
        tau = np.column_stack(
            [0.5 * np.sin(2.0 * np.pi * times), 0.25 * np.cos(2.0 * np.pi * times)]
        )
        frames = static.frames + tau[:, None, :]
        frames, times, z = _subsample(frames, times, static.z, step)
        return _make_trajectory(
            "A", "translation", seed, sig, step, times, frames, z, dict(static.latent)
        )
    if family != "A":
        raise ValueError("the matched controls exist only for family A")
    latent = _draw_latent("A", _latent_rng(seed, "A", "matched_forward"))
    z_values = MATCHED_Z[control]
    frames = _family_a_points(z_values, latent)
    noise = _draw_noise(
        "A",
        int(z_values.size),
        sig,
        seed,
        FAMILY_IDS["A"],
        LABEL_IDS["matched_forward"],
    )
    if noise is not None:
        frames = frames + noise
    frames, times, z = _subsample(frames, MATCHED_TIMES, z_values, step)
    return _make_trajectory("A", control, seed, sig, step, times, frames, z, latent)


def _validated_frames(family: str, frames) -> np.ndarray:
    array = np.ascontiguousarray(frames, dtype=np.float64)
    if family == "A":
        expected = (POINTS_PER_FRAME, 2)
    elif family == "B":
        expected = (FAMILY_B_SIDE, FAMILY_B_SIDE)
    else:
        raise ValueError(f"family must be one of {tuple(FAMILY_IDS)}; got {family!r}")
    if array.ndim != 3 or array.shape[1:] != expected:
        raise ValueError(
            f"family {family} frames must have trailing shape {expected}; "
            f"got {array.shape}"
        )
    return array


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _cache_directory(
    family: str, label: str, base_seed: int, sigma: float, stride: int, cache_dir
) -> Path:
    return (
        Path(cache_dir)
        / str(family)
        / str(label)
        / str(int(base_seed))
        / f"sigma{sigma_tag(sigma)}"
        / f"stride{int(stride)}"
        / "trajectory"
    )


def _write_sha256sums(directory: Path, names: tuple[str, ...]) -> None:
    lines = [f"{_sha256_file(directory / name)}  {name}" for name in names]
    (directory / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _verify_sha256sums(directory: Path, names: tuple[str, ...]) -> None:
    sums_path = directory / SHA256SUMS
    if not sums_path.is_file():
        raise FileNotFoundError(f"missing checksum file: {sums_path}")
    entries: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"malformed checksum line in {sums_path}: {line!r}")
        digest, name = parts
        entries[name] = digest
    if set(entries) != set(names):
        raise ValueError(
            f"checksum file {sums_path} must cover {sorted(names)}; "
            f"got {sorted(entries)}"
        )
    for name in names:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"checksum entry has no file: {path}")
        actual = _sha256_file(path)
        if actual != entries[name]:
            raise ValueError(
                f"SHA256 mismatch for {path}: expected {entries[name]}, got {actual}"
            )



@contextlib.contextmanager
def _cache_lock(directory: Path):
    """Exclusive per-cache lock; serializes verify, repair, and commit."""
    lock_path = directory.parent / (directory.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def save_trajectory(traj: Trajectory, cache_dir: str | Path) -> Path:
    """Persist one trajectory and its metadata under the frozen cache layout.

    Writes ``trajectory.npz`` (``frames``, ``timestamps``, ``z``, and a JSON
    copy of ``latent``), ``meta.json``, and ``SHA256SUMS``. Returns the
    per-trajectory cache directory. A per-cache file lock serializes
    verification, repair, and commit across processes; writes are staged in a
    unique temporary directory and committed with an atomic rename, so
    concurrent workers can never observe a partially written cache. An existing
    valid cache is reused; an existing corrupt cache is removed and replaced.
    """
    directory = _cache_directory(
        traj.family, traj.label, traj.base_seed, traj.sigma, traj.stride, cache_dir
    )
    directory.parent.mkdir(parents=True, exist_ok=True)
    with _cache_lock(directory):
        if directory.exists():
            try:
                load_trajectory(
                    traj.family,
                    traj.label,
                    traj.base_seed,
                    traj.sigma,
                    traj.stride,
                    cache_dir,
                )
                return directory
            except Exception:
                shutil.rmtree(directory, ignore_errors=True)
        staging = directory.parent / (
            f".{directory.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        )
        staging.mkdir(parents=False, exist_ok=False)
        try:
            frames = _validated_frames(traj.family, traj.frames)
            timestamps = np.ascontiguousarray(traj.timestamps, dtype=np.float64)
            z = np.ascontiguousarray(traj.z, dtype=np.float64)
            if timestamps.shape != (frames.shape[0],) or z.shape != (frames.shape[0],):
                raise ValueError("timestamps and z must match the number of frames")
            npz_path = staging / TRAJECTORY_NPZ
            np.savez_compressed(
                npz_path,
                frames=frames,
                timestamps=timestamps,
                z=z,
                latent_json=json.dumps(traj.latent, sort_keys=True),
            )
            meta = {
                "trajectory_id": str(traj.trajectory_id),
                "family": str(traj.family),
                "label": str(traj.label),
                "base_seed": int(traj.base_seed),
                "sigma": float(traj.sigma),
                "stride": int(traj.stride),
                "frame_count": int(frames.shape[0]),
                "latent": traj.latent,
                "sha256_frames": _sha256_bytes(frames.tobytes()),
                "sha256_timestamps": _sha256_bytes(timestamps.tobytes()),
                "sha256_z": _sha256_bytes(z.tobytes()),
                "sha256_npz": _sha256_file(npz_path),
            }
            (staging / META_JSON).write_text(
                json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            _write_sha256sums(staging, (TRAJECTORY_NPZ, META_JSON))
            os.rename(staging, directory)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return directory


def load_trajectory(
    family: str,
    label: str,
    base_seed: int,
    sigma: float,
    stride: int,
    cache_dir: str | Path,
) -> Trajectory:
    """Load and verify a trajectory written by :func:`save_trajectory`.

    Every file listed in ``SHA256SUMS`` is verified before any array is
    returned, the metadata is checked against the requested keys, and the
    loaded frames are checked against the stored frames checksum.
    """
    family_id(family)
    name = str(label)
    if name not in LABEL_IDS:
        raise ValueError(f"label must be one of {tuple(LABEL_IDS)}; got {label!r}")
    step = int(stride)
    sig = float(sigma)
    seed = int(base_seed)
    directory = _cache_directory(family, name, seed, sig, step, cache_dir)
    _verify_sha256sums(directory, (TRAJECTORY_NPZ, META_JSON))
    meta = json.loads((directory / META_JSON).read_text(encoding="utf-8"))
    if (
        str(meta.get("family")) != family
        or str(meta.get("label")) != name
        or int(meta.get("base_seed", -1)) != seed
        or int(meta.get("stride", -1)) != step
        or sigma_tag(meta.get("sigma", -1.0)) != sigma_tag(sig)
    ):
        raise ValueError(
            f"cache metadata does not match the requested trajectory ({directory})"
        )
    expected_id = trajectory_id(family, name, seed, sig)
    if str(meta.get("trajectory_id")) != expected_id:
        raise ValueError(
            f"cache trajectory_id {meta.get('trajectory_id')!r} does not match "
            f"{expected_id!r}"
        )
    with np.load(directory / TRAJECTORY_NPZ) as data:
        frames = _validated_frames(family, data["frames"])
        timestamps = np.ascontiguousarray(data["timestamps"], dtype=np.float64)
        z = np.ascontiguousarray(data["z"], dtype=np.float64)
    if timestamps.shape != (frames.shape[0],) or z.shape != (frames.shape[0],):
        raise ValueError("stored timestamps and z must match the number of frames")
    if _sha256_bytes(frames.tobytes()) != str(meta.get("sha256_frames")):
        raise ValueError("stored frames checksum does not match meta.json")
    latent = meta.get("latent")
    if not isinstance(latent, dict):
        raise ValueError("meta.json must carry a JSON object latent dict")
    return Trajectory(
        trajectory_id=expected_id,
        family=family,
        label=name,
        base_seed=seed,
        sigma=float(meta["sigma"]),
        stride=step,
        timestamps=timestamps,
        frames=frames,
        z=z,
        latent=latent,
    )
