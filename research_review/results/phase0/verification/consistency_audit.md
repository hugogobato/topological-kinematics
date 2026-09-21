# Phase 0 gate G0 consistency audit

**Artifact.** Independent consistency audit of the Phase 0 pre-registration set at gate G0.

**Date.** 2026-09-20.

**Auditor.** Independent audit session (opencode), no authorial role in the audited documents.

**Scope.** The audit covers the preregistration draft, the assumption ledger, the metric interface, the authoritative research plan, the authoritative pilot specification, and the Phase 0 witness evidence. It checks numeric traceability, decision-rule equivalence, cross-reference existence, claim-status agreement, language and typography, internal consistency, witness-note scope (pending), and YAML validity. No file was modified except this report. All computations were performed in this session with inline Python scripts.

**Re-verification.** A revision-2 re-verification (repairs to F1 and F4/F5, the new `witness_note.md`, and the 15-case witness suite) is recorded in Section 13. It contains the revision-2 hash table, the per-finding resolved/unresolved status, the witness-note verdict, the numeric re-check, and the final consistency verdict. The original revision-1 findings and evidence above are kept unchanged as required.

**Audited files and sha256 (computed in this session).**

| File | sha256 |
|---|---|
| `research_review/preregistration_draft.md` | `a8f679c9ee5b4eff597ee0e30ef342ff58f176f186cca6f2400ee3807c0c5d06` |
| `research_review/assumption_ledger.yaml` | `5de8eba33543795c64edd7bad433de3f32ffd525b795ea679d8b20ba4fd677f7` |
| `research_review/metric_interface.md` | `5eb194a63cd124a8054b0ff8aaa9a734b8379fa7d3d107c519c66bde79e24b9c` |
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` |
| `research_review/witness_note.md` | file does not exist (recorded as pending) |
| `research_review/results/phase0/witness/witness_results.json` | `2332637a7c99bf130b1d2d543b3dcc88e0ee2c25f88ca6a0532815428e139fde` |
| `research_review/results/phase0/witness/environment.json` | `b2da0b72db9bdd169f7836ea9821a092e348e13bcb225aa01e61e2b182fb26a4` |
| `research_review/results/phase0/witness/witness_summary.txt` | `58789fe05a3a9e7b7ad81c2dca08c543077a225139a6374e4b1b6a488d00ae35` |
| `research_review/results/phase0/witness/run.log` | `bb567fa267ba92a734972bd85e0d6f62a5dbd97bcff770f2a3e426fb9fec9c8a` |
| `research_review/results/phase0/witness/figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` |
| `research_review/results/phase0/witness/figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` |
| `research_review/results/phase0/witness/figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` |
| `research_review/results/phase0/witness/figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` |

`witness_note.md` is absent (filesystem check), so check 7 is recorded as pending rather than passed or failed.

## 1. Findings summary

| ID | Severity | Check | Finding |
|---|---|---|---|
| F1 | material | 2 (decision rules) | The preregistration adds H3 (cell stability of delta) as a condition that "must also hold for a GO" (prereg line 31), but pilot section 5 and plan WP-3.4 do not include H3 in the GO rule. The prereg's own section 7 GO sentence also omits H3. Not logically equivalent; the disagreement is not in the deviations log. |
| F2 | cosmetic | 3, 8 (cross-references) | The ledger `source_documents` role string for `witness_results.json` claims it contains "environment metadata, and figure manifest"; the file contains neither (top-level keys are only `suite, gate, scope, seed, summary, cases`). Environment data is in `environment.json`; figures are in `run.log` and `figures/`, both listed separately in the ledger. |
| F3 | cosmetic | 1, 6 (counts) | Prereg line 68 (and pilot line 50) say "the same six speed and speed-change summaries", but the compact row enumerates only five (mean, standard deviation, maximum of speed; mean absolute and maximum absolute speed-change). The wording is inherited verbatim from the pilot, so traceability passes, but the count cannot be reconciled with the list. |
| F4 | cosmetic | 1 (omissions) | Source values not restated in the preregistration: trailing-window pooling lengths 1, 3, 5 at strides 1, 2, 4 (pilot line 39); the 2-Wasserstein sensitivity branch (pilot line 37); pyyaml in the ledger environment list (ledger line 42). All are covered by the prereg delegation clause (line 11) or are explicitly outside the primary baseline, so there is no decision impact. |
| F5 | cosmetic | 6 (matched-speed controls) | The preregistration attributes the equal-speed correctness control to Phase 0 case W-06, pilot line 21 attributes it to the existing singleton-diagram script, plan WP-3.2 directs the G3 DGP to add a matched-speed ordering construction, and plan section 8 frames matched-speed controls as the test of claim C3. Substantively compatible (all treat it as a control, never a fourth class), but attribution, phase placement, and role differ. |

**Counts: 0 blocking, 1 material, 4 cosmetic. Pending: 1 (`witness_note.md`).**

**Top finding.** F1: the preregistration's GO rule adds H3 as a must-hold safeguard that is absent from pilot section 5 and from plan WP-3.4, so the two decision rules are not logically equivalent.

## 2. Check 1: numeric traceability

Every numeric constant, seed, threshold, and grid value in `preregistration_draft.md` was extracted and matched against `Pilot_Experiment_Specification.md` or the ledger/interface. All values match. Line numbers are from the current files whose hashes are listed above.

| Item | Value in preregistration | Prereg location | Source location | Match |
|---|---|---|---|---|
| Physical horizon | `[0, 1]` | lines 17, 41, 59 | pilot line 11 | yes |
| Master grid | `u = j/128`, `j = 0, ..., 128` | line 41 | pilot line 11 | yes |
| Master samples | 129 | line 41 | pilot line 11 | yes |
| Strides | 1, 2, 4 | lines 41, 57, 83 | pilot lines 11, 57, 61 | yes |
| Frame counts | 129, 65, 33 | line 41 | pilot line 11 | yes |
| Start time `a` | uniform `[0.15, 0.25]` | line 43 | pilot line 13 | yes |
| End time `b` | uniform `[0.75, 0.85]` | line 43 | pilot line 13 | yes |
| Midpoint `m` | `m = (a + b)/2` | line 43 | pilot line 13 | yes |
| Latent level `z(u)` | `z(u) = 0.5 + 2.5 g(u)` | line 43 | pilot line 13 | yes |
| Return control program | zero outside `[a, b]`; `(u - a)/(m - a)` for `a <= u <= m`; `(b - u)/(b - m)` for `m < u <= b` | line 47 | pilot line 17 | yes |
| Ramp control program | `clip((u - a)/(b - a), 0, 1)` | line 48 | pilot line 18 | yes |
| Jump control program | `1` if `u >= m`, else `0` | line 49 | pilot line 19 | yes |
| Family A orientation | `phi` uniform `[0, 2pi)` | line 53 | pilot line 23 | yes |
| Family A radius | `r` uniform `[0.9, 1.1]` | line 53 | pilot line 23 | yes |
| Family A angular samples | 32 equally spaced angles on each of two circles | line 53 | pilot line 23 | yes |
| Family A point count | 64 points per frame | line 53 | pilot line 23 | yes |
| Family A centers | `(-z(u)/2, 0)` and `(z(u)/2, 0)`, rotated by `phi` | line 53 | pilot line 23 | yes |
| Family B grid | 32 by 32 on `[-4, 4]^2` | line 55 | pilot line 25 | yes |
| Family B amplitudes | `A1, A2` independent uniform `[0.9, 1.1]` | line 55 | pilot line 29 | yes |
| Family B bump width | `w` uniform `[0.35, 0.45]` | line 55 | pilot line 29 | yes |
| Family B formula | two-Gaussian sum plus noise | line 55 | pilot line 27 | yes |
| Noise levels | `sigma` in `{0, 0.05}` | lines 27, 57 | pilot lines 57, 60, 61 | yes |
| Static control value | `z(u) = 0.5` | line 59 | pilot line 31 | yes |
| Translation tolerance | `1e-7` times `max(1, filtration range)` | line 59 | pilot line 37 | yes |
| Coefficient field | F2 | line 57 | pilot line 35 | yes |
| Primary and secondary degree | finite H0 primary, H1 secondary | line 57 | pilot line 35 | yes |
| Primary metric | bottleneck with L-infinity ground norm | line 57 | pilot line 37 | yes |
| Recurrence lags | 1, 2, 4, 8 | line 69 | pilot line 51 | yes |
| Raw geometry quantiles | 0.1, 0.5, 0.9 | line 70 | pilot line 52 | yes |
| Persistence moments | `j >= 1`, `i + j <= 3`, six coordinates | line 71 | pilot line 53 | yes |
| Moment signature level | through level 2 | line 72 | pilot line 54 | yes |
| Logistic regression `C` grid | `{0.01, 0.1, 1, 10}` | line 74 | pilot line 56 | yes |
| RBF SVM `C` grid | `{0.01, 0.1, 1, 10}` | line 74 | pilot line 56 | yes |
| RBF SVM `gamma` grid | `{0.1/d, 1/d, 10/d}` | line 74 | pilot line 56 | yes |
| Pilot seed | 11 | line 82 | pilot line 60 | yes |
| Pilot trajectories | 12 plus static and translation controls | line 82 | pilot line 60 | yes |
| Pilot stride and subsampling | stride 1, subsample saved frames for strides 2 and 4 | line 82 | pilot line 60 | yes |
| Training seed namespace | 1000-1039 | line 83 | pilot line 61 | yes |
| Validation seed namespace | 2000-2019 | line 83 | pilot line 61 | yes |
| Exploratory test seed namespace | 3000-3039 | line 83 | pilot line 61 | yes |
| Confirmatory seeds | new test seeds starting at 10000 | line 84 | pilot line 62 | yes |
| Confirmatory test sizes | `{200, 500, 1000, 2000}` base-seed clusters | lines 84, 94 | pilot line 62 | yes |
| Bootstrap resamples | 2000 | lines 35, 96 | pilot line 64 | yes |
| Bootstrap seed | 20260907 | lines 35, 96 | pilot line 64 | yes |
| Noninferiority threshold | 0.02 | lines 23, 25, 90, 94 | pilot lines 62, 70 | yes |
| Superiority threshold | negative 0.05 (pilot writes `-0.05`) | lines 23, 90 | pilot line 70 | yes (same value, prose "negative 0.05") |
| Parsimony factor | fourfold | lines 25, 90 | pilot line 70 | yes |
| Parsimony comparator band | within 0.02 of the best validation result | lines 25, 90 | pilot line 70 | yes |
| Family deterioration bound | 0.05 | lines 29, 90 | pilot line 70 | yes |
| Precision half-width | 0.01 for the 0.02 margin | line 94 | pilot line 62 | yes |
| Abstention calibration | `e` = 95th percentile of adjacent diagram distances | line 100 | pilot line 41; ledger line 280; interface line 105 | yes |
| Efficiency abstention floor | `L <= 2(T - 1)e` | line 100 | pilot line 41; ledger line 280; interface line 105 | yes |
| Comparison-angle floor | `min(a, b) <= 2e` | line 100 | pilot line 41; ledger line 280; interface line 105 | yes |
| Zero-noise abstention | only exact-zero abstention applies | line 100 | pilot line 41; ledger line 281; interface line 105 | yes |
| `L = 0` policy | eta null, `L` reported, flag recorded | line 102 | ledger line 270; interface policy 5, line 103 | yes |
| Zero-step policy | `a = 0` or `b = 0` gives null angle, step unresolved | line 102 | ledger line 274; interface policy 6, line 104 | yes |
| Cosine clip and anomaly | clip to `[-1, 1]`; `abs(z) > 1 + 1e-12` flags | line 102 | ledger line 290; interface lines 79, 106 | yes |
| Frozen environment | Python 3.12.3, numpy 2.4.3, scipy 1.17.1, matplotlib 3.10.8, gudhi 3.12.0, persim 0.3.8, pytest 9.0.3 | line 106 | ledger lines 34-47; `environment.json` package block | yes |
| Bottleneck implementation | `gudhi.bottleneck_distance` | lines 57, 106 | ledger line 99 | yes |
| Result table schema | 20 fields from `run_id` to `status` | line 37 | pilot line 78 | yes |
| Witness control W-06 | equal consecutive distances, equal L, equal R, constant speed, different intermediate order | line 59 | `witness_results.json` case W-06; `run.log` lines 23-35 | yes |

No value was found in the preregistration without a source.

Source values omitted from the preregistration prose are listed in F4. They are the trailing-window pooling grid (pilot line 39: "trailing-window pooling with lengths 1, 3, 5 frames and strides 1, 2, 4", also ledger `input_interface.trailing_window_pooling` lines 73-77 and interface item 8, line 24), the W2 sensitivity branch (pilot line 37: "W2 with the same ground norm is a sensitivity branch after the cheap pilot", also ledger `diagram_metric.sensitivity_branch` lines 116-123 and interface line 123), and pyyaml (ledger line 42: `pyyaml: "available"`; `environment.json` records `"yaml": "6.0.1"`). The first two are explicitly outside the primary frame-level baseline or delegated to the ledger/interface by prereg line 11, and pyyaml is tooling only.

## 3. Check 2: decision-rule equivalence

The GO, INDETERMINATE, INCREMENTAL-ONLY, and PIVOT rules in prereg section 7 (lines 90-94) were compared with pilot section 5 (lines 66-72).

Equivalence holds for the following. Route (a), superiority: prereg line 90 "the upper endpoint of a paired 95% confidence interval for delta lies below negative 0.05" equals pilot line 70 "the upper endpoint of a paired 95% interval for delta is below -0.05". Route (b), parsimony: prereg line 90 "that upper endpoint lies below 0.02 and the compact representation achieves at least a fourfold reduction in feature dimension or measured end-to-end prediction cost relative to the cheapest competitor whose validation macro balanced error lies within 0.02 of the best validation result" equals pilot line 70 verbatim in content. The comparator-set freeze: prereg "The eligible comparator set is frozen before test results are opened" equals pilot "Freeze this eligible comparator set before opening test results". The route freeze: prereg "the superiority-versus-parsimony route is frozen after exploration and before confirmation rather than chosen afterward" equals pilot "Freeze the superiority-versus-parsimony claim after exploration and before confirmation, rather than choosing the favorable route afterward". The weak-incumbent sentence and the family-bound sentence match. The INDETERMINATE, INCREMENTAL-ONLY, PIVOT, and repair sentences are verbatim equivalent (prereg lines 92, pilot line 72). The precision rule (prereg line 94; pilot line 62) is equivalent: one size from `{200, 500, 1000, 2000}`, exploratory paired error variance, 0.01 half-width for the 0.02 margin, cost estimated first, INDETERMINATE if the largest affordable size cannot resolve the margin, no peeking.

**F1 (material, decision-rule non-equivalence).** The preregistration's GO rule includes an extra condition. Prereg line 31 states: "H3 and H4 are safeguards that must also hold for a GO, and neither can substitute for the confirmatory pair." H3 is defined at line 29: "The results are stable across the noise and resolution cells (sigma in {0, 0.05} and strides 1, 2, 4). The directional requirement is that the sign and rough magnitude of delta do not reverse and are not concentrated in particular cells." Pilot line 70 states the complete GO requirement as "correctness and nuisance checks, adequate precision, and either (a) ... or (b) ...", plus the family bound, with no cell-stability condition. Plan WP-3.4 (line 133) matches the pilot: "simulation GO requires the superiority or noninferiority-plus-parsimony rule and family safeguards specified in Pilot_Experiment_Specification.md." The prereg's own section 7 GO sentence (line 90) also omits H3. Consequence: a confirmatory result that satisfies pilot rule (a) or (b) and the 0.05 family bound but whose delta is concentrated in particular cells, or reverses sign across cells, would receive GO under the pilot and plan and no GO under the prereg H3 safeguard. Prereg line 11 says the pilot "govern[s] every numeric pilot value" and that "If this draft disagrees with any of these sources, they govern, and the disagreement is recorded in the deviations log (Section 9) rather than silently resolved"; the deviations log (lines 112-114) is empty. Plan line 159 says the pilot "governs the pilot's executable decisions". H3 is not resolved here. Either H3 must be removed from the prereg's GO requirement, or H3 must be added to the pilot and plan decision rule and recorded. Note also that "rough magnitude" has no operational threshold.

## 4. Check 3: cross-references

Every project-internal file path referenced in the three Phase 0 documents (`preregistration_draft.md`, `assumption_ledger.yaml`, `metric_interface.md`) was extracted and tested against the filesystem. All exist.

| Referenced path | Referenced from | Exists |
|---|---|---|
| `research_review/Pilot_Experiment_Specification.md` | prereg line 11; ledger line 19 | yes |
| `research_review/assumption_ledger.yaml` | prereg line 11; interface line 3; ledger line 3 (self) | yes |
| `research_review/metric_interface.md` | prereg line 11; ledger line 434 | yes |
| `research_review/results/phase0/witness/` | prereg line 11 | yes |
| `src/tk_pilot/witnesses.py` | prereg line 11; ledger line 29; interface line 127 | yes |
| `research_review/Topological_Kinematics_Research_Plan.md` | prereg line 13; ledger line 17; interface line 3 | yes |
| `research_review/foundations.md` | ledger line 21 | yes |
| `research_review/email_proposal_audit.md` | ledger line 23 | yes |
| `research_review/topological_kinematics_witness.py` | ledger line 25; interface line 131 | yes |
| `research_review/results/metric_witness_results.txt` | ledger line 27 | yes |
| `research_review/results/phase0/witness/witness_results.json` | ledger lines 31, 400; interface line 127 | yes |
| `research_review/results/phase0/witness/figures/` | ledger line 401; interface line 127 | yes |
| `research_review/results/phase0/witness/environment.json` | ledger line 402 | yes |
| `src/tk_pilot/diagram_metrics.py` | ledger line 403 | yes |
| `src/tk_pilot/path_diagnostics.py` | ledger line 403 | yes |
| `scripts/run_witness_suite.py` | ledger line 404 | yes |

The four paths specifically requested all exist: `src/tk_pilot/witnesses.py`, `research_review/results/phase0/witness/witness_results.json`, `research_review/results/phase0/witness/figures/` (four PNG files), and `research_review/results/phase0/witness/environment.json`.

The interface's worked-example cross-reference (interface line 131, "the first four diagrams of path A in `research_review/topological_kinematics_witness.py` (lifespan 10)") is accurate: the legacy script defines `path_a = [0.0, 1.0, 2.0, 1.0, 0.0]` and `M = 10.0` at lines 64-68.

No file in the audited documents references `research_review/witness_note.md`, so its absence produces no broken reference.

**F2 (cosmetic).** Ledger lines 30-32 describe `research_review/results/phase0/witness/witness_results.json` with role "Phase 0 witness results, environment metadata, and figure manifest". The file's top-level keys are `suite, gate, scope, seed, summary, cases`; it contains no environment metadata and no figure manifest. Environment metadata is in `environment.json` (ledger line 402) and the figure list is in `run.log` plus the `figures/` directory (ledger line 401). No rule or number depends on this role string.

## 5. Check 4: claim-status agreement

The ledger's `claims_to_estimands` statuses were compared item by item with the plan section 2 table. All ten match exactly.

| ID | Plan section 2 status | Ledger status | Match |
|---|---|---|---|
| C1 | GO under declared metric and conventions | GO under declared metric and conventions | yes |
| C2 | GO as operational definitions; routine mathematically | GO as operational definitions; routine mathematically | yes |
| C3 | Rejected by Kramar et al. Eq. (16), printed p. 10 | Rejected by Kramar et al. Eq. (16), printed p. 10 | yes |
| C4 | Rejected in the broad form by vineyards and dynamic topology literature | Rejected in the broad form by vineyards and dynamic topology literature | yes |
| C5 | Open empirical question; valid as a finite difference of scalar speed | Open empirical question; valid as a finite difference of scalar speed | yes |
| C6 | Unsupported without extra structure | Unsupported without extra structure | yes |
| C7 | Not identified from persistence diagrams alone | Not identified from persistence diagrams alone | yes |
| C8 | Only a portability hypothesis | Only a portability hypothesis | yes |
| C9 | Unproven | Unproven | yes |
| C10 | No | No | yes |

The evidence-required strings also match exactly. The ledger adds `estimand` and `gate` fields not present in the plan table; those are additions, not status disagreements.

## 6. Check 5: language and typography

**Dashes.** A character-level scan of the three Phase 0 documents found zero occurrences of U+2014 (em dash) and zero occurrences of U+2013 (en dash) in each of `preregistration_draft.md`, `assumption_ledger.yaml`, and `metric_interface.md`.

**Forbidden claim language.** Every occurrence of the plan's forbidden phrases was located and classified. No occurrence is a claim violation; all are prohibitions, negation, or claim-status labels.

| Phrase | File and line | Exact context | Classification |
|---|---|---|---|
| physical acceleration | prereg line 19 | "No result may be described as physical acceleration (the reported quantity is a rate of change of an observable speed)" | prohibition |
| physical acceleration | ledger line 180 | `units: "... (formal units only; not physical acceleration)"` | prohibition |
| physical acceleration | ledger line 185 | "Never call this physical acceleration." | prohibition |
| physical acceleration | ledger line 386 | prohibited-language list entry | prohibition |
| physical acceleration | interface line 63 | "It is never called physical acceleration" | prohibition |
| physical acceleration | interface line 201 | "This interface defines no physical acceleration" | prohibition |
| identifies a latent cause | ledger line 387 | prohibited-language list entry: "identifies a latent cause (say observable statistic of the observed diagram path instead)" | prohibition |
| latent cause | prereg line 120 | "never physical identification of a latent cause" | prohibition |
| latent cause | ledger line 361 | C7 claim field: "Diagnostics identify latent physical causes" | claim status being audited, not an assertion |
| latent cause | ledger line 362 | C7 estimand: "Latent-cause labels, which are not recoverable from persistence diagrams alone" | denial |
| latent causes | interface line 197 | "Nothing here defines, recovers, or identifies a latent mechanism." | prohibition |
| canonical kinematics | prereg line 19 | "No result may be described ... as canonical kinematics" | prohibition |
| canonical kinematics | ledger line 389 | prohibited-language list entry | prohibition |
| domain independent | ledger line 367 | C8 claim field: "The collection is domain independent" | claim status being audited, status "Only a portability hypothesis" |
| domain independent | ledger line 390 | prohibited-language list entry: "domain independent (as an established property; portability hypothesis only)" | prohibition |
| domain independence | prereg line 19 | "or as established domain independence" | prohibition |
| new velocity | ledger line 137 | "Not a new velocity; not physical speed; not a metric derivative." | prohibition |
| new velocity | ledger line 391 | prohibited-language list entry | prohibition |
| turning direction | prereg line 19 | "as turning direction (only the symmetric comparison angle is reported, always together with its turn companion)" | prohibition |
| turning direction | ledger line 214 | "Not a turning direction; never report tau alone as if it were an angle." | prohibition |
| turning direction | ledger line 388 | prohibited-language list entry: "turning direction (unqualified)" | prohibition |

The phrase "acceleration" otherwise appears only as the fixed term speed-change rate, inside prohibitions, or in the C10 claim row (plan and ledger) where the theory is rejected.

## 7. Check 6: internal contradiction scan

### 7.1 Ledger policies versus interface edge-case list

The ledger has 12 `policies` entries; the interface has 14 numbered edge-case policies. All 12 ledger policies map to interface items with the same rule; the two extra interface items are the ledger's `diagram_metric.numerical_zero` and `diagram_metric.conditioning` content restated.

| Ledger policy | Interface item | Rule difference |
|---|---|---|
| `essential_classes` (line 234) | 1 (line 99) | none, wording matches |
| `empty_diagram` (line 242) | 2 (line 100) | none; ledger adds the label "Degenerate diagrams:" |
| `diagram_cardinality` (line 250) | 3 (line 101) | none |
| `missing_window` (line 260) | 4 (line 102) | none |
| `l_zero` (line 269) | 5 (line 103) | none |
| `zero_step` (line 273) | 6 (line 104) | none |
| `near_zero_floor` (line 277) | 7 (line 105) | none; identical thresholds and calibration |
| `cosine_clip` (line 288) | 8 (line 106) | none; interface drops the parenthetical rationale, which it keeps in item 14 |
| `matching_ties` (line 296) | 9 (line 107) | none |
| `nonpositive_interval` (line 304) | 10 (line 108) | none |
| `straight_and_reversal_reporting` (line 308) | 11 (line 109) | none |
| `no_selective_deletion` (line 314) | 12 (line 110) | none |
| `diagram_metric.numerical_zero` (line 104) | 13 (line 111) | interface adds the explicit linkage: "The exact-zero abstention in policy 7 refers to the exact `0.0` returned by the identity shortcut." The ledger does not state that linkage in `near_zero_floor`, but its `numerical_zero` field describes the identity shortcut and the tiny positive values. Consistent clarification, not a conflicting rule. |
| `diagram_metric.conditioning` (line 110) | 14 (line 112) | none; interface restates the same conditioning facts and the same `2e` guard |

### 7.2 Preregistration section 8 versus ledger `near_zero_floor` and interface policy 7

Prereg line 100: "The training-only static-noise calibration defines e as the 95th percentile of adjacent diagram distances. Abstain on efficiency when L <= 2(T - 1)e, and abstain on comparison angles when min(a, b) <= 2e; at zero noise, only exact-zero abstention applies. These floors are applied without deleting trajectories: performance is reported with and without the floors, and validity fractions and coverage are reported jointly with performance in every regime."

Ledger lines 279-282 and interface lines 105 state the same calibration, the same two thresholds, the same zero-noise exact-zero rule, and the same joint-reporting requirement. No rule is stated differently. The prereg's added sentence about reporting with and without the floors matches ledger `no_selective_deletion` line 318 ("L = 0, zero-step, and noise-floor cases are flagged or abstained, never dropped").

### 7.3 Matched-speed controls versus plan WP-3.2 and pilot line 21

Prereg line 59: "a matched-speed ordering construction as a correctness control, not a fourth scientific class. The Phase 0 witness suite supplies the equal-speed ordering correctness control (case W-06: equal consecutive distances, equal L, equal R, constant speed, different intermediate order), and a later independently pre-registered control may match movement budgets; that construction must not be selected because it favors a descriptor, and its results stay outside the three-class accuracy calculation."

Pilot line 21: "The return and ramp have deliberately different accumulated latent movement. Do not call this a matched-speed experiment. The existing singleton-diagram script supplies a separate equal-speed correctness control. A later independently preregistered control can match movement budgets; it must not be selected because it favors a descriptor."

Plan WP-3.2 line 129: "Use exactly three scientific classes, a triangular return pulse for reversible restructuring, a monotone ramp for persistent drift, and a jump for a shock. Add a matched-speed ordering construction as a correctness control, not a fourth scientific class."

Plan section 8 line 153: "C3, distinction beyond speed, tested by latent matched-speed reversal and drift controls."

The documents are compatible on the substantive rules: the construction is a correctness control and never a fourth scientific class, its results are not part of the three-class accuracy calculation, and a later matched-movement-budget control must not be selected because it favors a descriptor. The prereg's W-06 claims were verified against `witness_results.json` (equal consecutive distances, equal L = 4, equal R = 0, constant speed 4, differing angle sequences) and `run.log` lines 23-35. The differences are attribution and scope, not rule conflicts (see F5). Plan section 8's "tested by" framing gives matched-speed controls a claim-test role for C3, while WP-3.2 calls the same construction a correctness control and the prereg keeps it outside the primary accuracy calculation; the two roles can coexist only if the C3 test is an information comparison rather than the primary estimand, which the plan does not state explicitly.

## 8. Check 7: witness note scope

`research_review/witness_note.md` does not exist. Per the task instructions it is recorded as pending, so the note-scope checks (operational correctness only, G0 scope statement, 14/14 result, no novelty or utility claim) cannot be performed.

The underlying evidence is present and correct: `witness_results.json` reports `"n_cases": 14, "n_passed": 14, "n_failed": 0, "all_passed": true`, with the scope string "Operational correctness of the frozen finite-metric definitions only; not novelty, not extraction correctness, not utility." `witness_summary.txt` line 3 says "cases passed: 14/14" and line 5 says "verdict: operational correctness only". `run.log` line 107 says "summary: 14/14 cases passed". The note itself, which plan WP-0.2 lists as a required output ("machine-readable test results, figures, and a short witness note"), remains an open WP-0.2 deliverable.

## 9. Check 8: YAML validity and source paths

`assumption_ledger.yaml` parses without error under pyyaml 6.0.1 (safe_load), yielding the 23 top-level keys `schema_version, artifact, file, project, phase, gate, status, date, scope, source_documents, environment, clock_and_timestamps, input_interface, topology_conventions, diagram_metric, diagnostics, policies, claims_to_estimands, prohibited_language, prohibited_language_note, witness_suite, verification, g0_record`.

All eight `source_documents` paths exist: `research_review/Topological_Kinematics_Research_Plan.md`, `research_review/Pilot_Experiment_Specification.md`, `research_review/foundations.md`, `research_review/email_proposal_audit.md`, `research_review/topological_kinematics_witness.py`, `research_review/results/metric_witness_results.txt`, `src/tk_pilot/witnesses.py`, `research_review/results/phase0/witness/witness_results.json`.

All `witness_suite` paths exist: `primary_code`, `primary_results`, `figures/`, `environment`, both `supporting_code` files, `runner`, `legacy_code`, and `legacy_results`.

The ledger `status` and `g0_record.status` are both `pending_verification`, and the verification section states: "Independent verification by a second reader or audit is still pending; see g0_record.status." This audit is that verification input; no ledger claim of a passed gate was found. The prereg's status line "Draft frozen at gate G0" describes the draft's phase, not a declared gate pass, so no contradiction was found.

## 10. Additional consistency checks performed

The witness manifest in `environment.json` records sha256 values for 14 inputs. All 14 recomputed hashes match the current files, including the three Phase 0 documents, the plan, the pilot specification, `src/tk_pilot/witnesses.py`, the runner, and the tests. There is no drift between the artifacts audited here and the versions the witness suite ran against.

`witness_results.json` parses as valid JSON and its 14 case IDs (W-01 through W-14) and per-case pass flags agree with `run.log`, with no failed check in any case. The ledger's `witness_suite.cases` descriptions W-01 through W-14 were each matched to the corresponding case details (including W-03's 60 pairs, W-04's 40 triples, W-11's graph checks, W-13's abstention floors and clock dilation, and W-14's essential-class counts).

## 11. Finding details and options

**F1 (material).** Options without silent resolution: (i) the preregistration deletes the H3 GO linkage and keeps H3 as a reported safeguard only, matching pilot line 70 and plan WP-3.4; or (ii) the pilot specification (and plan WP-3.4 wording) adds the H3 cell-stability requirement to the GO rule, with an operational definition of "rough magnitude", and the change is recorded in the prereg deviations log. Until one is done, the confirmatory decision rule is ambiguous between two documents, and prereg line 11's own rule (deviations recorded, not silently resolved) is not satisfied.

**F2 (cosmetic).** The ledger role string for `witness_results.json` should name results only, since environment metadata and figures are separate ledger-listed artifacts.

**F3 (cosmetic).** The "six speed and speed-change summaries" count should be reconciled with the enumerated compact feature list when the feature schema is frozen; feature dimension feeds directly into the H2 fourfold parsimony comparison. The draft text matches its authoritative source, so this is an inherited ambiguity rather than a draft mismatch.

**F4 (cosmetic).** The omissions are either delegated to the ledger/interface by prereg line 11 or explicitly outside the primary baseline. No action is required for G0, but the prereg could restate them for reader convenience.

**F5 (cosmetic).** The prereg, pilot, and WP-3.2 agree on the control's role; the attribution to Phase 0 W-06 versus the legacy singleton script and the WP-3.2 instruction to add the construction in the G3 DGP should be harmonized in a later edit.

## 12. Limitations

This audit is text-level and evidence-level. It did not re-run the witness suite, the generators (which the pilot states do not exist yet), or any classifier. It did not verify the cited literature, the PDFs, or numeric claims outside the Phase 0 document set. The witness-note check is pending because the file is absent. The finding counts above cover only issues observable from the quoted text and hashed artifacts.

# Re-verification of revision 2 (2026-09-20)

**Purpose.** This section re-audits the repaired revision (preregistration revision 2, ledger and interface revisions, the new `research_review/witness_note.md`, and the 15-case witness suite). It preserves every original finding and all revision-1 evidence above, gives F1 through F5 a resolved/unresolved status, audits the witness note against check 7, re-runs the numeric traceability check over the current preregistration, recomputes all hashes, and issues a final consistency verdict. All computations in this section were performed in this session.

## 13.1 Revision-2 hashes

| File | sha256 | Relation to revision 1 |
|---|---|---|
| `research_review/preregistration_draft.md` | `7cb03316256937d9797b0f068103349f91a20d9139f813786f03d95f18bf0eaf` | changed |
| `research_review/assumption_ledger.yaml` | `bc466438ccb360c6a219474837d3bb10f4b4c5c4369a78fb36f949d3eba2425b` | changed |
| `research_review/metric_interface.md` | `48e9d5977ccc681b8350d6695fa202373dbbe4001defe4561b51c3d2aa07b7ca` | changed |
| `research_review/witness_note.md` | `b4902f1bd83290e76dfae5dbbf58e1490d8ffa9e13f884d8452edf0bc15e35e8` | new file (revision 1: absent) |
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` | unchanged |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` | unchanged |
| `research_review/results/phase0/witness/witness_results.json` | `10c32adb7eb0f30406fff3b7a8eecc9a7eff3688450e6f546e7e0b4f65df2dee` | changed (15 cases) |
| `research_review/results/phase0/witness/environment.json` | `b600ce7d6d9ac79f448983e87fd3c92acbfb5720895fa25c244a9c5a7f395597` | changed |
| `research_review/results/phase0/witness/witness_summary.txt` | `7f696d93f719657310112f131073fa571ce17584619bfacde01e34e0807215be` | changed |
| `research_review/results/phase0/witness/run.log` | `6232b20f97d405150b58693eb374e8b61ce5d0365bd3cc7f268548ebffec8b32` | changed |
| `research_review/results/phase0/witness/figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` | unchanged |
| `research_review/results/phase0/witness/figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` | unchanged |
| `research_review/results/phase0/witness/figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` | unchanged |
| `research_review/results/phase0/witness/figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` | unchanged |
| `research_review/results/phase0/verification/numerical_verification.md` | `0162da047bd8f72d64c4224832cd27ba20eb9074982586ab5f7a6a781787208b` | referenced by the witness note |
| `research_review/results/phase0/verification/second_reader_audit.md` | `df7ad0c869cce646c8b74a43ff3fb2987d64241149c6dbbf33853f00eff28bb6` | referenced by the witness note |
| `research_review/results/phase0/verification/independent_checks.py` | `644066a66141e478453ad6e9db6f97479954ec7dfde0e6536ad7f565823172e2` | referenced by the witness note |
| `research_review/results/phase0/verification/consistency_audit.md` | `a3cf4a3c0470a444bf13ced2135668082a66cbc1d7fca317ca14eb8356c160e7` | this report before this append; the post-append hash is at the end of Section 13.7 |

The plan and the pilot specification are byte-identical to revision 1, so all source-side numeric values used by the original traceability table are unchanged. `environment.json` records 14 hashed inputs, and all 14 recomputed hashes match the current files, so the 15-case run was executed against the revision-2 documents.

## 13.2 Tasks A and B: per-finding status

| ID | Revision-1 severity | Revision-2 status | Basis |
|---|---|---|---|
| F1 | material | RESOLVED | Prereg section 2 now makes H3 a non-binding diagnostic and H4 the pilot's family safeguard; the section 7 GO rule equals pilot section 5. Residual wording note R1. |
| F2 | cosmetic | UNRESOLVED | `assumption_ledger.yaml` line 32 still contains the old role string. The claimed repair is not present in the file. |
| F3 | cosmetic | ACCEPTED, DEFERRED | Prereg line 68 and pilot line 50 still say "six" while five summaries are enumerated. Accepted as an inherited ambiguity to close at the WP-1.2 feature-schema freeze. |
| F4 | cosmetic | RESOLVED | Prereg line 57 now states the 2-Wasserstein sensitivity branch and the trailing-window pooling grid. Residual: pyyaml still not listed in prereg line 106. |
| F5 | cosmetic | RESOLVED | Prereg line 59 now assigns the re-instantiated ordering construction to the plan section 8 C3 information comparison while keeping delta as the primary estimand. |

**Task A, F1 decision-rule re-derivation.** Prereg section 7 line 90 (unchanged) states: "GO to application feasibility requires correctness and nuisance checks, adequate precision, and at least one of two predeclared routes. Route (a), superiority: the upper endpoint of a paired 95% confidence interval for delta lies below negative 0.05. Route (b), parsimony: that upper endpoint lies below 0.02 and the compact representation achieves at least a fourfold reduction ... Neither route may hide a family-specific deterioration above 0.05; family bounds are simultaneous and Bonferroni-adjusted." Pilot section 5 line 70 states the same conditions with the same numeric thresholds, the same comparator freeze, the same weak-incumbent rule, and the same family safeguard. Prereg section 2 line 27 now states: "H3 is a reported stability diagnostic, not an additional GO condition: the GO rule is exactly the pilot specification rule, which requires correctness and nuisance checks, adequate precision, route (a) or (b), and the family safeguard. H3 cannot by itself deny a GO that otherwise satisfies that rule". Prereg line 29 states: "H4 (replication safeguard, part of the GO rule) ... This safeguard is part of the pilot specification's GO requirement: neither route may hide a family-specific deterioration above 0.05". Prereg line 31 now contains only the confirmatory-pair and route-freeze sentences; the revision-1 sentence "H3 and H4 are safeguards that must also hold for a GO" is gone. Plan WP-3.4 line 133 is unchanged and states that simulation GO requires the pilot specification's rule and family safeguards. The GO conditions in prereg sections 2 and 7 are therefore logically equivalent to pilot section 5: correctness and nuisance checks, adequate precision, route (a) or route (b), and the 0.05 family safeguard. The INDETERMINATE, INCREMENTAL-ONLY, PIVOT, and repair statements are unchanged from revision 1 and remain equivalent. F1 is resolved.

Residual R1 (cosmetic). Prereg line 27 adds: "and it may motivate a narrowed claim or a PIVOT at the discretion of the analysis review". This is not a GO condition and cannot deny a GO by itself, but it is not present in the pilot and could be read as discretionary authority to depart from a GO that mechanically satisfies pilot section 5. If strict mechanical equivalence is desired, the clause should be deleted or aligned with the pilot's PIVOT sentence.

**Task B, F2.** The revision note says the ledger role string now reads "Phase 0 witness results" only. The current file says otherwise. Ledger lines 31-32: "path: research_review/results/phase0/witness/witness_results.json" with "role: \"Phase 0 witness results, environment metadata, and figure manifest\"". A grep across the ledger finds exactly two role strings for witness artifacts, line 28 ("saved legacy witness results") and line 32 (the stale string). The ledger's `witness_suite` block does list the three artifacts separately (line 411 primary_results, line 412 figures, line 413 environment), so the inaccuracy is confined to the `source_documents` role string and has no numeric or rule impact. **F2 is unresolved.**

**F3 accepted deferral.** Prereg line 68 and pilot line 50 both say "plus the same six speed and speed-change summaries", while the compact row enumerates mean, standard deviation, and maximum of speed (three) and mean absolute and maximum absolute speed-change (two), a total of five. The user's instruction is to treat this as an accepted inherited ambiguity to be resolved at the WP-1.2 feature-schema freeze. This re-verification accepts that process decision and does not demand a change now, but notes that prereg section 9 freezes "the six representations and their semantics" at G0 and that H2's fourfold parsimony comparison uses feature dimension, so the "six" should be closed before confirmatory test seeds are opened and the closure recorded in the deviations log.

**F4.** Prereg line 57 now contains: "The 2-Wasserstein distance with the same L-infinity ground norm is a sensitivity branch after the cheap pilot, not a primary metric, and no stability constant is transferred between norms." This matches pilot line 37 and ledger `diagram_metric.sensitivity_branch` lines 120-127 plus interface line 125. It also contains: "Trailing-window pooling with lengths 1, 3, 5 frames and strides 1, 2, 4 is a later observation map (WP-2.1); it changes the observation map and is outside the primary frame-level baseline." This matches pilot line 39, ledger `input_interface.trailing_window_pooling`, and interface line 24. The two substantive omissions are closed. The only residue is pyyaml, which appears in the ledger environment (line 42) and `environment.json` but not in prereg line 106's frozen list; this is tooling only and has no decision impact.

**F5.** Prereg line 59 now ends: "When the ordering construction is re-instantiated inside the G3 raw pipeline as directed by the plan, it serves the plan section 8 C3 information comparison as a diagnostic; the primary confirmatory estimand remains delta on the three scientific classes." Plan WP-3.2 line 129 and plan section 8 line 153 are unchanged, and the prereg sentence now states the C3 role explicitly while keeping the correctness-control results outside the primary estimand. The attribution difference (Phase 0 W-06 versus the legacy singleton script) remains, but it changes no rule or estimate.

## 13.3 Task C: witness-note verdict

**File.** `research_review/witness_note.md` exists, 40 lines, sha256 `b4902f1bd83290e76dfae5dbbf58e1490d8ffa9e13f884d8452edf0bc15e35e8`.

**Verdict on the check-7 criteria: PASS**, with one documentation-accuracy observation (R2). Item by item:

1. **Operational correctness only.** Line 3: "This note is a correctness artifact. It is not evidence of novelty, predictive value, data-extraction correctness, or application utility." Line 40: "A passing witness is a correctness artifact, never a result." No contrary claim was found.
2. **Correct G0 scope.** Line 5: "The suite tests the frozen finite-metric definitions of `research_review/assumption_ledger.yaml` and `research_review/metric_interface.md`: finite persistence diagrams, bottleneck distance with the L-infinity ground norm, strictly increasing timestamps, and the derived path diagnostics ... Raw-data extraction belongs to gate G2 and is not tested here." Line 40: "G0 concerns only the restricted operational model ... Passing this suite authorizes no novelty, extraction, prediction, or application claim."
3. **Reports the actual 15/15 result.** Line 3: "The Phase 0 witness suite executes 15 cases and all 15 pass". The current `witness_results.json` summary is `"n_cases": 15, "n_passed": 15, "n_failed": 0, "all_passed": true`, with cases W-01 through W-15 all passed. `run.log` contains 15 `[PASS]` lines and ends "summary: 15/15 cases passed; wall 7.28 s". `witness_summary.txt` records "cases passed: 15/15".
4. **No novelty or utility claim.** The note contains only disclaimers about novelty, utility, prediction, and extraction (lines 3, 25, 40). A phrase scan found no forbidden claim language. The W-06 row explicitly says: "This is an information witness, not a utility claim."
5. **No em or en dashes.** Character scan: 0 occurrences of U+2014 and 0 occurrences of U+2013.
6. **Case-table accuracy.** Every quantitative claim in the case table was checked against `witness_results.json`: W-01 shifts `[0, 0.3, 4.9, 5.0, 5.1, 9.0]` with diagonal transition 5.0; W-03 60 pairs; W-04 40 triples; W-05 40 pairs; W-06 L = 4, R = 0, speeds all 4, angles (pi, 0, pi) and (0, 0, 0); W-09 sweep at eps 1e-4, 1e-6, 1e-8, 1e-10 with angle jump 3.14145 at a 2e-8 perturbation; W-11 150 Euclidean paths and 50 graph metrics; W-12 100 trials with max ratios 0.5855, 0.9974, 0.9976, 0.9549 (rounded in the note to 0.59, 0.997, 0.998, 0.955); W-13 floors and clock dilation; W-15 true-zero non-identical pair, 5e-13 snapped, 2e-12 preserved. All match.
7. **Reproduction claims.** Seed 20260920 appears in `witness_results.json` and `environment.json`; wall time 7.28 s matches "about 7 seconds"; the witness directory contains `witness_results.json`, `witness_summary.txt`, `environment.json`, `run.log`, and four figures; `run_witness_suite.py` line 230 returns 0 only when `all_passed`; the environment list matches `environment.json` (Python 3.12.3, numpy 2.4.3, gudhi 3.12.0, persim 0.3.8, scipy 1.17.1, matplotlib 3.10.8, pytest 9.0.3, ripser null). The three referenced verification artifacts exist.

**R2 (cosmetic, note accuracy).** Witness note line 38 states: "Three independent audits were performed and their findings were repaired and re-audited. ... All findings were repaired". This is not accurate for F2 (unresolved) and F3 (deferred), and the statement is repeated in the ledger verification bullet line 453 ("All audit findings were repaired"). The note's check-7 criteria are still met; the repair-status sentence should be corrected when either document is next edited.

## 13.4 Task D: numeric traceability re-check

The full numeric scan of the current preregistration was re-run. All revision-1 values remain in place with the same sources, since the plan and pilot are unchanged. The values added or clarified by revision 2 trace as follows.

| New or revised value in prereg | Prereg location | Source | Match |
|---|---|---|---|
| H3 cells: sigma in `{0, 0.05}`, strides 1, 2, 4 | line 27 | pilot line 57 | yes |
| Family deterioration bound 0.05 (twice) | line 29 | pilot line 70 | yes |
| 2-Wasserstein with the same L-infinity ground norm | line 57 | pilot line 37; ledger lines 120-127; interface line 125 | yes |
| Trailing-window pooling lengths 1, 3, 5 and strides 1, 2, 4 | line 57 | pilot line 39; ledger `input_interface.trailing_window_pooling`; interface line 24 | yes |
| `WP-2.1` reference | line 57 | plan WP-2.1; interface line 24 | yes |
| Plan section 8 C3 reference | line 59 | plan line 153 | yes |
| Three scientific classes | line 59 | pilot section 1 and stage table | yes |
| Per-cell calibration population `(family, degree, resolution, metric)` | line 100 | ledger lines 283-287; interface line 105 | yes |
| Calibration at `sigma = 0.05` on training-split static-noise trajectories | line 100 | ledger lines 283-287; interface line 105 | yes |
| `e` = 95th percentile of that population, never pooled | line 100 | ledger lines 285-287; interface line 105 | yes |
| Zero-noise regime `sigma = 0`, `e = 0`, only exact-zero abstention | line 100 | ledger lines 287-289; interface line 105 | yes |
| Exact zero under the numerical-zero convention | line 100 | ledger lines 104-113; interface policy 13, line 111 | yes |
| `L <= 2(T - 1)e`, `min(a, b) <= 2e`, `T` the number of intervals | line 100 | ledger lines 289-291; interface line 105 | yes |

No new untraceable value was found. The revision-1 traceability table in Section 2 remains valid in full for every unchanged value, including the horizon and master grid, strides and frame counts, draw ranges, `z(u)`, class programs, Family A and B constants, sigma levels, static z, translation tolerance, learner grids, seed namespaces, test sizes, bootstrap resampling and seed, the thresholds -0.05 and 0.02, the fourfold factor, the 0.01 half-width, and the 0.05 family bound. The prereg's section 8 calibration text now matches the ledger and interface almost verbatim, which also closes the generality gap noted in the revision-1 report.

## 13.5 Re-run checks

1. **YAML validity.** `assumption_ledger.yaml` parses under pyyaml 6.0.1 with 23 top-level keys; all 8 `source_documents` paths exist; all `witness_suite` paths exist.
2. **Claim-status agreement.** C1 through C10 in the current ledger still match the plan section 2 table exactly; the plan is unchanged.
3. **Cross-references.** Every path referenced by the revised prereg, ledger, interface, and witness note exists, including `numerical_verification.md`, `second_reader_audit.md`, `independent_checks.py`, `pyproject.toml`, and the witness evidence files.
4. **Typography and language.** Zero U+2014 and zero U+2013 in the prereg, ledger, interface, and witness note. All forbidden-language occurrences in the three documents remain prohibitions, negations, or claim-status labels; the witness note contains none.
5. **Witness manifest.** All 14 input hashes recorded in `environment.json` match the current files, confirming the 15-case run used revision 2.
6. **Suites and summary.** `witness_results.json`, `run.log`, and `witness_summary.txt` agree on 15/15 with no failed check.

**R3 (cosmetic, process).** The revision-2 edits changed the prereg's hypotheses and abstention text, but the deviations log (prereg lines 112-114) is still the empty placeholder "(to be filled if any change occurs)". Prereg section 9 governs changes; recording the revision-2 repairs there before the confirmatory freeze would complete the audit trail. No test outcomes had been inspected, so the edits themselves are permissible.

## 13.6 New cosmetic observations from this re-verification

| ID | Item | Basis | Recommendation |
|---|---|---|---|
| R1 | H3 discretion clause | Prereg line 27: "it may motivate a narrowed claim or a PIVOT at the discretion of the analysis review" | Delete or align with the pilot PIVOT sentence if strict mechanical equivalence is required |
| R2 | "All findings were repaired" overstatement | Witness note line 38; ledger line 453 | Correct to distinguish F2 (open) and F3 (deferred) |
| R3 | Revision-2 edits not logged | Prereg lines 112-114 | Record the repairs in the deviations log before the confirmatory freeze |
| R4 | Interface output list omits `timestamps` | Interface line 131 lists outputs but not `timestamps`; `PathDiagnostics.as_json()` returns it (`path_diagnostics.py` line 105) | Add `timestamps` to the list at the next interface edit |

## 13.7 Final verdict

The revision-2 repair resolved the only material finding: the preregistration's GO rule is now logically equivalent to pilot section 5, with H3 explicitly non-binding for GO and H4 explicitly the pilot's 0.05 family safeguard. The numeric traceability check passes with no untraceable value. The witness note satisfies check 7 (operational correctness only, correct G0 scope, actual 15/15 result, no novelty or utility claim, no em or en dashes, accurate case table), and the WP-0.2 witness-note deliverable is complete.

Open items are all cosmetic: F2 is unresolved (the ledger role string at line 32 still claims environment metadata and a figure manifest for `witness_results.json`), F3 is an accepted deferral to the WP-1.2 feature-schema freeze, and R1 through R4 are new documentation and process observations. No blocking or material issue remains.

**Final consistency verdict: PASS at gate G0, with one unresolved cosmetic repair claim (F2) and accepted or recommended documentation cleanups.** The only item that contradicts a stated revision-2 repair is F2.

Report sha256 after this append (computed after all edits in this session): see the final line below.

`research_review/results/phase0/verification/consistency_audit.md` post-append sha256 is recorded in the session final message; it cannot be embedded inside itself without changing the value.
