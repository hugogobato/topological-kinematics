# WP-2.2 edge-case report

Gate label: conditional_on_G1: WP-2.2 executed after the coordinator's G1 record and before the G2 decision; scientific pass condition is stable definitions only; no predictive value is claimed.

This report enumerates every degenerate case present in the evaluated diagram sequences, the treatment applied under the frozen policies in `research_review/assumption_ledger.yaml` and `research_review/metric_interface.md`, and the resulting abstention coverage. No trajectory and no valid case was dropped. Abstention means a quantity is reported as undefined for that time or that a validity flag is false; it never removes a row.

The tables refer to the corrected candidate backend `exact_scipy`, an independent exact solver verified against the project brute-force reference, persim, and an order-invariance test; the frozen backend table is written separately and its metric defect is documented in `metric_backend_audit.md`.

## 1. Evaluated grid

Cells: families A and B, classes return, ramp, jump, and the static calibration control, seeds 11, 1000, and 1001, sigma 0 and 0.05, strides 1, 2, and 4, degrees 0 (primary) and 1 (secondary). Seed 11 trajectories are the cached smoke draws; seeds 1000 and 1001 are the additional train-like draws computed fresh under the temporary cache. Strides 2 and 4 are exact subsamples of the stride-1 realization.

Rows written: 288. A missing-window event would exclude a whole trajectory with a recorded count; none occurred.

## 2. Degenerate-case inventory

| family | degree | sigma | unresolved zero-step times | L = 0 rows | efficiency abstentions | angle floor abstentions | q floor abstentions | cosine anomalies | empty diagrams | cardinality changes |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0 | 0.0 | 1859 | 9 | 9 | 1859 | 0 | 0 | 0 | 0 |
| A | 0 | 0.05 | 0 | 0 | 36 | 2613 | 2539 | 0 | 0 | 0 |
| A | 1 | 0.0 | 1880 | 9 | 9 | 1880 | 0 | 0 | 0 | 426 |
| A | 1 | 0.05 | 0 | 0 | 36 | 2643 | 2622 | 0 | 0 | 1920 |
| B | 0 | 0.0 | 1927 | 9 | 9 | 1927 | 0 | 0 | 1520 | 36 |
| B | 0 | 0.05 | 0 | 0 | 36 | 2605 | 2549 | 0 | 0 | 2547 |
| B | 1 | 0.0 | 2652 | 36 | 36 | 2652 | 0 | 0 | 2724 | 0 |
| B | 1 | 0.05 | 0 | 0 | 36 | 2652 | 2652 | 0 | 0 | 2590 |

Counts pool all classes, seeds, and strides within each family, degree, and sigma block, so they include the static calibration controls; the scientific classes alone are used in section 3.

## 3. Zero steps and undefined angles

A zero step is an adjacent diagram distance returned as exactly 0.0 under the declared numerical-zero convention, so the law-of-cosines denominator 2ab vanishes and the comparison angle is undefined. Policy: the step is counted as unresolved, the angle is null, and the trajectory stays in the table.

Scientific rows carry 5666 unresolved zero-step interior times out of 15912 interior times (35.6 percent). The largest concentrations are the exact-zero regime of family B, where degree 0 and degree 1 diagrams are mostly empty or carry one off-diagonal point, and the flat segments of the return and jump controls at sigma = 0, where consecutive diagrams are identical.

Undefined angles occur exactly when a = 0 or b = 0, which the machine check `angle_defined_iff_positive_steps` confirms with zero violations.

## 4. Paths with L = 0 and undefined efficiency

Rows with L = 0: 63. In every such row eta is null, the efficiency flag is false, comparison angles and q are undefined, and the row is retained. The machine check `eta_undefined_iff_L_zero` confirms the exact correspondence.

| family | class | seed | sigma | stride | degree |
|---|---|---|---|---|---|
| A | static | 11 | 0.0 | 1 | 0 |
| A | static | 11 | 0.0 | 1 | 1 |
| A | static | 11 | 0.0 | 2 | 0 |
| A | static | 11 | 0.0 | 2 | 1 |
| A | static | 11 | 0.0 | 4 | 0 |
| A | static | 11 | 0.0 | 4 | 1 |
| A | static | 1000 | 0.0 | 1 | 0 |
| A | static | 1000 | 0.0 | 1 | 1 |
| A | static | 1000 | 0.0 | 2 | 0 |
| A | static | 1000 | 0.0 | 2 | 1 |
| A | static | 1000 | 0.0 | 4 | 0 |
| A | static | 1000 | 0.0 | 4 | 1 |
| A | static | 1001 | 0.0 | 1 | 0 |
| A | static | 1001 | 0.0 | 1 | 1 |
| A | static | 1001 | 0.0 | 2 | 0 |
| A | static | 1001 | 0.0 | 2 | 1 |
| A | static | 1001 | 0.0 | 4 | 0 |
| A | static | 1001 | 0.0 | 4 | 1 |
| B | jump | 11 | 0.0 | 1 | 1 |
| B | jump | 11 | 0.0 | 2 | 1 |
| B | jump | 11 | 0.0 | 4 | 1 |
| B | jump | 1000 | 0.0 | 1 | 1 |
| B | jump | 1000 | 0.0 | 2 | 1 |
| B | jump | 1000 | 0.0 | 4 | 1 |
| B | jump | 1001 | 0.0 | 1 | 1 |
| B | jump | 1001 | 0.0 | 2 | 1 |
| B | jump | 1001 | 0.0 | 4 | 1 |
| B | ramp | 11 | 0.0 | 1 | 1 |
| B | ramp | 11 | 0.0 | 2 | 1 |
| B | ramp | 11 | 0.0 | 4 | 1 |
| B | ramp | 1000 | 0.0 | 1 | 1 |
| B | ramp | 1000 | 0.0 | 2 | 1 |
| B | ramp | 1000 | 0.0 | 4 | 1 |
| B | ramp | 1001 | 0.0 | 1 | 1 |
| B | ramp | 1001 | 0.0 | 2 | 1 |
| B | ramp | 1001 | 0.0 | 4 | 1 |
| B | return | 11 | 0.0 | 1 | 1 |
| B | return | 11 | 0.0 | 2 | 1 |
| B | return | 11 | 0.0 | 4 | 1 |
| B | return | 1000 | 0.0 | 1 | 1 |
| B | return | 1000 | 0.0 | 2 | 1 |
| B | return | 1000 | 0.0 | 4 | 1 |
| B | return | 1001 | 0.0 | 1 | 1 |
| B | return | 1001 | 0.0 | 2 | 1 |
| B | return | 1001 | 0.0 | 4 | 1 |
| B | static | 11 | 0.0 | 1 | 0 |
| B | static | 11 | 0.0 | 1 | 1 |
| B | static | 11 | 0.0 | 2 | 0 |
| B | static | 11 | 0.0 | 2 | 1 |
| B | static | 11 | 0.0 | 4 | 0 |
| B | static | 11 | 0.0 | 4 | 1 |
| B | static | 1000 | 0.0 | 1 | 0 |
| B | static | 1000 | 0.0 | 1 | 1 |
| B | static | 1000 | 0.0 | 2 | 0 |
| B | static | 1000 | 0.0 | 2 | 1 |
| B | static | 1000 | 0.0 | 4 | 0 |
| B | static | 1000 | 0.0 | 4 | 1 |
| B | static | 1001 | 0.0 | 1 | 0 |
| B | static | 1001 | 0.0 | 1 | 1 |
| B | static | 1001 | 0.0 | 2 | 0 |
| B | static | 1001 | 0.0 | 2 | 1 |
| B | static | 1001 | 0.0 | 4 | 0 |
| B | static | 1001 | 0.0 | 4 | 1 |

Scientific rows with L = 0: 27. These come from exactly static diagram sequences (family B at sigma = 0).

## 5. Near-zero floors and abstention coverage

The floor e is the 95th percentile of adjacent diagram distances of the static sigma = 0.05 calibration population for each (family, degree, stride) cell, using the train-like seeds 1000 and 1001. At sigma = 0 the floor is exactly zero. The checkpoint values are:

| cell (family, degree, stride) | e | seed 11 static sensitivity |
|---|---|---|
| A|0|1 | 0.0551537 | 0.0575466 |
| A|0|2 | 0.064674 | 0.0518833 |
| A|0|4 | 0.0578521 | 0.0541947 |
| A|1|1 | 0.104562 | 0.0988049 |
| A|1|2 | 0.110989 | 0.0869218 |
| A|1|4 | 0.108013 | 0.0902866 |
| B|0|1 | 0.0534446 | 0.0579373 |
| B|0|2 | 0.052177 | 0.0616991 |
| B|0|4 | 0.0414259 | 0.0557723 |
| B|1|1 | 0.0565059 | 0.0547622 |
| B|1|2 | 0.0571745 | 0.0504238 |
| B|1|4 | 0.0608253 | 0.0597748 |

Rows whose mean step L/(T-1) lies at or below the efficiency abstention bound 2e at sigma = 0.05: 144, which is every sigma = 0.05 row on this grid. These rows keep their values but are flagged efficiency-invalid, so the efficiency channel has zero coverage in the noise regime under the conservative floor. Comparison-angle floor coverage at sigma = 0.05 is likewise small; the exact fractions are in the table below.

Per-cell coverage, pooled over seeds and classes:

| family | degree | sigma | stride | angle defined | angle floor-valid | efficiency coverage | eta defined |
|---|---|---|---|---|---|---|---|
| A | 0 | 0.0 | 1 | 0.397 | 0.397 | 1.000 | 1.000 |
| A | 0 | 0.0 | 2 | 0.399 | 0.399 | 1.000 | 1.000 |
| A | 0 | 0.0 | 4 | 0.405 | 0.405 | 1.000 | 1.000 |
| A | 0 | 0.05 | 1 | 1.000 | 0.012 | 0.000 | 1.000 |
| A | 0 | 0.05 | 2 | 1.000 | 0.011 | 0.000 | 1.000 |
| A | 0 | 0.05 | 4 | 1.000 | 0.068 | 0.000 | 1.000 |
| A | 1 | 0.0 | 1 | 0.387 | 0.387 | 1.000 | 1.000 |
| A | 1 | 0.0 | 2 | 0.388 | 0.388 | 1.000 | 1.000 |
| A | 1 | 0.0 | 4 | 0.394 | 0.394 | 1.000 | 1.000 |
| A | 1 | 0.05 | 1 | 1.000 | 0.000 | 0.000 | 1.000 |
| A | 1 | 0.05 | 2 | 1.000 | 0.000 | 0.000 | 1.000 |
| A | 1 | 0.05 | 4 | 1.000 | 0.032 | 0.000 | 1.000 |
| B | 0 | 0.0 | 1 | 0.362 | 0.362 | 1.000 | 1.000 |
| B | 0 | 0.0 | 2 | 0.365 | 0.365 | 1.000 | 1.000 |
| B | 0 | 0.0 | 4 | 0.373 | 0.373 | 1.000 | 1.000 |
| B | 0 | 0.05 | 1 | 1.000 | 0.002 | 0.000 | 1.000 |
| B | 0 | 0.05 | 2 | 1.000 | 0.019 | 0.000 | 1.000 |
| B | 0 | 0.05 | 4 | 1.000 | 0.122 | 0.000 | 1.000 |
| B | 1 | 0.0 | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| B | 1 | 0.0 | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| B | 1 | 0.0 | 4 | 0.000 | 0.000 | 0.000 | 0.000 |
| B | 1 | 0.05 | 1 | 1.000 | 0.000 | 0.000 | 1.000 |
| B | 1 | 0.05 | 2 | 1.000 | 0.000 | 0.000 | 1.000 |
| B | 1 | 0.05 | 4 | 1.000 | 0.000 | 0.000 | 1.000 |

## 6. Cosine anomalies

Recorded cosine anomalies (|z| > 1 + 1e-12 before clipping): 0. The machine check `cosine_anomaly_accounting` verifies that the flags equal the set of defined cosines outside the tolerance, so no anomaly is hidden. Clipping keeps arccos total; straight and reversal cases are reported, not deleted.

Straight cases retained: 921. Reversal cases retained: 226. Near-straight within 1e-6: 1280. Near-reversal within 1e-6: 300.

## 7. Cardinality changes and empty diagrams

Cardinality changes and empty diagrams are expected objects under the frozen policy; the bottleneck metric handles unequal cardinality through diagonal matching, and empty finite diagrams are valid. Cardinality is recorded per frame; no persistence threshold or interpolation was applied.

Empty frames across all rows: 4244. Rows with at least one cardinality change: 162. Maximum single-frame cardinality change: 48.

## 8. Metric backend edge case

The frozen primary backend is itself a degenerate case: the gudhi implementation returns incorrect distances on some real pilot pairs, in some cases for every tested input order and with both the default and the exact algorithm, and it fails the declared tolerance pseudometric assumption by up to about 0.05. This is reported in full in `metric_backend_audit.md` and under the `gudhi_default` backend in `checks.json`. No value was repaired in place; the corrected candidate is reported as a separate labeled table, and cached frozen-backend artifacts must be regenerated after the interface amendment.

## 9. Summary of abstained quantities and coverage

1. eta is abstained exactly on L = 0 rows, tabulated in section 4; elsewhere it is reported.
2. The efficiency-valid flag is false whenever L <= 2 (T - 1) e, which captures every L = 0 row and the near-floor rows of section 5; eta itself is still reported when L > 0.
3. Comparison angles are abstained on zero steps and on steps below the calibrated floor min(a, b) <= 2e; the coverage columns in section 5 give the exact fractions per cell.
4. q_t is reported only on interior times with a + b > 4e, the predeclared sum floor. The q-valid counts and fractions are in the feature table and in section 2.

No valid straight or reversal index was removed, no trajectory was deleted, and every degenerate count above remains visible in `feature_table_exact_metric.csv` and `checks.json`.
