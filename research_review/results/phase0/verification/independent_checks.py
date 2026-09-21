#!/usr/bin/env python3
"""Independent adversarial verification of the Phase 0 (gate G0) witness suite.

Run from the project root:

    /usr/bin/python3 research_review/results/phase0/verification/independent_checks.py

Reference computations in this script use only the standard library, numpy,
gudhi, and persim.  ``tk_pilot`` is imported only inside the explicitly marked
cross-check sections (policy behavior of the code under test, the falsification
sweep of that code, the determinism run, and the numerical-zero policy
cross-check), never for the reference side.

The script prints one PASS/FAIL line per top-level check plus a final summary
and exits nonzero if any check fails.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[4]
WITNESS_DIR = ROOT / "research_review" / "results" / "phase0" / "witness"
RESULTS_JSON = WITNESS_DIR / "witness_results.json"
ENV_JSON = WITNESS_DIR / "environment.json"
SUMMARY_TXT = WITNESS_DIR / "witness_summary.txt"
RUN_LOG = WITNESS_DIR / "run.log"
FIG_DIR = WITNESS_DIR / "figures"
VERIFICATION_DIR = ROOT / "research_review" / "results" / "phase0" / "verification"

AUDITED_FILES = [
    "research_review/assumption_ledger.yaml",
    "research_review/metric_interface.md",
    "research_review/preregistration_draft.md",
    "research_review/witness_note.md",
    "src/tk_pilot/diagram_metrics.py",
    "src/tk_pilot/path_diagnostics.py",
    "src/tk_pilot/witnesses.py",
    "src/tk_pilot/witness_figures.py",
    "scripts/run_witness_suite.py",
    "tests/test_diagram_metrics.py",
    "tests/test_path_diagnostics.py",
    "tests/test_witnesses.py",
    "research_review/results/phase0/witness/witness_results.json",
    "research_review/results/phase0/witness/environment.json",
    "research_review/results/phase0/witness/witness_summary.txt",
    "research_review/results/phase0/witness/run.log",
    "research_review/results/phase0/witness/figures/fig_singleton_bottleneck.png",
    "research_review/results/phase0/witness/figures/fig_equal_speed_paths.png",
    "research_review/results/phase0/witness/figures/fig_angle_instability.png",
    "research_review/results/phase0/witness/figures/fig_random_path_checks.png",
]

FIGURE_NAMES = [
    "fig_singleton_bottleneck.png",
    "fig_equal_speed_paths.png",
    "fig_angle_instability.png",
    "fig_random_path_checks.png",
]

# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

RECORDS: list[tuple[str, str, bool]] = []
EXTRAS: list[tuple[str, str, bool]] = []


def report(check_id: str, name: str, passed: bool, details=()) -> None:
    passed = bool(passed)
    RECORDS.append((check_id, name, passed))
    print(f"[{'PASS' if passed else 'FAIL'}] {check_id}: {name}")
    for line in details:
        print(f"    {line}")


def report_extra(check_id: str, name: str, passed: bool, details=()) -> None:
    passed = bool(passed)
    EXTRAS.append((check_id, name, passed))
    print(f"[{'PASS' if passed else 'NOTE'}] {check_id} (extra): {name}")
    for line in details:
        print(f"    {line}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def max_dev(a, b) -> float:
    """NaN-aware max absolute deviation between two flat sequences."""
    aa = np.asarray(a, dtype=float).ravel()
    bb = np.asarray(b, dtype=float).ravel()
    if aa.shape != bb.shape:
        return float("inf")
    if aa.size == 0:
        return 0.0
    na, nb = np.isnan(aa), np.isnan(bb)
    if np.any(na != nb):
        return float("inf")
    both = ~na
    if not np.any(both):
        return 0.0
    return float(np.max(np.abs(aa[both] - bb[both])))


def sanitize(value):
    """JSON-safe conversion independent of the runner's own sanitizer."""
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, (bool, str)) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.generic):
        return sanitize(value.item())
    if isinstance(value, np.ndarray):
        return sanitize(value.tolist())
    return str(value)


def own_bottleneck(diagram_a, diagram_b) -> float:
    """Independent exact bottleneck distance by enumerating bijections.

    Augments each side with diagonal copies so that a bijection of the
    augmented index sets encodes a matching with the diagonal at infinite
    multiplicity.  The cost of a real point to a diagonal copy is
    ``(death - birth) / 2``; diagonal-to-diagonal costs zero.  Written from
    scratch for this verification; enumerates up to 8 augmented points so a
    self-distance on a four-point diagram (4+4) is still exact.
    """
    a = np.asarray(diagram_a, dtype=float).reshape(-1, 2)
    b = np.asarray(diagram_b, dtype=float).reshape(-1, 2)
    n, m = a.shape[0], b.shape[0]
    size = n + m
    if size == 0:
        return 0.0
    if size > 8:
        raise ValueError(f"independent enumeration limited to 8 points, got {n}+{m}")
    cost = np.zeros((size, size), dtype=float)
    for i in range(n):
        for j in range(m):
            cost[i, j] = np.max(np.abs(a[i] - b[j]))
    for i in range(n):
        cost[i, m:] = 0.5 * (a[i, 1] - a[i, 0])
    for j in range(m):
        cost[n:, j] = 0.5 * (b[j, 1] - b[j, 0])
    best = float("inf")
    for perm in itertools.permutations(range(size)):
        worst = 0.0
        for i, j in enumerate(perm):
            if cost[i, j] > worst:
                worst = cost[i, j]
                if worst >= best:
                    break
        if worst < best:
            best = worst
    return float(best)


def own_diagnostics(objects, timestamps, metric) -> dict:
    """Independent recomputation of every frozen scalar path diagnostic."""
    t = [float(x) for x in timestamps]
    n = len(t) - 1
    distances = [float(metric(objects[i], objects[i + 1])) for i in range(n)]
    h = [t[i + 1] - t[i] for i in range(n)]
    speeds = [distances[i] / h[i] for i in range(n)]
    midpoints = [0.5 * (t[i] + t[i + 1]) for i in range(n)]
    length = float(sum(distances))
    displacement = float(metric(objects[0], objects[-1]))
    eta = (displacement / length) if length > 0 else None
    rates = [
        (speeds[i] - speeds[i - 1]) / (midpoints[i] - midpoints[i - 1])
        for i in range(1, n)
    ]
    angles, turns, valid, cosines, anomalies, excess, excess_valid = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for k in range(1, n):
        a, b = distances[k - 1], distances[k]
        c = float(metric(objects[k - 1], objects[k + 1]))
        if a + b > 0:
            excess.append((a + b - c) / (a + b))
            excess_valid.append(True)
        else:
            excess.append(float("nan"))
            excess_valid.append(False)
        if a > 0 and b > 0:
            z = (a * a + b * b - c * c) / (2.0 * a * b)
            cosines.append(z)
            anomalies.append(bool(abs(z) > 1.0 + 1e-12))
            theta = math.acos(min(1.0, max(-1.0, z)))
            angles.append(theta)
            turns.append(math.pi - theta)
            valid.append(True)
        else:
            cosines.append(float("nan"))
            anomalies.append(False)
            angles.append(float("nan"))
            turns.append(float("nan"))
            valid.append(False)
    return {
        "adjacent_distances": distances,
        "interval_speeds": speeds,
        "interval_speed_times": midpoints,
        "length": length,
        "displacement": displacement,
        "efficiency": eta,
        "speed_change_rates": rates,
        "comparison_angles": angles,
        "comparison_turns": turns,
        "comparison_valid": valid,
        "cosine_raw": cosines,
        "cosine_anomaly": anomalies,
        "triangle_excess": excess,
        "triangle_excess_valid": excess_valid,
    }


# ---------------------------------------------------------------------------
# Check 1: JSON integrity, environment, and audited-file hashes
# ---------------------------------------------------------------------------


def check_01_json_integrity() -> bool:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    cases = payload["cases"]
    ids = [case["case_id"] for case in cases]
    expected_ids = [f"W-{i:02d}" for i in range(1, 16)]
    ids_ok = ids == expected_ids
    checks_bool_ok = all(
        isinstance(check.get("passed"), bool)
        for case in cases
        for check in case["checks"]
    )
    case_passed_ok = all(isinstance(case.get("passed"), bool) for case in cases)
    consistent = all(
        case["passed"] == all(check["passed"] for check in case["checks"])
        for case in cases
    )
    all_passed = all(case["passed"] for case in cases)
    summary = payload["summary"]
    summary_ok = (
        summary["n_cases"] == 15
        and summary["n_passed"] == 15
        and summary["n_failed"] == 0
        and summary["all_passed"] is True
    )
    per_cat = {}
    for case in cases:
        bucket = per_cat.setdefault(case["category"], [0, 0])
        bucket[0] += 1
        bucket[1] += int(case["passed"])
    categories_ok = all(
        per_cat.get(name, [None, None]) == [entry["cases"], entry["passed"]]
        for name, entry in summary["per_category"].items()
    )
    n_checks = sum(len(case["checks"]) for case in cases)
    name_kinds_ok = all(
        isinstance(check.get("name"), str)
        and check.get("kind") in {"max_abs_deviation", "boolean"}
        for case in cases
        for check in case["checks"]
    )

    env = json.loads(ENV_JSON.read_text(encoding="utf-8"))
    expected_packages = {
        "numpy": "2.4.3",
        "scipy": "1.17.1",
        "matplotlib": "3.10.8",
        "gudhi": "3.12.0",
        "persim": "0.3.8",
        "pytest": "9.0.3",
    }
    recorded_ok = all(env["packages"].get(k) == v for k, v in expected_packages.items())
    recorded_ok = recorded_ok and env["packages"].get("ripser") is None
    recorded_ok = recorded_ok and env["packages"].get("yaml") is not None
    python_ok = env.get("python", "").startswith("3.12.3") and env.get(
        "executable"
    ) == "/usr/bin/python3"
    seed_ok = env.get("seed") == 20260920

    import importlib

    live_versions = {}
    for name in expected_packages:
        module = importlib.import_module(name)
        live_versions[name] = getattr(module, "__version__", None)
    live_ok = all(live_versions[k] == v for k, v in expected_packages.items())
    try:
        importlib.import_module("ripser")

        ripser_absent = False
    except Exception:
        ripser_absent = True

    hash_mismatches = []
    for rel, expected in env["input_sha256"].items():
        path = ROOT / rel
        actual = sha256_file(path) if path.exists() else None
        if actual != expected:
            hash_mismatches.append((rel, expected, actual))

    passed = all(
        [
            ids_ok,
            checks_bool_ok,
            case_passed_ok,
            consistent,
            all_passed,
            summary_ok,
            categories_ok,
            name_kinds_ok,
            recorded_ok,
            python_ok,
            seed_ok,
            live_ok,
            ripser_absent,
            not hash_mismatches,
        ]
    )
    details = [
        f"cases={len(cases)} ids {expected_ids[0]}..{expected_ids[-1]} ordered={ids_ok}; "
        f"checks={n_checks} all with boolean 'passed'={checks_bool_ok}; "
        f"case-level passed consistency={consistent}; all cases passed={all_passed}",
        f"summary={summary['n_passed']}/{summary['n_cases']} all_passed={summary['all_passed']} "
        f"per-category consistent={categories_ok}",
        f"environment.json packages match ledger={recorded_ok}; python/executable={python_ok}; "
        f"seed={seed_ok}",
        f"live versions {live_versions}; ripser absent={ripser_absent}",
        f"input_sha256 mismatches vs current files: {len(hash_mismatches)}"
        + (f" -> {hash_mismatches}" if hash_mismatches else ""),
    ]
    report("CHECK 01", "JSON integrity, environment metadata, audited hashes", passed, details)
    return passed


# ---------------------------------------------------------------------------
# Check 2: W-01 analytic singleton recomputation
# ---------------------------------------------------------------------------


def check_02_w01_recompute() -> bool:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    case = next(c for c in payload["cases"] if c["case_id"] == "W-01")
    details = case["details"]
    lifespan = float(details["lifespan"])
    shifts = [float(s) for s in details["shifts"]]
    analytic = [min(abs(s), lifespan / 2.0) for s in shifts]
    stored_analytic = [float(x) for x in details["analytic_min_shifts"]]
    dev_analytic = max_dev(analytic, stored_analytic)

    # Independent recomputation of all three backends on the same inputs.
    import gudhi
    import persim

    base = np.array([[0.0, lifespan]])
    my_gudhi = [
        float(gudhi.bottleneck_distance(base, np.array([[s, s + lifespan]])))
        for s in shifts
    ]
    my_persim = [
        float(persim.bottleneck(base, np.array([[s, s + lifespan]]))) for s in shifts
    ]
    my_brute = [own_bottleneck(base, np.array([[s, s + lifespan]])) for s in shifts]

    # The revision-2 numerical-zero policy, reimplemented independently:
    # a computed distance at or below 1e-12 is returned as exactly 0.0.
    def snap(value: float) -> float:
        return 0.0 if value <= 1e-12 else float(value)

    expected_public = {
        "gudhi": [snap(v) for v in my_gudhi],
        "persim": [snap(v) for v in my_persim],
        "bruteforce": [snap(v) for v in my_brute],
    }

    deviations = {}
    for key, mine in (
        ("gudhi", my_gudhi),
        ("persim", my_persim),
        ("bruteforce", my_brute),
    ):
        deviations[f"raw_{key}_vs_analytic"] = max_dev(analytic, mine)
        deviations[f"raw_{key}_vs_stored"] = max_dev(details[key], mine)
        deviations[f"stored_{key}_vs_snapped_reference"] = max_dev(
            details[key], expected_public[key]
        )
    for key in ("gudhi", "persim", "bruteforce"):
        deviations[f"stored_{key}_vs_analytic"] = max_dev(analytic, details[key])

    worst = max(deviations.values())
    snap_exact = all(
        deviations[f"stored_{key}_vs_snapped_reference"] == 0.0
        for key in ("gudhi", "persim", "bruteforce")
    )
    passed = worst <= 1e-9 and dev_analytic == 0.0 and snap_exact
    rows = []
    for i, s in enumerate(shifts):
        rows.append(
            f"shift={s:>4}: analytic={analytic[i]:.6g} stored_gudhi={details['gudhi'][i]:.17g} "
            f"stored_persim={details['persim'][i]:.17g} stored_brute={details['bruteforce'][i]:.17g}"
        )
    details_lines = rows + [
        f"stored analytic_min_shifts exact match: {dev_analytic == 0.0}",
        f"max deviation across analytic/stored raw/snapped references: {worst:.3e} (tol 1e-9)",
        "stored values equal the independently snapped references exactly: "
        f"{snap_exact} (per backend: "
        + ", ".join(
            f"{key}={deviations[f'stored_{key}_vs_snapped_reference']:.3e}"
            for key in ("gudhi", "persim", "bruteforce")
        )
        + ")",
        f"raw gudhi on the identical shift=0 instance: {my_gudhi[0]!r} (denormal, snapped to 0.0 "
        f"by the declared policy; stored value is {details['gudhi'][0]!r})",
        "per-backend deviations: "
        + ", ".join(f"{k}={v:.3e}" for k, v in sorted(deviations.items())),
    ]
    report("CHECK 02", "W-01 singleton analytic min(|shift|, M/2) recomputation", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 3: independent exact bottleneck versus gudhi
# ---------------------------------------------------------------------------


def _random_pair(rng: np.random.Generator):
    n = int(rng.integers(0, 5))
    m = int(rng.integers(0, 5))
    if n + m > 7:
        m = 7 - n

    def make(size, label):
        if size == 0:
            return np.zeros((0, 2), dtype=float)
        birth = rng.uniform(-0.5, 2.0, size=size)
        persistence = rng.uniform(0.0, 3.0, size=size)
        points = np.column_stack([birth, birth + persistence])
        if size and rng.random() < 0.35:
            points[0] = (points[0, 0], points[0, 0])  # point on the diagonal
        if size > 1 and rng.random() < 0.25:
            points[1] = points[0]  # duplicate point
        return points

    return make(n, "a"), make(m, "b")


def check_03_independent_bottleneck() -> bool:
    import gudhi
    import persim

    empty = np.zeros((0, 2), dtype=float)
    tall = np.array([[0.0, 10.0]])
    short = np.array([[0.25, 0.75]])
    on_diag = np.array([[1.0, 1.0], [2.0, 2.0]])
    two = np.array([[0.0, 1.0], [0.0, 10.0]])
    hand_cases = [
        (empty, empty, 0.0),
        (empty, tall, 5.0),
        (tall, empty, 5.0),
        (empty, short, 0.25),
        (short, empty, 0.25),
        (on_diag, empty, 0.0),
        (empty, on_diag, 0.0),
        (two, np.array([[0.0, 1.0]]), 5.0),
        (np.array([[2.0, 3.0], [0.0, 5.0]]), np.array([[0.0, 5.0], [2.0, 3.0]]), 0.0),
        (tall, np.array([[0.3, 10.3]]), 0.3),
    ]
    hand_bad = []
    for i, (a, b, expected) in enumerate(hand_cases):
        got = own_bottleneck(a, b)
        if abs(got - expected) > 1e-9:
            hand_bad.append((i, a.tolist(), b.tolist(), expected, got))

    rng = np.random.default_rng(20260921)
    n_pairs = 120
    max_own_gudhi = 0.0
    max_own_gudhi_canonical = 0.0
    max_own_persim = 0.0
    max_gudhi_symmetry = 0.0
    max_own_symmetry = 0.0
    max_self = 0.0
    max_raw_gudhi_self = 0.0
    raw_self_nonzero = 0
    worst = None
    # Revision-2 policy cross-check: the public wrappers must return the
    # independently snapped exact value.  This is a cross-check of the code
    # under test, not part of the independent reference.
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.diagram_metrics import (  # cross-check section
        bottleneck_bruteforce,
        bottleneck_gudhi,
        bottleneck_persim,
    )

    max_wrapper_dev = 0.0
    snap_events = 0
    true_zero_nonidentical = 0
    for _ in range(n_pairs):
        a, b = _random_pair(rng)
        mine = own_bottleneck(a, b)
        g_ab = float(gudhi.bottleneck_distance(a, b))
        g_ba = float(gudhi.bottleneck_distance(b, a))
        p_ab = float(persim.bottleneck(a, b))
        own_ba = own_bottleneck(b, a)
        d1 = abs(mine - g_ab)
        if d1 > max_own_gudhi:
            max_own_gudhi = d1
            worst = (a.tolist(), b.tolist(), mine, g_ab)
        max_own_persim = max(max_own_persim, abs(mine - p_ab))
        max_own_gudhi_canonical = max(
            max_own_gudhi_canonical,
            abs(
                mine
                - float(
                    gudhi.bottleneck_distance(
                        _canonical_points(a), _canonical_points(b)
                    )
                )
            ),
        )
        max_gudhi_symmetry = max(max_gudhi_symmetry, abs(g_ab - g_ba))
        max_own_symmetry = max(max_own_symmetry, abs(mine - own_ba))
        max_self = max(max_self, abs(own_bottleneck(a, a)))
        self_raw = abs(float(gudhi.bottleneck_distance(a, a)))
        max_raw_gudhi_self = max(max_raw_gudhi_self, self_raw)
        raw_self_nonzero += int(self_raw != 0.0)
        expected_public = 0.0 if mine <= 1e-12 else mine
        max_wrapper_dev = max(
            max_wrapper_dev,
            abs(float(bottleneck_gudhi(a, b)) - expected_public),
            abs(float(bottleneck_persim(a, b)) - expected_public),
            abs(float(bottleneck_bruteforce(a, b)) - expected_public),
        )
        snap_events += int(0.0 < g_ab <= 1e-12)
        if mine == 0.0 and not (
            a.shape == b.shape and np.array_equal(a, b)
        ):
            true_zero_nonidentical += 1

    # New in the revision-2 re-verification: raw gudhi is order-sensitive on
    # some inputs.  The exact value is established by two independent methods
    # (bijection enumeration and threshold/matching), and the code's
    # canonicalization is what makes the frozen metric reproducible.
    os_a = np.array(
        [
            [0.7656414539052718, 1.3546889089204603],
            [0.38197412521465157, 1.1559903231059137],
            [-0.7977708010858131, -0.33555804047014187],
            [0.45366198498081167, 2.1114120477576535],
        ]
    )
    os_b = np.array(
        [
            [0.08799305431193427, 2.2527479101032633],
            [0.529869936383927, 0.529869936383927],
            [-0.5175050684740343, 1.0712327852241388],
            [0.2782960943926589, 2.351578581924966],
        ]
    )
    os_exact = own_bottleneck(os_a, os_b)
    os_sorted = float(
        gudhi.bottleneck_distance(_canonical_points(os_a), _canonical_points(os_b))
    )
    os_unsorted = float(gudhi.bottleneck_distance(os_a, os_b))
    perm_values = {}
    for pa in itertools.permutations(range(4)):
        for pb in itertools.permutations(range(4)):
            value = round(
                float(gudhi.bottleneck_distance(os_a[list(pa)], os_b[list(pb)])), 15
            )
            perm_values[value] = perm_values.get(value, 0) + 1
    n_perm_bad = sum(
        count for value, count in perm_values.items() if abs(value - os_exact) > 1e-9
    )
    order_ok = (
        abs(os_exact - os_sorted) <= 1e-12
        and abs(os_exact - float(persim.bottleneck(os_a, os_b))) <= 1e-12
        and abs(os_unsorted - os_exact) > 1e-6
    )

    passed = (
        not hand_bad
        and max_own_gudhi <= 1e-9
        and max_own_gudhi_canonical <= 1e-9
        and max_own_persim <= 1e-9
        and max_gudhi_symmetry <= 1e-9
        and max_own_symmetry <= 1e-9
        and max_self == 0.0
        and max_wrapper_dev <= 1e-9
        and order_ok
    )
    details = [
        f"hand-checked cases: {len(hand_cases)}, failures={len(hand_bad)}"
        + (f" -> {hand_bad}" if hand_bad else ""),
        f"random pairs: {n_pairs} (cardinality 0..4 per side, total<=7, empty diagrams, "
        f"on-diagonal points, duplicates)",
        f"max |own-gudhi(raw)|={max_own_gudhi:.3e}; "
        f"max |own-gudhi(canonical)|={max_own_gudhi_canonical:.3e}; "
        f"max |own-persim|={max_own_persim:.3e}; "
        f"gudhi symmetry dev={max_gudhi_symmetry:.3e}; own symmetry dev={max_own_symmetry:.3e}",
        f"own d(X,X) max deviation={max_self:.3e} (exact zero required)",
        f"raw gudhi d(X,X) max |value|={max_raw_gudhi_self:.3e} on {raw_self_nonzero}/{n_pairs} "
        "pairs: this reproduces the ledger numerical_zero note (denormal values for identical inputs)",
        f"revision-2 snap cross-check: max |public wrapper - independently snapped exact|="
        f"{max_wrapper_dev:.3e}; raw distances in (0, 1e-12] observed={snap_events}; "
        f"true-zero non-identical pairs observed={true_zero_nonidentical}",
        f"order-sensitivity witness: exact={os_exact!r}; gudhi canonical={os_sorted!r}; "
        f"gudhi raw unsorted={os_unsorted!r}; over 576 point permutations the raw values split as "
        f"{perm_values} with {n_perm_bad} permutations differing from exact by >1e-9; "
        f"persim={float(persim.bottleneck(os_a, os_b))!r}; the code's canonicalization selects "
        f"the exact value (new observation O3, not a defect)",
    ]
    if worst is not None and max_own_gudhi > 1e-9:
        details.append(f"worst pair raw evidence: a={worst[0]} b={worst[1]} own={worst[2]!r} gudhi={worst[3]!r}")
    report("CHECK 03", "independent exact bottleneck vs gudhi on >=80 random pairs", passed, details)
    return passed


# ---------------------------------------------------------------------------
# Check 4: W-06 recomputation
# ---------------------------------------------------------------------------


def check_04_w06_recompute() -> bool:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    case = next(c for c in payload["cases"] if c["case_id"] == "W-06")
    details = case["details"]
    timestamps = [float(x) for x in details["timestamps"]]
    path_a = [float(x) for x in details["path_a_singleton_birth_coordinates"]]
    path_b = [float(x) for x in details["path_b_singleton_birth_coordinates"]]

    def recompute(path):
        distances = [abs(path[i + 1] - path[i]) for i in range(len(path) - 1)]
        h = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        speeds = [distances[i] / h[i] for i in range(len(distances))]
        midpoints = [0.5 * (timestamps[i] + timestamps[i + 1]) for i in range(len(h))]
        rates = [
            (speeds[i] - speeds[i - 1]) / (midpoints[i] - midpoints[i - 1])
            for i in range(1, len(speeds))
        ]
        angles = []
        turns = []
        for k in range(1, len(distances)):
            a, b = distances[k - 1], distances[k]
            c = abs(path[k + 1] - path[k - 1])
            z = (a * a + b * b - c * c) / (2.0 * a * b)
            theta = math.acos(min(1.0, max(-1.0, z)))
            angles.append(theta)
            turns.append(math.pi - theta)
        return {
            "distances": distances,
            "speeds": speeds,
            "rates": rates,
            "angles": angles,
            "turns": turns,
            "length": sum(distances),
            "displacement": abs(path[-1] - path[0]),
        }

    rec_a = recompute(path_a)
    rec_b = recompute(path_b)
    pi = math.pi
    dev = {
        "path_a_angles_vs_stored": max_dev(rec_a["angles"], details["path_a_angles"]),
        "path_a_speeds_vs_stored": max_dev(rec_a["speeds"], details["path_a_speeds"]),
        "path_a_length_vs_stored": max_dev([rec_a["length"]], [details["path_a_length"]]),
        "path_a_displacement_vs_stored": max_dev(
            [rec_a["displacement"]], [details["path_a_displacement"]]
        ),
        "path_b_angles_vs_stored": max_dev(rec_b["angles"], details["path_b_angles"]),
    }
    expected_a_angles = [pi, 0.0, pi]
    expected_b_angles = [0.0, 0.0, 0.0]
    expected_a_turns = [0.0, pi, 0.0]
    dev["path_a_angles_vs_expected"] = max_dev(rec_a["angles"], expected_a_angles)
    dev["path_b_angles_vs_expected"] = max_dev(rec_b["angles"], expected_b_angles)
    dev["path_a_turns_vs_expected"] = max_dev(rec_a["turns"], expected_a_turns)
    dev["rates_vs_zero"] = max_dev(rec_a["rates"], [0.0, 0.0, 0.0])
    dev["distances_equal_across_paths"] = max_dev(rec_a["distances"], rec_b["distances"])

    # Library distances and angles (cross-check of the stored conditioning number).
    import gudhi

    singleton = lambda s: np.array([[s, s + 10.0]])
    library_angles = []
    for k in range(1, len(path_a) - 1):
        a = rec_a["distances"][k - 1]
        b = rec_a["distances"][k]
        c = float(gudhi.bottleneck_distance(singleton(path_a[k - 1]), singleton(path_a[k + 1])))
        z = (a * a + b * b - c * c) / (2.0 * a * b)
        library_angles.append(math.acos(min(1.0, max(-1.0, z))))
    library_dev = max(abs(x - y) for x, y in zip(library_angles, expected_a_angles))
    stored_library_dev = next(
        check["detail"]["max_angle_deviation"]
        for case_ in payload["cases"]
        if case_["case_id"] == "W-06"
        for check in case_["checks"]
        if check["name"].startswith("library angles")
    )

    tolerance = 1e-9
    passed = max(dev.values()) <= tolerance and abs(library_dev - stored_library_dev) <= 1e-9
    details_lines = [
        f"recomputed path A distances={rec_a['distances']} L={rec_a['length']} R={rec_a['displacement']} "
        f"speeds={rec_a['speeds']}",
        f"recomputed path A angles={rec_a['angles']} turns={rec_a['turns']} rates={rec_a['rates']}",
        f"recomputed path B distances={rec_b['distances']} angles={rec_b['angles']} rates={rec_b['rates']}",
        "deviations: " + ", ".join(f"{k}={v:.3e}" for k, v in sorted(dev.items())),
        f"library-angle max deviation recomputed={library_dev:.17g} vs stored={stored_library_dev!r} "
        f"(abs diff {abs(library_dev - stored_library_dev):.3e})",
        "note: speed-change rates and turns for W-06 are not stored in details; they are asserted "
        "by stored checks with deviation 0.0 and independently reproduced here",
    ]
    report("CHECK 04", "W-06 distances, L, R, speeds, rates, angles, turns recomputation", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 5: W-09 near-zero-step sweep recomputation
# ---------------------------------------------------------------------------


def check_05_w09_recompute() -> bool:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    case = next(c for c in payload["cases"] if c["case_id"] == "W-09")
    stored_sweep = case["details"]["sweep"]
    epsilons = [1e-4, 1e-6, 1e-8, 1e-10]

    my_sweep = []
    for eps in epsilons:
        p0 = np.array([0.0, 0.0])
        p2_plus = np.array([1.0 + eps, 0.0])
        p2_minus = np.array([1.0 - eps, 0.0])
        # a=1.0 and b=eps are the adjacent distances passed by the witness.
        c_plus = float(np.linalg.norm(p2_plus - p0))
        c_minus = float(np.linalg.norm(p2_minus - p0))
        z_plus = (1.0 + eps * eps - c_plus * c_plus) / (2.0 * eps)
        z_minus = (1.0 + eps * eps - c_minus * c_minus) / (2.0 * eps)
        theta_plus = math.acos(min(1.0, max(-1.0, z_plus)))
        theta_minus = math.acos(min(1.0, max(-1.0, z_minus)))
        my_sweep.append(
            {
                "epsilon": eps,
                "theta_plus": theta_plus,
                "theta_minus": theta_minus,
                "angle_jump": theta_plus - theta_minus,
                "configuration_perturbation": 2.0 * eps,
            }
        )
    sweep_dev = {}
    for key in ("theta_plus", "theta_minus", "angle_jump", "configuration_perturbation"):
        sweep_dev[key] = max_dev(
            [row[key] for row in my_sweep], [row[key] for row in stored_sweep]
        )

    # Diagram-space instance (exact singleton metric with the passed b = 1e-8).
    eps = float(case["details"]["diagram_instance_eps"])
    singleton = lambda s: np.array([[s, s + 10.0]])
    c_plus = own_bottleneck(singleton(0.0), singleton(1.0 + eps))
    c_minus = own_bottleneck(singleton(0.0), singleton(1.0 - eps))
    z_plus = (1.0 + eps * eps - c_plus * c_plus) / (2.0 * eps)
    z_minus = (1.0 + eps * eps - c_minus * c_minus) / (2.0 * eps)
    theta_plus = math.acos(min(1.0, max(-1.0, z_plus)))
    theta_minus = math.acos(min(1.0, max(-1.0, z_minus)))
    stored_plus = next(
        check["detail"]["theta_plus"]
        for check in case["checks"]
        if check["name"].startswith("diagram-space plus")
    )
    stored_minus = next(
        check["detail"]["theta_minus"]
        for check in case["checks"]
        if check["name"].startswith("diagram-space minus")
    )
    diag_dev = max(abs(theta_plus - stored_plus), abs(theta_minus - stored_minus))
    anomaly_plus = abs(z_plus) > 1.0 + 1e-12
    anomaly_minus = abs(z_minus) > 1.0 + 1e-12
    # Revision-2 fix for prior observation O1: W-09 now serializes both raw
    # cosines and both anomaly flags, and asserts the plus-side anomaly.
    stored_anomaly_fields_ok = (
        max_dev([z_plus], [case["details"]["diagram_plus_raw_cosine"]]) <= 1e-15
        and bool(case["details"]["diagram_plus_anomaly"]) == anomaly_plus
        and max_dev([z_minus], [case["details"]["diagram_minus_raw_cosine"]]) <= 1e-15
        and bool(case["details"]["diagram_minus_anomaly"]) == anomaly_minus
        and any(
            check["name"].startswith("roundoff anomaly") and check["passed"]
            for check in case["checks"]
        )
    )
    one_minus_z = 1.0 - z_minus
    sqrt_approx = math.sqrt(max(0.0, 2.0 * one_minus_z))

    passed = (
        max(sweep_dev.values()) <= 1e-12
        and diag_dev <= 1e-12
        and stored_anomaly_fields_ok
    )
    details_lines = [
        "epsilon    stored_plus      rec_plus        stored_minus     rec_minus       stored_jump     rec_jump",
    ]
    for stored, mine in zip(stored_sweep, my_sweep):
        details_lines.append(
            f"{stored['epsilon']:<10.0e} {stored['theta_plus']:.15g} {mine['theta_plus']:.15g} "
            f"{stored['theta_minus']:.15g} {mine['theta_minus']:.15g} "
            f"{stored['angle_jump']:.15g} {mine['angle_jump']:.15g}"
        )
    details_lines += [
        "sweep deviations: " + ", ".join(f"{k}={v:.3e}" for k, v in sorted(sweep_dev.items())),
        f"diagram-space: c_plus={c_plus!r} c_minus={c_minus!r}",
        f"diagram-space z_plus={z_plus!r} theta_plus={theta_plus!r} vs stored={stored_plus!r}",
        f"diagram-space z_minus={z_minus!r} theta_minus={theta_minus!r} vs stored={stored_minus!r}; "
        f"max dev={diag_dev:.3e}",
        f"why minus is ~3.2e-5 and not 0: z_minus = 1 - {one_minus_z:.6e}; "
        f"arccos(1-delta) ~ sqrt(2 delta) = {sqrt_approx:.6e}; the exact value is 0 but "
        "cancellation in a^2+b^2-c^2 at the 1e-16 level plus arccos conditioning turns it into "
        "an O(sqrt(roundoff)) angle, while the plus side lands at or below -1 and clips to pi",
        f"serialized W-09 anomaly fields match the independent recomputation: "
        f"plus raw cosine={case['details']['diagram_plus_raw_cosine']!r} anomaly="
        f"{bool(case['details']['diagram_plus_anomaly'])} (recomputed {anomaly_plus}); "
        f"minus raw cosine={case['details']['diagram_minus_raw_cosine']!r} anomaly="
        f"{bool(case['details']['diagram_minus_anomaly'])} (recomputed {anomaly_minus}); "
        f"fields_ok={stored_anomaly_fields_ok} (prior observation O1 resolved)",
    ]
    report("CHECK 05", "W-09 near-zero-step sweep recomputation and explanation", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 6: W-13 irregular timestamps and clock recomputation
# ---------------------------------------------------------------------------


def check_06_w13_recompute() -> bool:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    case = next(c for c in payload["cases"] if c["case_id"] == "W-13")
    details = case["details"]
    raw = details["raw_diagnostics"]
    timestamps = [float(x) for x in details["timestamps"]]
    births = [0.0, 1.0, 0.5, 2.0, 1.0]  # case definition in witnesses.py

    distances = [min(abs(births[i + 1] - births[i]), 5.0) for i in range(4)]
    h = [timestamps[i + 1] - timestamps[i] for i in range(4)]
    speeds = [distances[i] / h[i] for i in range(4)]
    midpoints = [0.5 * (timestamps[i] + timestamps[i + 1]) for i in range(4)]
    rates = [
        (speeds[i] - speeds[i - 1]) / (midpoints[i] - midpoints[i - 1]) for i in range(1, 4)
    ]
    length = sum(distances)
    displacement = min(abs(births[-1] - births[0]), 5.0)
    eta = displacement / length
    cosines = []
    angles = []
    turns = []
    for k in range(1, 4):
        a, b = distances[k - 1], distances[k]
        c = min(abs(births[k + 1] - births[k - 1]), 5.0)
        z = (a * a + b * b - c * c) / (2.0 * a * b)
        cosines.append(z)
        theta = math.acos(min(1.0, max(-1.0, z)))
        angles.append(theta)
        turns.append(math.pi - theta)

    # Exact rational arithmetic for the mathematical values.
    h_frac = [Fraction(1, 10), Fraction(2, 10), Fraction(3, 10), Fraction(1, 10)]
    d_frac = [Fraction(1), Fraction(1, 2), Fraction(3, 2), Fraction(1)]
    nu_frac = [d_frac[i] / h_frac[i] for i in range(4)]
    m_frac = [Fraction(1, 20), Fraction(1, 5), Fraction(9, 20), Fraction(13, 20)]
    rate_frac = [
        (nu_frac[i] - nu_frac[i - 1]) / (m_frac[i] - m_frac[i - 1]) for i in range(1, 4)
    ]

    # 95th-percentile floor with my own linear interpolation.
    ordered = sorted(distances)
    pos = 0.95 * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    my_floor = ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
    np_floor = float(np.percentile(distances, 95.0))
    stored_floor = float(details["noise_floor_e"])

    angle_pairs = list(zip(distances[:-1], distances[1:]))
    my_angle_flags = [min(a, b) > 2.0 * stored_floor for a, b in angle_pairs]
    my_efficiency_flag = length > 2.0 * (len(h) - 1) * stored_floor
    my_zero_floor_flags = [min(a, b) > 0.0 for a, b in angle_pairs]

    dev = {
        "adjacent_distances": max_dev(distances, raw["adjacent_distances"]),
        "interval_speeds": max_dev(speeds, raw["interval_speeds"]),
        "interval_speed_times": max_dev(midpoints, raw["interval_speed_times"]),
        "speed_change_rates": max_dev(rates, raw["speed_change_rates"]),
        "speed_change_times": max_dev(midpoints[1:], raw["speed_change_times"]),
        "length": max_dev([length], [raw["length"]]),
        "displacement": max_dev([displacement], [raw["displacement"]]),
        "efficiency": max_dev([eta], [raw["efficiency"]]),
        "comparison_angles": max_dev(angles, raw["comparison_angles"]),
        "comparison_turns": max_dev(turns, raw["comparison_turns"]),
        "cosine_raw": max_dev(cosines, raw["cosine_raw"]),
        "triangle_excess": max_dev(
            [(a + b - c) / (a + b) for a, b, c in zip(distances[:-1], distances[1:], [
                min(abs(births[k + 1] - births[k - 1]), 5.0) for k in range(1, 4)
            ])],
            raw["triangle_excess"],
        ),
        "noise_floor": max_dev([my_floor], [stored_floor]),
    }

    # Clock dilation: timestamps x2 halves speeds and quarters speed-change rates.
    stretched_t = [2.0 * t for t in timestamps]
    h2 = [stretched_t[i + 1] - stretched_t[i] for i in range(4)]
    speeds2 = [distances[i] / h2[i] for i in range(4)]
    mids2 = [0.5 * (stretched_t[i] + stretched_t[i + 1]) for i in range(4)]
    rates2 = [(speeds2[i] - speeds2[i - 1]) / (mids2[i] - mids2[i - 1]) for i in range(1, 4)]
    dilation_dev = max(
        max_dev([x / 2.0 for x in speeds], speeds2),
        max_dev([x / 4.0 for x in rates], rates2),
    )
    relabel_t = [0.0, 0.2, 0.4, 0.6, 0.8]
    h3 = [relabel_t[i + 1] - relabel_t[i] for i in range(4)]
    relabel_distances = [min(abs(births[i + 1] - births[i]), 5.0) for i in range(4)]
    relabel_inv = (
        abs(sum(relabel_distances) - length) == 0.0
        and abs(min(abs(births[-1] - births[0]), 5.0) - displacement) == 0.0
    )

    # Rejection of non-increasing timestamps with my own predicate and the code's.
    bad_series = [[0.0, 1.0, 1.0], [0.0, 0.5, 0.2], [0.0, 0.2, 0.1, 0.5, 0.4]]
    my_rejects = [
        all(b > a for a, b in zip(series, series[1:])) is False for series in bad_series
    ]
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.path_diagnostics import validate_timestamps  # cross-check section

    code_rejects = []
    for series in bad_series:
        try:
            validate_timestamps(series)
            code_rejects.append(False)
        except ValueError:
            code_rejects.append(True)

    passed = (
        max(dev.values()) <= 1e-9
        and dilation_dev <= 1e-9
        and relabel_inv
        and all(my_rejects)
        and all(code_rejects)
        and my_angle_flags == [bool(x) for x in details["angle_validity_floor_flags"]]
        and my_efficiency_flag == bool(details["efficiency_validity_flag"])
        and my_zero_floor_flags
    )
    details_lines = [
        f"recomputed distances={distances} speeds={speeds} midpoints={midpoints}",
        f"recomputed rates={rates} exact rational rates={[str(x) for x in rate_frac]}",
        f"L={length} R={displacement} eta={eta} angles={angles} turns={turns}",
        "deviations vs stored raw_diagnostics: "
        + ", ".join(f"{k}={v:.3e}" for k, v in sorted(dev.items())),
        f"floor e: my manual={my_floor!r} numpy={np_floor!r} stored={stored_floor!r}",
        f"angle flags mine={my_angle_flags} stored={details['angle_validity_floor_flags']}; "
        f"efficiency flag mine={my_efficiency_flag} stored={details['efficiency_validity_flag']}; "
        f"zero-floor flags mine={my_zero_floor_flags}",
        f"clock dilation x2: max deviation from speeds/2 and rates/4 = {dilation_dev:.3e}; "
        f"order-preserving relabel invariance={relabel_inv}",
        f"non-increasing timestamp rejection: own={my_rejects} code={code_rejects}",
    ]
    report("CHECK 06", "W-13 irregular-clock, floor, abstention, and dilation recomputation", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 7: falsification sweep over >= 500 random finite metric paths
# ---------------------------------------------------------------------------


def _euclidean_metric(p, q):
    return float(np.linalg.norm(np.asarray(p, dtype=float) - np.asarray(q, dtype=float)))


_SNAP_EVENTS = {"count": 0}


def _canonical_points(points) -> np.ndarray:
    """Independent canonicalization: lexsort by (birth, death), as declared."""
    arr = np.asarray(points, dtype=float).reshape(-1, 2)
    if arr.shape[0] <= 1:
        return arr
    order = np.lexsort((arr[:, 1], arr[:, 0]))
    return arr[order]


def _diagram_metric(a, b):
    import gudhi

    aa = _canonical_points(a)
    bb = _canonical_points(b)
    if aa.shape == bb.shape and np.array_equal(aa, bb):
        return 0.0
    if aa.shape[0] == 0 and bb.shape[0] == 0:
        return 0.0
    value = float(gudhi.bottleneck_distance(aa, bb))
    if value <= 1e-12:  # revision-2 numerical-zero policy, independently reimplemented
        _SNAP_EVENTS["count"] += 1
        return 0.0
    return value


def _floyd_warshall(weights: np.ndarray) -> np.ndarray:
    n = weights.shape[0]
    dist = weights.astype(float).copy()
    np.fill_diagonal(dist, 0.0)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                candidate = dist[i, k] + dist[k, j]
                if candidate < dist[i, j]:
                    dist[i, j] = candidate
    return dist


def _random_diagram(rng: np.random.Generator, n: int) -> np.ndarray:
    if n == 0:
        return np.zeros((0, 2), dtype=float)
    birth = rng.uniform(-1.0, 1.0, size=n)
    persistence = rng.choice([0.0, 0.05, 0.2], size=n, p=[0.15, 0.25, 0.6])
    persistence = persistence + rng.uniform(0.0, 2.0, size=n) * (persistence > 0)
    return np.column_stack([birth, birth + persistence])


def check_07_falsification_sweep() -> bool:
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.path_diagnostics import compute_path_diagnostics  # cross-check section

    rng = np.random.default_rng(20260922)
    n_per_kind = 180
    totals = {
        "paths": 0,
        "L_zero": 0,
        "zero_steps": 0,
        "anomalies": 0,
        "R_violations": 0,
        "eta_violations": 0,
        "angle_range_violations": 0,
        "valid_with_zero_step": 0,
        "speed_violations": 0,
        "cosine_flag_mismatches": 0,
        "excess_violations": 0,
        "formula_mismatches": 0,
        "raw_positive_R_minus_L": 0,
        "default_wrapper_mismatches": 0,
        "snapped_distances": 0,
    }
    extremes = {
        "max_R_minus_L": -float("inf"),
        "min_eta": float("inf"),
        "max_eta": -float("inf"),
        "min_angle": float("inf"),
        "max_angle": -float("inf"),
        "min_speed": float("inf"),
        "min_excess": float("inf"),
        "max_excess": -float("inf"),
        "max_formula_dev": 0.0,
        "max_formula_field": None,
        "max_default_wrapper_dev": 0.0,
    }
    witnesses = []

    def finish_path(objects, timestamps, metric, kind_label):
        totals["paths"] += 1
        pd = compute_path_diagnostics(objects, timestamps, metric)
        mine = own_diagnostics(objects, timestamps, metric)
        devs = {
            "adjacent_distances": max_dev(mine["adjacent_distances"], pd.adjacent_distances),
            "interval_speeds": max_dev(mine["interval_speeds"], pd.interval_speeds),
            "interval_speed_times": max_dev(
                mine["interval_speed_times"], pd.interval_speed_times
            ),
            "length": max_dev([mine["length"]], [pd.length]),
            "displacement": max_dev([mine["displacement"]], [pd.displacement]),
            "efficiency": (
                0.0
                if (mine["efficiency"] is None) == (pd.efficiency is None)
                and (
                    mine["efficiency"] is None
                    or abs(mine["efficiency"] - pd.efficiency) <= 1e-12
                )
                else float("inf")
            ),
            "speed_change_rates": max_dev(mine["speed_change_rates"], pd.speed_change_rates),
            "comparison_angles": max_dev(mine["comparison_angles"], pd.comparison_angles),
            "comparison_turns": max_dev(mine["comparison_turns"], pd.comparison_turns),
            "cosine_raw": max_dev(mine["cosine_raw"], pd.cosine_raw),
            "triangle_excess": max_dev(mine["triangle_excess"], pd.triangle_excess),
        }
        max_here = max(devs.values())
        if max_here > extremes["max_formula_dev"]:
            extremes["max_formula_dev"] = max_here
            extremes["max_formula_field"] = (kind_label, max(devs, key=devs.get))
        if max_here > 1e-9:
            totals["formula_mismatches"] += 1
            witnesses.append((kind_label, "formula_mismatch", devs))

        dists = mine["adjacent_distances"]
        totals["L_zero"] += int(pd.length == 0.0)
        totals["zero_steps"] += sum(
            1 for k in range(1, len(dists)) if dists[k - 1] == 0.0 or dists[k] == 0.0
        )
        extremes["max_R_minus_L"] = max(extremes["max_R_minus_L"], pd.displacement - pd.length)
        totals["raw_positive_R_minus_L"] += int(pd.displacement - pd.length > 0.0)
        if pd.displacement - pd.length > 1e-9:
            totals["R_violations"] += 1
            witnesses.append((kind_label, "R_gt_L", (pd.displacement, pd.length)))
        if pd.efficiency is not None:
            extremes["min_eta"] = min(extremes["min_eta"], pd.efficiency)
            extremes["max_eta"] = max(extremes["max_eta"], pd.efficiency)
            if pd.efficiency < -1e-12 or pd.efficiency > 1.0 + 1e-12:
                totals["eta_violations"] += 1
                witnesses.append((kind_label, "eta_range", pd.efficiency))
        extremes["min_speed"] = min(extremes["min_speed"], float(np.min(pd.interval_speeds)))
        if float(np.min(pd.interval_speeds)) < -1e-12:
            totals["speed_violations"] += 1
            witnesses.append((kind_label, "negative_speed", float(np.min(pd.interval_speeds))))

        for k in range(len(pd.comparison_angles)):
            if pd.comparison_valid[k]:
                theta = float(pd.comparison_angles[k])
                extremes["min_angle"] = min(extremes["min_angle"], theta)
                extremes["max_angle"] = max(extremes["max_angle"], theta)
                if theta < -1e-12 or theta > math.pi + 1e-12:
                    totals["angle_range_violations"] += 1
                    witnesses.append((kind_label, "angle_range", theta))
                if not (dists[k] > 0.0 and dists[k + 1] > 0.0):
                    totals["valid_with_zero_step"] += 1
                    witnesses.append((kind_label, "valid_zero_step", (dists[k], dists[k + 1])))
            raw_z = float(pd.cosine_raw[k])
            if not math.isnan(raw_z):
                flag = bool(pd.cosine_anomaly[k])
                totals["anomalies"] += int(flag)
                if flag != (abs(raw_z) > 1.0 + 1e-12):
                    totals["cosine_flag_mismatches"] += 1
                    witnesses.append((kind_label, "cosine_flag", raw_z))
        for k in range(len(pd.triangle_excess)):
            if pd.triangle_excess_valid[k]:
                q = float(pd.triangle_excess[k])
                extremes["min_excess"] = min(extremes["min_excess"], q)
                extremes["max_excess"] = max(extremes["max_excess"], q)
                if q < -1e-9 or q > 1.0 + 1e-9:
                    totals["excess_violations"] += 1
                    witnesses.append((kind_label, "excess_range", q))
        return pd

    # (a) Euclidean point paths in dimensions 1..8, with duplicates and collinear runs.
    for _ in range(n_per_kind):
        dim = int(rng.integers(1, 9))
        n_points = int(rng.integers(3, 11))
        points = rng.normal(size=(n_points, dim))
        mode = rng.random()
        if mode < 0.25:
            for i in range(1, n_points):
                if rng.random() < 0.35:
                    points[i] = points[i - 1]
        elif mode < 0.5:
            for i in range(2, n_points):
                points[i] = 2.0 * points[i - 1] - points[i - 2] + 1e-10 * rng.normal(size=dim)
        timestamps = np.cumsum(rng.uniform(0.05, 1.0, size=n_points))
        finish_path([row for row in points], timestamps, _euclidean_metric, "euclidean")

    # (b) graph shortest-path metrics from random positive-weight complete graphs.
    for _ in range(n_per_kind):
        n_nodes = int(rng.integers(4, 10))
        upper = rng.uniform(0.01, 2.0, size=(n_nodes, n_nodes))
        weights = np.triu(upper, 1)
        weights = weights + weights.T
        dist = _floyd_warshall(weights)
        path = list(rng.permutation(n_nodes))
        if rng.random() < 0.3 and len(path) > 2:
            path[-2] = path[-1]
        metric = (lambda d: lambda i, j: float(d[i, j]))(dist)
        timestamps = np.cumsum(rng.uniform(0.05, 1.0, size=len(path)))
        finish_path(path, timestamps, metric, "graph")

    # (c) random finite persistence diagrams under the L-infinity bottleneck.
    for idx in range(n_per_kind):
        n_diagrams = int(rng.integers(3, 10))
        diagrams = []
        if rng.random() < 0.2:
            # structured near-degenerate singleton path to exercise angle instability
            eps = float(rng.choice([1e-12, 1e-10, 1e-8, 1e-6]))
            signs = [0.0, 1.0, 1.0 + eps] if rng.random() < 0.5 else [0.0, 1.0, 1.0 - eps]
            diagrams = [np.array([[s, s + 10.0]]) for s in signs]
        else:
            previous = None
            for _ in range(n_diagrams):
                if previous is not None and rng.random() < 0.25:
                    diagrams.append(previous.copy())
                    continue
                card = int(rng.integers(0, 5))
                if previous is not None and rng.random() < 0.3:
                    card = previous.shape[0]
                diagrams.append(_random_diagram(rng, card))
                previous = diagrams[-1]
        timestamps = np.cumsum(rng.uniform(0.05, 1.0, size=len(diagrams)))
        pd_mine = finish_path(diagrams, timestamps, _diagram_metric, "diagram")
        # Revision-2 snap policy: the code's own default wrapper must agree with
        # the independently snapped metric on every diagram path.
        pd_default = compute_path_diagnostics(diagrams, timestamps)
        default_dev = max(
            max_dev(pd_mine.adjacent_distances, pd_default.adjacent_distances),
            max_dev([pd_mine.length], [pd_default.length]),
            max_dev([pd_mine.displacement], [pd_default.displacement]),
        )
        extremes["max_default_wrapper_dev"] = max(
            extremes["max_default_wrapper_dev"], default_dev
        )
        totals["default_wrapper_mismatches"] += int(default_dev > 1e-12)

    totals["snapped_distances"] = _SNAP_EVENTS["count"]

    violations = (
        totals["R_violations"]
        + totals["eta_violations"]
        + totals["angle_range_violations"]
        + totals["valid_with_zero_step"]
        + totals["speed_violations"]
        + totals["cosine_flag_mismatches"]
        + totals["excess_violations"]
        + totals["formula_mismatches"]
        + totals["default_wrapper_mismatches"]
    )
    passed = totals["paths"] >= 500 and violations == 0
    details_lines = [
        f"paths={totals['paths']} (euclidean={n_per_kind}, graph={n_per_kind}, diagram={n_per_kind}); "
        f"L=0 paths={totals['L_zero']}; zero steps discharged={totals['zero_steps']}; "
        f"cosine anomalies observed={totals['anomalies']}",
        f"revision-2 snap: diagram-metric snap events={totals['snapped_distances']}; "
        f"max |default wrapper path - independently snapped path|="
        f"{extremes['max_default_wrapper_dev']:.3e}; mismatches="
        f"{totals['default_wrapper_mismatches']}",
        f"extremes: max(R-L)={extremes['max_R_minus_L']:.3e} (raw-positive count="
        f"{totals['raw_positive_R_minus_L']}, all within the 1e-9 floating-point tolerance); "
        f"eta in "
        f"[{extremes['min_eta']:.6g}, {extremes['max_eta']:.6g}]; angle in "
        f"[{extremes['min_angle']:.6g}, {extremes['max_angle']:.6g}]; min speed="
        f"{extremes['min_speed']:.3e}; excess in [{extremes['min_excess']:.6g}, "
        f"{extremes['max_excess']:.6g}]",
        f"max |code - independent| over all scalar formulas: {extremes['max_formula_dev']:.3e} "
        f"(field={extremes['max_formula_field']})",
        f"violation counts: R>L={totals['R_violations']}, eta={totals['eta_violations']}, "
        f"angle range={totals['angle_range_violations']}, valid-with-zero-step="
        f"{totals['valid_with_zero_step']}, speed<0={totals['speed_violations']}, "
        f"cosine-flag mismatch={totals['cosine_flag_mismatches']}, excess="
        f"{totals['excess_violations']}, formula mismatch={totals['formula_mismatches']}",
    ]
    if witnesses:
        details_lines.append(f"first violation witnesses: {witnesses[:3]}")
    report("CHECK 07", "falsification sweep over >=500 random finite metric paths", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 8: policy cross-check against ledger text
# ---------------------------------------------------------------------------


def check_08_policy_crosscheck() -> bool:
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.diagram_metrics import (
        NUMERICAL_ZERO,
        as_diagram,
        bottleneck_bruteforce,
        bottleneck_gudhi,
        bottleneck_persim,
        strip_essential,
        wasserstein2_linf,
    )
    from tk_pilot.path_diagnostics import (
        angle_validity_flags,
        comparison_angles,
        compute_path_diagnostics,
        efficiency_validity_flag,
        validate_timestamps,
    )
    from tk_pilot.witnesses import _exact_singleton_metric, _singleton

    subchecks = []

    # (a) essential class stripping and counts; -inf and NaN deaths are rejected
    finite, n_essential = strip_essential(np.array([[0.0, 1.0], [0.5, np.inf]]))
    all_essential, n_all = strip_essential(np.array([[0.0, np.inf], [1.0, np.inf]]))
    bad_death_rejected = True
    bad_death_evidence = []
    for bad_death in (-np.inf, np.nan):
        try:
            strip_essential(np.array([[0.0, bad_death]]))
            bad_death_rejected = False
            bad_death_evidence.append(bad_death)
        except ValueError:
            pass
    strip_ok = (
        np.array_equal(finite, np.array([[0.0, 1.0]]))
        and n_essential == 1
        and all_essential.shape[0] == 0
        and n_all == 2
        and bad_death_rejected
    )
    subchecks.append(("essential +inf stripped and counted; -inf/NaN rejected", strip_ok,
                      f"finite={finite.tolist()} n={n_essential} all_essential_n={n_all}; "
                      f"unrejected bad deaths={bad_death_evidence}"))

    # (b) identical diagrams give exactly 0.0
    diagram = np.array([[0.0, 1.0], [2.0, 3.0], [1.0, 2.0]])
    permuted = np.array([[2.0, 3.0], [0.0, 1.0], [1.0, 2.0]])
    identical_ok = (
        bottleneck_gudhi(diagram, diagram) == 0.0
        and bottleneck_gudhi(diagram, permuted) == 0.0
        and bottleneck_gudhi(np.zeros((0, 2)), np.zeros((0, 2))) == 0.0
    )
    subchecks.append(("identical diagrams exactly 0.0", identical_ok,
                      f"self={bottleneck_gudhi(diagram, diagram)!r} "
                      f"permuted={bottleneck_gudhi(diagram, permuted)!r}"))

    # (c) raw non-finite diagrams rejected by as_diagram
    reject_ok = True
    rejected_what = []
    for bad in (np.array([[0.0, np.inf]]), np.array([[0.0, -np.inf]]), np.array([[np.nan, 1.0]])):
        try:
            as_diagram(bad)
            reject_ok = False
            rejected_what.append(bad.tolist())
        except ValueError:
            pass
    subchecks.append(("as_diagram rejects raw non-finite diagrams", reject_ok,
                      f"non-rejected={rejected_what}"))

    # (d) L = 0 gives eta None
    constant = compute_path_diagnostics(
        [_singleton(0.0) for _ in range(3)], [0.0, 0.25, 0.5], _exact_singleton_metric
    )
    l_zero_ok = constant.efficiency is None and constant.length == 0.0
    subchecks.append(("L=0 gives eta None, L reported", l_zero_ok,
                      f"L={constant.length!r} eta={constant.efficiency!r}"))

    # (e) zero step gives NaN angle and invalid flag
    one_zero = compute_path_diagnostics(
        [_singleton(s) for s in (0.0, 1.0, 1.0)], [0.0, 0.25, 0.5], _exact_singleton_metric
    )
    first_zero = compute_path_diagnostics(
        [_singleton(s) for s in (0.0, 0.0, 1.0)], [0.0, 0.25, 0.5], _exact_singleton_metric
    )
    zero_step_ok = (
        math.isnan(float(one_zero.comparison_angles[0]))
        and not bool(one_zero.comparison_valid[0])
        and math.isnan(float(first_zero.comparison_angles[0]))
        and not bool(first_zero.comparison_valid[0])
    )
    subchecks.append(("zero step gives NaN angle and invalid flag", zero_step_ok,
                      f"b=0 angle={one_zero.comparison_angles[0]!r} valid={bool(one_zero.comparison_valid[0])}"))

    # (f) cosine anomaly for a non-metric triple and clipping
    def triple_metric(a, b, c):
        pairs = {(0, 1): a, (0, 2): c, (1, 2): b}
        return lambda i, j: 0.0 if i == j else pairs[(min(i, j), max(i, j))]

    non_metric = comparison_angles([0, 1, 2], np.array([1.0, 1.0]), triple_metric(1.0, 1.0, 3.0))
    roundoff = comparison_angles(
        [0, 1, 2], np.array([1.0, 1.0]), triple_metric(1.0, 1.0, 2.0 * (1.0 + 1e-13))
    )
    anomaly_ok = (
        bool(non_metric.cosine_anomaly[0])
        and abs(float(non_metric.cosine_raw[0]) - (-3.5)) <= 1e-12
        and abs(float(non_metric.angle[0]) - math.pi) <= 1e-12
        and not bool(roundoff.cosine_anomaly[0])
        and abs(float(roundoff.angle[0]) - math.pi) <= 1e-12
    )
    subchecks.append(("cosine anomaly flag and clip to [-1,1]", anomaly_ok,
                      f"non_metric z={float(non_metric.cosine_raw[0])!r} flag={bool(non_metric.cosine_anomaly[0])}; "
                      f"roundoff z={float(roundoff.cosine_raw[0])!r} flag={bool(roundoff.cosine_anomaly[0])}"))

    # (g) nonpositive timestamps raise ValueError
    rejection_ok = True
    rejection_evidence = []
    for bad in ([0.0, 1.0, 1.0], [0.0, 0.5, 0.2], [0.0, 0.2, 0.1, 0.5, 0.4], [0.0, np.nan, 1.0]):
        try:
            validate_timestamps(bad)
            rejection_ok = False
            rejection_evidence.append(bad)
        except ValueError:
            pass
    subchecks.append(("nonpositive/non-finite timestamps raise ValueError", rejection_ok,
                      f"non-rejected={rejection_evidence}"))

    # (h) exact-zero abstention at e = 0
    zero_floor = angle_validity_flags(np.array([1.0, 0.0, 1.0]), np.array([0.0, 1.0, 1.0]), 0.0)
    zero_floor_ok = list(map(bool, zero_floor)) == [False, False, True]
    subchecks.append(("at e=0 only exact-zero steps abstain", zero_floor_ok,
                      f"flags={[bool(x) for x in zero_floor]}"))

    # (i) efficiency abstention just above and just below L = 2 (T-1) e
    n_intervals = 4
    floor = 1.0
    threshold = 2.0 * (n_intervals - 1) * floor
    below = efficiency_validity_flag(threshold - 1e-9, n_intervals, floor)
    at = efficiency_validity_flag(threshold, n_intervals, floor)
    above = efficiency_validity_flag(threshold + 1e-9, n_intervals, floor)
    efficiency_abstention_ok = (below is False) and (at is False) and (above is True)
    subchecks.append(("efficiency abstention L <= 2(T-1)e", efficiency_abstention_ok,
                      f"T={n_intervals} e={floor} threshold={threshold}: "
                      f"L=thr-1e-9 -> valid={below}, L=thr -> valid={at}, L=thr+1e-9 -> valid={above}"))

    # (j) ledger near-zero angle abstention uses strict min(a,b) > 2e
    flags = angle_validity_flags(
        np.array([2.0, 2.0 - 1e-9, 2.0 + 1e-9]),
        np.array([2.0, 2.0 + 1e-9, 2.0 + 1e-9]),
        1.0,
    )
    near_floor_ok = list(map(bool, flags)) == [False, False, True]
    subchecks.append(("angle abstention min(a,b) <= 2e", near_floor_ok,
                      f"flags={[bool(x) for x in flags]}"))

    # (k) efficiency formula consistency on a real computed path (W-13 style)
    diagrams = [_singleton(s) for s in (0.0, 1.0, 0.5, 2.0, 1.0)]
    timestamps = [0.0, 0.1, 0.3, 0.6, 0.7]
    pd = compute_path_diagnostics(diagrams, timestamps, _exact_singleton_metric)
    e = float(np.percentile(pd.adjacent_distances, 95.0))
    real_flag = efficiency_validity_flag(pd.length, pd.n_intervals, e)
    real_ok = real_flag == (pd.length > 2.0 * (pd.n_intervals - 1) * e)
    subchecks.append(("real-path efficiency flag matches ledger predicate", real_ok,
                      f"L={pd.length} T={pd.n_intervals} e={e!r} flag={real_flag}"))

    # (l) revision-2 numerical-zero policy on every public backend (W-15)
    base = np.array([[0.0, 1.0], [2.0, 3.0]])
    extra = np.array([[0.0, 1.0], [2.0, 3.0], [5.0, 5.0]])
    singleton = lambda s: np.array([[s, s + 10.0]])
    zero_pair = (
        bottleneck_gudhi(base, extra) == 0.0
        and bottleneck_persim(base, extra) == 0.0
        and bottleneck_bruteforce(base, extra) == 0.0
        and wasserstein2_linf(base, extra) == 0.0
    )
    tiny_snapped = (
        bottleneck_gudhi(singleton(0.0), singleton(5e-13)) == 0.0
        and bottleneck_persim(singleton(0.0), singleton(5e-13)) == 0.0
        and bottleneck_bruteforce(singleton(0.0), singleton(5e-13)) == 0.0
        and wasserstein2_linf(singleton(0.0), singleton(5e-13)) == 0.0
    )
    above_g = bottleneck_gudhi(singleton(0.0), singleton(2e-12))
    above_b = bottleneck_bruteforce(singleton(0.0), singleton(2e-12))
    above_preserved = above_g > 0.0 and abs(above_g - above_b) <= 1e-15
    exact_zero = own_bottleneck(base, extra)
    exact_tiny = own_bottleneck(singleton(0.0), singleton(5e-13))
    exact_above = own_bottleneck(singleton(0.0), singleton(2e-12))
    math_ok = exact_zero == 0.0 and 0.0 < exact_tiny <= 1e-12 and exact_above > 1e-12
    numerical_zero_ok = (
        NUMERICAL_ZERO == 1e-12 and zero_pair and tiny_snapped and above_preserved and math_ok
    )
    subchecks.append((
        "numerical-zero policy on all public backends (W-15)",
        numerical_zero_ok,
        f"NUMERICAL_ZERO={NUMERICAL_ZERO!r}; true-zero pair 0.0 from gudhi/persim/brute/w2={zero_pair}; "
        f"5e-13 snapped by all backends={tiny_snapped}; 2e-12 gudhi={above_g!r} "
        f"brute={above_b!r} preserved={above_preserved}; independent exact values "
        f"zero={exact_zero!r}, tiny={exact_tiny!r}, above={exact_above!r}",
    ))

    passed = all(ok for _, ok, _ in subchecks)
    details_lines = [f"({letter}) {name}: {'ok' if ok else 'MISMATCH'} -- {evidence}"
                     for (name, ok, evidence), letter in zip(subchecks, "abcdefghijkl")]
    report("CHECK 08", "policy cross-check against the ledger", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 9: determinism of run_all(seed=20260920)
# ---------------------------------------------------------------------------


def check_09_determinism() -> bool:
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.witnesses import run_all  # allowed determinism cross-check

    started = time.time()
    first = run_all(seed=20260920)
    second = run_all(seed=20260920)
    elapsed = time.time() - started
    first_json = json.dumps(sanitize(first), sort_keys=True)
    second_json = json.dumps(sanitize(second), sort_keys=True)
    identical = first_json == second_json
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    stored_json = json.dumps(sanitize(payload["cases"]), sort_keys=True)
    matches_stored = first_json == stored_json
    stored_cases = payload["cases"]
    differences = []
    if not matches_stored:
        for i, (a, b) in enumerate(zip(first, stored_cases)):
            a_clean, b_clean = sanitize(a), sanitize(b)
            if a_clean != b_clean:
                differences.append(a.get("case_id", f"index {i}"))
    passed = identical and matches_stored and len(first) == 15
    details_lines = [
        f"two runs of run_all(seed=20260920): JSON-serializable output identical={identical}; "
        f"run wall time {elapsed:.2f} s",
        f"first run output matches stored witness_results.json cases exactly={matches_stored}; "
        f"differing cases={differences}",
    ]
    report("CHECK 09", "determinism and reproducibility of the stored witness results", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Check 10: figures
# ---------------------------------------------------------------------------


def _png_is_valid(path: Path) -> tuple[bool, str]:
    data = path.read_bytes()
    if len(data) < 20:
        return False, "file shorter than 20 bytes"
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False, "bad magic bytes"
    if data[12:16] != b"IHDR":
        return False, "first chunk is not IHDR"
    if data[-12:-8] != b"\x00\x00\x00\x00" or data[-8:-4] != b"IEND":
        return False, "missing terminal IEND chunk"
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        return False, f"nonpositive dimensions {width}x{height}"
    return True, f"{width}x{height}, {len(data)} bytes, sha256={sha256_file(path)[:16]}"


def check_10_figures() -> bool:
    problems = []
    evidence = []
    for name in FIGURE_NAMES:
        path = FIG_DIR / name
        if not path.exists():
            problems.append(f"{name} missing")
            continue
        if path.stat().st_size == 0:
            problems.append(f"{name} empty")
            continue
        ok, detail = _png_is_valid(path)
        if not ok:
            problems.append(f"{name}: {detail}")
        evidence.append(f"{name}: {detail}")

    regeneration_ok = False
    try:
        sys.path.insert(0, str(ROOT / "src"))
        import matplotlib

        matplotlib.use("Agg")
        from tk_pilot import witness_figures  # cross-check section

        payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = witness_figures.make_all_figures(Path(tmp), payload["cases"])
            same = []
            for path in regenerated:
                stored_path = FIG_DIR / path.name
                match = sha256_file(path) == sha256_file(stored_path)
                same.append((path.name, match))
            regeneration_ok = all(match for _, match in same)
            evidence.append(
                "regenerated byte-identical PNGs: "
                + ", ".join(f"{name}={match}" for name, match in same)
            )
    except Exception as exc:  # pragma: no cover - diagnostic path
        evidence.append(f"figure regeneration failed: {type(exc).__name__}: {exc}")

    passed = not problems and len(evidence) >= len(FIGURE_NAMES) and regeneration_ok
    details_lines = evidence + (["problems: " + "; ".join(problems)] if problems else [])
    report("CHECK 10", "figure files exist, are valid PNGs, and reproduce byte-for-byte", passed, details_lines)
    return passed


# ---------------------------------------------------------------------------
# Extra check: prior finding E1 (-inf death) is resolved in revision 2
# ---------------------------------------------------------------------------


def extra_inf_death() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.diagram_metrics import as_diagram, strip_essential

    outcomes = {}
    for label, value in (("-inf", -np.inf), ("NaN", np.nan), ("+inf", np.inf)):
        try:
            finite, n_essential = strip_essential(np.array([[0.0, value]]))
            outcomes[label] = (finite.tolist(), int(n_essential))
        except ValueError as exc:
            outcomes[label] = f"ValueError: {exc}"
    as_diagram_rejects = False
    try:
        as_diagram(np.array([[0.0, -np.inf]]))
    except ValueError:
        as_diagram_rejects = True
    resolved = (
        isinstance(outcomes["-inf"], str)
        and isinstance(outcomes["NaN"], str)
        and outcomes["+inf"] == ([], 1)
        and as_diagram_rejects
    )
    report_extra(
        "E1",
        "prior finding resolved: strip_essential rejects death=-inf (and NaN) while counting death=+inf",
        resolved,
        [
            f"strip_essential with -inf -> {outcomes['-inf']}",
            f"strip_essential with NaN  -> {outcomes['NaN']}",
            f"strip_essential with +inf -> {outcomes['+inf']} (finite part empty, one essential class counted)",
            f"as_diagram still rejects raw non-finite input: {as_diagram_rejects}",
        ],
    )


# ---------------------------------------------------------------------------
# Extra check: the snap policy can break the exact triangle inequality
# ---------------------------------------------------------------------------


def extra_snap_triangle() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from tk_pilot.diagram_metrics import NUMERICAL_ZERO, bottleneck_gudhi
    from tk_pilot.path_diagnostics import compute_path_diagnostics

    singleton = lambda s: np.array([[s, s + 10.0]])
    x, y, z = singleton(0.0), singleton(9e-13), singleton(2e-12)
    pd = compute_path_diagnostics([x, y, z], [0.0, 1.0, 2.0])
    r_minus_l = float(pd.displacement - pd.length)
    eta = pd.efficiency
    detected = r_minus_l > 0.0 and eta is not None and eta > 1.0
    report_extra(
        "E2",
        "snap policy makes R <= L and eta <= 1 hold only up to about 2*NUMERICAL_ZERO",
        not detected,
        [
            f"witness: D0={{(0,10)}}, D1={{(9e-13,10+9e-13)}}, D2={{(2e-12,10+2e-12)}}",
            f"d(D0,D1)={bottleneck_gudhi(x, y)!r} (raw 9.006e-13 snapped at NUMERICAL_ZERO={NUMERICAL_ZERO}); "
            f"d(D1,D2)={bottleneck_gudhi(y, z)!r}; d(D0,D2)={bottleneck_gudhi(x, z)!r}",
            f"L={pd.length!r} R={pd.displacement!r} eta={eta!r} R-L={r_minus_l!r}",
            "the violation is bounded by 2*NUMERICAL_ZERO and is far inside the suite's 1e-9 "
            "floating-point tolerance, so no stored witness fails; the ledger's exact "
            "triangle-inequality wording is now approximate under the declared snap",
        ],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def print_hashes() -> None:
    print("sha256 of audited files")
    for rel in AUDITED_FILES:
        path = ROOT / rel
        digest = sha256_file(path) if path.exists() else "MISSING"
        print(f"    {digest}  {rel}")
    print()


def main() -> int:
    print("Independent adversarial verification of the Phase 0 witness suite (gate G0)")
    print(f"project root: {ROOT}")
    print()
    print_hashes()

    checks = [
        check_01_json_integrity,
        check_02_w01_recompute,
        check_03_independent_bottleneck,
        check_04_w06_recompute,
        check_05_w09_recompute,
        check_06_w13_recompute,
        check_07_falsification_sweep,
        check_08_policy_crosscheck,
        check_09_determinism,
        check_10_figures,
    ]
    for check in checks:
        try:
            check()
        except Exception as exc:  # a raised exception is a failed check
            report(check.__name__, f"raised {type(exc).__name__}", False, [str(exc)])

    try:
        extra_inf_death()
    except Exception as exc:
        report_extra("E1", f"raised {type(exc).__name__}", False, [str(exc)])

    try:
        extra_snap_triangle()
    except Exception as exc:
        report_extra("E2", f"raised {type(exc).__name__}", False, [str(exc)])

    n_passed = sum(1 for _, _, ok in RECORDS if ok)
    n_total = len(RECORDS)
    failed_ids = [cid for cid, _, ok in RECORDS if not ok]
    extras_failed = [cid for cid, _, ok in EXTRAS if not ok]
    print()
    print(f"SUMMARY: {n_passed}/{n_total} top-level checks passed; failed={failed_ids or 'none'}")
    if EXTRAS:
        print(
            f"EXTRA findings: {len(EXTRAS) - len(extras_failed)}/{len(EXTRAS)} clean; "
            f"notes={extras_failed or 'none'}"
        )
    return 0 if n_passed == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
