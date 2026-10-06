"""Matched-budget reversible-versus-drift trajectories for the post-PIVOT protocol.

This module is a new stage, not part of the frozen three-class pilot. It reuses
the frozen Family A and Family B raw maps, the frozen persistence conventions,
and the frozen exact metric, and it changes only the latent control programs.

The two scientific classes are ``reversible`` and ``drift``. Both share one
latent movement budget ``B`` by construction:

- the master clock is ``u = j / 128`` for ``j = 0, ..., 128``;
- a window ``[a, b]`` is drawn as in the frozen generator (``a`` uniform on
  ``[0.15, 0.25]`` and ``b`` uniform on ``[0.75, 0.85]``), an even number
  ``2k`` of master intervals fall inside it, and a shared nonnegative step
  profile ``w_1, ..., w_{2k}`` is drawn once per trajectory and mirrored so
  that the first and second halves carry the same weights;
- the step magnitudes are ``B * w_i / sum(w)`` for both classes, so the two
  classes have an identical multiset of latent step magnitudes, an identical
  latent path length ``B``, and an identical latent speed profile;
- ``reversible`` uses ``+`` steps for the first ``k`` intervals and ``-`` steps
  for the last ``k``, so the latent level returns exactly to its start;
- ``drift`` uses ``+`` steps for all ``2k`` intervals, so the latent level
  moves persistently away.

The only latent difference between the classes is the direction order, not how
much the system moves. Raw frames and noise are generated exactly as in the
frozen generator, with a new label namespace (``reversible`` id 7, ``drift``
id 8) so existing caches and label ids are untouched.
"""

from __future__ import annotations

import numpy as np

from . import generators
from .generators import (
    FAMILY_IDS,
    Trajectory,
    _draw_latent,
    _draw_noise,
    _family_a_points,
    _family_b_fields,
    _master_timestamps,
    _subsample,
    sigma_tag,
)

__all__ = [
    "DEFAULT_BUDGET",
    "DEFAULT_JITTER",
    "MATCHED_CLASSES",
    "MATCHED_LABEL_IDS",
    "Z_BASE",
    "build_matched_trajectory",
    "matched_latent_profile",
    "matched_trajectory_id",
]

MATCHED_CLASSES = ("reversible", "drift")
MATCHED_LABEL_IDS = {"reversible": 7, "drift": 8}
DEFAULT_BUDGET = 1.0
DEFAULT_JITTER = 0.25
Z_BASE = 0.5


def matched_trajectory_id(
    family: str, class_name: str, base_seed: int, sigma: float, budget: float
) -> str:
    """Identifier including the budget, which the frozen id does not carry."""
    return (
        f"{family}_{class_name}_{int(base_seed)}_sigma{sigma_tag(sigma)}"
        f"_B{float(budget):g}"
    )


def _latent_rng(base_seed: int, family: str) -> np.random.Generator:
    """Class-independent latent RNG.

    Both classes of one seed must share the window, the family parameters, and
    the step profile, so the latent stream carries no class key. Only the sign
    pattern and the noise stream (which does carry the class key) differ.
    """
    return np.random.default_rng([int(base_seed), FAMILY_IDS[family], 303])


def matched_latent_profile(
    class_name: str,
    latent: dict,
    budget: float,
    jitter: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Latent level ``z(u)`` on the 129-frame master grid.

    Both classes receive the same mirrored weight vector and hence the same
    individual step magnitudes; only the signs differ.
    """
    key = str(class_name)
    if key not in MATCHED_LABEL_IDS:
        raise ValueError(f"class must be one of {MATCHED_CLASSES}; got {class_name!r}")
    if float(budget) <= 0.0:
        raise ValueError(f"budget must be positive; got {budget!r}")
    if not 0.0 <= float(jitter) < 1.0:
        raise ValueError(f"jitter must lie in [0, 1); got {jitter!r}")
    u = _master_timestamps()
    n_intervals = int(u.size) - 1
    a = float(latent["a"])
    b = float(latent["b"])
    start = int(np.ceil(a * n_intervals))
    stop = int(np.floor(b * n_intervals))
    n_window = stop - start
    if n_window % 2 == 1:
        n_window -= 1
    if n_window < 4:
        raise ValueError(
            f"the window [{a:.4f}, {b:.4f}] holds {n_window} master intervals; "
            "at least four are required"
        )
    half = n_window // 2
    first_half = 1.0 + float(jitter) * (2.0 * rng.random(half) - 1.0)
    weights = np.concatenate([first_half, first_half[::-1]])
    steps = float(budget) * weights / float(weights.sum())
    if key == "reversible":
        signs = np.concatenate([np.ones(half), -np.ones(n_window - half)])
    else:
        signs = np.ones(n_window)
    z = np.full(u.size, Z_BASE, dtype=np.float64)
    for offset in range(n_window):
        z[start + 1 + offset] = z[start + offset] + signs[offset] * steps[offset]
    if n_window and start + n_window + 1 <= u.size - 1:
        z[start + n_window + 1 :] = z[start + n_window]
    return z


def build_matched_trajectory(
    class_name: str,
    family: str,
    base_seed: int,
    sigma: float,
    stride: int = 1,
    budget: float = DEFAULT_BUDGET,
    jitter: float = DEFAULT_JITTER,
) -> Trajectory:
    """Build one matched-budget trajectory.

    The noise realization is drawn on the 129-frame master grid and only then
    subsampled, so every stride variant is an exact subsample of the same
    realization, as in the frozen generator.
    """
    key = str(class_name)
    if key not in MATCHED_LABEL_IDS:
        raise ValueError(f"class must be one of {MATCHED_CLASSES}; got {class_name!r}")
    generators.family_id(family)
    step = int(stride)
    if step < 1:
        raise ValueError(f"stride must be a positive integer; got {stride!r}")
    sig = float(sigma)
    if not np.isfinite(sig) or sig < 0.0:
        raise ValueError(f"sigma must be finite and non-negative; got {sigma!r}")
    seed = int(base_seed)
    rng = _latent_rng(seed, family)
    latent = _draw_latent(family, rng)
    latent["budget"] = float(budget)
    latent["jitter"] = float(jitter)
    latent["matched_class"] = key
    z = matched_latent_profile(key, latent, budget, jitter, rng)
    timestamps = _master_timestamps()
    if family == "A":
        frames = _family_a_points(z, latent)
    else:
        frames = _family_b_fields(z, latent)
    noise = _draw_noise(
        family,
        int(z.size),
        sig,
        seed,
        FAMILY_IDS[family],
        MATCHED_LABEL_IDS[key],
    )
    if noise is not None:
        frames = frames + noise
    frames = np.ascontiguousarray(frames, dtype=np.float64)
    frames, timestamps, z = _subsample(frames, timestamps, z, step)
    return Trajectory(
        trajectory_id=matched_trajectory_id(family, key, seed, sig, budget),
        family=family,
        label=key,
        base_seed=seed,
        sigma=sig,
        stride=step,
        timestamps=timestamps,
        frames=frames,
        z=z,
        latent=latent,
    )
