# WP-3.3 null, baseline-favorable, and stress controls

This report is the WP-3.3 artifact for gate G3. It contains the falsification controls requested by the research plan: constant-diagram nulls, the equal-speed ordering control, time reparameterization, raw-label-preserving transformations, very coarse sampling, and a documented adversarial full-matrix-sufficient case. All controls use the frozen package modules without modification and a private cache; the runner distance caches under `research_review/results/cache/` were not read or written.

## 0. Provenance and verdict summary

- exact command: `/usr/bin/python3 scripts/run_wp33_nulls.py --out research_review/results/g3/nulls --report research_review/results/g3/reports/wp33_nulls_report.md --cache /tmp/opencode/wp33_cache --budget-seconds 2700`
- working directory: `/home/hugo_souto/Stuff/Research/Topological_Kinematics`
- started (UTC): 2026-09-21T05:21:52Z
- finished (UTC): 2026-09-21T05:35:15Z
- wall time: 721.7 s
- worker processes: 1 (budget 2700 s)
- peak RAM (ru_maxrss): 311.7 MB
- private cache: `/tmp/opencode/wp33_cache`
- report file: `/home/hugo_souto/Stuff/Research/Topological_Kinematics/research_review/results/g3/reports/wp33_nulls_report.md`

| control | verdict | wall time (s) |
|---|---|---|
| static_null | RESIDUAL | 240.115 |
| matched_ordering | PASS | 12.7368 |
| time_reparam | PASS | 209.75 |
| raw_preserving | PASS | 28.121 |
| coarse_sampling | PASS | 145.779 |
| adversarial_matrix | RESIDUAL | 85.1748 |

## 1. Constant-diagram null (static z = 0.5)

Calibration uses training seeds 1000 to 1004 and evaluation uses seeds 1005 to 1019, a disjoint training-namespace split. The threshold `e95` is the 95th percentile of pooled calibration adjacent distances at the same family and sigma. A cell fails when a seed shows a strong monotone trend (Spearman p below 0.001 with absolute rho above 0.5) or when two or more seeds show exceedance clustering at the G2-verified longest-run permutation p below 0.01; it is RESIDUAL when the pooled exceedance count exceeds the 99 percent binomial bound or when a single seed shows weaker trend or clustering signatures.

| family | sigma | e95 | n above | n intervals | rate | binom p | seeds trend fail | seeds cluster p<0.01 | max run | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0 | 0 | 0 | 1920 | 0 | 1 | 0 | 0 | 0 | PASS |
| A | 0.05 | 0.0573754 | 96 | 1920 | 0.05 | 0.514621 | 0 | 0 | 2 | PASS |
| B | 0 | 0 | 0 | 1920 | 0 | 1 | 0 | 0 | 0 | PASS |
| B | 0.05 | 0.0547087 | 91 | 1920 | 0.0473958 | 0.714087 | 0 | 1 | 5 | RESIDUAL |

Degenerate assertions at sigma = 0 for A_sigma0: nonzero adjacent-distance trajectories 0, max absolute adjacent distance 0, L zero everywhere true, eta undefined everywhere true, angles unresolved everywhere true, triangle excess unresolved everywhere true, speed changes exactly zero true, efficiency flag false everywhere true, unique H0 diagrams per trajectory 1, verdict PASS.

Degenerate assertions at sigma = 0 for B_sigma0: nonzero adjacent-distance trajectories 0, max absolute adjacent distance 0, L zero everywhere true, eta undefined everywhere true, angles unresolved everywhere true, triangle excess unresolved everywhere true, speed changes exactly zero true, efficiency flag false everywhere true, unique H0 diagrams per trajectory 1, verdict PASS.

The full adjacent-distance samples are machine readable in `control1_static_null/adjacent_distances.csv` for the primary H0 channel; the per-trajectory summaries are in `control1_static_null/per_trajectory.csv`. Figure: `control1_static_null/figure_static_null.png`.

## 2. Equal-speed ordering control

The frozen `matched_forward` and `matched_folded` controls share one latent and noise realization and have identical consecutive |dz| steps and identical endpoints. The speed, L, R, and eta agreement is reported as matched-hits at 1e-9; the diagnostic separation is the count of seeds whose comparison-angle or triangle-excess arrays differ by more than 1e-6. The Family B rows are an auxiliary construction at sigma = 0 built from the frozen field formula; the frozen generator defines the matched controls for Family A only.

| group | seeds | structural ok | angle/shape separated | separation hits | all four matched at 1e-9 | L matched | R matched | eta matched | max speed matched |
|---|---|---|---|---|---|---|---|---|---|
| A_sigma0 | 20 | true | true | 20 | 0 | 0 | 20 | 20 | 0 |
| A_sigma50 | 20 | true | true | 20 | 0 | 0 | 20 | 0 | 0 |
| B_sigma0 | 5 | true | true | 5 | 0 | 0 | 5 | 5 | 0 |

No seed matches L, R, eta, and the speed sequence within 1e-9. Consecutive |dz| steps are identical by construction, but the bottleneck distance is nonlinear in the separation z, so the forward ordering (0.5, 1.0, 1.5, 1.0, 0.5) and the folded ordering (0.5, 1.0, 0.5, 1.0, 0.5) produce different step distances, hence different L and different speed sequences. The endpoint displacement R is unchanged at sigma = 0 (both zero) and is noise driven at sigma = 0.05, and eta inherits R. The angle and triangle-excess sequences separate the two orderings in every seed, which is the C3 diagnostic comparison; the matched-step property alone is not sufficient to make the path summaries equal.

The comparison stays outside the three-class accuracy calculation. Figure: `control2_matched_ordering/figure_matched_ordering.png`.

## 3. Time reparameterization

Two monotone warps are tested: `u**1.5` and a piecewise-linear warp with a fast first quarter (slope 2) and a slow remainder (slope 2/3). The clock-warp variant keeps the master states and changes the timestamps; the resampled variant selects master frames under the warped clock and re-times them uniformly. Qualified intervals restrict the derivative comparison to midpoint u at least 0.1, where the local-derivative approximation is not dominated by the vanishing derivative of `u**1.5` at zero.

| group | exact same-states | exact resampled | fresh step checks | preserved angles | max abs rel dev qualified | max abs rel dev low u | derivative ok | verdict |
|---|---|---|---|---|---|---|---|---|
| A_piecewise_fast_slow | true | true | true | true | 1.436e-14 | 0 | true | PASS |
| A_u_pow_1p5 | true | true | true | true | 5.717e-05 | 0.0606602 | true | PASS |
| B_piecewise_fast_slow | true | true | true | true | 1.436e-14 | 0 | true | PASS |
| B_u_pow_1p5 | true | true | true | true | 5.717e-05 | 0.0606602 | true | PASS |

For the piecewise-linear warp the local derivative is constant on every grid interval (the kink sits exactly on a master grid point), so the observed ratio must match the prediction to floating-point precision; that is the sharp pass criterion. For `u**1.5` the observed error grows as the curvature term, and the low-u column is the expected degradation regime rather than a failure. Figure: `control3_time_reparameterization/figure_reparam.png`.

## 4. Raw-label-preserving transformations

A constant rigid translation and a fixed global rotation of 0.7 radians are applied to an identical Family A static realization. The declared bound is 1e-7 times max(1, filtration range) with the range measured as the largest pairwise distance in the base realization. Diagnostic changes are reported for both degrees in the per-frame table and for degree 0 in the diagnostic table.

| group | frames checked | max distance | tolerance | argmax frame | verdict |
|---|---|---|---|---|---|
| rotation_degree0 | 330 | 0 | 2.702e-07 | n/a | PASS |
| rotation_degree1 | 330 | 0 | 2.702e-07 | n/a | PASS |
| translation_degree0 | 330 | 0 | 2.702e-07 | n/a | PASS |
| translation_degree1 | 330 | 0 | 2.702e-07 | n/a | PASS |

Largest diagnostic changes across all seeds and sigmas: |dL| 8.882e-16, |dR| 1.110e-16, |deta| 8.674e-17, |dspeed| 7.105e-15, |dangle| 1.765e-14, max compact difference 1.847e-13. Figure: `control4_raw_preserving/figure_raw_preserving.png`.

## 5. Very coarse sampling

Strides 8 and 16 keep 17 and 9 frames on the fixed horizon. The separation check uses the 12-dimensional compact vector with nearest-centroid classification, standardization statistics fitted on training seeds only, and no hyperparameter tuning. Efficiency coverage is the fraction of test trajectories whose efficiency validity flag is one under exact-zero abstention; the calibrated columns use the control-1 e95 floor. The verdict thresholds are balanced error below 0.5 for PASS, below 2/3 for RESIDUAL, and at or above 2/3 (the three-class chance level) for FAIL.

| family | sigma | stride | balanced error | recall return | recall ramp | recall jump | efficiency coverage | angle coverage | verdict |
|---|---|---|---|---|---|---|---|---|---|
| A | 0 | 8 | 0.0666667 | 0.8 | 1 | 1 | 1 | 0.435556 | PASS |
| A | 0 | 16 | 0.1 | 0.7 | 1 | 1 | 1 | 0.47619 | PASS |
| A | 0.05 | 8 | 0.0666667 | 0.8 | 1 | 1 | 1 | 1 | PASS |
| A | 0.05 | 16 | 0.1 | 0.8 | 1 | 0.9 | 1 | 1 | PASS |
| B | 0 | 8 | 0 | 1 | 1 | 1 | 1 | 0.362222 | PASS |
| B | 0 | 16 | 0 | 1 | 1 | 1 | 1 | 0.380952 | PASS |
| B | 0.05 | 8 | 0 | 1 | 1 | 1 | 1 | 1 | PASS |
| B | 0.05 | 16 | 0.0333333 | 1 | 0.9 | 1 | 1 | 1 | PASS |

Coverage and performance are reported jointly in the same table so that abstention cannot manufacture robustness. Figure: `control5_coarse_sampling/figure_coarse_sampling.png`.

## 6. Adversarial full-matrix-sufficient case

A single constant-diagram-null frame is replaced by a raw realization at a different separation with the same latent parameters and the same noise draw at that frame. The primary injection uses z = 3.0, where the two circles or bumps are cleanly separated and the diagram shift is large; a secondary near-floor injection uses z = 1.5. The full distance matrix and the compact maximum adjacent distance are both scored. A detection is called attributed only when the injected statistic strictly exceeds the null statistic and the argmax localizes the injected frame or its adjacent interval. The cost comparison is reported honestly: the full matrix carries T(T-1)/2 features and T(T-1)/2 distance calls against 12 compact features and roughly 2T-3 distance calls, and the full matrix localizes the injected frame exactly while the compact report localizes only the adjacent interval. This is a documented adversarial control, not a claimed win for the compact summaries.

| family | sigma | injection z | attributed (full) | attributed (compact) | localization full | localization compact | false detections null (full) | false detections null (compact) | full dim | compact dim | full calls | compact calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0 | 3 | 5 | 5 | 5 | 5 | 0 | 0 | 136 | 12 | 136 | 31 |
| A | 0 | 1.5 | 5 | 5 | 5 | 5 | 0 | 0 | 136 | 12 | 136 | 31 |
| A | 0.05 | 3 | 5 | 5 | 5 | 5 | 5 | 3 | 136 | 12 | 136 | 31 |
| A | 0.05 | 1.5 | 1 | 1 | 1 | 1 | 5 | 3 | 136 | 12 | 136 | 31 |
| B | 0 | 3 | 5 | 5 | 5 | 5 | 0 | 0 | 136 | 12 | 136 | 31 |
| B | 0 | 1.5 | 5 | 5 | 5 | 5 | 0 | 0 | 136 | 12 | 136 | 31 |
| B | 0.05 | 3 | 5 | 5 | 5 | 5 | 4 | 2 | 136 | 12 | 136 | 31 |
| B | 0.05 | 1.5 | 5 | 5 | 5 | 5 | 4 | 2 | 136 | 12 | 136 | 31 |

The per-pair e95 threshold is calibrated on adjacent distances and is a marginal, not a trajectory-level, threshold. At stride 8 the null adjacent maximum exceeds it in some seeds at sigma = 0.05 (see the false-detection columns), while the full-matrix null maximum exceeds it in nearly every seed, because the maximum over T(T-1)/2 weakly dependent entries is stochastically larger than the maximum over T-1 adjacent entries. A fair alarm comparison requires a trajectory-level calibration for both statistics; the attribution rule used here instead requires the injected statistic to exceed the paired null statistic and to localize the injection, so the detection comparison is not driven by that threshold mismatch. Figure: `control6_adversarial_matrix/figure_adversarial.png`.

## 7. Files written

Relative to the output directory:

- `control1_static_null/per_trajectory.csv`
- `control1_static_null/adjacent_distances.csv`
- `control1_static_null/summary.csv`
- `control1_static_null/degenerate_assertions.json`
- `control2_matched_ordering/per_condition.csv`
- `control2_matched_ordering/angle_differences.csv`
- `control2_matched_ordering/summary.csv`
- `control3_time_reparameterization/speed_ratios.csv`
- `control3_time_reparameterization/sequence_checks.csv`
- `control3_time_reparameterization/summary.csv`
- `control4_raw_preserving/per_frame_distances.csv`
- `control4_raw_preserving/diagnostic_changes.csv`
- `control4_raw_preserving/summary.csv`
- `control5_coarse_sampling/per_trajectory.csv`
- `control5_coarse_sampling/predictions.csv`
- `control5_coarse_sampling/confusion.csv`
- `control5_coarse_sampling/separation.csv`
- `control6_adversarial_matrix/per_trajectory.csv`
- `control6_adversarial_matrix/summary.csv`
- `control1_static_null/figure_static_null.png`
- `control2_matched_ordering/figure_matched_ordering.png`
- `control3_time_reparameterization/figure_reparam.png`
- `control4_raw_preserving/figure_raw_preserving.png`
- `control5_coarse_sampling/figure_coarse_sampling.png`
- `control6_adversarial_matrix/figure_adversarial.png`
- `manifest.json`
- `run_log.txt`
- `SHA256SUMS`

The artifact manifest records input hashes, environment versions, seed namespaces, per-control verdicts, and the measured wall time and peak RAM. `SHA256SUMS` covers every file in the output directory and the report itself (listed with a `../reports/` relative path).

## 8. Limitations and residuals

Exceedance counts at e95 are binomial approximations because adjacent windows overlap; the trend, runs, and clustering diagnostics are reported alongside the count rather than replaced by it. Family B carries the larger diagram cardinalities and hence the slower bottleneck evaluations, so the coarse-sampling grid and the adversarial matrix control use strides 8 and 16. The equal-speed ordering control is defined by the frozen generator for Family A; the Family B variant at sigma = 0 is an auxiliary reproducibility construction and is labeled as such in the tables. The near-floor adversarial injection at z = 1.5 is not attributed for Family A at sigma = 0.05, where its diagram shift is comparable to the noise scale; that boundary is reported rather than hidden. The module hashes recorded in `manifest.json` differ from the hash table of the WP-3.1 raw-correctness report for `generators.py`, `persistence.py`, and `features.py`, while `diagram_metrics.py` and `path_diagnostics.py` match that table. The three listed hashes appear stale relative to the current working tree; this run used the current working-tree modules, re-verified the raw-frame evaluator against them bitwise, and re-checked the key static-null and translation-invariance properties in this work package.


