"""Persistence-diagram extraction under the frozen pilot conventions.

Frozen conventions (``Pilot_Experiment_Specification.md`` section 2,
``assumption_ledger.yaml`` sections ``topology_conventions``/``diagram_metric``,
and the Phase-1 implementation contract section 5):

- Coefficient field F2 everywhere. Family A uses Euclidean Vietoris--Rips H0/H1
  with the edge-length filtration convention; Family B uses cubical H0/H1 of the
  sublevel sets of ``-f``.
- Essential classes (``death = +inf``) are stripped before any metric call and
  their per-window counts are recorded; every finite bar is retained with no
  label-dependent persistence threshold.
- The diagonal itself and empty finite diagrams are valid objects, represented
  as ``(0, 2)`` float64 arrays.
- One simplex tree and one ``compute_persistence`` call per frame serve every
  requested degree in :func:`trajectory_diagrams`.
- Trailing-window pooling is the separate WP-2.1 observation map: Family A
  concatenates points and Family B averages fields. Pooled results are never
  mixed into the primary frame-level claim.

Cache layout (contract section 5):
``{cache_dir}/{family}/{label}/{base_seed}/sigma{sigma_tag}/stride{stride}/``
holds ``diagrams.npz`` (keys ``d0_000``, ``d1_000``, ``d0_001``, ...),
``essential.npz`` (keys ``e0_000``, ``e1_000``, ...), ``meta.json``, and
``SHA256SUMS``. Loading verifies every checksum before returning arrays.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import numpy as np

from .diagram_metrics import strip_essential

if TYPE_CHECKING:
    from .generators import Trajectory

__all__ = [
    "finite_diagram",
    "family_a_diagram",
    "family_b_diagram",
    "trajectory_diagrams",
    "trajectory_essential_counts",
    "save_diagram_cache",
    "load_diagram_cache",
    "pool_window",
    "diagrams_for_windows",
]

_DEFAULT_DEGREES: tuple[int, ...] = (0, 1)
_POOL_LENGTHS: tuple[int, ...] = (1, 3, 5)
_POOL_STRIDES: tuple[int, ...] = (1, 2, 4)
_CACHE_FILES: tuple[str, ...] = ("diagrams.npz", "essential.npz", "meta.json")
_SHA256SUMS = "SHA256SUMS"


def finite_diagram(raw_intervals) -> tuple[np.ndarray, int]:
    """Return ``(finite_diagram, n_essential)`` for raw persistence intervals.

    Rows with a non-finite death (in particular ``+inf``) are removed and
    counted. Non-finite births, NaN deaths, ``-inf`` deaths, and finite bars
    with ``death < birth`` are rejected. The result is float64, canonically
    sorted lexicographically by ``(birth, death)``, and has shape ``(0, 2)``
    when no finite bar remains.
    """
    finite, n_essential = strip_essential(raw_intervals)
    return np.asarray(finite, dtype=np.float64), int(n_essential)


def _family_complex(family: str, payload) -> object:
    import gudhi

    if family == "A":
        complex_ = gudhi.RipsComplex(
            points=np.asarray(payload, dtype=float)
        ).create_simplex_tree(max_dimension=2)
    elif family == "B":
        complex_ = gudhi.CubicalComplex(
            top_dimensional_cells=-np.asarray(payload, dtype=float)
        )
    else:
        raise ValueError(f"family must be 'A' or 'B'; got {family!r}")
    complex_.compute_persistence(homology_coeff_field=2, min_persistence=0.0)
    return complex_


def family_a_diagram(points: np.ndarray, degree: int) -> tuple[np.ndarray, int]:
    """Family A Vietoris--Rips finite diagram in dimension ``degree``."""
    complex_ = _family_complex("A", points)
    return finite_diagram(complex_.persistence_intervals_in_dimension(int(degree)))


def family_b_diagram(field: np.ndarray, degree: int) -> tuple[np.ndarray, int]:
    """Family B cubical finite diagram in dimension ``degree`` for ``-field``."""
    complex_ = _family_complex("B", field)
    return finite_diagram(complex_.persistence_intervals_in_dimension(int(degree)))


def _normalize_degrees(degrees) -> tuple[int, ...]:
    if isinstance(degrees, (int, np.integer)):
        return (int(degrees),)
    return tuple(int(degree) for degree in degrees)


def _trajectory_finite_and_essential(
    frames: Sequence[np.ndarray], family: str, degrees
) -> tuple[dict[int, list[np.ndarray]], dict[int, list[int]]]:
    family = str(family)
    if family not in ("A", "B"):
        raise ValueError(f"family must be 'A' or 'B'; got {family!r}")
    normalized = _normalize_degrees(degrees)
    diagrams: dict[int, list[np.ndarray]] = {degree: [] for degree in normalized}
    essential: dict[int, list[int]] = {degree: [] for degree in normalized}
    for frame in frames:
        complex_ = _family_complex(family, frame)
        for degree in normalized:
            finite, count = finite_diagram(
                complex_.persistence_intervals_in_dimension(degree)
            )
            diagrams[degree].append(finite)
            essential[degree].append(count)
    return diagrams, essential


def trajectory_diagrams(
    frames: Sequence[np.ndarray], family: str, degrees=(0, 1)
) -> dict[int, list[np.ndarray]]:
    """Finite diagrams for every frame, keyed by degree.

    One simplex tree and one persistence computation per frame serve all
    requested degrees.
    """
    diagrams, _ = _trajectory_finite_and_essential(frames, family, degrees)
    return diagrams


def trajectory_essential_counts(
    frames: Sequence[np.ndarray], family: str, degrees=(0, 1)
) -> dict[int, list[int]]:
    """Per-frame essential-class counts, keyed by degree."""
    _, essential = _trajectory_finite_and_essential(frames, family, degrees)
    return essential


def _sigma_tag(sigma) -> int:
    return int(round(float(sigma) * 1000.0))


def _cache_path(traj: Trajectory, cache_dir) -> Path:
    return (
        Path(cache_dir)
        / str(traj.family)
        / str(traj.label)
        / str(int(traj.base_seed))
        / f"sigma{_sigma_tag(traj.sigma)}"
        / f"stride{int(traj.stride)}"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_sha256sums(directory: Path) -> None:
    lines = [f"{_sha256_file(directory / name)}  {name}" for name in _CACHE_FILES]
    (directory / _SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _verify_sha256sums(directory: Path) -> None:
    sums_path = directory / _SHA256SUMS
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
    if set(entries) != set(_CACHE_FILES):
        raise ValueError(
            f"checksum file {sums_path} must cover {sorted(_CACHE_FILES)}; "
            f"got {sorted(entries)}"
        )
    for name in _CACHE_FILES:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"checksum entry has no file: {path}")
        actual = _sha256_file(path)
        if actual != entries[name]:
            raise ValueError(
                f"SHA256 mismatch for {path}: expected {entries[name]}, got {actual}"
            )


def save_diagram_cache(traj: Trajectory, cache_dir) -> Path:
    """Compute and persist diagrams, essential counts, metadata, and checksums.

    Returns the per-trajectory cache directory.
    """
    import gudhi

    directory = _cache_path(traj, cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    frames = np.asarray(traj.frames)
    timestamps = np.asarray(traj.timestamps, dtype=float)
    n_frames = int(frames.shape[0])
    if timestamps.shape != (n_frames,):
        raise ValueError(
            f"timestamps shape {timestamps.shape} does not match {n_frames} frames"
        )
    diagrams, essential = _trajectory_finite_and_essential(
        frames, traj.family, _DEFAULT_DEGREES
    )
    diagram_arrays: dict[str, np.ndarray] = {}
    essential_arrays: dict[str, np.ndarray] = {}
    for degree in _DEFAULT_DEGREES:
        for index in range(n_frames):
            diagram_arrays[f"d{degree}_{index:03d}"] = diagrams[degree][index]
            essential_arrays[f"e{degree}_{index:03d}"] = np.asarray(
                essential[degree][index], dtype=np.int64
            )
    np.savez(directory / "diagrams.npz", **diagram_arrays)
    np.savez(directory / "essential.npz", **essential_arrays)
    meta = {
        "family": str(traj.family),
        "label": str(traj.label),
        "base_seed": int(traj.base_seed),
        "sigma": float(traj.sigma),
        "stride": int(traj.stride),
        "frame_count": n_frames,
        "timestamps": [float(value) for value in timestamps],
        "degrees": [int(degree) for degree in _DEFAULT_DEGREES],
        "gudhi_version": gudhi.__version__,
    }
    (directory / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_sha256sums(directory)
    return directory


def load_diagram_cache(traj: Trajectory, cache_dir) -> dict:
    """Load and verify a diagram cache written by :func:`save_diagram_cache`.

    Every file listed in ``SHA256SUMS`` is hashed and compared before any array
    is returned. The result is ``{"diagrams": {degree: [...]},
    "essential": {degree: [...]}, "meta": {...}}``.
    """
    directory = _cache_path(traj, cache_dir)
    _verify_sha256sums(directory)
    meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    n_frames = int(meta["frame_count"])
    trajectory_frames = np.asarray(traj.frames)
    if trajectory_frames.shape[0] != n_frames:
        raise ValueError(
            f"cache holds {n_frames} frames but the trajectory holds "
            f"{trajectory_frames.shape[0]}"
        )
    degrees = [int(degree) for degree in meta["degrees"]]
    diagrams: dict[int, list[np.ndarray]] = {}
    essential: dict[int, list[int]] = {}
    diagram_file = np.load(directory / "diagrams.npz")
    essential_file = np.load(directory / "essential.npz")
    try:
        for degree in degrees:
            diagram_list: list[np.ndarray] = []
            count_list: list[int] = []
            for index in range(n_frames):
                diagram_key = f"d{degree}_{index:03d}"
                count_key = f"e{degree}_{index:03d}"
                if diagram_key not in diagram_file:
                    raise ValueError(f"missing diagram array {diagram_key}")
                if count_key not in essential_file:
                    raise ValueError(f"missing essential count array {count_key}")
                diagram_list.append(
                    np.asarray(diagram_file[diagram_key], dtype=np.float64)
                )
                count_list.append(int(essential_file[count_key]))
            diagrams[degree] = diagram_list
            essential[degree] = count_list
    finally:
        diagram_file.close()
        essential_file.close()
    return {"diagrams": diagrams, "essential": essential, "meta": meta}


def pool_window(
    frames: Sequence[np.ndarray], family: str, length: int, stride: int
) -> tuple[np.ndarray, np.ndarray]:
    """Trailing-window pooling of a frame stack (WP-2.1 observation map).

    Windows of ``length`` frames are emitted at output ``stride``; the first
    window ends at index ``length - 1`` and later windows end ``stride`` frames
    apart. Family A concatenates the points of a window, Family B averages the
    fields. The returned timestamps are the end-of-window time coordinates,
    which under this frozen signature (frames only) are the end-of-window frame
    indices; map them through the trajectory clock with
    ``trajectory.timestamps[ends]``. Only lengths 1, 3, 5 and strides 1, 2, 4
    are supported.
    """
    family = str(family)
    if family not in ("A", "B"):
        raise ValueError(f"family must be 'A' or 'B'; got {family!r}")
    length = int(length)
    stride = int(stride)
    if length not in _POOL_LENGTHS:
        raise ValueError(
            f"pool_window supports lengths {_POOL_LENGTHS}; got {length}"
        )
    if stride not in _POOL_STRIDES:
        raise ValueError(
            f"pool_window supports strides {_POOL_STRIDES}; got {stride}"
        )
    arr = np.asarray(frames)
    n_frames = int(arr.shape[0])
    if n_frames < length:
        raise ValueError(
            f"pooling length {length} exceeds the {n_frames} available frames"
        )
    ends = np.arange(length - 1, n_frames, stride, dtype=np.int64)
    if family == "A":
        pooled = np.stack(
            [
                arr[end - length + 1 : end + 1].reshape(-1, arr.shape[-1])
                for end in ends
            ],
            axis=0,
        )
    else:
        pooled = np.stack(
            [arr[end - length + 1 : end + 1].mean(axis=0) for end in ends], axis=0
        )
    return pooled, ends.astype(np.float64)


def diagrams_for_windows(
    frames: Sequence[np.ndarray], family: str, length: int, stride: int, degrees=(0, 1)
) -> dict:
    """Pool trailing windows and extract their finite diagrams."""
    pooled_frames, _ = pool_window(frames, family, length, stride)
    return trajectory_diagrams(pooled_frames, family, degrees)
