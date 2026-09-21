# WP-2.2 stability report

Gate label: conditional_on_G1: WP-2.2 executed after the coordinator's G1 record and before the G2 decision; scientific pass condition is stable definitions only; no predictive value is claimed.

Scope. This report checks whether the bounded metric diagnostics keep a stable operational definition across sampling rates and noise levels on the evaluated diagram sequences. WP-2.2 passes on stable definitions only; nothing here is evidence of predictive value, and no classification or decision claim is made.

The main tables use the corrected candidate backend `exact_scipy` (an independent exact solver, verified against the project brute-force reference, persim, and an order-invariance test). The frozen backend `gudhi_default` fails the metric axiom checks, as reported in `checks.json` and `metric_backend_audit.md`; its stability numbers are therefore not interpreted.

## 1. Data and uncertainty

Rows evaluated: 288 over families A and B, classes return, ramp, jump, and static, seeds 11 (cached smoke), 1000 and 1001 (additional train-like draws), sigma 0 and 0.05, strides 1, 2, and 4, and degrees 0 and 1. Uncertainty is reported as the across-seed sample standard deviation within each cell in `cell_summary.csv`; with three seeds per cell it is a spread indicator, not an inferential confidence interval. The declared numerical zero is 1e-12, so differences below that scale are not resolvable.

## 2. Sampling-rate sensitivity

Strides 2 and 4 subsample the same master realization and keep the physical horizon fixed, so interval counts fall and each interval spans more physical time. Table cells below are means over classes and seeds of the stride-specific values at sigma = 0.05.

| family | degree | stride | mean L | mean L/(T-1) | mean eta | mean speed | angle floor-valid | mean q |
|---|---|---|---|---|---|---|---|---|
| A | 0 | 1 | 6.396 | 0.05036 | 0.05152 | 6.396 | 0.0122 | 0.4314 |
| A | 0 | 2 | 3.472 | 0.05512 | 0.09981 | 3.472 | 0.0106 | 0.2673 |
| A | 0 | 4 | 2.091 | 0.06746 | 0.1657 | 2.091 | 0.0681 | 0.1971 |
| A | 1 | 1 | 8.581 | 0.06756 | 0.05309 | 8.581 | 0 | 0.08133 |
| A | 1 | 2 | 4.798 | 0.07617 | 0.09801 | 4.798 | 0 | 0.09912 |
| A | 1 | 4 | 2.96 | 0.0955 | 0.1675 | 2.96 | 0.0323 | 0.1047 |
| B | 0 | 1 | 5.78 | 0.04551 | 0.05147 | 5.78 | 0.00175 | 0.4451 |
| B | 0 | 2 | 3.222 | 0.05114 | 0.0954 | 3.222 | 0.0194 | 0.2534 |
| B | 0 | 4 | 1.96 | 0.06322 | 0.1636 | 1.96 | 0.122 | 0.2199 |
| B | 1 | 1 | 4.407 | 0.0347 | 0.008048 | 4.407 | 0 | n/a |
| B | 1 | 2 | 2.187 | 0.03472 | 0.01618 | 2.187 | 0 | n/a |
| B | 1 | 4 | 1.134 | 0.0366 | 0.0314 | 1.134 | 0 | n/a |

On the fixed horizon [0, 1] the mean interval speed in distance units per unit physical time equals L, so the mean L and mean speed columns coincide by construction and are not independent evidence.

Relative change of the cell mean from stride 1 to stride 4, sigma = 0.05:

| family | degree | L ratio s4/s1 | L/(T-1) ratio s4/s1 | eta ratio s4/s1 |
|---|---|---|---|---|
| A | 0 | 0.327 | 1.34 | 3.22 |
| A | 1 | 0.345 | 1.41 | 3.16 |
| B | 0 | 0.339 | 1.39 | 3.18 |
| B | 1 | 0.257 | 1.05 | 3.9 |

Across cells, the stride-4 to stride-1 ratio of L has median 0.333 and range [0.257, 0.345]; for L/(T-1) the median ratio is 1.36 with range [1.05, 1.41]; for eta the median ratio is 3.2 with range [3.16, 3.9].

Interpretation and flags. L is a discretization-dependent accumulation by construction: it counts resolved steps, so its value is only comparable within a fixed stride cell. The observed stride-4 to stride-1 ratios show how strongly the cell means move with resolution: L falls by a median factor of 3 (range 2.9 to 3.88), L/(T-1) changes by a median factor of 1.36 (range 1.05 to 1.41), and eta changes by a median factor of 3.2 (range 3.16 to 3.9). The definitions of L, L/(T-1), and eta are unchanged across cells and their coverage is reported, but their values are not sampling-invariant on this grid. Flag: eta is strongly resolution-sensitive and must not be compared across stride cells; it is retained with exploratory status for any cross-resolution statement. Flag: L/(T-1) is mildly resolution-sensitive and is likewise reported per cell rather than pooled. Peak speeds of the jump class shrink at stride 4 because the transition is resolved by fewer intervals; this is a resolution effect, not a change of definition.

## 3. Noise sensitivity

Table cells below are means over classes and seeds at stride 1.

| family | degree | sigma | mean L | mean eta | mean speed | angle defined | angle floor-valid | mean q | zero-step times |
|---|---|---|---|---|---|---|---|---|---|
| A | 0 | 0.0 | 2.146 | 0.4091 | 2.146 | 0.397 | 0.397 | 0.1472 | 689 |
| A | 0 | 0.05 | 6.396 | 0.05152 | 6.396 | 1 | 0.0122 | 0.4314 | 0 |
| A | 1 | 0.0 | 1.828 | 0.4857 | 1.828 | 0.387 | 0.387 | 0.12 | 701 |
| A | 1 | 0.05 | 8.581 | 0.05309 | 8.581 | 1 | 0 | 0.08133 | 0 |
| B | 0 | 0.0 | 1.171 | 0.4724 | 1.171 | 0.362 | 0.362 | 0.04204 | 729 |
| B | 0 | 0.05 | 5.78 | 0.05147 | 5.78 | 1 | 0.00175 | 0.4451 | 0 |
| B | 1 | 0.0 | 0 | n/a | 0 | 0 | 0 | n/a | 1143 |
| B | 1 | 0.05 | 4.407 | 0.008048 | 4.407 | 1 | 0 | n/a | 0 |

Interpretation and flags. sigma is a regime label, not a nuisance parameter: at sigma = 0 the diagram sequences are deterministic, exact zero steps are common on flat segments, and family B collapses to sparse H0 and empty H1 diagrams, while at sigma = 0.05 every adjacent distance is strictly positive and the floor e is positive. Features computed in the two regimes are not pooled and are not numerically comparable.

A second structural finding is coverage, not definition: under the conservative floor the usable channels shrink sharply with noise. At sigma = 0.05 the angle floor-valid fraction is near zero in every cell (it ranges from 0.000 to 0.122 in the coverage table), and the efficiency flag is false in every row because the mean step never clears 2e. The angle and efficiency channels are therefore populated mainly at sigma = 0, where exact zeros, not the calibrated floor, dominate the abstentions. Flag: any use of the angle or efficiency channels must report this coverage jointly and must not treat the abstained majority at sigma = 0.05 as evidence of stability or instability.

## 4. Meaning changes across cells and unstable quantities

The following structural findings bound the interpretation.

1. Family B at sigma = 0 has near-empty degree 0 diagrams and empty degree 1 diagrams. In that regime L is frequently exactly zero, eta is undefined, and comparison angles and q are mostly undefined. These rows are retained with flags, but the angle channel is inapplicable there. This is a regime-limited meaning change, not a definition failure.
2. The floor e changes per (family, degree, stride) cell and is never pooled. The seed 11 static sensitivity values differ from the train-like floor, which shows that the floor estimate itself carries calibration uncertainty; abstention coverage is therefore reported per cell, as done here.
3. L is resolution-dependent by construction and must not be compared across stride cells; L/(T-1), eta, and the floor-gated fractions are the sampling-comparable summaries.
4. Speed-change rates are finite differences of speeds and amplify distance noise by the midpoint spacing. They are retained as descriptive, exploratory quantities and are not promoted to any decision role in WP-2.2.
5. Comparison angles and q keep their definitions in every cell where they are defined; the only variation is coverage through the calibrated floor and the exact-zero rule. Straight and reversal cases are reported wherever ab > 0.
6. The frozen metric backend is a definition-level failure, not a stability finding: the gudhi implementation returns incorrect distances on some real diagram pairs, in some cases for every tested input order and with both the default and the exact algorithm, so the triangle inequality itself breaks. It is flagged for repair before any G2 sign-off and is not used for the stability conclusions.

## 5. Machine checks

### Backend `gudhi_default`: pass

| check | verdict | detail |
|---|---|---|
| R_le_L | pass | n_checked=288, n_violations=0, worst_R_minus_L=0.0, tolerance=1e-09 |
| eta_range | pass | n_checked=225, n_violations=0, worst_eta_minus_one=0.0, worst_minus_eta=0.0, tolerance=1e-09 |
| eta_undefined_iff_L_zero | pass | n_rows_with_L_zero=63, n_undefined_with_L_positive=0, n_defined_with_L_zero=0 |
| triangle_inequality | pass | n_triples_checked=21216, n_violations=0, worst_excess=5.551115123125783e-17, tolerance=1e-09 |
| triangle_excess_range | pass | n_checked=13066, n_violations=0, worst_q_minus_one=0.0, worst_minus_q=1.5531164106501242e-16, tolerance=1e-09 |
| angle_defined_iff_positive_steps | pass | n_violations=0 |
| cosine_anomaly_accounting | pass | n_violations=0, tolerance=1e-12 |
| straight_and_reversal_retained | pass | n_violations=0, n_straight=921, n_reversal=226 |
| no_trajectory_deleted | pass | n_expected_rows=288, n_rows_written=288 |
| floor_calibration_positive_sigma50 | pass | n_cells=12, cells_with_nonpositive_floor=[] |
| floor_zero_sigma0 | pass | n_rows_sigma0=144, n_nonzero=0 |
| timestamps_strictly_increasing | pass | n_rows=288, n_violations=0, note=compute_path_diagnostics raises on any nonpositive interval; no silent repair is used |
| cached_distance_matrix_comparison | pass | n_values_compared=2064, n_above_tolerance=0, max_abs_difference=0.0, tolerance=1e-12, note=the cached matrices were produced by the frozen backend, so exact agreement is a reproducibility check, not a correctness check |

### Backend `exact_scipy`: pass

| check | verdict | detail |
|---|---|---|
| R_le_L | pass | n_checked=288, n_violations=0, worst_R_minus_L=0.0, tolerance=1e-09 |
| eta_range | pass | n_checked=225, n_violations=0, worst_eta_minus_one=0.0, worst_minus_eta=0.0, tolerance=1e-09 |
| eta_undefined_iff_L_zero | pass | n_rows_with_L_zero=63, n_undefined_with_L_positive=0, n_defined_with_L_zero=0 |
| triangle_inequality | pass | n_triples_checked=21216, n_violations=0, worst_excess=5.551115123125783e-17, tolerance=1e-09 |
| triangle_excess_range | pass | n_checked=13066, n_violations=0, worst_q_minus_one=0.0, worst_minus_q=1.5531164106501242e-16, tolerance=1e-09 |
| angle_defined_iff_positive_steps | pass | n_violations=0 |
| cosine_anomaly_accounting | pass | n_violations=0, tolerance=1e-12 |
| straight_and_reversal_retained | pass | n_violations=0, n_straight=921, n_reversal=226 |
| no_trajectory_deleted | pass | n_expected_rows=288, n_rows_written=288 |
| floor_calibration_positive_sigma50 | pass | n_cells=12, cells_with_nonpositive_floor=[] |
| floor_zero_sigma0 | pass | n_rows_sigma0=144, n_nonzero=0 |
| timestamps_strictly_increasing | pass | n_rows=288, n_violations=0, note=compute_path_diagnostics raises on any nonpositive interval; no silent repair is used |
| cached_distance_matrix_comparison | pass | n_values_compared=2064, n_above_tolerance=0, max_abs_difference=0.0, tolerance=1e-12, note=differences against the cached frozen-backend matrices quantify the backend defect |

WP-2.2 verdict on definitions. Under the corrected candidate backend all structural checks pass: L (per stride), eta, the speed summaries, the floor-gated comparison angle and q, and the zero-step and anomaly accounting are stable operational definitions on this grid. eta and the angle channel are regime-limited where L = 0 or where the diagrams are empty, and speed-change rates are exploratory under noise. Under the frozen backend the failing checks are none, so the frozen results are not signed off and the metric backend is a blocker. No predictive value is claimed, and the gate label remains conditional on G1 until the coordinator records the G2 decision.
