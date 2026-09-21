# G2 decision record: raw-data and topology pipeline correctness

**Decision.** G2 is **PASS with recorded residuals**. The frame-to-diagram pipeline is
deterministic, hash-verifiable, invariant under the declared rigid-translation control, and its
diagnostic definitions are stable under the exact primary metric. The G2 decision authorizes the
Phase 3 simulation work already in flight (WP-3.2/WP-3.3 exploratory stage and the confirmatory
stage after the route freeze). The metric backend amendment below is part of this decision.

**Scope.** `research_review/Topological_Kinematics_Research_Plan.md` WP-2.1, WP-2.2, WP-3.1 and
the G2 gate definition; the frozen conventions in `assumption_ledger.yaml` and
`metric_interface.md` as amended.

## Evidence

| Evidence | Artifact | Verdict |
|---|---|---|
| WP-2.1 interface determinism | `research_review/results/g2/interface/determinism.json` | PASS: two independent recomputations are bitwise identical, canonical array SHA256 equal, `diagrams_for_windows(length=1,stride=1)` equals `trajectory_diagrams` for both families and degrees |
| WP-2.1 resampling and window metadata | `research_review/results/g2/interface/resampling.csv`, `window_metadata.json` | PASS: all nine (length, stride) window maps match the declared trailing-window counts and timestamps; resampling shifts are reported descriptively, including point subsampling and grid coarsening |
| WP-3.1 static and smooth controls | `research_review/results/g2/reports/raw_correctness_report.md` | PASS: exact zeros at sigma = 0; bounded, monotone responses for smooth deformation (Family A slope 0.99-1.00 against latent increments; Family B finite-H0 onset at z about 0.89 with monotone persistence growth) |
| WP-3.1 topology-changing controls | same | RESIDUAL: the literal H0-cardinality criterion is mis-specified for Vietoris-Rips connectivity (Family A H0 always has n minus 1 finite bars); the transition is verified through the largest finite H0 death and the H1 channel with event frames aligned to 0-1 frames. Family B cardinality changes 0 to 1 at the predicted onset |
| WP-3.1 noisy null | same | RESIDUAL: no significant trends or exceedance clustering under permutation tests, but 10 of 36 frozen-snapshot runs exceed the static z = 0.5 calibration floor because the floor is configuration-specific. This is a calibration-transfer limitation, reported as a coverage caveat, not a temporal event |
| WP-3.1 sampling and translation | same | PASS: the stability bound holds with d_B/delta at most 0.99 and d_B/(2 delta) at most 0.49; rigid translation gives exactly 0 under the frozen tolerance for degrees 0 and 1 at both sigmas |
| WP-2.2 diagnostic stability | `research_review/results/g2/diagnostics/` | PASS under the amended metric: 13 of 13 checks pass (triangle inequality on 21,216 triples, eta bounds on all L > 0 rows, q in [0,1] on 13,066 defined times, exact-zero abstention at sigma = 0, undefined values exactly where declared), with straight and reversal cases retained |
| Metric backend repair | `research_review/results/g2/diagnostics/metric_backend_audit.md`, `metric_interface.md` G2 amendment, `tests/test_metric_exact.py` | PASS: gudhi 3.12.0 bottleneck is order-dependent and wrong on some inputs (witness exact 0.3985347143760231 versus canonical-order 0.6650287460769155); the primary metric is now the exact augmented-matching binary-search solver, independently validated against the project brute force, persim, and an order-invariance suite |

## Amendments

1. Primary metric backend: `bottleneck_linf` now resolves to `bottleneck_exact`; `bottleneck_gudhi`
   is retained for audit only. Affected caches were invalidated and regenerated; the smoke stage,
   WP-2.1, WP-3.1, and WP-2.2 were rerun under the amended definition.
2. Exploratory grid reduction: recorded in `baseline_protocol.md` Amendment 1, pre-outcome, with
   the exact-metric cost measurement as the reason.

## Residuals carried into G3 reporting

1. Family A H0 cardinality cannot serve as a topology-change criterion; use the largest finite H0
   death and H1 instead (documented in the raw-correctness report).
2. Noise-floor calibration is configuration-specific; frozen-snapshot runs can exceed the static
   floor. The exploratory and confirmatory reports must present coverage jointly with performance
   and must not treat the 2e floors as coverage guarantees.
3. eta is resolution-sensitive (median stride-4 over stride-1 ratio about 3.2); it remains a stable
   definition but its value is not sampling-invariant, and it is flagged as resolution-conditional.

## Date and status

2026-09-21. Status: PASS with residuals. Phase 3 is authorized; the confirmatory stage requires the
written route freeze first.
