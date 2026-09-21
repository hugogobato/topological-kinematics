# G1 decision record: prior-art and baseline lock

**Decision.** G1 is **CONDITIONAL GO** for Phase 2 (WP-2.1 window-to-diagram interface and the G2
raw-correctness work). Confirmatory and confirmatory-seed work remains unauthorized until the G3
prerequisites and the route freeze are recorded. This record follows
`research_review/results/phase1/verification/G1_audit.md` and closes the PENDING items that the
evidence resolves.

**Scope of the decision.** WP-1.1 (primary-source and implementation verification) and WP-1.2
(fair baseline and referee protocol). It does not evaluate prediction, applications, or theory.

## Work-package verdicts

| Work package | Verdict | Evidence |
|---|---|---|
| WP-1.1 source verification | PASS | `citation_ledger.yaml`: 36 claims, 33 verified at exact locators, 3 corrected locators (Giusti-Lee Section 6 span, Giusti-Lee published DOI, Khormali Theorem 4.5 page). Independent spot-check of nine claims in `G1_audit.md`, including Kramar Eq. (16) printed p. 10 and Giusti-Lee Theorem 4.2 partial-W1 scope |
| WP-1.1 baseline reproducibility | PASS with residuals | Kramar-style speed is implemented in `path_diagnostics`; distance-matrix recurrence, persistence moments, and level-2 signatures with and without time augmentation are implemented and tested; the smoke stage ran with all ten representations. Residual: learner selection can differ across reruns when validation errors tie exactly, because the predeclared tie-break uses measured prediction time; reproducibility of features and error grids is bitwise, reproducibility of the tie-broken learner choice is not claimed |
| WP-1.1 availability status | PASS | `reproducibility_status.md`: vineyards code available, Giusti-Lee code available, Xian partial, Kramar pipeline not found; unavailable baselines are transparent reimplementations and are labeled as such, never as author-code reproductions |
| WP-1.2 protocol freeze | PASS with residuals | `baseline_protocol.md` freezes comparators, equal tuning, complete-trajectory splitting, incumbent rule, two-route thresholds, route-freeze procedure, feature schema, abstention and coverage rules, and the family safeguard; `claims_to_tests.yaml` covers C1-C10 with C3, C4, C10 correctly withdrawn. Residuals listed below |
| Independent smoke rerun | PASS | `G1_audit.md`: 112 tests passed; fresh-cache smoke probe exit 0 in 248 s at 2 workers; translation control max distance 0.0 at the frozen tolerance |

## Claim statuses carried forward

C1 GO (operational), C2 GO (operational definitions), C3 withdrawn (Kramar Eq. (16)),
C4 withdrawn in the broad form, C5 open empirical question, C6 unsupported beyond a
comparison-angle/triangle-shape diagnostic, C7 not identified from diagrams alone, C8 portability
hypothesis only, C9 unproven, C10 no. The prohibited-language list in `assumption_ledger.yaml`
remains binding.

## Intended contribution statement (checked against the withdrawn claims)

The project claims only the following: a frozen, reproducible discrete metric-path diagnostic
suite evaluated as a decision-relevant, cost-aware alternative to speed-only and full-distance
representations on the pilot data-generating processes, with explicit sampling, noise, and
abstention behavior. It does not claim that diagram trajectories, inter-frame diagram speed, path
length, or path-space representations are new, and it does not claim physical identification,
direction, acceleration, or domain independence. This wording uses only terms permitted by the
ledger's prohibited-language policy.

## Conditions carried to G2 and G3

1. The primary metric implementation is repaired (exact augmented-matching solver) and documented
   in the G2 amendment; every affected cached artifact is regenerated before any G3 result is used.
2. The noisy-null calibration-transfer caveat from WP-3.1 (frozen-snapshot runs above the static
   floor) must be carried into the exploratory and confirmatory reporting as a coverage limitation.
3. The reduced exploratory grid recorded in `baseline_protocol.md` Amendment 1 remains a
   pre-outcome reduction; the confirmatory stage keeps the frozen protocol.
4. Remaining housekeeping residuals from `G1_audit.md` are recorded in the execution log: the
   claims-to-tests artifact-path typo, the frozen-authority hash refresh, the optional
   `diagram_hash` field, and the compact speed/L/R/eta ablation. The ablation is implemented as an
   additional representation and reported separately; the others do not affect any estimand.

## Date and status

2026-09-21. Status: CONDITIONAL GO. Phase 2 and the G2 correctness work are authorized;
confirmatory test seeds remain closed.
