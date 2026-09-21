# Pre-registration draft: compact diagram-path diagnostics for offline trajectory classification (WP-0.1)

**Title.** Compact diagram-path diagnostics for offline fixed-length trajectory classification: a confirmatory simulation pre-registration.

**Version.** 0.1 (draft).

**Date.** 2026-09-20.

**Status.** Draft frozen at gate G0. This is the WP-0.1 pre-registration draft for the confirmatory simulation stage. It is to be re-confirmed, together with the pilot specification, immediately before any confirmatory test seeds are opened.

**Authoritative numeric appendix.** `research_review/Pilot_Experiment_Specification.md` governs every numeric pilot value (generator constants, grid, strides, seeds, learner grids, thresholds, and precision targets). `research_review/assumption_ledger.yaml` and `research_review/metric_interface.md` govern metric, timestamp, and edge-case conventions, and `src/tk_pilot/witnesses.py` with its saved results in `research_review/results/phase0/witness/` is the Phase 0 correctness evidence for those conventions. If this draft disagrees with any of these sources, they govern, and the disagreement is recorded in the deviations log (Section 9) rather than silently resolved.

**Relationship to the research plan.** This document operationalizes the offline fixed-length trajectory classification experiment described in `research_review/Topological_Kinematics_Research_Plan.md` Section 8, its data-generating process in WP-3.2, and the predeclared simulation decision that WP-3.4 applies. It stays inside the G0 scope: a finite sequence of finite persistence diagrams with finite birth and death coordinates, a fixed diagram metric, and strictly increasing timestamps. G0 does not establish data-extraction correctness (G2), predictive value (G3), application utility (G4), or theory (G5), and no statement here may be read as passing those gates.

## 1. Scope and non-claims

This is an offline, fixed-length trajectory classification study on two synthetic families. The unit of observation is a complete trajectory sampled over the fixed physical horizon [0, 1], and each trajectory carries exactly one label from the three scientific classes: return, ramp, and jump. Labels are assigned from latent control programs before any persistence computation. The primary observation map is one frame per sample, so the study evaluates whole observed diagram paths rather than online detection.

The study does not claim early warning or online detection, latent-cause identification, or application utility. The prohibited interpretations are explicit. No result may be described as physical acceleration (the reported quantity is a rate of change of an observable speed), as turning direction (only the symmetric comparison angle is reported, always together with its turn companion), as canonical kinematics, or as established domain independence. Failure on these generators limits this formulation only, not the wider possibility of useful topological dynamics.

## 2. Research questions and hypotheses

**H1 (confirmatory, noninferiority or superiority).** The compact diagnostic representation matches the strongest validation-selected incumbent within the predeclared noninferiority margin or beats it. In terms of the primary estimand, the upper endpoint of the paired 95% interval for delta is below 0.02 (noninferiority), or below negative 0.05 (superiority). The direction of interest is that the compact representation is not worse.

**H2 (confirmatory, parsimony).** While within the 0.02 noninferiority margin, the compact representation attains a material parsimony advantage: at least a fourfold reduction in feature dimension or in measured end-to-end prediction cost relative to the cheapest competitor whose validation macro balanced error lies within 0.02 of the best validation result. The direction of interest is a cost or dimension ratio of at least four.

**H3 (stability diagnostic).** The results are reported across the noise and resolution cells (sigma in {0, 0.05} and strides 1, 2, 4) with per-cell estimates and family-specific differences. The expectation is that the sign of delta does not reverse across cells and that any gain is not concentrated in a single cell. H3 is a reported stability diagnostic, not an additional GO condition: the GO rule is exactly the pilot specification rule, which requires correctness and nuisance checks, adequate precision, route (a) or (b), and the family safeguard. H3 cannot by itself deny a GO that otherwise satisfies that rule, and it may motivate a narrowed claim or a PIVOT at the discretion of the analysis review.

**H4 (replication safeguard, part of the GO rule).** The results replicate across both raw families without a family-specific deterioration above 0.05, under simultaneous Bonferroni-adjusted family bounds. This safeguard is part of the pilot specification's GO requirement: neither route may hide a family-specific deterioration above 0.05, and one family may not be traded away for a pooled result.

H1 and H2 are the confirmatory pair. The route that will be claimed (superiority or parsimony) is frozen after the exploratory stage and before the confirmatory test seeds are opened, not selected afterward.

## 3. Estimands

The primary estimand is delta, the trajectory-level macro balanced error of the compact diagnostic representation minus that of the validation-selected incumbent, with macro balanced error evaluated within each family, noise, and resolution cell and the cells then averaged with equal weight. The unit of analysis is one complete trajectory with one label per trajectory. The clustering unit is the base seed: all trajectories, noise variants, and resolution variants derived from one base seed move together in the paired bootstrap of whole base-seed clusters, which uses 2000 resamples and bootstrap seed 20260907 and preserves the pairing of all methods. Reported uncertainty is conditional on the frozen fitted models; it is not uncertainty over retraining.

The secondary estimands are per-class confusion matrices, validity and coverage fractions for the efficiency and comparison-angle abstention rules, feature dimension per representation, extraction seconds, feature seconds, prediction seconds, peak RAM bytes, and family-specific error differences. The saved results table carries the fields run_id, base_seed, family, class, sigma, stride, degree, metric, representation, learner, split, true_label, predicted_label, valid_fraction, feature_dim, extraction_seconds, feature_seconds, prediction_seconds, peak_ram_bytes, and status. End-to-end prediction cost includes diagram extraction, and distance, feature, and classifier costs are also reported separately.

## 4. Data-generating process

Physical time is u in [0, 1], initially sampled on the master grid u = j/128 with j = 0, ..., 128, giving 129 samples. Every resolution experiment subsamples the same master realization at stride 1, 2, or 4, giving 129, 65, or 33 frames with the same physical horizon. Separate fixed-dimensional models are trained at each resolution.

For each independent seed, a start time a is drawn uniformly on [0.15, 0.25], an end time b uniformly on [0.75, 0.85], and m = (a + b)/2. The latent level is z(u) = 0.5 + 2.5 g(u), and the three scientific classes are defined by the latent control program g before any persistence calculation:

| Class | Latent control g(u) |
|---|---|
| Return | Zero outside [a, b]; (u - a)/(m - a) for a <= u <= m; (b - u)/(b - m) for m < u <= b |
| Ramp | clip((u - a)/(b - a), 0, 1) |
| Jump | 1 if u >= m, otherwise 0 |

The return is a triangular pulse, the ramp is a clipped linear rise, and the jump is a step at m. The return and ramp have deliberately different accumulated latent movement, and this study is not a matched-speed experiment.

**Family A, point clouds.** Draw a fixed orientation phi uniformly on [0, 2pi), a radius r uniformly on [0.9, 1.1], and 32 equally spaced angles on each of two circles with independently randomized phase offsets. At time u the circle centers are (-z(u)/2, 0) and (z(u)/2, 0), both circles have radius r, the whole configuration is rotated by phi, and independent isotropic Gaussian coordinate noise with standard deviation sigma is added. There are 64 points per frame. The circle sampling phases stay fixed over time; the later resampling control that redraws them at every frame is outside the primary analysis. Orientation, radius, phase, and noise vary across independent seeds.

**Family B, scalar fields.** On a fixed 32 by 32 grid in [-4, 4]^2, evaluate f_u(x, y) = A1 exp(-((x + z(u)/2)^2 + y^2)/(2 w^2)) + A2 exp(-((x - z(u)/2)^2 + y^2)/(2 w^2)) plus noise. Draw A1 and A2 independently uniformly on [0.9, 1.1] and w uniformly on [0.35, 0.45], fixed within each trajectory. Pixel noise is independent Gaussian with standard deviation sigma. In Family B, sigma is in field-amplitude units, whereas Family A uses coordinate units, so the families are analyzed separately before any equal-weight aggregation.

The noise levels are sigma in {0, 0.05}, crossed with both families, the three classes, and strides 1, 2, 4 in every stage. The persistence conventions are coefficient field F2; Euclidean Vietoris-Rips H0 and H1 with the edge-length filtration for Family A; cubical H0 and H1 of the sublevel sets of -f for Family B; primary finite H0 in both families with H1 as a predeclared secondary channel; essential infinite-death bars removed with recorded counts; all finite bars retained without label-dependent persistence thresholds; primary metric the bottleneck distance with L-infinity ground norm; and empty finite diagrams treated as valid. The 2-Wasserstein distance with the same L-infinity ground norm is a sensitivity branch after the cheap pilot, not a primary metric, and no stability constant is transferred between norms. Trailing-window pooling with lengths 1, 3, 5 frames and strides 1, 2, 4 is a later observation map (WP-2.1); it changes the observation map and is outside the primary frame-level baseline.

The controls are reported separately from the three-class accuracy calculation. They are static trajectories with z(u) = 0.5, with and without observation noise; a time-dependent rigid translation of the identical Family A point realization, whose Vietoris-Rips diagrams must be unchanged up to numerical tolerance of 1e-7 times max(1, filtration range); a scale-sensitivity analysis, since scaling coordinates changes persistence coordinates and is not an invariance, where a scale-normalized analysis would change the observation map and must normalize every comparator identically; and a matched-speed ordering construction as a correctness control, not a fourth scientific class. The Phase 0 witness suite supplies the equal-speed ordering correctness control (case W-06: equal consecutive distances, equal L, equal R, constant speed, different intermediate order), and a later independently pre-registered control may match movement budgets; that construction must not be selected because it favors a descriptor, and its results stay outside the three-class accuracy calculation. When the ordering construction is re-instantiated inside the G3 raw pipeline as directed by the plan, it serves the plan section 8 C3 information comparison as a diagnostic; the primary confirmatory estimand remains delta on the three scientific classes.

## 5. Representations and learners

All representations receive the same complete trajectory. They are built within each resolution as follows.

| Representation | Fixed construction within each resolution |
|---|---|
| Compact email diagnostics | L, R, eta; mean, standard deviation, and maximum of speed; mean absolute and maximum absolute speed-change; mean cosine comparison-angle; angle-valid fraction; efficiency-valid flag. Missing numeric features use a training median plus a mask. The speed/L/R/eta ablation is reported separately. |
| Speed history | Entire adjacent speed vector, plus the same six speed and speed-change summaries. |
| Complete distances | Flattened upper triangle of the full diagram-distance matrix in temporal order; also a recurrence-summary baseline with mean and minimum distances at lags 1, 2, 4, 8 and endpoint displacement. |
| Raw geometry | Family A: framewise pairwise-distance quantiles 0.1, 0.5, 0.9, covariance eigenvalues, and nearest-neighbor distance mean. Family B: framewise mean, standard deviation, maximum, and gradient-energy mean. Flatten temporal histories; also compare their temporal mean/std summaries. |
| Persistence moments | Per frame, sums of b^i p^j for p = death - birth, j >= 1 and i + j <= 3 (six coordinates). Flatten histories and compare mean/std summaries. These finite moments are not claimed injective. |
| Moment signatures | Piecewise-linear path of the six moment coordinates, signature through level 2, both without time and with u as an extra coordinate. Coordinate scaling is fit on training data. This is an explicit finite-vector comparator, not subtraction of unmatched diagrams or a borrowed bottleneck stability theorem. |

Centering, scaling, and imputation are fit on training data only, missing-feature masks are retained where needed, and no latent z, generator identity, or test label enters any feature. The same learner grids are used for all representations: multinomial logistic regression with C in {0.01, 0.1, 1, 10}, and RBF SVM with C in the same set and gamma in {0.1/d, 1/d, 10/d}, where d is the postprocessed feature dimension. Multiclass labels are predicted by the fitted classifier, never by a binary threshold. The best learner for each representation is selected by validation macro balanced error, with ties broken by lower measured prediction cost. The incumbent representation is selected on validation and frozen before test evaluation. All individual incumbent results are retained so that a small raw or moment baseline cannot be hidden behind a large matrix comparator.

## 6. Splitting, leakage, and causality

Splits are by complete trajectory only, with no overlapping windows distributed across splits. Seed namespaces include family and class, and every noise or resolution variant of one base seed stays in the same split.

| Stage | Seed namespaces | Grid |
|---|---|---|
| Correctness and resource pilot | seed 11 | Both families, three classes, sigma in {0, 0.05}, stride 1: 12 trajectories plus static and translation controls. Run one trajectory first and measure wall time and peak RAM before the remaining pilot; subsample saved frames for strides 2 and 4. |
| Exploratory implementation study | training 1000-1039, validation 2000-2019, exploratory test 3000-3039 | Both families, three classes, sigma in {0, 0.05}, strides 1, 2, 4. |
| Confirmatory study | new test seeds starting at 10000; one size from {200, 500, 1000, 2000} base-seed clusters | Choices frozen after the exploratory stage; training and validation data retained. |

Raw trajectories, diagrams, and distances are cached, and the split manifest records every trajectory. If profiling projects excessive cost, the exploratory grid may be reduced before running it, with the reduction recorded; cells are never reduced after outcomes are seen. Preprocessing is fit inside training only. If online detection is later authorized as a separate study, it uses trailing causal windows only, and every comparator receives the same prefix or trailing inputs.

## 7. Analysis plan and decision rules

GO to application feasibility requires correctness and nuisance checks, adequate precision, and at least one of two predeclared routes. Route (a), superiority: the upper endpoint of a paired 95% confidence interval for delta lies below negative 0.05. Route (b), parsimony: that upper endpoint lies below 0.02 and the compact representation achieves at least a fourfold reduction in feature dimension or measured end-to-end prediction cost relative to the cheapest competitor whose validation macro balanced error lies within 0.02 of the best validation result. The eligible comparator set is frozen before test results are opened, and the superiority-versus-parsimony route is frozen after exploration and before confirmation rather than chosen afterward. A tiny raw-data or speed-summary incumbent that ties the method at lower cost defeats the parsimony argument. Neither route may hide a family-specific deterioration above 0.05; family bounds are simultaneous and Bonferroni-adjusted.

An interval too wide to decide gives INDETERMINATE, not failure. Reliable domination by a simpler incumbent gives INCREMENTAL-ONLY for this diagnostic task. A reproducible but narrower useful result gives PIVOT, with a new protocol and untouched test seeds. Broken extraction, circular labels, or leakage requires repairing and rerunning the affected stage.

The precision rule is fixed in advance. One confirmatory test size is chosen from {200, 500, 1000, 2000} base-seed clusters using the exploratory paired error variance and a target confidence-interval half-width of 0.01 for the 0.02 noninferiority margin. Cost is estimated before scheduling a large run. If even the largest affordable size cannot resolve the margin, the result is INDETERMINATE. There is no repeated peeking, and no stopping when significance appears.

Estimation follows the frozen plan: macro balanced error is computed within each family, noise, and resolution cell and then averaged equally across cells; the paired bootstrap of whole base-seed clusters uses 2000 resamples and seed 20260907 and preserves the pairing of all methods and all correlated noise and resolution variants. Per-class confusion matrices and family-specific error differences are reported.

## 8. Multiple comparisons, exclusions, and abstentions

Bonferroni-adjusted simultaneous family bounds enforce that no family deteriorates above 0.05. For each cell defined by (family, degree, resolution, metric), the training-only static-noise calibration population is the set of adjacent diagram distances computed on the training-split static-noise trajectories at sigma = 0.05 for that cell, and e is the 95th percentile of that population, computed with numpy.percentile's default linear interpolation; calibrations are never pooled across families, degrees, resolutions, or metrics because the distance units differ. Abstain on efficiency when L <= 2(T - 1)e with T the number of intervals, and abstain on comparison angles when min(a, b) <= 2e; at zero noise (sigma = 0), e = 0 and only exact-zero abstention applies, with exact zero the value returned under the numerical-zero convention of the metric interface. These floors are applied without deleting trajectories: performance is reported with and without the floors, and validity fractions and coverage are reported jointly with performance in every regime. Straight and reversal angle cases are valid and are retained, never deleted to obtain a Lipschitz theorem.

Missing-window trajectories are excluded from the primary offline analysis with recorded counts, and never silently; there is no interpolation and no window pooling to repair gaps. Degenerate cases follow the frozen conventions: when L = 0, eta is undefined (null), L is reported, and a flag is recorded; when a = 0 or b = 0, the comparison angle is null and the step is counted as unresolved; the cosine is clipped to [-1, 1], and |z| > 1 + 1e-12 records a cosine-anomaly flag.

## 9. Freezing and deviations

Frozen now: the scope and the prohibited interpretations; the three class labels and the latent control definitions; the generator constants and noise levels; the master grid and strides; the six representations and their semantics; the primary estimand (macro balanced error) and delta; the learner grids; the seed namespaces and split rule; the decision thresholds and rules; the precision rule; and the analysis unit and clustering unit. The frozen environment is Python 3.12.3 with numpy 2.4.3, scipy 1.17.1, matplotlib 3.10.8, gudhi 3.12.0, persim 0.3.8, and pytest 9.0.3, with gudhi.bottleneck_distance as the primary bottleneck implementation.

Only the exploratory stage may change implementation details, and only with a recorded deviation: cached formats, library call patterns, worker scheduling, and a pre-run reduction of the exploratory grid if profiling projects excessive cost. Nothing that changes the estimand, hypotheses, thresholds, seeds, or decision rules may change after test outcomes have been inspected.

Deviations log:

| Date | Section | Change | Reason | Outcome inspection status | Approval |
|---|---|---|---|---|---|
| 2026-09-20 | Sections 2, 4, 8 | H3 stated as a reported stability diagnostic and H4 as part of the GO rule; per-cell calibration population defined; W2 sensitivity branch and deferred pooling grid restated; matched-speed role harmonized | Repairs from the Phase 0 consistency audit and second-reader audit at gate G0 | No test outcomes inspected | Phase 0 G0 audits (see research_review/results/phase0/verification/) |
| 2026-09-20 | Section 5 | The phrase "six speed and speed-change summaries" is inherited verbatim from the authoritative pilot specification (line 50), which enumerates five; the count is left unchanged for traceability | Inherited ambiguity, no decision impact | No test outcomes inspected | Deferred to the WP-1.2 feature-schema freeze |

No entry in this log changes the estimand, the hypotheses, the thresholds, the seeds, or the decision rules.

Confirmatory test seeds are opened only once, after this document and the pilot specification are both frozen. All outputs, including failures, are preserved and are not gitignored.

## 10. Limitations

The generators are deliberately simple and give raw geometric baselines a strong opportunity to win, so a failure of the compact diagnostics limits this formulation rather than the wider possibility of useful topological dynamics. Two synthetic families cannot establish domain independence, and no universal kinematics claim follows from any outcome of this study. The decision thresholds are pragmatic simulation design choices, not established application utility thresholds. Uncertainty is conditional on the frozen fitted models rather than over retraining, so it does not include model-selection variability. The study is offline and fixed-length; event timing, early warning, and online detection are outside its scope, and any later online study requires a separate authorization and protocol. A successful classifier establishes a useful observable diagnostic under the declared data-generating processes, never physical identification of a latent cause.
