"""Regression tests for the G2 primary metric backend ``bottleneck_exact``.

These tests were added with the G2 amendment that replaced the defective
``gudhi.bottleneck_distance`` primary backend with the exact augmented-matching
solver ``tk_pilot.diagram_metrics.bottleneck_exact``. The witness pair is the
minimal 3 versus 4 point pair stored in
``research_review/results/g2/diagnostics/metric_backend_witness.json``. The
frozen exact value is 0.3985347143760231 and gudhi 3.12.0 returns
0.41061420919138303 on the canonical order; the gudhi value is recorded as an
observation rather than asserted, because the legacy backend is retained only
for audit.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from tk_pilot.diagram_metrics import (
    bottleneck_bruteforce,
    bottleneck_exact,
    bottleneck_gudhi,
    bottleneck_linf,
    bottleneck_persim,
)

WITNESS_PATH = (
    Path(__file__).resolve().parents[1]
    / "research_review"
    / "results"
    / "g2"
    / "diagnostics"
    / "metric_backend_witness.json"
)
WITNESS_EXACT = 0.3985347143760231
EXACT_TOL = 1e-12
TRIANGLE_TOL = 1e-9


def _random_diagram(rng, n):
    if n == 0:
        return np.zeros((0, 2))
    birth = rng.uniform(0.0, 2.0, size=n)
    persistence = rng.uniform(1e-3, 3.0, size=n)
    return np.column_stack([birth, birth + persistence])


def _witness_pair():
    payload = json.loads(WITNESS_PATH.read_text(encoding="utf-8"))["witness"]
    return np.asarray(payload["diagram_a"]), np.asarray(payload["diagram_b"])


def test_primary_alias_is_exact():
    assert bottleneck_linf is bottleneck_exact


def test_witness_pair_exact_backends_agree(record_property):
    a, b = _witness_pair()
    exact_value = bottleneck_exact(a, b)
    force_value = bottleneck_bruteforce(a, b)
    persim_value = bottleneck_persim(a, b)
    gudhi_value = bottleneck_gudhi(a, b)
    record_property("witness_exact", repr(exact_value))
    record_property("witness_bruteforce", repr(force_value))
    record_property("witness_persim", repr(persim_value))
    record_property("witness_gudhi_canonical", repr(gudhi_value))
    print(
        "witness pair: exact={!r} bruteforce={!r} persim={!r} "
        "gudhi_canonical={!r} expected={!r}".format(
            exact_value, force_value, persim_value, gudhi_value, WITNESS_EXACT
        )
    )
    assert exact_value == pytest.approx(WITNESS_EXACT, abs=EXACT_TOL)
    assert force_value == pytest.approx(WITNESS_EXACT, abs=EXACT_TOL)
    assert persim_value == pytest.approx(WITNESS_EXACT, abs=EXACT_TOL)


def test_order_invariance_and_persim_agreement():
    rng = np.random.default_rng(20260921)
    for pair_index in range(20):
        n = int(rng.integers(10, 41))
        m = int(rng.integers(10, 41))
        a = _random_diagram(rng, n)
        b = _random_diagram(rng, m)
        reference = bottleneck_exact(a, b)
        if pair_index < 3:
            assert bottleneck_persim(a, b) == pytest.approx(reference, abs=EXACT_TOL)
        for _ in range(5):
            permuted_a = a[rng.permutation(n)]
            permuted_b = b[rng.permutation(m)]
            assert bottleneck_exact(permuted_a, permuted_b) == pytest.approx(
                reference, abs=EXACT_TOL
            )


def test_triangle_inequality(record_property):
    rng = np.random.default_rng(20260922)
    gudhi_violations = 0
    for _ in range(50):
        x = _random_diagram(rng, int(rng.integers(10, 41)))
        y = _random_diagram(rng, int(rng.integers(10, 41)))
        z = _random_diagram(rng, int(rng.integers(10, 41)))
        d_xy = bottleneck_exact(x, y)
        d_yz = bottleneck_exact(y, z)
        d_xz = bottleneck_exact(x, z)
        assert d_xz <= d_xy + d_yz + TRIANGLE_TOL
        if (
            bottleneck_gudhi(x, z)
            > bottleneck_gudhi(x, y) + bottleneck_gudhi(y, z) + TRIANGLE_TOL
        ):
            gudhi_violations += 1
    record_property("gudhi_triangle_violations", gudhi_violations)
    print(f"gudhi triangle violations over 50 random triples: {gudhi_violations}")


def test_small_diagram_agreement_with_bruteforce():
    rng = np.random.default_rng(20260923)
    for _ in range(40):
        total = int(rng.integers(0, 8))
        n = int(rng.integers(0, total + 1))
        m = total - n
        a = _random_diagram(rng, n)
        b = _random_diagram(rng, m)
        assert bottleneck_exact(a, b) == pytest.approx(
            bottleneck_bruteforce(a, b), abs=EXACT_TOL
        )
