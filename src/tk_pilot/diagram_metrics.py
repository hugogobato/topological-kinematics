"""Finite persistence-diagram distances under the frozen G0 conventions.

Frozen conventions (see ``assumption_ledger.yaml`` and ``metric_interface.md``):

- A diagram is a finite multiset of pairs ``(birth, death)`` with
  ``birth <= death``. Essential classes (``death = +inf``) are stripped before
  any metric call, and their count is recorded by the caller.
- The primary metric is the bottleneck distance with the L-infinity ground norm
  and the diagonal carrying infinite multiplicity. Matching a point ``p`` to the
  diagonal costs ``(death - birth) / 2``.
- The empty diagram is a valid operand.

Backends: ``bottleneck_exact`` is the primary implementation, an exact
augmented-matching binary search over the candidate costs of the cost matrix
produced by ``_bruteforce_cost_matrix`` whose feasibility test uses
``scipy.sparse.csgraph.maximum_bipartite_matching``. ``persim`` is a secondary
cross-check, and an exact brute-force enumeration over matchings with diagonal
copies is an independent reference for diagram pairs with at most seven points
in total. All are finite-diagram only; ``as_diagram`` rejects non-finite input
so a backend can never silently drop an essential class.

``gudhi.bottleneck_distance`` (gudhi 3.12.0) is retained under
``bottleneck_gudhi`` for audit and legacy comparison only. That implementation
is defective in the frozen environment: its result depends on the order of the
input points and it returns wrong distances on some real pilot diagrams even
when the exact ``e=0.0`` algorithm is requested, to the point of breaking the
triangle inequality (WP-2.2 audit, ``metric_backend_witness.json``). It must
not be used as a primary backend.

Numerical zero. All public distance functions apply the declared numerical-zero
convention ``NUMERICAL_ZERO = 1e-12``: a computed distance at or below this
value is returned as exactly ``0.0``. The legacy ``gudhi`` backend can return
denormal values (about ``1e-308``) for a true-zero distance between
non-identical diagrams, for example when one diagram carries an extra point on
the diagonal. Without the snap, the frozen exact-zero step rule would not
trigger at zero noise. The tolerance is declared, not hidden, and is far below
the smallest distance that is meaningful at the pilot's coordinate scale.
"""

from __future__ import annotations

from itertools import permutations
from typing import Callable, Iterable, Sequence

import numpy as np

__all__ = [
    "as_diagram",
    "strip_essential",
    "diagonal_cost",
    "bottleneck_bruteforce",
    "bottleneck_exact",
    "bottleneck_gudhi",
    "bottleneck_persim",
    "bottleneck_linf",
    "wasserstein2_linf",
    "pairwise_distance_matrix",
]

_TRIANGLE_ANOMALY_TOL = 1e-12
NUMERICAL_ZERO = 1e-12


def _snap(value: float) -> float:
    """Apply the declared numerical-zero convention to a computed distance."""
    return 0.0 if value <= NUMERICAL_ZERO else float(value)


def _empty_diagram() -> np.ndarray:
    return np.zeros((0, 2), dtype=float)


def _canonical(points: np.ndarray) -> np.ndarray:
    if points.shape[0] <= 1:
        return points
    order = np.lexsort((points[:, 1], points[:, 0]))
    return points[order]


def _as_two_column_array(points) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    if arr.size == 0:
        return _empty_diagram()
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(
            "a diagram must have shape (n, 2) with columns (birth, death); "
            f"got shape {arr.shape}"
        )
    return arr


def strip_essential(points) -> tuple[np.ndarray, int]:
    """Return ``(finite_diagram, n_essential)`` for a raw diagram.

    Bars with ``death = +inf`` are removed and counted. Non-finite births and
    NaN deaths are rejected. Finite bars must satisfy ``birth <= death``. The
    returned array is canonical: lexicographically sorted by ``(birth, death)``.
    """
    arr = _as_two_column_array(points)
    if arr.shape[0] == 0:
        return _empty_diagram(), 0
    if not np.all(np.isfinite(arr[:, 0])):
        raise ValueError("birth coordinates must be finite")
    death = arr[:, 1]
    if np.any(np.isnan(death)):
        raise ValueError("death coordinates may be finite or +inf, not NaN")
    if np.any(np.isneginf(death)):
        raise ValueError("death coordinates must be finite or +inf; -inf is invalid")
    finite_mask = np.isfinite(death)
    finite = arr[finite_mask]
    if finite.shape[0] and np.any(finite[:, 1] < finite[:, 0]):
        raise ValueError("found a finite bar with death < birth")
    n_essential = int(arr.shape[0] - finite.shape[0])
    return _canonical(finite), n_essential


def as_diagram(points) -> np.ndarray:
    """Validate and canonicalize a finite diagram.

    Rejects non-finite deaths so that essential classes cannot enter a metric
    call unrecorded. Use :func:`strip_essential` first for raw diagrams.
    """
    arr = _as_two_column_array(points)
    if arr.shape[0] == 0:
        return _empty_diagram()
    if not np.all(np.isfinite(arr)):
        raise ValueError(
            "non-finite diagram coordinates are not allowed; strip essential "
            "classes with strip_essential before computing a metric"
        )
    if np.any(arr[:, 1] < arr[:, 0]):
        raise ValueError("found a bar with death < birth")
    return _canonical(arr)


def diagonal_cost(point: Sequence[float]) -> float:
    """Cost of matching a persistence point to the diagonal, ``(d - b) / 2``."""
    b, d = float(point[0]), float(point[1])
    return 0.5 * (d - b)


def _point_costs(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    diff = np.abs(a[:, None, :] - b[None, :, :])
    return np.max(diff, axis=2)


def _bruteforce_cost_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n, m = a.shape[0], b.shape[0]
    size = n + m
    costs = np.zeros((size, size), dtype=float)
    if n and m:
        costs[:n, :m] = _point_costs(a, b)
    da = 0.5 * (a[:, 1] - a[:, 0])
    db = 0.5 * (b[:, 1] - b[:, 0])
    if n:
        costs[:n, m:] = da[:, None]
    if m:
        costs[n:, :m] = db[None, :]
    return costs


def bottleneck_bruteforce(d1, d2) -> float:
    """Exact bottleneck distance by enumerating matchings with diagonal copies.

    Independent of ``gudhi`` and ``persim``. Intended for small diagrams:
    raises if the two diagrams together contain more than seven points.
    """
    a = as_diagram(d1)
    b = as_diagram(d2)
    n, m = a.shape[0], b.shape[0]
    size = n + m
    if size == 0:
        return 0.0
    if size > 7:
        raise ValueError(
            "brute-force reference is limited to 7 points in total; "
            f"got {n} + {m}"
        )
    costs = _bruteforce_cost_matrix(a, b)
    best = np.inf
    for perm in permutations(range(size)):
        worst = 0.0
        for i, j in enumerate(perm):
            value = costs[i, j]
            if value > worst:
                worst = value
                if worst >= best:
                    break
        if worst < best:
            best = worst
    return _snap(best)


def _identical(a: np.ndarray, b: np.ndarray) -> bool:
    """True when two canonical diagrams are elementwise identical.

    Identical diagrams have distance exactly zero. Backends can return tiny
    denormal values instead of zero for this case, which would break the frozen
    exact-zero step policy, so short-circuit before the library call.
    """
    return a.shape == b.shape and np.array_equal(a, b)


def bottleneck_gudhi(d1, d2) -> float:
    """Legacy ``gudhi.bottleneck_distance`` backend, retained for audit only.

    Defective in gudhi 3.12.0: order dependent and incorrect on some inputs,
    and able to break the triangle inequality on real diagrams. See the module
    docstring and the WP-2.2 audit; do not use as a primary backend.
    """
    import gudhi

    a = as_diagram(d1)
    b = as_diagram(d2)
    if a.shape[0] == 0 and b.shape[0] == 0:
        return 0.0
    if _identical(a, b):
        return 0.0
    return _snap(gudhi.bottleneck_distance(a, b))


def bottleneck_persim(d1, d2) -> float:
    """Secondary cross-check: ``persim.bottleneck`` (L-infinity ground)."""
    import persim

    a = as_diagram(d1)
    b = as_diagram(d2)
    if _identical(a, b):
        return 0.0
    return _snap(persim.bottleneck(a, b))


def _perfect_matching_exists(costs: np.ndarray, threshold: float) -> bool:
    """True when the threshold graph on the augmented cost matrix has a
    perfect matching.

    The graph is bipartite and square, with an edge ``(i, j)`` exactly when
    ``costs[i, j] <= threshold``; a perfect matching is detected with
    ``scipy.sparse.csgraph.maximum_bipartite_matching``.
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching

    graph = csr_matrix(costs <= threshold)
    matching = maximum_bipartite_matching(graph, perm_type="row")
    return bool(np.all(matching >= 0))


def bottleneck_exact(d1, d2) -> float:
    """Primary implementation: exact bottleneck with diagonal copies.

    Binary search over the unique entries of the augmented cost matrix
    produced by :func:`_bruteforce_cost_matrix`, with feasibility at each
    candidate threshold tested by
    ``scipy.sparse.csgraph.maximum_bipartite_matching`` on the threshold graph.
    The optimum of the bottleneck matching problem is always one of the
    augmented cost entries, so the search returns the exact value. The result
    is invariant to the order of the input points and is total on finite
    diagrams. The empty-diagram and identical-diagram short circuits and the
    declared numerical-zero snap are applied exactly as in the other backends.
    """
    a = as_diagram(d1)
    b = as_diagram(d2)
    n, m = a.shape[0], b.shape[0]
    if n == 0 and m == 0:
        return 0.0
    if _identical(a, b):
        return 0.0
    costs = _bruteforce_cost_matrix(a, b)
    candidates = np.unique(costs)
    low = 0
    high = int(candidates.shape[0]) - 1
    while low < high:
        middle = (low + high) // 2
        if _perfect_matching_exists(costs, float(candidates[middle])):
            high = middle
        else:
            low = middle + 1
    return _snap(float(candidates[low]))


bottleneck_linf = bottleneck_exact


def wasserstein2_linf(d1, d2) -> float:
    """Sensitivity branch: 2-Wasserstein with the same L-infinity ground norm."""
    from gudhi.wasserstein import wasserstein_distance

    a = as_diagram(d1)
    b = as_diagram(d2)
    if a.shape[0] == 0 and b.shape[0] == 0:
        return 0.0
    if _identical(a, b):
        return 0.0
    return _snap(wasserstein_distance(a, b, order=2, internal_p=np.inf))


def pairwise_distance_matrix(
    diagrams: Sequence, metric: Callable[[object, object], float] = bottleneck_linf
) -> np.ndarray:
    """Full symmetric matrix of pairwise diagram distances (zero diagonal)."""
    items = list(diagrams)
    n = len(items)
    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            value = float(metric(items[i], items[j]))
            matrix[i, j] = value
            matrix[j, i] = value
    return matrix
