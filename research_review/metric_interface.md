# Metric interface for the finite diagram path (WP-0.1)

Companion artifacts: `research_review/assumption_ledger.yaml` (machine-readable ledger) and `research_review/Topological_Kinematics_Research_Plan.md` (authoritative plan). The frozen conventions are the ones in `assumption_ledger.yaml`; if this document and the ledger ever disagree, the ledger wins and the disagreement must be reported, not silently resolved.

Acceptance test (WP-0.1 verification): a second reader must be able to compute every quantity below from one held-out trajectory using only this document and the ledger, with no unstated convention. The worked example in section 6 is the numerical anchor for that test.

## 1. Purpose and scope

This document fixes the operational meaning of every quantity used in Phase 0 at gate G0. It covers the restricted finite-metric model only: a finite sequence of finite persistence diagrams with finite birth and death coordinates, a fixed diagram metric, and strictly increasing timestamps. It does not cover data extraction correctness (G2), predictive value (G3), applications (G4), or theory (G5), and it makes no causal claim. Every diagnostic here is an observable statistic of the observed diagram path under the frozen observation map. None of them is a latent physical cause, a direction, or an acceleration.

The frame-to-diagram map itself (window, filtration, coefficient field, truncation) is declared elsewhere and belongs to G2. This interface starts from diagrams that are already given and validated.

## 2. Exact input object and validation rules

A trajectory is a pair (D, t) with the following structure.

1. `D` is an ordered list `D_0, ..., D_T` of persistence diagrams. Each `D_i` is a finite multiset of points `(b, d)` with `b <= d`. Raw inputs may contain essential classes with `d = +inf`; those are removed by item 4 before a metric call, so every metric always sees finite diagrams with finite `d`. A diagram may be empty (zero points), and the diagonal itself (all points on the diagonal) counts as an empty finite diagram.
2. `t` is a list of timestamps `t_0 < t_1 < ... < t_T`, with `T >= 1` (at least two diagrams, hence at least one step).
3. Strictly increasing timestamps are required. Any nonpositive `h_t = t_{t+1} - t_t` is an input error and must be rejected; no silent repair.
4. Essential classes (death = +inf) are removed before any metric computation, and the per-window count is recorded.
5. Diagram cardinality may change between windows; the metric handles unequal cardinality through diagonal matching. Per-window cardinality and essential-class count are recorded.
6. All finite bars are retained; no label-dependent persistence threshold is allowed.
7. Windows are causal: `D_i` may use only observations at or before `t_i`. Future observations are forbidden, and detection windows are trailing windows.
8. The primary observation map is one frame per sample (single-frame window). Trailing-window pooling (lengths 1, 3, 5; strides 1, 2, 4) is a later, separately reported observation map (WP-2.1) and is not part of the primary baseline.
9. The master grid uses physical time `u = j/128`, `j = 0..128`; strides 1, 2, 4 subsample the same master realization and keep the physical horizon `[0, 1]` fixed.

## 3. Quantities

Notation: `d` is the diagram metric of section 5, applied to finite diagrams after essential classes have been removed. `T` is the number of intervals, so there are `T + 1` diagrams.

### 3.1 Interval sizes and interval speed

For `t = 0, ..., T - 1`:

```
h_t  = t_{t+1} - t_t            (positive by validation)
m_t  = (t_t + t_{t+1}) / 2      (interval midpoint)
nu_t = d(D_t, D_{t+1}) / h_t    (interval speed, timestamped at m_t)
```

`nu_t` is a finite-interval average speed. It is not a metric derivative and it is established background (Kramar et al. Eq. (16)).

### 3.2 Path length, endpoint displacement, efficiency

```
L   = sum_{t=0}^{T-1} d(D_t, D_{t+1})
R   = d(D_0, D_T)
eta = R / L, defined only when L > 0
```

`R <= L` and `0 <= eta <= 1` when `L > 0`, by the triangle inequality. These statements are exact for the mathematical metric. In the public snapped implementation, with `T` intervals, `R - L <= T * NUMERICAL_ZERO` and `eta <= 1 + T * NUMERICAL_ZERO / L`, because each adjacent distance can be decreased by at most `NUMERICAL_ZERO`; `eta` can therefore exceed 1 when `L` is inside the numerical band, and at pilot-scale lengths the excess is negligible. Policy 13 makes the implementation a tolerance pseudometric at that scale, and the witness suite tests the bounds at a `1e-9` tolerance. When `L = 0`, `eta` is null, `L` is still reported, and a flag is recorded; no imputation. Order-preserving relabeling of timestamps leaves `L` and `R` unchanged.

### 3.3 Speed-change rate and the midpoint denominator

For `t = 1, ..., T - 1`:

```
a_t = (nu_t - nu_{t-1}) / (m_t - m_{t-1})
```

Midpoint denominator explanation. `nu_t` is an average over the interval `[t_t, t_{t+1}]` and is stamped at its midpoint `m_t`. The natural clock for a difference of two such interval averages is therefore the midpoint clock, and the frozen denominator is the observed midpoint spacing `m_t - m_{t-1}`. This avoids silently assuming a regular grid. On a regular grid with `t_j = t_0 + j dt`, the midpoint spacing equals `dt`, so `a_t = (nu_t - nu_{t-1}) / dt`, which matches the regular-grid definition in the plan. For irregular clocks, only the midpoint form is used.

`a_t` is the rate of change of the scalar speed. It is never called physical acceleration, and it cannot detect a constant-speed change of direction. Finite differences amplify observation and persistence-estimation error.

### 3.4 Comparison angle and turn

At an interior time `t = 1, ..., T - 1`, define

```
a = d(D_{t-1}, D_t)
b = d(D_t, D_{t+1})
c = d(D_{t-1}, D_{t+1})
z = (a^2 + b^2 - c^2) / (2ab)
theta_t = arccos( clip(z, -1, 1) ), defined only when ab > 0
```

Validity condition: `ab > 0`, that is `a > 0` and `b > 0`. If `a = 0` or `b = 0`, `theta_t` is null and the step is counted as unresolved (zero step).

Clipping: `z` is clipped to `[-1, 1]` before `arccos` so the computation is total. If `|z| > 1 + 1e-12`, a cosine-anomaly flag is recorded; this indicates roundoff beyond tolerance or a violated metric-triangle input and is never hidden. `theta_t` lies in `[0, pi]`.

Convention: `theta_t` is the interior angle of the metric triangle `(D_{t-1}, D_t, D_{t+1})`. Straight continuation gives `theta = pi`; exact reversal gives `theta = 0`.

Turn companion: `tau_t = pi - theta_t`, defined on the same domain, so straight continuation gives `tau = 0`. Report `theta` and `tau` together; never report `tau` alone as if it were an angle. Neither quantity is a direction; the interface defines no orientation and no signed turning.

### 3.5 Optional triangle excess

For interior `t` with `a + b > 0`:

```
q_t = (a + b - c) / (a + b)
```

`q_t` lies in `[0, 1]`. The freeze defines it on `a + b > 0`; the pilot WP-2.2 operational guidance additionally reports it only above a predeclared noise-calibrated scale floor because it is unstable near `a + b = 0`. It is an explicitly optional extension and is not a solution to the angle problem. It is reported at the interior time `t`.

## 4. Edge-case policies

These restate the frozen policies. Every rule is total or explicitly undefined; nothing is imputed, silently deleted, or repaired.

1. **Essential classes.** Essential classes (death = +inf) are removed before any metric computation; the per-window count is recorded. The extended-metric alternative is declared but unused in the first study.
2. **Empty diagrams.** Empty finite diagrams are valid objects with zero points. The diagonal itself (all points on the diagonal) is an empty finite diagram.
3. **Cardinality changes.** Diagram cardinality may change between windows; metric definitions handle unequal cardinality through diagonal matching. Per-window cardinality is recorded. All finite bars are retained; no label-dependent persistence threshold is allowed.
4. **Missing window.** A missing window (extraction failure or absent observation) excludes the entire trajectory from the primary offline analysis; the exclusion count is recorded. No interpolation and no window pooling to repair gaps. Trajectories are never silently deleted.
5. **L = 0.** `eta` is undefined (null), `L` is reported, and a flag is recorded. No imputation.
6. **Zero step.** If `a = 0` or `b = 0`, `theta` is undefined (null) and the step is counted as unresolved.
7. **Near-zero noise floor.** For each cell defined by (family, degree, resolution, metric), the calibration population is the set of adjacent diagram distances computed on the training-split static-noise trajectories at `sigma = 0.05` for that cell, and `e` is the 95th percentile of that population, computed with `numpy.percentile`'s default linear interpolation. Calibrations are never pooled across families, degrees, resolutions, or metrics because the distance units differ. The zero-noise regime is declared as `sigma = 0`, where `e = 0` and only exact-zero abstention applies, with exact zero the value returned under policy 13. Abstain on efficiency when `L <= 2(T-1)e` with `T` the number of intervals; abstain on comparison angles when `min(a, b) <= 2e`. Validity fractions and coverage must be reported jointly with performance for every regime, and abstention never deletes a trajectory.
8. **Cosine anomaly.** Clip `z` to `[-1, 1]`; if `|z| > 1 + 1e-12` record a cosine-anomaly flag. Never silently hide it.
9. **Nonunique matchings.** Nonunique optimal matchings are allowed. Metric distances are well-defined regardless of matching multiplicity; no feature identity or correspondence is claimed.
10. **Nonpositive interval.** Strictly increasing timestamps are required. Any nonpositive `h_t` is an input error and must be rejected; no silent repair.
11. **Straight and reversal reporting.** Straight and reversal cases are valid and must be reported; they are never deleted to obtain a Lipschitz theorem.
12. **No selective deletion.** No trajectory and no valid case may be selectively deleted or silently removed. Missing windows are excluded with recorded counts; `L = 0`, zero-step, and noise-floor cases are flagged or abstained, never dropped. Failed and negative results are retained.
13. **Numerical zero.** All public metric functions apply a declared numerical-zero tolerance `NUMERICAL_ZERO = 1e-12`: a computed distance at or below it is returned as exactly `0.0`. The primary backend can return denormal values (about `1e-308`) for a true-zero distance between non-identical diagrams, for example when one diagram carries an extra point on the diagonal; without the snap, the exact-zero step rule and the zero-noise abstention rule would not trigger. The tolerance is declared, not hidden, and is far below the smallest distance that is meaningful at the pilot's coordinate scale. The independent brute-force reference applies the same convention. Witness case W-15 records the behavior, and the exact-zero abstention in policy 7 refers to the exact `0.0` returned under this policy. Consequence: the public distance is a tolerance pseudometric; for a single triangle the deviation is at most `2 * NUMERICAL_ZERO`, and for a path with `T` intervals the bounds in section 3.2 are `R - L <= T * NUMERICAL_ZERO` and `eta <= 1 + T * NUMERICAL_ZERO / L`. The numerical verification report exhibits the single-triangle deviation, and the final audit report exhibits the multi-interval deviation.
14. **Comparison-angle conditioning.** `arccos` is ill-conditioned near `0` and `pi`: at well-scaled steps, distance roundoff at the `1e-16` level moves the angle by about `1e-8`, and cancellation in `a^2 + b^2 - c^2` amplifies the error as steps approach zero. Structural angle checks in the witness suite therefore use the exact brute-force reference, the library is checked separately against that reference, and abstention is governed by the calibrated floor `2e`. Straight and reversal cases are never deleted to avoid this conditioning.

## 5. Implementation mapping

Only the diagram metric `d` is library-dependent. All scalar quantities (`h, nu, L, R, eta, a, theta, tau, q`) are computed from the distance sequence with plain Python or NumPy, with one exception: `theta_t` and `q_t` also need the non-adjacent distance `c = d(D_{t-1}, D_{t+1})`, which requires one further metric call per interior time.

Definition of the primary metric. `d(D, D')` is the bottleneck distance: the minimum, over bijections between the two diagrams extended with diagonal copies, of the maximum cost over matched pairs, where the cost of matching points `p` and `q` is `||p - q||_inf = max(|Delta b|, |Delta d|)` and the cost of matching a point `(b, d)` to the diagonal is `(d - b)/2`. The diagonal carries infinite multiplicity, so unmatched points are matched to distinct diagonal copies. The empty diagram is a valid operand.

| Object | Implementation | Version and notes |
|---|---|---|
| Primary metric `d` | `gudhi.bottleneck_distance(D_i, D_{i+1})` | gudhi 3.12.0. Bottleneck distance with L-infinity ground norm, diagonal with infinite multiplicity, point-to-diagonal cost `(d - b)/2`, empty diagram a valid operand. Essential classes removed before the call. |
| Independent reference | Brute-force exact bottleneck inside the project package | Enumerates matchings that include diagonal copies; restricted to diagram pairs with at most 7 points in total. Used to validate the library call on small inputs. |
| Secondary cross-check | `persim.bottleneck` | persim 0.3.8, finite diagrams only. |
| Sensitivity branch (not primary) | `gudhi.wasserstein_distance(order=2, internal_p=np.inf)` | 2-Wasserstein with the same L-infinity ground norm. Essential parts stripped before the call. No bottleneck or Wasserstein stability constant is transferred between p-norms. |

Point difference and diagonal cost, for reference: `||p - q||_inf = max(|Delta b|, |Delta d|)` and the cost of matching `p = (b, d)` to the diagonal is `(d - b)/2`.

Numerical-zero and conditioning conventions are policies 13 and 14 in section 4. WP-0.2 checks this interface with 15 machine-readable witness cases in `src/tk_pilot/witnesses.py`, whose saved results are `research_review/results/phase0/witness/witness_results.json` and whose figures are in `research_review/results/phase0/witness/figures/`. The witness verdict is operational correctness only, never novelty evidence. Structural angle cases use the exact brute-force reference because of policy 14, and the library implementation is separately checked against that reference in cases W-01 through W-05.

Input canonicalization. Every public metric call canonicalizes each diagram (lexicographic sort by `(birth, death)`) before the backend call. This makes the result deterministic and reproduces the exact value on inputs where the raw library call is order-sensitive; witness case W-03 records an explicit regression pair.

Machine-readable outputs. `PathDiagnostics.as_json()` (in `src/tk_pilot/path_diagnostics.py`) reports `timestamps`, `adjacent_distances`, `interval_speeds`, `interval_speed_times`, `length`, `displacement`, `efficiency` (null when `L = 0`), `speed_change_rates`, `speed_change_times`, `comparison_angles` and `comparison_turns` (null when `a = 0` or `b = 0`), `comparison_valid`, `cosine_raw`, `cosine_anomaly`, `triangle_excess` and `triangle_excess_valid` (null when `a + b = 0`), and `angle_valid_fraction` (valid angles divided by the number of interior times `T - 1`, null when there are none). Undefined values are NaN internally and null in JSON. Unresolved-step counts are the complement of `comparison_valid`.

## 6. Worked numerical example

Setup: four singleton diagrams `D_j = {(s_j, s_j + 10)}` at `s = (0, 1, 2, 1)`, with timestamps `t = (0, 0.25, 0.5, 0.75)`. So `T = 3` intervals and four timestamps. This is the first four diagrams of path A in `research_review/topological_kinematics_witness.py` (lifespan 10).

Analytic singleton bottleneck: for `D_s = {(s, s+10)}` and `D_r = {(r, r+10)}`,

```
d(D_s, D_r) = min(|s - r|, 5)
```

because matching the two off-diagonal points costs `|s - r|` under the L-infinity ground norm, matching both points to the diagonal costs `max(5, 5) = 5`, and the bottleneck is the smaller of these optimal matching costs.

Step quantities:

| `t` | `h_t` | `d(D_t, D_{t+1})` | `m_t` | `nu_t` |
|---|---|---|---|---|
| 0 | 0.25 | 1 | 0.125 | 4 |
| 1 | 0.25 | 1 | 0.375 | 4 |
| 2 | 0.25 | 1 | 0.625 | 4 |

Path summaries:

| Quantity | Value |
|---|---|
| `L` | `1 + 1 + 1 = 3` |
| `R = d(D_0, D_3) = min(1, 5)` | `1` |
| `eta = R / L` | `1/3 = 0.3333333333333333` |
| `a_1 = (4 - 4) / 0.25` | `0` |
| `a_2 = (4 - 4) / 0.25` | `0` |

Interior diagnostics:

| `t` | `a` | `b` | `c` | `z` | `theta_t` | `tau_t` | `q_t` |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 2 | -1 | `pi = 3.141592653589793` | 0 | 0 |
| 2 | 1 | 1 | 0 | 1 | 0 | `pi = 3.141592653589793` | 1 |

Derivations: at `t = 1`, `a = d(D_0, D_1) = 1`, `b = d(D_1, D_2) = 1`, `c = d(D_0, D_2) = min(2, 5) = 2`, so `z = (1 + 1 - 4) / 2 = -1`, `theta_1 = arccos(-1) = pi` (straight continuation in the singleton line), `tau_1 = 0`, `q_1 = (1 + 1 - 2) / 2 = 0`. At `t = 2`, `a = 1`, `b = 1`, `c = d(D_1, D_3) = min(0, 5) = 0`, so `z = (1 + 1 - 0) / 2 = 1`, `theta_2 = arccos(1) = 0` (exact reversal), `tau_2 = pi`, `q_2 = (1 + 1 - 0) / 2 = 1`.

Reproduction. The values were computed by running Python with the analytic formula and independently confirmed with `gudhi.bottleneck_distance` (gudhi 3.12.0), which returns `1.0` for each of the three consecutive step distances and `1.0` for the endpoint pair. The essential part of the snippet is:

```python
import numpy as np
from gudhi import bottleneck_distance

M = 10.0
s = [0.0, 1.0, 2.0, 1.0]
t = [0.0, 0.25, 0.5, 0.75]
d = [min(abs(s[i] - s[i + 1]), M / 2.0) for i in range(3)]
h = [t[i + 1] - t[i] for i in range(3)]
nu = [d[i] / h[i] for i in range(3)]
m = [(t[i] + t[i + 1]) / 2.0 for i in range(3)]
L = sum(d)
R = min(abs(s[0] - s[-1]), M / 2.0)
eta = R / L
a1 = (nu[1] - nu[0]) / (m[1] - m[0])
a2 = (nu[2] - nu[1]) / (m[2] - m[1])
for i in range(3):
    g = bottleneck_distance(np.array([[s[i], s[i] + M]]),
                            np.array([[s[i + 1], s[i + 1] + M]]))
    assert g == d[i]
print(d, h, nu, m, L, R, eta, a1, a2)
```

Note on the noise floor: this example is exact, so no abstention applies. No training-only calibration is defined here, all steps satisfy `a, b > 0`, and `L = 3 > 0`.

The tables above are analytic values, not outputs of the frozen implementation. The implementation calls the library for the non-adjacent distance `c = d(D_0, D_2)` as well and receives `1.9999999999999998`, producing `z = -0.9999999999999996`, `theta_1 = 3.1415926237874707`, `tau_1 = 2.98e-08`, and `q_1 = 1.11e-16` instead of the exact analytic entries. Policy 14 anticipates this conditioning; the analytic values are the reference, and the implementation is checked against the exact brute-force reference for structural cases in the witness suite.

## 7. What this interface does not define

Latent causes. Nothing here defines, recovers, or identifies a latent mechanism. Persistence diagrams need not be injective on the underlying system, and distinct raw processes can share a diagram path. The estimand is always the observed diagram-path statistic under the frozen map, never a cause.

Direction. `theta_t` and `tau_t` are scalar triangle-shape summaries. This interface defines no orientation, no tangent vector, no geodesic direction, and no signed turning. `tau_t` is a reporting convention companion to `theta_t`, not a direction.

Physical acceleration. `a_t` is a finite-difference rate of change of the scalar speed. This interface defines no physical acceleration and no second-order lifted object. If each diagram distance carries error of order `eps`, a speed has error of order `eps / h`, and a speed difference of order `eps / h^2`, so finite differences amplify error as the step shrinks.

Extraction. The frame-to-diagram map, filtration, coefficient field, and truncation rule are declared elsewhere and are checked at G2. This interface assumes validated diagrams as input and does not certify extraction.

Stability theory. No stability, convergence, differentiability, or Lipschitz theorem is defined here. `R <= L` and `0 <= eta <= 1` are elementary triangle-inequality consequences, not a stability theory. No bottleneck or Wasserstein stability constant is transferred between p-norms, and no regularity is assumed that would let a straight or reversal case be deleted.

## 8. Conflicts found

None. Two layered statements were checked and are consistent rather than conflicting: (i) `q_t` is mathematically defined when `a + b > 0`, while WP-2.2 additionally gates reporting on a noise-calibrated scale floor, which is explicit in section 3.5; (ii) the freeze defines the speed at the interval midpoint and the plan's regular-grid formula uses `dt`, and the two agree on a regular grid, which is explicit in section 3.3.
