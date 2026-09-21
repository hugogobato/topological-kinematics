"""Exact level-2 path signatures under the frozen pilot convention.

For a piecewise-linear path ``x_0, ..., x_{n-1}`` with increments
``dx_k = x_{k+1} - x_k`` the frozen construction is

- ``S1 = sum_k dx_k``;
- ``S2 = sum_k [ outer(dx_k, S1_{<k}) + 0.5 * outer(dx_k, dx_k) ]`` with
  ``S1_{<k} = sum_{s < k} dx_s`` (Chen's identity).

:func:`signature_level2` returns ``[S1, S2]`` with ``S2`` flattened row-major.
:func:`signature_level2_time` appends the timestamp as a trailing coordinate
before the same construction. Coordinate scaling is fitted downstream on
training data only; this module never scales.
"""

from __future__ import annotations

import numpy as np

__all__ = ["signature_level2", "signature_level2_time"]


def _as_path(path) -> np.ndarray:
    points = np.asarray(path, dtype=np.float64)
    if points.ndim != 2:
        raise ValueError(f"path must be a 2-D array; got shape {points.shape}")
    if points.shape[0] < 2:
        raise ValueError("a path with fewer than two points has no signature")
    return points


def signature_level2(path) -> np.ndarray:
    """Level-1 and level-2 signature of a piecewise-linear path.

    Returns a 1-D float64 vector of length ``d + d**2`` for a path in
    ``R**d``. Raises ``ValueError`` when the path has fewer than two points.
    """
    points = _as_path(path)
    increments = np.diff(points, axis=0)
    prefix = np.cumsum(increments, axis=0) - increments
    s1 = increments.sum(axis=0)
    s2 = np.einsum("ki,kj->ij", increments, prefix)
    s2 = s2 + 0.5 * np.einsum("ki,kj->ij", increments, increments)
    return np.concatenate([s1, s2.ravel()])


def signature_level2_time(path, timestamps) -> np.ndarray:
    """Level-2 signature of the path with timestamps as a trailing coordinate."""
    points = _as_path(path)
    t = np.asarray(timestamps, dtype=np.float64)
    if t.ndim != 1:
        raise ValueError("timestamps must be one-dimensional")
    if t.size != points.shape[0]:
        raise ValueError(
            f"got {t.size} timestamps for {points.shape[0]} path points; "
            "they must match"
        )
    return signature_level2(np.column_stack([points, t]))
