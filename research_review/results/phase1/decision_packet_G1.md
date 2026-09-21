**Status update (2026-09-21):** superseded by `research_review/results/phase1/G1_decision.md`.
This file is retained as the pre-decision template; all `[PENDING: ...]` markers below were resolved by the
independent audit `research_review/results/phase1/verification/G1_audit.md` and by the written decision record.

# G1 decision packet: prior-art and baseline lock (template)

**Gate.** G1 between Phase 1 and Phase 2.

**Document status.** Template, not a decision. It contains only what is already established by the frozen Phase 0 records and the plan. Every item that depends on an agent output is marked `[PENDING: ...]`, and no result may be written into this file before it exists as an artifact.

**Outcome-inspection statement.** No outcome label, prediction, error rate, or comparative result from any stage has been inspected at the time this template is written. The pilot package beyond the Phase 0 artifacts does not exist, no smoke run has occurred, and no citation ledger has been produced. The G1 decision is written only after the citation ledger, the baseline smoke tests, and the protocol-freeze verification exist.

**How to complete this packet.** Replace each `[PENDING: ...]` marker with an artifact path and a one-line finding, delete markers only when their evidence exists, keep every established-background sentence unchanged, and record the decision under Section 4 with the exact status vocabulary of the plan (GO, CONDITIONAL GO, PIVOT, INCREMENTAL-ONLY, KILL, INDETERMINATE). An item that remains unresolved is recorded as unresolved rather than silently omitted.

## 1. Prior-art status

The following novelty positions are already established and are not open for revision at G1. Inter-frame persistence-diagram speed is established background: Kramár et al. (2016) define bottleneck and Wasserstein diagram distances and the consecutive speed `d(PD(f_i), PD(f_{i+1})) / Delta t` in Eq. (16) on printed p. 10, and study changes in speed in Section 6, printed pp. 9-11. Parameterized diagram trajectories are established background: Cohen-Steiner, Edelsbrunner, and Morozov (2006) define vineyards, vines, and knees and track points through updates. Time-indexed diagram summaries and their continuity are established background: Xian, Adams, Topaz, and Ziegelmeier (2021) develop dynamic metric spaces and continuity of persistence summaries. Path signatures of persistence diagrams are an established incumbent with a precise scope: Giusti and Lee (2021) prove a Lipschitz-free embedding for the partial 1-Wasserstein quotient only, not for arbitrary W_p or bottleneck distance, and signatures are reparameterization invariant unless time is augmented. Three recent preprints report topological velocity or activity measures (Khormali 2025; Malhotra et al. 2026; Bernal-Alvarado et al. 2026) and are cited as source-reported application precedents, not as peer-reviewed priority claims. Kramár et al. Theorem 7.3 on a delta-dense subsample is a bottleneck perturbation bound that supports a sampling stress test, not a universal finite-sample guarantee.

The corresponding novelty withdrawals are binding. The project does not claim that inter-frame diagram speed is new, that a trajectory of diagrams is new in the broad form, that a broad topological-velocity theory is new, that the comparison angle supplies direction or turning, that the diagnostics identify latent physical causes, that the collection is domain independent as an established property, that it improves a real decision, or that a new calculus or acceleration theory follows. The intended contribution sentence, which must be statable without any of these claims, is: a predeclared operational comparison of a compact, interpretable metric-path diagnostic set against a full distance-matrix baseline, a speed-history baseline, raw-data baselines, persistence moments, and moment signatures with and without time augmentation, under equal tuning budgets and complete-trajectory splits, on a latent-control classification task separating reversible restructuring, persistent drift, and shock.

WP-1.1 PASS requires that the intended contribution can be stated without claiming existing results, and that every novelty-sensitive statement resolves to a primary source with an exact locator. If an incumbent baseline cannot be reproduced, the outcome is reported as INDETERMINATE with a narrowed scope rather than as a positive claim. The current literature-derived status is CONDITIONAL GO for a narrowly specified diagnostic study, per plan Sections 1 and 4.

`[PENDING: A3 citation ledger path and result: every DOI or primary URL resolved, every novelty-sensitive statement mapped to an exact equation or page, and any unavailable code or data documented.]`

`[PENDING: final wording check of the intended contribution sentence against the citation ledger, with any change recorded.]`

## 2. Baseline reproducibility status

The comparison targets are frozen by the implementation contract: Kramár-style consecutive speed, the full distance-matrix upper triangle with its recurrence summaries, raw geometry features for both families, persistence moments, and moment signatures without and with time augmentation, each as a concrete representation name. The smoke stage is defined as seed 11, both families, three classes, `sigma` in `{0, 0.05}`, stride 1, plus static and translation controls, with a first single-trajectory resource measurement, a wall-time cap of 20 minutes with 2 workers, and outputs under `research_review/results/phase1/smoke/`. No smoke result exists yet, and this template asserts no accuracy, cost, or reproducibility value.

The G1 baseline question is whether each incumbent family has a reproducible implementation or a transparently documented reimplementation, and whether the smoke stage produces constant feature dimensions per cell, the expected signature values, and measured costs consistent with the planning placeholders. An inaccessible repository is not evidence that no implementation exists; it is recorded as a reproduction limitation with a transparent reimplementation and a marked status.

`[PENDING: A3 reproducibility memo path and result, including which incumbents have available code or data, which are transparent reimplementations, and any unavailable artifacts.]`

`[PENDING: smoke-stage manifest and report path, with per-representation feature dimensions, timing and peak-RAM measurements, and the single-trajectory resource measurement.]`

`[PENDING: baseline API smoke-test result for every comparator representation, including the analytic signature checks on a straight path and an L-shape.]`

`[PENDING: signature path-coordinate scaling verification. The pilot specification requires coordinate scaling fitted on training data for the moment-signature path, and baseline_protocol.md Section 7 freezes training-only per-coordinate scaling of the six moment coordinates with the time coordinate unscaled. The current features.py builds both signatures from raw moment coordinates and leaves scaling to the model pipeline, which standardizes the final signature columns rather than the path coordinates. Confirm before G1 that a training-only path scaling exists, or record the divergence as a deviation and show that the signature comparator is still not disadvantaged; otherwise the fair-baseline PASS condition of WP-1.2 is not met.]`

## 3. Protocol freeze status

WP-1.2 freezes the comparison before any outcome is seen. The frozen rules are: the six comparator families and their ten representation names; equal tuning with 16 hyperparameter evaluations per cell and representation, identical preprocessing, and ties broken by measured cost; cell-wise model fitting with validation-selected learners; complete-trajectory splits with base-seed variant clustering, no overlapping windows across splits, and trailing causal windows for any detection work; incumbent selection as the best non-compact representation by validation macro balanced error, with the full ranking recorded and the eligible comparator set frozen from validation at 0.02; the two-route decision rule with thresholds `-0.05` and `0.02` and the fourfold parsimony requirement; the route-freeze procedure before confirmatory seeds are opened; the feature schema with exact dimensions; the missing-value and abstention policies; and the Bonferroni family safeguard. The frozen authority versions are listed in Appendix B.

WP-1.2 PASS requires that an independent rerun obtains the same feature dimensions and that no trajectory appears in multiple splits, and that no comparator is disadvantaged by timing or tuning. Failure of either check resets all empirical results.

`[PENDING: sha256 values of baseline_protocol.md and claims_to_tests.yaml at the freeze instant, appended to the freeze table in baseline_protocol.md and to the execution log.]`

`[PENDING: independent verification of the split manifest: every trajectory identifier appears under exactly one split, and every family, class, sigma, stride, and degree variant of one base seed stays together.]`

`[PENDING: independent rerun of the smoke manifest feature dimensions against the schema table.]`

`[PENDING: execution-log entries for the two recorded readings of the authority documents: the compact representation is 12 nominal features after the six-summary resolution, superseding the stale "(11 features)" label in the implementation contract, and the fourfold dimension and cost comparison uses the worst-case cell ratio against the best non-compact validation reference.]`

## 4. Claim statuses

The overall G1 decision takes exactly one value from GO, CONDITIONAL GO, PIVOT, INCREMENTAL-ONLY, KILL, or INDETERMINATE. The value is written only after Sections 1 through 3 are complete, and it must be consistent with the per-claim statuses below and with the rule that no claim status may be upgraded without the gate evidence the plan requires. The current literature-derived status is CONDITIONAL GO for the narrow diagnostic study; the final decision is `[PENDING: overall G1 status with the evidence sentence that fixes it]`.

| Claim | Established position before G1 | Status to record at G1 |
|---|---|---|
| C1, metric-valued discrete path | GO under the declared metric and conventions at G0 | GO if the smoke regression and dimension checks pass; `[PENDING: T-C1-01, T-C1-02]` |
| C2, `nu`, `L`, `R`, `eta` as summaries | GO as operational definitions at G0 | GO for the definitions if the smoke totality checks pass; sensitivity remains for G3; `[PENDING: T-C2-01]` |
| C3, inter-frame speed is new | Rejected; Kramár Eq. (16), printed p. 10 | Withdrawn, no novelty claim; `[PENDING: T-C3-01, T-C3-02]` |
| C4, a trajectory of diagrams is new | Rejected in the broad form; vineyards and dynamic topology literature | Withdrawn as novelty; the precise decision use replaces it; `[PENDING: T-C4-01]` |
| C5, scalar speed-change is useful | Open empirical question | Open; tested at G3; `[PENDING: T-C5-01, T-C5-02]` |
| C6, `theta` identifies turning or direction | Unsupported without extra structure | Triangle-shape diagnostic only, direction withdrawn; `[PENDING: T-C6-01, T-C6-02]` |
| C7, diagnostics identify latent causes | Not identified from persistence diagrams alone | Not identified; identification claims prohibited; `[PENDING: T-C7-01, T-C7-02]` |
| C8, domain independence | Only a portability hypothesis | Open; requires the G3 family safeguard; `[PENDING: T-C8-01]` |
| C9, improvement of a real decision | Unproven | Open; requires WP-4.1 and WP-4.2 and remains INDETERMINATE if data are inaccessible; `[PENDING: T-C9-01]` |
| C10, new calculus or acceleration theory | No | Withdrawn and deferred to G5; `[PENDING: T-C10-01]` |

Decision rules for filling the statuses: a claim moves to GO only with its named gate evidence; a claim whose baseline cannot be reproduced is recorded as INDETERMINATE with a narrowed scope, never as positive evidence; a claim that cannot be stated without claiming existing results moves the project to INCREMENTAL-ONLY or PIVOT as the plan directs; and a claim that would require theory is deferred to G5 without exception.

## 5. Authorization for Phase 2

Phase 2 is dormant until G1 passes. Passing G1 authorizes WP-2.1 and the G2 raw-data correctness work only; it does not authorize applications, theory, or the opening of confirmatory seeds, which require the route freeze (WP-1.2) and the exploratory stage respectively. If G1 does not pass, the authorized work is limited to the repair that the failed check requires, recorded in the execution log.

Authorization line: `[PENDING: authorized or not authorized, with the citation-ledger result, the baseline smoke result, and the protocol-freeze verification result that establish the decision.]`

Required evidence for authorization: WP-1.1 PASS with resolved locators and documented reproduction status; WP-1.2 PASS with constant feature dimensions and an isolated split manifest; no prohibited-language occurrence for any withdrawn claim; and a written overall decision with a consistent per-claim table. Any missing item leaves Phase 2 dormant.

## Appendix A: pending items

The pending items of this packet are exactly the following: the citation ledger and its resolution result, the reproducibility memo, the smoke-stage manifest and report, the baseline API smoke tests, the signature path-coordinate scaling verification, the freeze-time hashes of the WP-1.2 documents, the independent split-manifest verification, the independent feature-dimension rerun, the execution-log entries for the two recorded readings, and the overall G1 status with its evidence sentence. Each is completed only from a real artifact.

## Appendix B: freeze-time hashes of the authority documents

These hashes were computed when the WP-1.2 protocol was frozen and are repeated here for the G1 record. They fix the versions the protocol refers to.

| Document | sha256 |
|---|---|
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` |
| `research_review/preregistration_draft.md` | `669bd3db1b434b2693bbd688d942907d0cb97acfa27eac446921dfea7e93e770` |
| `research_review/assumption_ledger.yaml` | `ea46fab5960c0e8648bcd61bf187e86446a1a4cc7eeaae0ac1259ce8a1220844` |
| `research_review/metric_interface.md` | `7a8a25137ad82050c23d0388f46b5f46f4fc3e86d0b754cce166132687700c33` |
| `research_review/results/phase1/implementation_contract.md` | `b024c04f5126c8c5f7781b931a567d7dd3666774e5d12fb168dd447555a6c4f0` |
| `research_review/results/phase0/G0_decision.md` | `44571b588492bbf01507b1ee191cb238828bcf3ca41444561c24a8c7688a31cb` |
| `research_review/results/phase0/verification/consistency_audit.md` | `b399b8c1054b6d55bced92b48bbc81d17db495cb306ab93d4a39f110031bc660` |
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` |
| `research_review/results/phase1/baseline_protocol.md` | `1a31cb509bad64b0d9584cde997127c01d46af3d21d21469f8d8885c2246fdd9` |
| `research_review/results/phase1/claims_to_tests.yaml` | `[PENDING: sha256 at the G1 freeze instant]` |
