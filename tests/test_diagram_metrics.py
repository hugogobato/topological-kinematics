"""Tests for the frozen finite-diagram metrics (WP-0.2)."""

import numpy as np
import pytest

from tk_pilot.diagram_metrics import (
    NUMERICAL_ZERO,
    as_diagram,
    bottleneck_bruteforce,
    bottleneck_gudhi,
    bottleneck_linf,
    bottleneck_persim,
    diagonal_cost,
    pairwise_distance_matrix,
    strip_essential,
    wasserstein2_linf,
)


def singleton(s, lifespan=10.0):
    return np.array([[float(s), float(s) + lifespan]])


@pytest.mark.parametrize("shift", [0.0, 0.3, 4.9, 5.0, 5.1, 9.0])
def test_singleton_analytic(shift):
    expected = min(abs(shift), 5.0)
    for backend in (bottleneck_gudhi, bottleneck_persim, bottleneck_bruteforce):
        assert backend(singleton(0.0), singleton(shift)) == pytest.approx(
            expected, abs=1e-9
        )


def test_diagonal_cost():
    assert diagonal_cost((0.0, 10.0)) == pytest.approx(5.0)
    assert diagonal_cost((2.0, 2.0)) == 0.0


def test_empty_diagrams():
    empty = np.zeros((0, 2))
    assert bottleneck_gudhi(empty, empty) == 0.0
    assert bottleneck_persim(empty, empty) == 0.0
    assert bottleneck_bruteforce(empty, empty) == 0.0
    assert bottleneck_gudhi(empty, singleton(0.0)) == pytest.approx(5.0)
    assert bottleneck_gudhi(empty, np.array([[0.25, 0.75]])) == pytest.approx(0.25)
    assert bottleneck_gudhi(np.array([[0.0, 0.5]]), np.array([[0.25, 0.75]])) == pytest.approx(0.25)
    assert bottleneck_gudhi(singleton(0.25), np.array([[0.25, 0.75]])) == pytest.approx(5.0)


def test_diagonal_points_equal_empty():
    on_diagonal = np.array([[1.0, 1.0], [2.0, 2.0]])
    assert bottleneck_gudhi(on_diagonal, np.zeros((0, 2))) == 0.0


def test_random_bruteforce_agreement():
    rng = np.random.default_rng(7)
    for _ in range(30):
        n = int(rng.integers(0, 5))
        m = int(rng.integers(0, max(1, 8 - n)))
        m = min(m, 7 - n)
        a = _random_diagram(rng, n)
        b = _random_diagram(rng, m)
        reference = bottleneck_bruteforce(a, b)
        assert bottleneck_gudhi(a, b) == pytest.approx(reference, abs=1e-9)
        assert bottleneck_persim(a, b) == pytest.approx(reference, abs=1e-9)
        assert bottleneck_gudhi(a, b) == pytest.approx(bottleneck_gudhi(b, a), abs=1e-9)


def test_random_metric_axioms():
    rng = np.random.default_rng(11)
    for _ in range(20):
        x = _random_diagram(rng, int(rng.integers(0, 5)))
        y = _random_diagram(rng, int(rng.integers(0, 5)))
        z = _random_diagram(rng, int(rng.integers(0, 5)))
        assert bottleneck_gudhi(x, x) == pytest.approx(0.0, abs=1e-9)
        assert bottleneck_gudhi(x, z) <= (
            bottleneck_gudhi(x, y) + bottleneck_gudhi(y, z) + 1e-9
        )


def test_bottleneck_bounded_by_wasserstein2():
    rng = np.random.default_rng(13)
    for _ in range(20):
        a = _random_diagram(rng, int(rng.integers(0, 5)))
        b = _random_diagram(rng, int(rng.integers(0, 5)))
        assert bottleneck_gudhi(a, b) <= wasserstein2_linf(a, b) + 1e-9


def test_as_diagram_rejects_non_finite():
    with pytest.raises(ValueError):
        as_diagram(np.array([[0.0, np.inf]]))
    with pytest.raises(ValueError):
        as_diagram(np.array([[1.0, 0.5]]))


def test_strip_essential_counts_and_canonicalizes():
    finite, n = strip_essential(np.array([[0.5, np.inf], [2.0, 3.0], [0.0, 5.0]]))
    assert n == 1
    assert np.array_equal(finite, np.array([[0.0, 5.0], [2.0, 3.0]]))
    finite2, n2 = strip_essential(np.array([[0.0, np.inf]]))
    assert finite2.shape == (0, 2)
    assert n2 == 1


def test_strip_essential_rejects_negative_inf():
    with pytest.raises(ValueError):
        strip_essential(np.array([[0.0, -np.inf]]))
    with pytest.raises(ValueError):
        strip_essential(np.array([[0.0, np.nan]]))


def test_numerical_zero_policy():
    base = np.array([[0.0, 1.0], [2.0, 3.0]])
    with_diagonal = np.array([[0.0, 1.0], [2.0, 3.0], [5.0, 5.0]])
    assert bottleneck_gudhi(base, with_diagonal) == 0.0
    assert bottleneck_persim(base, with_diagonal) == 0.0
    assert bottleneck_bruteforce(base, with_diagonal) == 0.0
    assert bottleneck_gudhi(singleton(0.0), singleton(5e-13)) == 0.0
    assert bottleneck_gudhi(singleton(0.0), singleton(2e-12)) > 0.0
    assert NUMERICAL_ZERO == 1e-12


def test_pairwise_distance_matrix():
    diagrams = [singleton(0.0), singleton(1.0), singleton(3.0)]
    matrix = pairwise_distance_matrix(diagrams, metric=bottleneck_linf)
    assert matrix.shape == (3, 3)
    assert np.allclose(matrix, matrix.T)
    assert np.allclose(np.diag(matrix), 0.0)
    assert matrix[0, 2] == pytest.approx(3.0)


def _random_diagram(rng, n):
    if n == 0:
        return np.zeros((0, 2))
    birth = rng.uniform(0.0, 2.0, size=n)
    persistence = rng.uniform(1e-3, 3.0, size=n)
    return np.column_stack([birth, birth + persistence])
