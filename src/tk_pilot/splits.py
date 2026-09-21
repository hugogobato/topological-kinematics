"""Frozen split namespaces and split-manifest writing for the pilot.

The split key is the base seed (``implementation_contract.md`` sections 3 and
8): training 1000-1039, validation 2000-2019, exploratory test 3000-3039, and
confirmatory test seeds starting at 10000. Every family, class, sigma, and
stride variant of one base seed stays in a single split. The manifest CSV has
the frozen columns ``trajectory_id, base_seed, family, class, sigma, stride,
split, cluster_id`` with ``cluster_id = f"{family}_{class}_{base_seed}"``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .generators import family_id, label_id, trajectory_id

__all__ = [
    "CONFIRMATORY_START",
    "MANIFEST_FIELDS",
    "SPLIT_RANGES",
    "family_id",
    "label_id",
    "split_for_base_seed",
    "write_split_manifest",
]

SPLIT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("train", 1000, 1039),
    ("validation", 2000, 2019),
    ("test_exploratory", 3000, 3039),
)
CONFIRMATORY_START = 10000
MANIFEST_FIELDS: tuple[str, ...] = (
    "trajectory_id",
    "base_seed",
    "family",
    "class",
    "sigma",
    "stride",
    "split",
    "cluster_id",
)


def split_for_base_seed(base_seed: int) -> str | None:
    """Return the frozen split name for a base seed, or ``None`` if unnamed."""
    seed = int(base_seed)
    for name, lower, upper in SPLIT_RANGES:
        if lower <= seed <= upper:
            return name
    if seed >= CONFIRMATORY_START:
        return "test_confirmatory"
    return None


def write_split_manifest(config: dict, out_path: str | Path) -> Path:
    """Write the independent split manifest for the configured grid.

    ``config`` is the parsed ``configs/tk_pilot.yaml`` mapping. Rows are
    emitted for the training, validation, and exploratory namespaces of
    ``seed_namespaces`` (falling back to the frozen ranges) and, when
    ``seed_namespaces.test_confirmatory_count`` is present, for that many
    confirmatory seeds starting at ``test_confirmatory_start``. Deterministic
    row order: split block, base seed, family, class, sigma, then stride.
    """
    families = [str(value) for value in config.get("families", ("A", "B"))]
    classes = [str(value) for value in config.get("classes", ("return", "ramp", "jump"))]
    sigmas = [float(value) for value in config.get("sigmas", (0.0, 0.05))]
    strides = [int(value) for value in config.get("strides", (1, 2, 4))]
    for family in families:
        family_id(family)
    for name in classes:
        label_id(name)
    namespaces = dict(config.get("seed_namespaces", {}))
    blocks: list[tuple[str, int, int]] = []
    for split, lower, upper in SPLIT_RANGES:
        bounds = namespaces.get(split, [lower, upper])
        blocks.append((split, int(bounds[0]), int(bounds[1])))
    count = namespaces.get("test_confirmatory_count")
    if count is not None:
        start = int(namespaces.get("test_confirmatory_start", CONFIRMATORY_START))
        blocks.append(("test_confirmatory", start, start + int(count) - 1))
    rows: list[dict] = []
    for split, lower, upper in blocks:
        for seed in range(lower, upper + 1):
            for family in families:
                for name in classes:
                    for sigma in sigmas:
                        for stride in strides:
                            rows.append(
                                {
                                    "trajectory_id": trajectory_id(
                                        family, name, seed, sigma
                                    ),
                                    "base_seed": seed,
                                    "family": family,
                                    "class": name,
                                    "sigma": sigma,
                                    "stride": stride,
                                    "split": split,
                                    "cluster_id": f"{family}_{name}_{seed}",
                                }
                            )
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MANIFEST_FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return destination
