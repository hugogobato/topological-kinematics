"""Machine-readable witness cases for the frozen Phase 0 (G0) definitions.

Every case returns a record with ``case_id``, ``category``, ``description``,
``checks``, ``passed``, and JSON-safe ``details``. These are correctness
witnesses for the finite-metric definitions only. They are not evidence of
novelty, predictive value, or application utility, and they do not test the
raw-data-to-diagram extraction pipeline (that is gate G2).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .diagram_metrics import (
    NUMERICAL_ZERO,
    as_diagram,
    bottleneck_bruteforce,
    bottleneck_gudhi,
    bottleneck_linf,
    bottleneck_persim,
    strip_essential,
    wasserstein2_linf,
)
from .path_diagnostics import (
    angle_validity_flags,
    comparison_angles,
    compute_path_diagnostics,
    efficiency_validity_flag,
    interval_speeds,
    noise_floor,
    validate_timestamps,
)

WITNESS_SEED = 20260920


def _close(name: str, expected, observed, tol: float = 1e-9) -> dict:
    exp = np.asarray(expected, dtype=float)
    obs = np.asarray(observed, dtype=float)
    if exp.shape != obs.shape:
        return {
            "name": name,
            "kind": "max_abs_deviation",
            "deviation": float("inf"),
            "tolerance": tol,
            "passed": False,
            "note": f"shape mismatch {exp.shape} vs {obs.shape}",
        }
    if exp.size == 0:
        deviation = 0.0
    else:
        finite = np.isfinite(exp) & np.isfinite(obs)
        if np.all(finite):
            deviation = float(np.max(np.abs(exp - obs)))
        else:
            deviation = float("inf")
    return {
        "name": name,
        "kind": "max_abs_deviation",
        "deviation": deviation,
        "tolerance": tol,
        "passed": bool(deviation <= tol),
    }


def _true(name: str, condition, detail=None) -> dict:
    record = {"name": name, "kind": "boolean", "passed": bool(condition)}
    if detail is not None:
        record["detail"] = detail
    return record


def _lists(values) -> list:
    out = []
    for value in values:
        value = float(value)
        out.append(None if not np.isfinite(value) else value)
    return out


def _singleton(s: float, lifespan: float = 10.0) -> np.ndarray:
    return np.array([[float(s), float(s) + lifespan]])


def _exact_singleton_metric(d1, d2) -> float:
    """Exact bottleneck for small diagrams, used for structural angle checks.

    The library bottleneck perturbs distances at the 1e-16 level, and arccos is
    ill-conditioned near 0 and pi, so exact single-step distances are used when
    the witness asserts exact angle values. Cases W-01 to W-05 separately verify
    that the library agrees with this reference.
    """
    return bottleneck_bruteforce(d1, d2)


def _euclidean(p, q) -> float:
    return float(np.linalg.norm(np.asarray(p, dtype=float) - np.asarray(q, dtype=float)))


def _random_diagram(rng: np.random.Generator, n: int) -> np.ndarray:
    if n == 0:
        return np.zeros((0, 2), dtype=float)
    birth = rng.uniform(0.0, 2.0, size=n)
    persistence = rng.uniform(1e-3, 3.0, size=n)
    return np.column_stack([birth, birth + persistence])


def _random_diagram_pair(rng: np.random.Generator, max_total: int = 7):
    n = int(rng.integers(0, 5))
    m = int(rng.integers(0, max(1, max_total - n + 1)))
    m = min(m, max_total - n)
    return _random_diagram(rng, n), _random_diagram(rng, m)


def case_singleton_analytic_bottleneck(rng) -> dict:
    lifespan = 10.0
    base = _singleton(0.0, lifespan)
    shifts = [0.0, 0.3, 4.9, 5.0, 5.1, 9.0]
    analytic = [min(abs(s), lifespan / 2.0) for s in shifts]
    targets = [_singleton(s, lifespan) for s in shifts]
    gudhi = [bottleneck_gudhi(base, t) for t in targets]
    persim = [bottleneck_persim(base, t) for t in targets]
    brute = [bottleneck_bruteforce(base, t) for t in targets]
    return {
        "case_id": "W-01",
        "category": "metric_implementation",
        "description": (
            "Singleton diagrams {(s, s + M)} have bottleneck distance "
            "min(|s - t|, M/2); the diagonal takes over at |s - t| = M/2."
        ),
        "checks": [
            _close("gudhi matches analytic min(|ds|, M/2)", analytic, gudhi, 1e-9),
            _close("persim matches analytic min(|ds|, M/2)", analytic, persim, 1e-9),
            _close("bruteforce matches analytic min(|ds|, M/2)", analytic, brute, 1e-9),
            _close("bruteforce matches gudhi", gudhi, brute, 1e-9),
        ],
        "details": {
            "lifespan": lifespan,
            "shifts": shifts,
            "analytic_min_shifts": analytic,
            "gudhi": gudhi,
            "persim": persim,
            "bruteforce": brute,
            "diagonal_transition": lifespan / 2.0,
        },
    }


def case_empty_and_diagonal_diagrams(rng) -> dict:
    empty = np.zeros((0, 2), dtype=float)
    tall = np.array([[0.0, 10.0]])
    short = np.array([[0.25, 0.75]])
    on_diagonal = np.array([[1.0, 1.0], [2.0, 2.0]])
    expected = [0.0, 5.0, 0.25, 0.0]
    pairs = [(empty, empty), (empty, tall), (empty, short), (on_diagonal, empty)]
    gudhi = [bottleneck_gudhi(a, b) for a, b in pairs]
    persim = [bottleneck_persim(a, b) for a, b in pairs]
    brute = [bottleneck_bruteforce(a, b) for a, b in pairs]
    return {
        "case_id": "W-02",
        "category": "metric_implementation",
        "description": (
            "Empty diagrams are valid: d(empty, empty) = 0, "
            "d(empty, point) = persistence / 2, and points on the diagonal "
            "are indistinguishable from empty."
        ),
        "checks": [
            _close("gudhi matches expected empty/diagonal values", expected, gudhi, 1e-9),
            _close("persim matches expected empty/diagonal values", expected, persim, 1e-9),
            _close("bruteforce matches expected empty/diagonal values", expected, brute, 1e-9),
        ],
        "details": {
            "expected": expected,
            "gudhi": gudhi,
            "persim": persim,
            "bruteforce": brute,
        },
    }


def case_bruteforce_backend_agreement(rng) -> dict:
    n_pairs = 60
    gudhi_deviation = 0.0
    persim_deviation = 0.0
    symmetry_deviation = 0.0
    for _ in range(n_pairs):
        a, b = _random_diagram_pair(rng)
        reference = bottleneck_bruteforce(a, b)
        gudhi_deviation = max(
            gudhi_deviation, abs(reference - bottleneck_gudhi(a, b))
        )
        persim_deviation = max(
            persim_deviation, abs(reference - bottleneck_persim(a, b))
        )
        symmetry_deviation = max(
            symmetry_deviation, abs(reference - bottleneck_gudhi(b, a))
        )
    mismatch_a = np.array([[0.0, 1.0], [0.0, 10.0]])
    mismatch_b = np.array([[0.0, 1.0]])
    mismatch_value = bottleneck_gudhi(mismatch_a, mismatch_b)

    order_a = np.array(
        [
            [0.7656414539052718, 1.3546889089204603],
            [0.38197412521465157, 1.1559903231059137],
            [-0.7977708010858131, -0.33555804047014187],
            [0.45366198498081167, 2.1114120477576535],
        ]
    )
    order_b = np.array(
        [
            [0.08799305431193427, 2.2527479101032633],
            [0.529869936383927, 0.529869936383927],
            [-0.5175050684740343, 1.0712327852241388],
            [0.2782960943926589, 2.351578581924966],
        ]
    )
    order_expected = 0.8980590011828029
    order_public = bottleneck_gudhi(order_a, order_b)
    order_reference = bottleneck_persim(order_a, order_b)
    order_shuffled = bottleneck_gudhi(order_a[::-1], order_b[::-1])
    raw_unsorted = None
    try:
        import gudhi

        raw_unsorted = float(gudhi.bottleneck_distance(order_a, order_b))
    except Exception:
        raw_unsorted = None
    return {
        "case_id": "W-03",
        "category": "randomized_checks",
        "description": (
            "On 60 random finite diagram pairs (cardinality 0 to 4, including "
            "mismatched cardinalities), the independent brute-force reference "
            "agrees with gudhi and persim, and the distance is symmetric. An "
            "explicit order-sensitive pair is also checked: the public "
            "canonicalizing API returns the exact reference value even though "
            "the raw library call is input-order sensitive on that pair."
        ),
        "checks": [
            _true(
                "gudhi agrees with brute force",
                gudhi_deviation <= 1e-9,
                {"max_deviation": gudhi_deviation, "tolerance": 1e-9},
            ),
            _true(
                "persim agrees with brute force",
                persim_deviation <= 1e-9,
                {"max_deviation": persim_deviation, "tolerance": 1e-9},
            ),
            _true(
                "distance is symmetric",
                symmetry_deviation <= 1e-9,
                {"max_deviation": symmetry_deviation, "tolerance": 1e-9},
            ),
            _close(
                "cardinality mismatch case equals 5 (large bar to diagonal)",
                5.0,
                mismatch_value,
                1e-9,
            ),
            _close(
                "canonicalized public distance matches the exact reference on the order-sensitive pair",
                [order_expected],
                [order_public],
                1e-12,
            ),
            _close(
                "persim cross-check on the order-sensitive pair",
                [order_expected],
                [order_reference],
                1e-12,
            ),
            _close(
                "public distance is invariant to input row order",
                [order_public],
                [order_shuffled],
                1e-15,
            ),
        ],
        "details": {
            "n_pairs": n_pairs,
            "max_gudhi_deviation": gudhi_deviation,
            "max_persim_deviation": persim_deviation,
            "max_symmetry_deviation": symmetry_deviation,
            "cardinality_mismatch_example": {
                "diagram_a": [[0.0, 1.0], [0.0, 10.0]],
                "diagram_b": [[0.0, 1.0]],
                "value": mismatch_value,
            },
            "order_sensitive_pair": {
                "expected_exact": order_expected,
                "public_canonicalized": order_public,
                "persim_cross_check": order_reference,
                "raw_unsorted_library_value": raw_unsorted,
                "note": (
                    "the public API canonicalizes input rows, so the frozen "
                    "metric is deterministic even though the raw library call "
                    "can depend on input order on rare configurations"
                ),
            },
        },
    }


def case_bottleneck_metric_axioms_random(rng) -> dict:
    n_triples = 40
    identity_deviation = 0.0
    symmetry_deviation = 0.0
    triangle_violation = 0.0
    for _ in range(n_triples):
        x = _random_diagram(rng, int(rng.integers(0, 5)))
        y = _random_diagram(rng, int(rng.integers(0, 5)))
        z = _random_diagram(rng, int(rng.integers(0, 5)))
        identity_deviation = max(identity_deviation, abs(bottleneck_gudhi(x, x)))
        symmetry_deviation = max(
            symmetry_deviation, abs(bottleneck_gudhi(x, y) - bottleneck_gudhi(y, x))
        )
        d_xy = bottleneck_gudhi(x, y)
        d_yz = bottleneck_gudhi(y, z)
        d_xz = bottleneck_gudhi(x, z)
        triangle_violation = max(triangle_violation, d_xz - d_xy - d_yz)
    return {
        "case_id": "W-04",
        "category": "randomized_checks",
        "description": (
            "Over 40 random finite diagram triples, the bottleneck distance "
            "satisfies identity, symmetry, and the triangle inequality."
        ),
        "checks": [
            _close("d(D, D) = 0", [0.0], [identity_deviation], 1e-9),
            _close("d(X, Y) = d(Y, X)", [0.0], [symmetry_deviation], 1e-9),
            _true(
                "d(X, Z) <= d(X, Y) + d(Y, Z)",
                triangle_violation <= 1e-9,
                {"max_triangle_violation": triangle_violation, "tolerance": 1e-9},
            ),
        ],
        "details": {
            "n_triples": n_triples,
            "max_identity_deviation": identity_deviation,
            "max_symmetry_deviation": symmetry_deviation,
            "max_triangle_violation": triangle_violation,
        },
    }


def case_bottleneck_bounded_by_wasserstein2(rng) -> dict:
    n_pairs = 40
    max_violation = -float("inf")
    for _ in range(n_pairs):
        a, b = _random_diagram_pair(rng)
        max_violation = max(max_violation, bottleneck_gudhi(a, b) - wasserstein2_linf(a, b))
    return {
        "case_id": "W-05",
        "category": "metric_implementation",
        "description": (
            "The frozen primary metric never exceeds the 2-Wasserstein "
            "sensitivity branch with the same L-infinity ground norm "
            "(Kramar et al. Definition 5.1 ordering d_B <= d_Wp)."
        ),
        "checks": [
            _true(
                "d_bottleneck <= d_W2 for all pairs",
                max_violation <= 1e-9,
                {"max_violation": max_violation, "tolerance": 1e-9},
            ),
        ],
        "details": {"n_pairs": n_pairs, "max_bottleneck_minus_w2": max_violation},
    }


def case_equal_speed_different_order(rng) -> dict:
    lifespan = 10.0
    timestamps = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    path_a = [0.0, 1.0, 2.0, 1.0, 0.0]
    path_b = [0.0, 1.0, 0.0, 1.0, 0.0]
    diag_a = [_singleton(s, lifespan) for s in path_a]
    diag_b = [_singleton(s, lifespan) for s in path_b]
    pd_a = compute_path_diagnostics(diag_a, timestamps, _exact_singleton_metric)
    pd_b = compute_path_diagnostics(diag_b, timestamps, _exact_singleton_metric)
    pd_a_lib = compute_path_diagnostics(diag_a, timestamps, bottleneck_linf)
    library_angle_deviation = float(
        np.nanmax(np.abs(pd_a_lib.comparison_angles - pd_a.comparison_angles))
    )
    pi = float(np.pi)
    return {
        "case_id": "W-06",
        "category": "path_definitions",
        "description": (
            "Two singleton-diagram paths have identical consecutive bottleneck "
            "distances, zero endpoint displacement, length 4, and constant "
            "speed 4, but different intermediate order. Only the comparison "
            "angle sequence distinguishes them."
        ),
        "checks": [
            _close(
                "equal consecutive distances",
                pd_a.adjacent_distances,
                pd_b.adjacent_distances,
                1e-12,
            ),
            _close("equal path length L = 4", [4.0], [pd_a.length], 1e-12),
            _close("equal path length for path B", [4.0], [pd_b.length], 1e-12),
            _close("equal endpoint displacement R = 0", [0.0], [pd_a.displacement], 1e-12),
            _close(
                "constant speed 4 on the uniform grid",
                [4.0, 4.0, 4.0, 4.0],
                pd_a.interval_speeds,
                1e-12,
            ),
            _close(
                "zero speed-change rates on both paths",
                [0.0, 0.0, 0.0],
                pd_a.speed_change_rates,
                1e-12,
            ),
            _close(
                "path A comparison angles (pi, 0, pi)",
                [pi, 0.0, pi],
                pd_a.comparison_angles,
                1e-12,
            ),
            _close(
                "path B comparison angles (0, 0, 0)",
                [0.0, 0.0, 0.0],
                pd_b.comparison_angles,
                1e-12,
            ),
            _close(
                "path A turns (0, pi, 0)",
                [0.0, pi, 0.0],
                pd_a.comparison_turns,
                1e-12,
            ),
            _true(
                "angle sequences differ",
                not np.allclose(pd_a.comparison_angles, pd_b.comparison_angles),
            ),
            _close(
                "library consecutive distances match the exact reference",
                pd_a.adjacent_distances,
                pd_a_lib.adjacent_distances,
                1e-12,
            ),
            _true(
                "library angles stay within the arccos conditioning tolerance",
                library_angle_deviation <= 1e-6,
                {
                    "max_angle_deviation": library_angle_deviation,
                    "tolerance": 1e-6,
                    "note": (
                        "arccos is ill-conditioned near 0 and pi; an O(1e-16) "
                        "distance perturbation can move the angle by O(1e-8)"
                    ),
                },
            ),
        ],
        "details": {
            "timestamps": [float(x) for x in timestamps],
            "path_a_singleton_birth_coordinates": path_a,
            "path_b_singleton_birth_coordinates": path_b,
            "path_a_angles": _lists(pd_a.comparison_angles),
            "path_b_angles": _lists(pd_b.comparison_angles),
            "path_a_speeds": _lists(pd_a.interval_speeds),
            "path_a_length": pd_a.length,
            "path_a_displacement": pd_a.displacement,
            "note": (
                "L, R, and the speed history are identical across the two "
                "paths; the angle sequence separates them. This is an "
                "information witness, not a utility claim."
            ),
        },
    }


def case_straight_reversal_angle_convention(rng) -> dict:
    lifespan = 10.0
    straight = compute_path_diagnostics(
        [_singleton(s, lifespan) for s in (0.0, 1.0, 2.0)],
        [0.0, 1.0, 2.0],
        _exact_singleton_metric,
    )
    reversal = compute_path_diagnostics(
        [_singleton(s, lifespan) for s in (0.0, 1.0, 0.0)],
        [0.0, 1.0, 2.0],
        _exact_singleton_metric,
    )
    straight_library = compute_path_diagnostics(
        [_singleton(s, lifespan) for s in (0.0, 1.0, 2.0)],
        [0.0, 1.0, 2.0],
        bottleneck_linf,
    )
    library_angle_deviation = abs(
        float(straight_library.comparison_angles[0]) - float(np.pi)
    )
    right_angle = compute_path_diagnostics(
        [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
        [0.0, 1.0, 2.0],
        _euclidean,
    )
    scalene_table = np.array(
        [[0.0, 3.0, 5.0], [3.0, 0.0, 4.0], [5.0, 4.0, 0.0]]
    )
    scalene = comparison_angles(
        [0, 1, 2],
        np.array([3.0, 4.0]),
        lambda i, j: float(scalene_table[i, j]),
    )
    equilateral = comparison_angles(
        [0, 1, 2], np.array([1.0, 1.0]), lambda i, j: 0.0 if i == j else 1.0
    )
    pi = float(np.pi)
    return {
        "case_id": "W-07",
        "category": "path_definitions",
        "description": (
            "Angle convention: theta = pi for straight continuation, "
            "theta = 0 for exact reversal, tau = pi - theta is the turn "
            "companion, and generic triangles reproduce the law of cosines."
        ),
        "checks": [
            _close("straight continuation gives theta = pi", [pi], [straight.comparison_angles[0]], 1e-12),
            _close("straight continuation gives tau = 0", [0.0], [straight.comparison_turns[0]], 1e-12),
            _close("exact reversal gives theta = 0", [0.0], [reversal.comparison_angles[0]], 1e-12),
            _close("exact reversal gives tau = pi", [pi], [reversal.comparison_turns[0]], 1e-12),
            _close("right angle gives theta = pi/2", [pi / 2.0], [right_angle.comparison_angles[0]], 1e-12),
            _close("3-4-5 triangle gives theta = pi/2", [pi / 2.0], [scalene.angle[0]], 1e-12),
            _close("unit triangle gives theta = pi/3", [pi / 3.0], [equilateral.angle[0]], 1e-12),
            _true(
                "all reported angles lie in [0, pi]",
                bool(
                    np.all(straight.comparison_angles >= 0)
                    and np.all(straight.comparison_angles <= pi + 1e-12)
                    and np.all(right_angle.comparison_angles >= 0)
                ),
            ),
            _true(
                "library straight angle stays within the arccos conditioning tolerance",
                library_angle_deviation <= 1e-6,
                {
                    "library_deviation_from_pi": library_angle_deviation,
                    "tolerance": 1e-6,
                },
            ),
        ],
        "details": {
            "straight_theta": _lists(straight.comparison_angles),
            "straight_tau": _lists(straight.comparison_turns),
            "reversal_theta": _lists(reversal.comparison_angles),
            "reversal_tau": _lists(reversal.comparison_turns),
            "right_angle_theta": _lists(right_angle.comparison_angles),
            "scalene_example_sides": {"a": 3.0, "b": 4.0, "c": 5.0},
            "equilateral_theta": _lists(equilateral.angle),
            "note": "theta is the comparison angle; tau is the reported turn (pi - theta).",
        },
    }


def case_zero_step_undefined(rng) -> dict:
    lifespan = 10.0
    one_zero = compute_path_diagnostics(
        [_singleton(s, lifespan) for s in (0.0, 1.0, 1.0)],
        [0.0, 0.25, 0.5],
        _exact_singleton_metric,
    )
    first_zero = compute_path_diagnostics(
        [_singleton(s, lifespan) for s in (0.0, 0.0, 1.0)],
        [0.0, 0.25, 0.5],
        _exact_singleton_metric,
    )
    constant = compute_path_diagnostics(
        [_singleton(0.0, lifespan) for _ in range(3)],
        [0.0, 0.25, 0.5],
        _exact_singleton_metric,
    )
    return {
        "case_id": "W-08",
        "category": "edge_cases",
        "description": (
            "Zero steps make the comparison angle undefined (a = 0 or b = 0), "
            "a constant path has L = 0 and undefined efficiency, and triangle "
            "excess is undefined only when a + b = 0. Undefined is not zero."
        ),
        "checks": [
            _true(
                "b = 0 gives undefined angle",
                bool(np.isnan(one_zero.comparison_angles[0]))
                and not bool(one_zero.comparison_valid[0]),
            ),
            _true(
                "b = 0 gives undefined turn",
                bool(np.isnan(one_zero.comparison_turns[0])),
            ),
            _true(
                "a = 0 gives undefined angle",
                bool(np.isnan(first_zero.comparison_angles[0]))
                and not bool(first_zero.comparison_valid[0]),
            ),
            _close(
                "triangle excess is still defined when a + b > 0",
                [0.0],
                [one_zero.triangle_excess[0]],
                1e-12,
            ),
            _true(
                "constant path has L = 0",
                constant.length == 0.0,
                {"length": constant.length},
            ),
            _true(
                "constant path has undefined efficiency",
                constant.efficiency is None,
            ),
            _true(
                "constant path has undefined excess",
                bool(np.isnan(constant.triangle_excess[0]))
                and not bool(constant.triangle_excess_valid[0]),
            ),
            _true(
                "constant path has zero valid angles",
                constant.angle_valid_fraction == 0.0,
                {"angle_valid_fraction": constant.angle_valid_fraction},
            ),
        ],
        "details": {
            "one_zero_step": one_zero.as_json(),
            "first_zero_step": first_zero.as_json(),
            "constant_path": constant.as_json(),
        },
    }


def case_near_zero_angle_instability(rng) -> dict:
    epsilons = [1e-4, 1e-6, 1e-8, 1e-10]
    sweep = []
    for eps in epsilons:
        plus = comparison_angles(
            [(0.0, 0.0), (1.0, 0.0), (1.0 + eps, 0.0)],
            np.array([1.0, eps]),
            _euclidean,
        )
        minus = comparison_angles(
            [(0.0, 0.0), (1.0, 0.0), (1.0 - eps, 0.0)],
            np.array([1.0, eps]),
            _euclidean,
        )
        sweep.append(
            {
                "epsilon": eps,
                "theta_plus": float(plus.angle[0]),
                "theta_minus": float(minus.angle[0]),
                "angle_jump": float(plus.angle[0] - minus.angle[0]),
                "configuration_perturbation": 2.0 * eps,
            }
        )
    diagram_plus = comparison_angles(
        [_singleton(0.0), _singleton(1.0), _singleton(1.0 + 1e-8)],
        np.array([1.0, 1e-8]),
        _exact_singleton_metric,
    )
    diagram_minus = comparison_angles(
        [_singleton(0.0), _singleton(1.0), _singleton(1.0 - 1e-8)],
        np.array([1.0, 1e-8]),
        _exact_singleton_metric,
    )
    plus_anomaly = bool(diagram_plus.cosine_anomaly[0])
    pi = float(np.pi)
    return {
        "case_id": "W-09",
        "category": "edge_cases",
        "description": (
            "Near a zero step with fixed first step, a perturbation of 2 eps "
            "in the configuration flips the comparison angle between pi and 0. "
            "The angle is not continuous at zero step size, which is why the "
            "noise-calibrated abstention floor exists."
        ),
        "checks": [
            _true(
                "angle jump exceeds 3.14 at eps = 1e-8",
                sweep[2]["angle_jump"] > 3.14,
                {"angle_jump": sweep[2]["angle_jump"]},
            ),
            _true(
                "configuration perturbation is below 1e-7 at eps = 1e-8",
                sweep[2]["configuration_perturbation"] < 1e-7,
                {"perturbation": sweep[2]["configuration_perturbation"]},
            ),
            _true(
                "diagram-space plus side is pi within arccos conditioning",
                abs(float(diagram_plus.angle[0]) - pi) <= 1e-3,
                {
                    "theta_plus": float(diagram_plus.angle[0]),
                    "deviation": abs(float(diagram_plus.angle[0]) - pi),
                    "note": (
                        "cancellation in a^2 + b^2 - c^2 at 1e-16 mixed with "
                        "arccos conditioning near pi gives O(sqrt(eps)) angle error"
                    ),
                },
            ),
            _true(
                "diagram-space minus side is 0 within arccos conditioning",
                abs(float(diagram_minus.angle[0])) <= 1e-3,
                {
                    "theta_minus": float(diagram_minus.angle[0]),
                    "deviation": abs(float(diagram_minus.angle[0])),
                },
            ),
            _true(
                "monotone sweep: jump is still pi at eps = 1e-10",
                abs(sweep[3]["angle_jump"] - pi) <= 1e-9,
                {"final_jump": sweep[3]["angle_jump"]},
            ),
            _true(
                "roundoff anomaly near pi is flagged, not hidden",
                plus_anomaly,
                {
                    "raw_cosine": float(diagram_plus.cosine_raw[0]),
                    "anomaly": plus_anomaly,
                },
            ),
        ],
        "details": {
            "sweep": sweep,
            "diagram_instance_eps": 1e-8,
            "diagram_plus_raw_cosine": float(diagram_plus.cosine_raw[0]),
            "diagram_plus_anomaly": plus_anomaly,
            "diagram_minus_raw_cosine": float(diagram_minus.cosine_raw[0]),
            "diagram_minus_anomaly": bool(diagram_minus.cosine_anomaly[0]),
        },
    }


def case_cosine_clip_and_anomaly(rng) -> dict:
    def triple(a: float, b: float, c: float):
        pairs = {(0, 1): a, (0, 2): c, (1, 2): b}
        metric = lambda i, j: 0.0 if i == j else pairs[(min(i, j), max(i, j))]
        return comparison_angles([0, 1, 2], np.array([a, b]), metric)

    valid_right = triple(1.0, 1.0, float(np.sqrt(2.0)))
    straight = triple(1.0, 1.0, 2.0)
    roundoff = triple(1.0, 1.0, 2.0 * (1.0 + 1e-13))
    non_metric = triple(1.0, 1.0, 3.0)
    return {
        "case_id": "W-10",
        "category": "edge_cases",
        "description": (
            "Cosine inputs are clipped to [-1, 1]. A raw cosine outside "
            "1 + 1e-12 raises an anomaly flag instead of being silently "
            "hidden; small roundoff is clipped without a flag."
        ),
        "checks": [
            _close(
                "right angle raw cosine is 0 without anomaly",
                [0.0],
                [valid_right.cosine_raw[0]],
                1e-12,
            ),
            _true("right angle has no anomaly", not bool(valid_right.cosine_anomaly[0])),
            _close(
                "straight raw cosine is exactly -1",
                [-1.0],
                [straight.cosine_raw[0]],
                1e-15,
            ),
            _true("straight has no anomaly", not bool(straight.cosine_anomaly[0])),
            _close(
                "roundoff case is clipped to theta = pi",
                [float(np.pi)],
                [roundoff.angle[0]],
                1e-12,
            ),
            _true(
                "roundoff case within 1e-12 does not raise an anomaly",
                not bool(roundoff.cosine_anomaly[0]),
                {"raw_cosine": float(roundoff.cosine_raw[0])},
            ),
            _true(
                "non-metric triple raises the anomaly flag",
                bool(non_metric.cosine_anomaly[0]),
                {"raw_cosine": float(non_metric.cosine_raw[0])},
            ),
            _close(
                "non-metric triple is clipped to theta = pi",
                [float(np.pi)],
                [non_metric.angle[0]],
                1e-12,
            ),
        ],
        "details": {
            "right_angle_raw_cosine": float(valid_right.cosine_raw[0]),
            "roundoff_raw_cosine": float(roundoff.cosine_raw[0]),
            "roundoff_anomaly": bool(roundoff.cosine_anomaly[0]),
            "non_metric_raw_cosine": float(non_metric.cosine_raw[0]),
            "non_metric_anomaly": bool(non_metric.cosine_anomaly[0]),
        },
    }


def case_triangle_inequality_efficiency_random(rng) -> dict:
    n_euclidean = 150
    max_violation = -float("inf")
    min_eta = float("inf")
    max_eta = -float("inf")
    n_undefined = 0
    for _ in range(n_euclidean):
        dim = int(rng.choice([1, 2, 3, 5, 8]))
        n_points = int(rng.integers(5, 13))
        points = rng.normal(size=(n_points, dim))
        timestamps = np.arange(n_points, dtype=float)
        pd = compute_path_diagnostics(points, timestamps, _euclidean)
        max_violation = max(max_violation, pd.displacement - pd.length)
        if pd.efficiency is None:
            n_undefined += 1
        else:
            min_eta = min(min_eta, pd.efficiency)
            max_eta = max(max_eta, pd.efficiency)

    n_graphs = 50
    graph_violation = -float("inf")
    graph_metric_violation = -float("inf")
    graph_eta_range = [float("inf"), -float("inf")]
    for _ in range(n_graphs):
        n_nodes = 6
        weights = rng.uniform(0.1, 2.0, size=(n_nodes, n_nodes))
        weights = np.triu(weights, 1)
        weights = weights + weights.T
        dist = weights.copy()
        np.fill_diagonal(dist, 0.0)
        for k in range(n_nodes):
            dist = np.minimum(dist, dist[:, k][:, None] + dist[k, :][None, :])
        path = rng.permutation(n_nodes)
        objects = list(path)
        metric = lambda i, j: float(dist[i, j])
        pd = compute_path_diagnostics(objects, np.arange(n_nodes, dtype=float), metric)
        graph_violation = max(graph_violation, pd.displacement - pd.length)
        for i in range(n_nodes):
            for j in range(n_nodes):
                for k in range(n_nodes):
                    graph_metric_violation = max(
                        graph_metric_violation,
                        dist[i, j] - dist[i, k] - dist[k, j],
                    )
        graph_eta_range[0] = min(graph_eta_range[0], pd.efficiency)
        graph_eta_range[1] = max(graph_eta_range[1], pd.efficiency)

    discrete_metric = lambda i, j: 0.0 if i == j else 1.0
    discrete_path = compute_path_diagnostics([0, 1, 0, 2, 0], np.arange(5), discrete_metric)
    constant_path = compute_path_diagnostics([0, 0, 0], np.arange(3), discrete_metric)
    return {
        "case_id": "W-11",
        "category": "randomized_checks",
        "description": (
            "For random Euclidean paths, random graph shortest-path metrics, "
            "and a discrete 0/1 metric, R <= L and 0 <= eta <= 1 hold, and "
            "L = 0 yields undefined efficiency."
        ),
        "checks": [
            _true(
                "Euclidean paths satisfy R <= L",
                max_violation <= 1e-9,
                {"max_R_minus_L": max_violation, "tolerance": 1e-9},
            ),
            _true("all Euclidean efficiencies lie in [0, 1]", min_eta >= -1e-12 and max_eta <= 1 + 1e-12, {"min_eta": min_eta, "max_eta": max_eta}),
            _true("no zero-length Euclidean path was generated", n_undefined == 0),
            _true(
                "graph shortest-path metrics satisfy R <= L",
                graph_violation <= 1e-9,
                {"max_R_minus_L": graph_violation},
            ),
            _true(
                "graph shortest-path metric satisfies the triangle inequality",
                graph_metric_violation <= 1e-9,
                {"max_violation": graph_metric_violation},
            ),
            _true(
                "graph efficiencies lie in [0, 1]",
                graph_eta_range[0] >= -1e-12 and graph_eta_range[1] <= 1 + 1e-12,
                {"min_eta": graph_eta_range[0], "max_eta": graph_eta_range[1]},
            ),
            _close(
                "discrete metric excursion has eta = 0",
                [0.0],
                [discrete_path.efficiency],
                1e-12,
            ),
            _true(
                "constant discrete path has undefined efficiency",
                constant_path.efficiency is None,
            ),
        ],
        "details": {
            "n_euclidean_paths": n_euclidean,
            "max_euclidean_R_minus_L": max_violation,
            "euclidean_eta_range": [min_eta, max_eta],
            "n_graphs": n_graphs,
            "max_graph_R_minus_L": graph_violation,
            "max_graph_triangle_violation": graph_metric_violation,
            "graph_eta_range": graph_eta_range,
            "discrete_excursion": discrete_path.as_json(),
        },
    }


def case_perturbation_bounds_random(rng) -> dict:
    n_trials = 100
    n_points = 8
    step = 0.1
    max_ratios = {"length": -float("inf"), "displacement": -float("inf"), "speed": -float("inf"), "speed_change": -float("inf")}
    for _ in range(n_trials):
        points = rng.normal(size=(n_points, 2))
        eps = rng.uniform(1e-4, 0.02, size=n_points)
        noise = rng.normal(size=(n_points, 2))
        norms = np.linalg.norm(noise, axis=1, keepdims=True)
        noise = noise / np.where(norms == 0, 1.0, norms) * eps[:, None]
        perturbed = points + noise
        timestamps = np.arange(n_points, dtype=float) * step
        true = compute_path_diagnostics(points, timestamps, _euclidean)
        approx = compute_path_diagnostics(perturbed, timestamps, _euclidean)
        length_bound = float(np.sum(eps[:-1] + eps[1:]))
        displacement_bound = float(eps[0] + eps[-1])
        max_ratios["length"] = max(
            max_ratios["length"],
            abs(approx.length - true.length) / length_bound,
        )
        max_ratios["displacement"] = max(
            max_ratios["displacement"],
            abs(approx.displacement - true.displacement) / displacement_bound,
        )
        speed_bounds = (eps[:-1] + eps[1:]) / step
        speed_ratios = np.abs(approx.interval_speeds - true.interval_speeds) / speed_bounds
        max_ratios["speed"] = max(max_ratios["speed"], float(np.max(speed_ratios)))
        change_bounds = (
            eps[:-2] + 2.0 * eps[1:-1] + eps[2:]
        ) / (step * step)
        change_ratios = (
            np.abs(approx.speed_change_rates - true.speed_change_rates) / change_bounds
        )
        max_ratios["speed_change"] = max(
            max_ratios["speed_change"], float(np.max(change_ratios))
        )
    return {
        "case_id": "W-12",
        "category": "randomized_checks",
        "description": (
            "For 100 randomly perturbed Euclidean paths with per-diagram error "
            "budgets eps_t, the metric reverse-triangle bounds hold: length, "
            "displacement, speed, and speed-change errors never exceed "
            "sum(eps_t + eps_t+1), eps_0 + eps_T, (eps_t + eps_t+1)/h, and "
            "(eps_t-1 + 2 eps_t + eps_t+1)/h^2 respectively."
        ),
        "checks": [
            _true(
                "length error within sum(eps_t + eps_t+1)",
                max_ratios["length"] <= 1 + 1e-9,
                {"max_ratio": max_ratios["length"]},
            ),
            _true(
                "displacement error within eps_0 + eps_T",
                max_ratios["displacement"] <= 1 + 1e-9,
                {"max_ratio": max_ratios["displacement"]},
            ),
            _true(
                "speed error within (eps_t + eps_t+1)/h",
                max_ratios["speed"] <= 1 + 1e-9,
                {"max_ratio": max_ratios["speed"]},
            ),
            _true(
                "speed-change error within (eps_t-1 + 2 eps_t + eps_t+1)/h^2",
                max_ratios["speed_change"] <= 1 + 1e-9,
                {"max_ratio": max_ratios["speed_change"]},
            ),
        ],
        "details": {
            "n_trials": n_trials,
            "n_points": n_points,
            "step": step,
            "max_observed_over_bound": max_ratios,
        },
    }


def case_irregular_timestamps_and_clock(rng) -> dict:
    lifespan = 10.0
    births = [0.0, 1.0, 0.5, 2.0, 1.0]
    diagrams = [_singleton(s, lifespan) for s in births]
    timestamps = np.array([0.0, 0.1, 0.3, 0.6, 0.7])
    pd = compute_path_diagnostics(diagrams, timestamps, _exact_singleton_metric)
    expected_speeds = np.array([1.0, 0.5, 1.5, 1.0]) / np.array([0.1, 0.2, 0.3, 0.1])
    expected_midpoints = np.array([0.05, 0.2, 0.45, 0.65])
    expected_changes = np.diff(expected_speeds) / np.diff(expected_midpoints)

    stretched = compute_path_diagnostics(diagrams, 2.0 * timestamps, _exact_singleton_metric)
    relabeled = compute_path_diagnostics(
        diagrams, np.array([0.0, 0.2, 0.4, 0.6, 0.8]), _exact_singleton_metric
    )

    rejections = []
    for bad in ([0.0, 1.0, 1.0], [0.0, 0.5, 0.2], [0.0, 0.2, 0.1, 0.5, 0.4]):
        try:
            validate_timestamps(bad)
        except ValueError:
            rejections.append(True)
        else:
            rejections.append(False)

    floor = noise_floor(pd.adjacent_distances)
    angle_flags = angle_validity_flags(pd.adjacent_distances[:-1], pd.adjacent_distances[1:], floor)
    efficiency_flag = efficiency_validity_flag(pd.length, pd.n_intervals, floor)
    zero_floor_flags = angle_validity_flags(pd.adjacent_distances[:-1], pd.adjacent_distances[1:], 0.0)
    return {
        "case_id": "W-13",
        "category": "path_definitions",
        "description": (
            "Irregular timestamps use h_t in the speed and midpoint "
            "differences in the speed-change denominator. L and R are "
            "unchanged by order-preserving relabeling; speeds scale with the "
            "clock. Non-increasing timestamps are rejected. The noise floors "
            "and abstention rules follow the frozen formulas."
        ),
        "checks": [
            _close("speeds use observed h_t", expected_speeds, pd.interval_speeds, 1e-12),
            _close("speed timestamps are interval midpoints", expected_midpoints, pd.interval_speed_times, 1e-12),
            _close("speed-change rates use midpoint differences", expected_changes, pd.speed_change_rates, 1e-12),
            _close("L = 4", [4.0], [pd.length], 1e-12),
            _close("R = 1", [1.0], [pd.displacement], 1e-12),
            _close("eta = 0.25", [0.25], [pd.efficiency], 1e-12),
            _close("L is timestamp-relabel invariant", [pd.length], [relabeled.length], 1e-15),
            _close("R is timestamp-relabel invariant", [pd.displacement], [relabeled.displacement], 1e-15),
            _close("clock dilation halves speeds", pd.interval_speeds / 2.0, stretched.interval_speeds, 1e-12),
            _close("clock dilation quarters speed-change rates", pd.speed_change_rates / 4.0, stretched.speed_change_rates, 1e-12),
            _true("non-increasing timestamps are rejected", all(rejections)),
            _true(
                "noise-floor angle validity is min(a, b) > 2 e",
                bool(np.all(angle_flags == (np.minimum(pd.adjacent_distances[:-1], pd.adjacent_distances[1:]) > 2.0 * floor))),
                {"floor": floor, "flags": [bool(x) for x in angle_flags]},
            ),
            _true(
                "efficiency validity is L > 2 (T - 1) e",
                efficiency_flag == (pd.length > 2.0 * (pd.n_intervals - 1) * floor),
                {"floor": floor, "efficiency_valid": efficiency_flag},
            ),
            _true(
                "at zero noise only exact-zero steps are unresolved",
                bool(np.all(zero_floor_flags)),
                {"flags": [bool(x) for x in zero_floor_flags]},
            ),
        ],
        "details": {
            "timestamps": [float(x) for x in timestamps],
            "raw_diagnostics": pd.as_json(),
            "noise_floor_e": floor,
            "angle_validity_floor_flags": [bool(x) for x in angle_flags],
            "efficiency_validity_flag": efficiency_flag,
        },
    }


def case_essential_class_stripping(rng) -> dict:
    raw = np.array([[0.0, 1.0], [0.5, np.inf]])
    finite, n_essential = strip_essential(raw)
    all_essential = np.array([[0.0, np.inf], [1.0, np.inf]])
    empty_finite, n_all = strip_essential(all_essential)
    rejected = False
    try:
        as_diagram(raw)
    except ValueError:
        rejected = True
    unsorted = np.array([[2.0, 3.0], [0.0, 5.0]])
    canonical, _ = strip_essential(unsorted)
    return {
        "case_id": "W-14",
        "category": "policies",
        "description": (
            "Essential classes (death = +inf) are removed before any metric "
            "call and counted; the finite remainder is canonicalized; and "
            "passing a raw non-finite diagram to a metric raises instead of "
            "silently dropping a bar."
        ),
        "checks": [
            _close("finite part of raw diagram", [[0.0, 1.0]], finite, 0.0),
            _true("one essential class counted", n_essential == 1, {"n_essential": n_essential}),
            _true("all-essential diagram leaves the empty diagram", empty_finite.shape[0] == 0),
            _true("two essential classes counted", n_all == 2, {"n_essential": n_all}),
            _true("raw non-finite diagrams are rejected by as_diagram", rejected),
            _true(
                "canonical order is sorted by (birth, death)",
                bool(np.array_equal(canonical, np.array([[0.0, 5.0], [2.0, 3.0]]))),
                {"canonical": [[float(x), float(y)] for x, y in canonical]},
            ),
            _close(
                "stripped diagram distance to a singleton is the metric value",
                [1.0],
                [bottleneck_gudhi(finite, np.array([[0.0, 2.0]]))],
                1e-9,
            ),
        ],
        "details": {
            "raw_diagram": [[0.0, 1.0], [0.5, None]],
            "finite_part": [[float(x), float(y)] for x, y in finite],
            "n_essential": n_essential,
            "n_essential_all": n_all,
        },
    }


def case_numerical_zero_tolerance(rng) -> dict:
    base = np.array([[0.0, 1.0], [2.0, 3.0]])
    extra_diagonal_point = np.array([[0.0, 1.0], [2.0, 3.0], [5.0, 5.0]])
    gudhi_zero = bottleneck_gudhi(base, extra_diagonal_point)
    persim_zero = bottleneck_persim(base, extra_diagonal_point)
    brute_zero = bottleneck_bruteforce(base, extra_diagonal_point)
    tiny = bottleneck_gudhi(_singleton(0.0), _singleton(5e-13))
    above_gudhi = bottleneck_gudhi(_singleton(0.0), _singleton(2e-12))
    above_brute = bottleneck_bruteforce(_singleton(0.0), _singleton(2e-12))
    return {
        "case_id": "W-15",
        "category": "policies",
        "description": (
            "Numerical-zero policy: a true-zero distance between non-identical "
            "diagrams (an extra point on the diagonal) returns exactly 0.0 from "
            "every backend, so the exact-zero step rule triggers at zero noise; "
            "a declared numerical zero of 1e-12 snaps below-tolerance values "
            "and preserves values above it."
        ),
        "checks": [
            _close(
                "gudhi returns exactly 0.0 for the true-zero non-identical pair",
                [0.0],
                [gudhi_zero],
                0.0,
            ),
            _close(
                "persim returns exactly 0.0 for the true-zero non-identical pair",
                [0.0],
                [persim_zero],
                0.0,
            ),
            _close(
                "brute force returns exactly 0.0 for the true-zero non-identical pair",
                [0.0],
                [brute_zero],
                0.0,
            ),
            _close(
                "a 5e-13 distance is snapped to exactly 0.0",
                [0.0],
                [tiny],
                0.0,
            ),
            _true(
                "a 2e-12 distance is preserved above the numerical zero",
                above_gudhi > 0.0,
                {"value": above_gudhi, "numerical_zero": NUMERICAL_ZERO},
            ),
            _close(
                "gudhi and brute force agree above the numerical zero",
                [above_brute],
                [above_gudhi],
                1e-15,
            ),
        ],
        "details": {
            "true_zero_pair": {
                "base": [[0.0, 1.0], [2.0, 3.0]],
                "with_extra_diagonal_point": [[0.0, 1.0], [2.0, 3.0], [5.0, 5.0]],
                "gudhi": gudhi_zero,
                "persim": persim_zero,
                "bruteforce": brute_zero,
            },
            "numerical_zero": NUMERICAL_ZERO,
            "tiny_distance_case": tiny,
            "above_tolerance_case_gudhi": above_gudhi,
            "above_tolerance_case_bruteforce": above_brute,
        },
    }


CASES: list[tuple[str, str, str, Callable]] = [
    ("W-01", "metric_implementation", "singleton analytic bottleneck", case_singleton_analytic_bottleneck),
    ("W-02", "metric_implementation", "empty and diagonal diagrams", case_empty_and_diagonal_diagrams),
    ("W-03", "randomized_checks", "brute-force and backend agreement", case_bruteforce_backend_agreement),
    ("W-04", "randomized_checks", "bottleneck metric axioms", case_bottleneck_metric_axioms_random),
    ("W-05", "metric_implementation", "bottleneck bounded by W2", case_bottleneck_bounded_by_wasserstein2),
    ("W-06", "path_definitions", "equal speed, different order", case_equal_speed_different_order),
    ("W-07", "path_definitions", "straight, reversal, angle convention", case_straight_reversal_angle_convention),
    ("W-08", "edge_cases", "zero step undefined", case_zero_step_undefined),
    ("W-09", "edge_cases", "near-zero angle instability", case_near_zero_angle_instability),
    ("W-10", "edge_cases", "cosine clipping and anomaly", case_cosine_clip_and_anomaly),
    ("W-11", "randomized_checks", "R <= L and efficiency", case_triangle_inequality_efficiency_random),
    ("W-12", "randomized_checks", "perturbation bounds", case_perturbation_bounds_random),
    ("W-13", "path_definitions", "irregular timestamps and clock", case_irregular_timestamps_and_clock),
    ("W-14", "policies", "essential class stripping", case_essential_class_stripping),
    ("W-15", "policies", "numerical zero tolerance", case_numerical_zero_tolerance),
]


def run_all(seed: int = WITNESS_SEED) -> list[dict]:
    """Run every witness case with a single seeded generator."""
    rng = np.random.default_rng(seed)
    records = []
    for case_id, category, description, function in CASES:
        record = function(rng)
        record["case_id"] = case_id
        record["category"] = category
        record["description"] = description
        record["passed"] = bool(all(check["passed"] for check in record["checks"]))
        records.append(record)
    return records
