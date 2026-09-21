# Second-reader audit of WP-0.1 (assumption ledger and metric interface)

**Auditor role:** independent second reader, adversarial verification of the WP-0.1 acceptance test.

**Date:** 2026-09-20.

**Task origin:** WP-0.1 verification requirement, "a second reader can compute every quantity from one held-out trajectory using only the ledger and the metric interface document, with no unstated convention" (`Topological_Kinematics_Research_Plan.md`, section 7 WP-0.1; `assumption_ledger.yaml`, `verification.requirement`).

**Files audited (sha256 taken before and after the audit):**

| File | sha256 |
|---|---|
| `research_review/assumption_ledger.yaml` | `5de8eba33543795c64edd7bad433de3f32ffd525b795ea679d8b20ba4fd677f7` |
| `research_review/metric_interface.md` | `5eb194a63cd124a8054b0ff8aaa9a734b8379fa7d3d107c519c66bde79e24b9c` |

**Reference and implementation files also read for tasks B to D (hashes for traceability):**

| File | sha256 |
|---|---|
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` |
| `research_review/preregistration_draft.md` | `a8f679c9ee5b4eff597ee0e30ef342ff58f176f186cca6f2400ee3807c0c5d06` |
| `src/tk_pilot/diagram_metrics.py` | `5bb48c6396beabb7c3529637c490fbcfaa25a47f5bc6e38da3cf244a57f3b199` |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` |
| `src/tk_pilot/witnesses.py` | `bf85e8c53e96f980d3be3c940319e5d6670e1ed9c0bfab893acc65914b58294c` |
| `research_review/results/phase0/witness/witness_results.json` | `2332637a7c99bf130b1d2d543b3dcc88e0ee2c25f88ca6a0532815428e139fde` |

No file was modified except this report. `src/tk_pilot` was not read before the independent Task A computation; it was read and executed only afterwards. The witness suite was not rerun, so its saved `all_passed` status is reported as a read of the saved artifact, not as an independent rerun.

**Severity definitions used:** blocking prevents computation; material changes a number or a validity decision; cosmetic is wording only.

**Findings summary:** 1 blocking (A2, scoped to the noise floor and abstention flags), 1 material (A1, zero-distance/zero-step validity), 6 cosmetic (A3 to A6, C1, D1). All central formulas and all other held-out quantities agree with the documented reading.

**Note added during re-verification of revision 2:** all findings above were subsequently repaired by the project, and this report was re-run against the revised files; see the clearly marked "Re-verification of revision 2" section at the end. The original findings and evidence above are retained unchanged.

---

## Task A. Held-out computation

### A.1 Trajectory

Constructed for this audit and appearing in no project document. Six finite diagrams, irregular strictly increasing timestamps, only one singleton, several multi-point diagrams, distinct birth coordinates and lifespans, and one deliberately true-zero consecutive pair via a point on the diagonal (the exact case named in ledger `diagram_metric.primary.numerical_zero`).

| i | D_i | points | lifespans |
|---|---|---|---|
| 0 | `{(0.0,1.0), (2.0,3.0)}` | 2 | 1, 1 |
| 1 | `{(0.0,1.0), (2.0,3.0), (5.0,5.0)}` | 3 | 1, 1, 0 |
| 2 | `{(0.5,1.5), (2.0,3.0)}` | 2 | 1, 1 |
| 3 | `{(0.5,1.5)}` | 1 | 1 |
| 4 | `{(0.5,1.5), (1.5,3.5), (4.0,8.0)}` | 3 | 1, 2, 4 |
| 5 | `{(0.0,1.0), (1.5,3.5)}` | 2 | 1, 2 |

Timestamps: `t = (0.0, 0.4, 0.7, 1.1, 1.6, 2.3)`, so `T = 5` intervals and `T + 1 = 6` diagrams. Validation rules of `metric_interface.md` section 2 hold: all `d` finite, `b <= d`, strictly increasing timestamps, `T >= 1`.

### A.2 Conventions taken from the documents, and points the documents did not fix

1. **Input and validation** (`metric_interface.md` 2.1 to 2.3): finite multiset of `(b, d)`, `b <= d`, `d` finite, strict increase, rejection of nonpositive `h_t`. Applied without adjustment. Fixed.
2. **Bottleneck distance** (`metric_interface.md` section 5; ledger `diagram_metric`): minimum over partial matchings of the maximum of matched-pair `L-infinity` costs and unmatched-point diagonal costs `(d - b)/2`, diagonal of infinite multiplicity. The general min-over-matchings formula is not written out; it is assumed as the standard definition and is confirmed by the singleton derivation in section 6. Marked cosmetic (A5).
3. **`h_t = t_{t+1} - t_t`, `m_t = (t_t + t_{t+1})/2`, `nu_t = d(D_t, D_{t+1})/h_t`** (section 3.1). Fixed. Computed in double precision, so `0.7 - 0.4 = 0.29999999999999993` and similar; the documents do not require exact decimals.
4. **`L = sum d`, `R = d(D_0, D_T)`, `eta = R/L` defined only when `L > 0`** (section 3.2; ledger `policies.l_zero`). Fixed. Here `L = 5.0 > 0`, so `eta` is defined and no `L = 0` flag is recorded.
5. **Speed-change denominator** (section 3.3; ledger `clock_and_timestamps.speed_change_timestamp`): `a_t = (nu_t - nu_{t-1}) / (m_t - m_{t-1})`, indexed by the later midpoint. Fixed and used for the irregular clock, as required.
6. **Comparison angle** (section 3.4): `theta_t = arccos(clip(z, -1, 1))` with `z = (a^2 + b^2 - c^2)/(2ab)`, `a = d(D_{t-1}, D_t)`, `b = d(D_t, D_{t+1})`, `c = d(D_{t-1}, D_{t+1})`, defined only when `ab > 0`; `tau_t = pi - theta_t`; clip plus cosine-anomaly flag at `|z| > 1 + 1e-12`. Fixed. The formula requires an additional metric call for `c`, which section 5's phrase "computed directly from the distance sequence" does not mention (cosmetic A4).
7. **Triangle excess** (section 3.5; ledger `diagnostics.triangle_excess`): defined on `a + b > 0`, reported as optional. Fixed; reported here.
8. **Zero step** (section 3.4; section 4 policy 6; ledger `policies.zero_step`): "If `a = 0` or `b = 0`, `theta_t` is null and the step is counted as unresolved." The documents do not state whether `a` in this test is the true mathematical distance or the raw backend return, and policy 13 explicitly allows a true-zero non-identical pair to yield "a tiny positive value". This gap is material and is exercised by `D_0` against `D_1`; see finding A1.
9. **Noise floor** (section 4 policy 7; ledger `policies.near_zero_floor`): "Training-only static-noise calibration sets `e` = the 95th percentile of adjacent diagram distances. Abstain on efficiency when `L <= 2(T-1)e`; abstain on comparison angles when `min(a, b) <= 2e`." The percentile population is not further specified (which training trajectories, which family/degree/resolution/noise levels, whether pooled), and no material is given to compute `e` from a held-out trajectory alone. See A2.
10. **Zero-noise branch** (policy 7): "At zero noise, only exact-zero abstention applies." How a second reader decides that a given held-out trajectory is in the zero-noise regime is not specified. Folded into A2.
11. **Missing windows, cardinality, empty diagrams** (section 4 policies 2 to 4). Not triggered by this trajectory; cardinality changes are handled by diagonal matching and all finite bars are retained.
12. **Essential classes** (section 2.4, policy 1; ledger `policies.essential_classes`). None present; no counts to record.
13. **Causality and master grid** (sections 2.7 to 2.9). The trajectory is already a validated diagram path, so these apply to extraction, not to the quantities. The held-out path is deliberately off the master grid; section 3.3 explicitly permits irregular clocks ("For irregular clocks, only the midpoint form is used").
14. **Flag names and serialization** are not specified (the documents say "a flag is recorded", "counted as unresolved", "validity fractions ... reported"); only prose semantics are given. Cosmetic A3.

### A.3 Results under the documented mathematical reading

Independent computation used my own brute-force enumeration of matchings with diagonal copies (code excerpt in appendix), no project code. Pairwise true distances:

| pair | (0,1) | (0,2) | (0,3) | (0,4) | (0,5) | (1,2) | (1,3) | (1,4) | (1,5) | (2,3) | (2,4) | (2,5) | (3,4) | (3,5) | (4,5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d | **0.0** | 0.5 | 0.5 | 2.0 | 0.5 | 0.5 | 0.5 | 2.0 | 0.5 | 0.5 | 2.0 | 0.5 | 2.0 | 1.0 | 2.0 |

Step quantities (documented reading):

| t | h_t | d(D_t, D_{t+1}) | m_t | nu_t |
|---|---|---|---|---|
| 0 | 0.4 | 0.0 | 0.2 | 0.0 |
| 1 | 0.29999999999999993 | 0.5 | 0.55 | 1.666666666666667 |
| 2 | 0.40000000000000013 | 0.5 | 0.9 | 1.2499999999999996 |
| 3 | 0.5 | 2.0 | 1.35 | 4.0 |
| 4 | 0.6999999999999997 | 2.0 | 1.95 | 2.857142857142858 |

Path summaries: `L = 5.0` (defined), `R = 0.5` (defined), `eta = 0.1` (defined, `L > 0`).

Speed-change rates (all defined):

| t | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| a_t | 4.761904761904762 | -1.1904761904761927 | 6.111111111111112 | -1.9047619047619035 |

Interior diagnostics (documented reading):

| t | a | b | c | z | theta_t | tau_t | q_t | status |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 | 0.5 | 0.5 | undefined | undefined (null) | undefined (null) | 0.0 | zero step, unresolved |
| 2 | 0.5 | 0.5 | 0.5 | 0.5 | 1.0471975511965979 | 2.0943951023931953 | 0.5 | defined |
| 3 | 0.5 | 2.0 | 2.0 | 0.125 | 1.4454684956268313 | 1.6961241579629618 | 0.2 | defined |
| 4 | 2.0 | 2.0 | 1.0 | 0.875 | 0.5053605102841573 | 2.636232143305636 | 0.75 | defined |

Documented abstention and flags: cosine-anomaly flag none; `L = 0` flag not applicable; missing-window exclusion not applicable; zero-step unresolved count 1 (t = 1); angle-valid fraction 3/4 = 0.75; noise-floor-based efficiency and angle abstention undetermined for lack of `e` (see A2). Under the zero-noise branch "only exact-zero abstention applies", which under this reading abstains at t = 1.

### A.4 Implementation results

Run with `sys.path` insertion of `src`, with `gudhi.bottleneck_distance` as configured by `tk_pilot.diagram_metrics.bottleneck_gudhi`. Pairwise distances agree with the true values for every pair except (0,1):

| pair | true (my brute force, and persim) | primary gudhi |
|---|---|---|
| (0,1) | 0.0 | **1.686290654524293e-308** (denormal) |
| all others | as in A.3 | identical to true value |

The denormal is deterministic across repeated calls and symmetric in argument order. It differs from both the project brute-force reference (0.0) and `persim.bottleneck` (0.0). The only affected raw library call is `d(D_0, D_1)`.

Full implementation output for this trajectory:

| quantity | implementation value |
|---|---|
| adjacent distances | `[1.686290654524293e-308, 0.5, 0.5, 2.0, 2.0]` |
| interval speeds | `[4.215726636310733e-308, 1.666666666666667, 1.2499999999999996, 4.0, 2.857142857142858]` |
| L, R, eta | 5.0, 0.5, 0.1 |
| speed-change rates | `[4.761904761904762, -1.1904761904761927, 6.111111111111112, -1.9047619047619035]` |
| theta | `[1.5707963267948966, 1.0471975511965979, 1.4454684956268313, 0.5053605102841573]` |
| tau | `[1.5707963267948966, 2.0943951023931953, 1.6961241579629618, 2.636232143305636]` |
| comparison_valid | `[true, true, true, true]` |
| cosine_raw, cosine_anomaly | `[0.0, 0.5, 0.125, 0.875]`, all false |
| triangle excess / valid | `[0.0, 0.5, 0.2, 0.75]`, all true |
| angle-valid fraction | 1.0 |

### A.5 Comparison and the disagreement (finding A1)

Every quantity agrees with the documented reading except the t = 1 triangle. There, `a = d(D_0, D_1)` is `0` mathematically but `1.686290654524293e-308` from the primary backend. Because the implementation tests `a > 0` on the raw value, it computes `theta_1 = arccos(0.0/1.686e-308) = 1.5707963267948966` (pi/2), `tau_1 = pi/2`, marks the step valid, and reports angle-valid fraction 1.0. The documented mathematical reading makes `theta_1` and `tau_1` null and counts one unresolved step (fraction 0.75).

Both readings can be defended from the frozen text, which is the defect:

1. Policy 13 and ledger `numerical_zero` say a true-zero non-identical pair "can also return a tiny positive value" and "the raw value is always recorded", with the calibrated floor `2e` as "the operational guard". Read that way, the implementation follows the raw value and is consistent.
2. The zero-step rule is written as exact equality `a = 0` on `a = d(D_{t-1}, D_t)`, and `d` is defined as a mathematical metric under which this pair has distance exactly zero. Read that way, `theta_1` must be null and the step unresolved.
3. Policy 13 also says "The exact-zero abstention in policy 7 refers to the exact `0.0` returned by the identity shortcut", and policy 7 says that at zero noise only exact-zero abstention applies. For this pair the identity shortcut cannot apply (the diagrams are not identical), so at zero noise there is no guard at all and the two readings diverge without a documented tie-breaker.
4. The documents do not say whether zero-lifespan points must be canonicalized away before a metric call. Removing `(5.0, 5.0)` would make `D_1` identical to `D_0` and force the exact `0.0`; keeping it produces the denormal. Both are consistent with the text, and the choice changes the validity decision.
5. The saved witness suite does not close the gap. W-02 checks the distance value within tolerance 1e-9 and passes for diagonal-only versus empty (gudhi returned exactly 0.0 for that pair); W-08 and W-13 exercise the zero-step and zero-floor policies with an exact singleton metric that never produces a denormal. I verified this by reading `witnesses.py` and the saved `witness_results.json`, not by rerunning the suite.

This is reported as a document/implementation disagreement, not asserted as a code bug. Its impact: one validity decision, two null-versus-number entries (`theta_1`, `tau_1`), one feature (`angle_valid_fraction` 0.75 versus 1.0), and one unresolved-step count. The raw numerical impact on the other quantities is zero at display precision (`L`, `R`, `eta`, and `a_1` are unchanged). The same gap would affect any held-out trajectory containing a consecutive pair with true distance zero but non-identical canonical diagrams, which is exactly the case the ledger names.

### A.6 Noise floor and abstention flags (finding A2)

The definition is present in both artifacts (`metric_interface.md` section 4 policy 7; ledger `policies.near_zero_floor`): `e` is the 95th percentile of adjacent diagram distances from a training-only static-noise calibration. From one held-out trajectory plus the two documents, `e` cannot be computed. The calibration population is not specified (all training trajectories of the family, only the static controls, per degree, per resolution, per noise level, or pooled), and the documents give no rule for declaring a held-out trajectory to be in the zero-noise regime.

Consequences for this trajectory. Efficiency: `L = 5.0`, `T - 1 = 4`, so abstention triggers if and only if `e >= 0.625`. Angles: abstention at t = 1 triggers for every `e >= 0` under the mathematical reading and for every `e > 0` under the raw-value reading; at t = 2 and t = 3 (`min(a,b) = 0.5`) if and only if `e >= 0.25`; at t = 4 (`min(a,b) = 2.0`) if and only if `e >= 1.0`. Thus the required abstention flags are not uniquely determined by the allowed inputs. Under the explicit zero-noise branch (`e = 0`): efficiency is not abstained, and angle abstention is no abstention under the raw-value reading; under the mathematical reading t = 1 is undefined and exact-zero abstention applies there. For the record, computing the 95th percentile on the held-out trajectory's own adjacent distances would give `e = 2.0` and abstain everywhere; that would be leakage and is not the frozen rule.

### A.7 Task A findings

| ID | Finding | Severity |
|---|---|---|
| A1 | True-zero non-identical pair (`D_0`, `D_1`) returns a gudhi denormal `1.686290654524293e-308`; the documents do not fix whether the zero-step test uses the true distance or the raw return, nor whether zero-lifespan points are canonicalized away. Documented reading: `theta_1`, `tau_1` null, one unresolved step, angle-valid fraction 0.75. Implementation: `theta_1 = tau_1 = pi/2`, all steps valid, fraction 1.0. The witness suite does not cover this composition. | Material |
| A2 | `e`, and hence the efficiency and comparison-angle abstention flags, cannot be computed from one held-out trajectory plus the two documents; the training calibration population and the zero-noise regime test are unspecified. Efficiency flips at `e = 0.625`; angles flip at `e = 0.25` and `e = 1.0`. | Blocking for the noise-floor/abstention sub-item; material for the flags themselves |
| A3 | Machine-readable flag names, unresolved-step counter, validity-fraction denominator, and JSON serialization are not specified. | Cosmetic |
| A4 | `metric_interface.md` section 5 says all scalars are "computed directly from the distance sequence", but `theta` and `tau` require the extra non-adjacent distance `c = d(D_{t-1}, D_{t+1})`, a further metric call. | Cosmetic |
| A5 | The general min-over-matchings bottleneck definition is assumed standard and never spelled out; only the singleton case and the diagonal cost are given. | Cosmetic |
| A6 | Input rule 2.1 requires `d` finite, while rule 2.4 and policy 1 remove essential classes before the metric call; the two statements describe raw and validated inputs without saying so. No impact here (no essential classes). | Cosmetic |

---

## Task B. WP-0.1 completeness checklist

Plan section 7 WP-0.1 actions, checked jointly against the ledger and the interface.

| # | WP-0.1 action | Status | Location |
|---|---|---|---|
| 1 | Choose one primary metric for the first study | Present | ledger `diagram_metric.primary` (bottleneck, L-infinity, gudhi 3.12.0), `diagram_metric.sensitivity_branch` marked not primary, `no_threshold_transfer`; interface section 5 |
| 2 | Homology and filtration conventions | Present (joint) | ledger `topology_conventions` (F2, H0 primary, H1 secondary, VR edge-length for A, cubical sublevel sets of `-f` for B) and `input_interface.families`; interface section 1 and item 8 defer extraction to G2 explicitly |
| 3 | Finite-diagram treatment of essential classes | Present | ledger `policies.essential_classes`, `topology_conventions.essential_classes`; interface item 2.4 and section 4 policy 1 (removed before the metric call, counts recorded, extended metric declared and unused) |
| 4 | Regular or irregular timestamps and the exact speed-change denominator | Present | ledger `clock_and_timestamps`; interface items 2.2, 2.3, 3.3 (`a_t = (nu_t - nu_{t-1})/(m_t - m_{t-1})`; irregular clocks use the midpoint form only) |
| 5 | `L = 0` policy | Present | ledger `policies.l_zero` and `diagnostics.eta`; interface 3.2 and policy 5 (null `eta`, `L` reported, flag recorded, no imputation) |
| 6 | Zero-step policy | Present, boundary-ambiguous | ledger `policies.zero_step`, `diagnostics.comparison_angle`, `diagnostics.turn`; interface 3.4 and policy 6. Exact-zero determination is not fixed when the raw distance is a tiny positive value (finding A1) |
| 7 | Missing-window policy | Present | ledger `policies.missing_window`; interface policy 4 (trajectory excluded, count recorded, no interpolation or pooling, no silent deletion) |
| 8 | Diagram-cardinality policy | Present | ledger `policies.diagram_cardinality`; interface item 2.5 and policy 3 (diagonal matching, per-window cardinality recorded, all finite bars retained) |
| 9 | Empty-diagram policy | Present | ledger `policies.empty_diagram`, `topology_conventions.degenerate_diagram`; interface item 2.1 and policy 2 (empty valid, the diagonal itself is empty) |
| 10 | Causal windows | Present | ledger `input_interface.causality`; interface item 2.7 (use only observations at or before `t_i`, trailing detection windows, future observations forbidden) and item 2.8 (single-frame primary) |
| 11 | Claim-to-estimand table | Present | ledger `claims_to_estimands` C1 to C10; interface sections 1 and 7 state the non-claims |

Supplementary check of plan section 13 immediate actions 1 and 2: "freeze one metric and one causal window convention for the first baseline run; do not mix bottleneck, W1, and W2 results in a single claim" is covered by ledger `diagram_metric.primary`, `sensitivity_branch`, `no_threshold_transfer`, `input_interface.primary_window`, and `causality`.

Task B verdict: **present for all 11 items**, jointly covered (several items rely on the ledger; the interface defers extraction conventions to G2 by design). Item 6 and the noise-floor policy wait on the A1 and A2 ambiguities; those are specification gaps, not missing items.

---

## Task C. Claim statuses and language

### C.1 Claim-to-estimand comparison, plan section 2 table versus ledger `claims_to_estimands`

| # | Claim | Plan status | Ledger status | Change, omission, addition, wording |
|---|---|---|---|---|
| 1 | A finite diagram sequence is a metric-valued discrete path | GO under declared metric and conventions | GO under declared metric and conventions | None. Ledger adds an estimand row and gate `G0` |
| 2 | nu, L, R, eta are meaningful summaries | GO as operational definitions; routine mathematically | GO as operational definitions; routine mathematically | None. Ledger adds an estimand and the gate split `G0 for the definitions; G2/G3 for sensitivity analysis` (addition only) |
| 3 | Inter-frame persistence-diagram speed is new | Rejected by Kramar et al. Eq. (16), printed p. 10 | Rejected by Kramar et al. Eq. (16), printed p. 10 | None. Ledger adds "the novelty claim is withdrawn" (consistent) and gate `G1`; accent dropped from "Kramar" (cosmetic) |
| 4 | A trajectory of diagrams is new | Rejected in the broad form | Rejected in the broad form | None. Ledger adds "any intended new decision use must be stated precisely" and gate `G1` (consistent) |
| 5 | Scalar speed-change a_t is useful | Open empirical question; valid as a finite difference of scalar speed | Open empirical question; valid as a finite difference of scalar speed | None. Ledger adds estimand and gate `G3` |
| 6 | theta_t identifies turning or direction | Unsupported without extra structure | Unsupported without extra structure | None. Ledger adds the diagnostic-name instruction and gate `G0`/`G3` |
| 7 | Diagnostics identify latent physical causes | Not identified from persistence diagrams alone | Not identified from persistence diagrams alone | None. Ledger adds estimand and gate `G3 and G4` |
| 8 | The collection is domain independent | Only a portability hypothesis | Only a portability hypothesis | None. Ledger adds gate `G3` |
| 9 | The collection improves a real decision | Unproven | Unproven | None. Ledger adds estimand and gate `G4` |
| 10 | A new calculus or acceleration theory follows | No | No | None. Ledger adds "theory is dormant until evidence earns it" and gate `G5` |

No status was changed, softened, or strengthened; no claim row was omitted; no new claim was added. The additions are estimand and gate columns and ASCII transliterations (nu, eta, Kramar, theta). One documentation observation, not a defect in this artifact pair: the plan uses the labels C1 to C5 in section 8 for a different decomposition (implementation correctness, stability, distinction beyond speed, value beyond the distance matrix, portability), while the ledger's C1 to C10 follow section 2; a reader moving between the documents should not confuse the two label systems. Reported as cosmetic C1.

### C.2 Forbidden and overreaching language scan

Scanned `assumption_ledger.yaml`, `metric_interface.md`, and `preregistration_draft.md` for "physical acceleration", "identifies a latent cause", "turning direction" (unqualified), "canonical kinematics", "domain independent" as an established property, "new velocity", and "solves the direction problem", plus close variants ("latent cause", "domain independence", "turning", "direction", "velocity", "acceleration", "canonical"). Every occurrence found is classified as a prohibition, a quotation of a rejected or unsupported claim, or a benign technical use. No violation was found.

| File and line | Context (abbreviated) | Classification |
|---|---|---|
| ledger 22 | source role "mathematical caveats for speed, length, direction, acceleration, identification" | Neutral topic label; not a claim |
| ledger 105 | "Identical canonical diagrams return exactly 0.0 ..." | "canonical" in canonical-form sense; not "canonical kinematics" |
| ledger 137 | "Not a new velocity; not physical speed; not a metric derivative." | Prohibition |
| ledger 180 | "formal units only; not physical acceleration" | Prohibition |
| ledger 185 | "Never call this physical acceleration. It does not detect a constant-speed change of direction." | Prohibition |
| ledger 199 to 200 | "no orientation, no signed turning, and no turning direction" | Prohibition |
| ledger 214 | "Not a turning direction; never report tau alone ..." | Prohibition |
| ledger 355 | claim "theta_t identifies turning or direction" (C6) | Quotation of a rejected/unsupported claim, status "Unsupported" |
| ledger 367 | claim "The collection is domain independent" (C8) | Quotation, status "Only a portability hypothesis" |
| ledger 379 | "A new calculus or acceleration theory follows" (C10) | Quotation, status "No" |
| ledger 386 to 392 | `prohibited_language` list, including all seven target phrases | Prohibitions (the list itself) |
| ledger 394 | "The word acceleration is allowed only in the fixed term speed-change rate or when quoting a rejected claim." | Prohibition note; wording glitch because the fixed term does not contain the word "acceleration" (cosmetic C1) |
| ledger 422 | W-14 "canonical order" | Canonical-form sense; neutral |
| interface 9 | "None of them is a latent physical cause, a direction, or an acceleration." | Prohibition/scope |
| interface 63 | "It is never called physical acceleration ..." | Prohibition |
| interface 83 | "Neither quantity is a direction ... no signed turning." | Prohibition |
| interface 111 | "Identical canonical diagrams ..." | Canonical-form sense |
| interface 197 | "Nothing here defines, recovers, or identifies a latent mechanism." | Prohibition |
| interface 199 | "no geodesic direction ... not a direction" | Prohibition |
| interface 201 | "This interface defines no physical acceleration ..." | Prohibition |
| prereg 19 | "No result may be described as physical acceleration ... as turning direction ... as canonical kinematics, or as established domain independence." | Prohibition |
| prereg 23, 25, 27, 29 | "direction of interest", "directional requirement", "the direction is" | Statistical direction of an effect; benign technical use |
| prereg 120 | "Two synthetic families cannot establish domain independence ... never physical identification of a latent cause." | Prohibition/limitation |

The phrase "solves the direction problem" appears only in the ledger `prohibited_language` list (line 392). The phrase "new velocity" appears only at ledger line 137 as a prohibition. The phrase "identifies a latent cause" appears only in the ledger list (line 387); the related wording elsewhere is either negated or quoted as a rejected claim.

### C.3 Em dash and en dash scan

A character-level UTF-8 scan (Python) was run over the three files for U+2012 FIGURE DASH, U+2013 EN DASH, U+2014 EM DASH, U+2015 HORIZONTAL BAR, U+2212 MINUS SIGN, U+2E3A TWO-EM DASH, and U+2E3B THREE-EM DASH. Result: **none present** in `assumption_ledger.yaml`, `metric_interface.md`, or `preregistration_draft.md`.

Task C verdict: **PASS**. Claim statuses match the plan section 2 table row by row with no change, omission, or added claim; the only wording differences are ASCII transliterations and added estimand/gate metadata. Language scan clean. No em or en dashes in the three files.

---

## Task D. Worked example verification (`metric_interface.md` section 6)

Setup as documented: four singleton diagrams `D_j = {(s_j, s_j + 10)}` with `s = (0, 1, 2, 1)` and timestamps `t = (0, 0.25, 0.5, 0.75)`. I recomputed the analytic singleton formula from the min-over-matchings definition, independently enumerated the matchings by brute force, and ran the frozen implementation. All 16 listed numbers are confirmed. The table below gives the document value, my independent analytic/brute-force value, and the frozen implementation result (with `gudhi` supplying `d`).

| Quantity | Documented | Independent check | Frozen implementation | Verdict |
|---|---|---|---|---|
| `h_0, h_1, h_2` | 0.25, 0.25, 0.25 | 0.25, 0.25, 0.25 | 0.25, 0.25, 0.25 | Confirmed |
| `d(D_0,D_1), d(D_1,D_2), d(D_2,D_3)` | 1, 1, 1 | 1, 1, 1 (brute force and analytic) | 1.0, 1.0, 1.0 | Confirmed |
| `m_0, m_1, m_2` | 0.125, 0.375, 0.625 | 0.125, 0.375, 0.625 | 0.125, 0.375, 0.625 | Confirmed |
| `nu_0, nu_1, nu_2` | 4, 4, 4 | 4.0, 4.0, 4.0 | 4.0, 4.0, 4.0 | Confirmed |
| `L` | 3 | 3.0 | 3.0 | Confirmed |
| `R = d(D_0,D_3) = min(1,5)` | 1 | 1.0 | 1.0 | Confirmed |
| `eta = R/L` | 0.3333333333333333 | 0.3333333333333333 | 0.3333333333333333 | Confirmed |
| `a_1 = (4-4)/0.25` | 0 | 0.0 | 0.0 | Confirmed |
| `a_2 = (4-4)/0.25` | 0 | 0.0 | 0.0 | Confirmed |
| t = 1: `a, b, c` | 1, 1, 2 | 1, 1, 2 (brute force `c = min(2,5) = 2`) | 1.0, 1.0, 1.9999999999999998 (gudhi for `D_0,D_2`) | Value confirmed analytically; library last-digit note below |
| t = 1: `z` | -1 | -1 | -0.9999999999999996 | Confirmed analytically; see note |
| t = 1: `theta_1` | pi = 3.141592653589793 | 3.141592653589793 | 3.1415926237874707 | Confirmed analytically; see note |
| t = 1: `tau_1` | 0 | 0 | 2.9802322387695312e-08 | Confirmed analytically; see note |
| t = 1: `q_1` | 0 | 0 | 1.1102230246251565e-16 | Confirmed analytically; see note |
| t = 2: `a, b, c` | 1, 1, 0 | 1, 1, 0 (brute force `c = min(0,5) = 0`) | 1.0, 1.0, 0.0 | Confirmed |
| t = 2: `z, theta_2, tau_2, q_2` | 1, 0, pi = 3.141592653589793, 1 | 1, 0.0, 3.141592653589793, 1 | 1.0, 0.0, 3.141592653589793, 1.0 | Confirmed |

Additional claims in section 6 checked: `T = 3` intervals with four timestamps, true; the example is the first four diagrams of path A in `research_review/topological_kinematics_witness.py` with lifespan 10, true (path A is `[0.0, 1.0, 2.0, 1.0, 0.0]`, `M = 10.0`); "gudhi returns 1.0 for each of the three consecutive step distances and 1.0 for the endpoint pair", true in my run; "this example is exact, so no abstention applies", true at `e = 0` because `L = 3 > 0` and all `a, b > 0`.

**Cosmetic finding D1.** The section 6 tables are analytic values. They are not outputs of the frozen implementation, which calls `gudhi` for the non-adjacent distance `c = d(D_0, D_2)` as well and receives `1.9999999999999998`, producing `cosine_raw = -0.9999999999999996`, `theta_1 = 3.1415926237874707`, `tau_1 = 2.98e-08`, `q_1 = 1.11e-16` instead of the table's exact `z = -1`, `theta_1 = pi`, `tau_1 = 0`, `q_1 = 0`. The reproduction paragraph discloses that the values come from the analytic formula and that `gudhi` was used only for the three consecutive step distances and the endpoint pair, and policy 14 explicitly anticipates this conditioning; no table number is wrong. The note is that section 6 does not say in one sentence that the table is analytic while the implementation-level t = 1 values differ in the last digits.

Task D verdict: **PASS**. Every listed number is confirmed; no refutation found; D1 is a cosmetic clarity note only.

---

## Overall verdicts

| Task | Verdict | Basis |
|---|---|---|
| A. Held-out computation | **FAIL on the strict WP-0.1 acceptance test, PASS on the core formulas** | All step and path quantities (`h`, `nu`, `L`, `R`, `eta`, `a`, `q`, and `theta`/`tau` at t = 2, 3, 4) are computable from the two documents and agree with the implementation. The zero step at t = 1 is implementation-dependent (A1), and the noise floor with its abstention flags cannot be computed from the permitted inputs (A2). |
| B. WP-0.1 completeness | **PASS** | All 11 named actions are covered jointly by the ledger and the interface; item 6 and the noise-floor policy carry the A1/A2 specification gaps. |
| C. Claim statuses and language | **PASS** | Row-by-row match with no status change, omission, or added claim; no forbidden-language violations; no em or en dashes. |
| D. Worked example | **PASS** | All 16 listed quantities confirmed; one cosmetic note (D1). |

**Recommended repairs, reported but not applied (no silent repair):**

1. A1: state explicitly whether the zero-step test uses the true mathematical distance or the raw backend return, and whether zero-lifespan points are canonicalized away before metric calls; alternatively, define a tolerance for "exact zero" that does not depend on a library denormal, and state the intended behavior at zero noise.
2. A2: state the exact calibration population for `e` (which trajectories, families, degrees, resolutions, noise levels, and pooling rule) and how a held-out trajectory is assigned to the zero-noise branch; provide the calibration artifact alongside the ledger so the acceptance test inputs are complete.

---

## Appendix. Reproduction details

Commands run for this audit (read-only except for this report):

```
python3 /tmp/opencode/sr_heldout_independent.py      # my brute-force bottleneck + formulas
python3 /tmp/opencode/sr_heldout_impl.py             # frozen implementation, same trajectory
python3 /tmp/opencode/sr_worked_example.py           # Task D, analytic + implementation
python3 -c "... gudhi/persim/bruteforce on (D0,D1) ..."   # raw-backend cross-check
```

Independent bottleneck distance used in Task A (all points matched or sent to the diagonal; cost of an unmatched point is `(d - b)/2`; matched-pair cost is the L-infinity distance):

```python
def bottleneck(P, Q):
    n, m = len(P), len(Q)
    best = float("inf")
    for k in range(0, min(n, m) + 1):
        for ps in itertools.combinations(range(n), k):
            for qs in itertools.permutations(range(m), k):
                cost = 0.0
                for i, j in zip(ps, qs):
                    cost = max(cost, max(abs(P[i][0] - Q[j][0]), abs(P[i][1] - Q[j][1])))
                for i in range(n):
                    if i not in ps:
                        cost = max(cost, (P[i][1] - P[i][0]) / 2.0)
                for j in range(m):
                    if j not in qs:
                        cost = max(cost, (Q[j][1] - Q[j][0]) / 2.0)
                best = min(best, cost)
    return best
```

Raw-backend cross-check for the affected pair, frozen environment:

```
gudhi 3.12.0, numpy 2.4.3, persim 0.3.8, scipy 1.17.1
bottleneck_gudhi(D0, D1) = 1.686290654524293e-308   (D0 = [(0,1),(2,3)], D1 = D0 + [(5,5)])
bottleneck_gudhi(D1, D0) = 1.686290654524293e-308   (symmetric, repeatable)
bottleneck_bruteforce(D0, D1) = 0.0
bottleneck_persim(D0, D1) = 0.0
raw gudhi on diagonal-only vs empty = 0.0
```

Saved witness-suite status (read from `witness_results.json`, not rerun): 14 of 14 cases passed; W-02 `gudhi` list `[0.0, 5.0, 0.25, 0.0]`; W-08 zero steps computed with the exact singleton metric; W-13 zero-floor check computed with the exact singleton metric and contains no true-zero adjacent pair.

---

# Re-verification of revision 2

**Date:** 2026-09-20, same session, after the project repairs listed in the re-verification request.

**Scope:** Tasks A to E were re-run against the current files. The original findings and evidence above are retained unchanged. No project file was modified except this report. The re-checked implementation functions were read only after the re-computation, as before.

**Current hashes (revision 2, computed in this session):**

| File | sha256 | Changed since original audit |
|---|---|---|
| `research_review/assumption_ledger.yaml` | `bc466438ccb360c6a219474837d3bb10f4b4c5c4369a78fb36f949d3eba2425b` | yes |
| `research_review/metric_interface.md` | `48e9d5977ccc681b8350d6695fa202373dbbe4001defe4561b51c3d2aa07b7ca` | yes |
| `research_review/preregistration_draft.md` | `7cb03316256937d9797b0f068103349f91a20d9139f813786f03d95f18bf0eaf` | yes |
| `src/tk_pilot/diagram_metrics.py` | `4d22315d5ea871d8d6afa321c70e7a593a7b149cc1d8654b93047b053b288044` | yes |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` | no |
| `src/tk_pilot/witnesses.py` | `3fa010ec2c80ad3bda4bbb490634af801868a26ce04b95121a21c783fea1130b` | yes |
| `research_review/results/phase0/witness/witness_results.json` | `10c32adb7eb0f30406fff3b7a8eecc9a7eff3688450e6f546e7e0b4f65df2dee` | yes |
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` | no |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` | no |

## Per-finding status

| Prior finding | Status | Evidence verified in this session |
|---|---|---|
| A1 zero-step determination for a true-zero non-identical pair | **Resolved** | Interface policy 13 and ledger `diagram_metric.primary.numerical_zero` declare `NUMERICAL_ZERO = 1e-12`; `src/tk_pilot/diagram_metrics.py` applies `_snap` in all public metric functions. `bottleneck_gudhi`, `bottleneck_persim`, and `bottleneck_bruteforce` now all return exactly `0.0` for my held-out pair (`D_0` vs `D_0 + (5,5)`). The frozen implementation now matches my documented reading exactly: `theta_1` and `tau_1` null, `comparison_valid[0] = false`, `angle_valid_fraction = 0.75`, `nu_0 = 0.0`. See the agreement table below. |
| A2 noise-floor calibration population and zero-noise regime | **Resolved** | Interface policy 7 and ledger `policies.near_zero_floor` now define the population per cell `(family, degree, resolution, metric)` as the adjacent diagram distances on the training-split static-noise trajectories at `sigma = 0.05`, never pooled across cells, with `sigma = 0` the declared zero-noise regime where `e = 0` and only exact-zero abstention applies using the policy 13 value. The preregistration draft section 8 and section 4, and the ledger `witness_suite` metadata, were updated consistently. Residual minor notes are R2 and R3 below. |
| A3 machine-readable outputs unspecified | **Resolved** | Interface section 5 now has a "Machine-readable outputs" paragraph naming every quantity, the `NaN`/`null` convention, unresolved-step counts as the complement of `comparison_valid`, and `angle_valid_fraction` as valid angles divided by `T - 1`. Micro-note: the JSON key `timestamps` is carried by `as_json()` but is not named in that paragraph. |
| A4 `theta`/`q` need the non-adjacent distance | **Resolved** | Interface section 5 now states that `theta_t` and `q_t` also need `c = d(D_{t-1}, D_{t+1})`, one further metric call per interior time. |
| A5 general bottleneck definition omitted | **Resolved** | Interface section 5 now gives the min-over-bijections definition with diagonal copies, the L-infinity point cost, and the `(d - b)/2` diagonal cost. |
| A6 raw versus validated inputs | **Resolved** | Interface item 2.1 now states that raw inputs may contain essential classes with `d = +inf`, removed by item 4, so every metric always sees finite diagrams. |
| D1 worked-example analytic-versus-implementation note | **Resolved** | Interface section 6 now contains a note stating the tables are analytic, that the implementation receives `1.9999999999999998` for `c = d(D_0, D_2)`, and quoting `z = -0.9999999999999996`, `theta_1 = 3.1415926237874707`, `tau_1 = 2.98e-08`, `q_1 = 1.11e-16`. I re-ran the implementation and reproduced those exact values. |

## Held-out computation, revision 2

Documented reading now includes the declared snap (a computed distance at or below `1e-12` is `0.0`), independently reproduced with my own brute-force bottleneck plus the snap. The documented reading and the frozen implementation now agree on every quantity:

| Quantity | Documented reading (with snap) | Frozen implementation |
|---|---|---|
| adjacent distances | `[0.0, 0.5, 0.5, 2.0, 2.0]` | `[0.0, 0.5, 0.5, 2.0, 2.0]` |
| `nu` | `[0.0, 1.666666666666667, 1.2499999999999996, 4.0, 2.857142857142858]` | identical |
| `L`, `R`, `eta` | `5.0`, `0.5`, `0.1` | identical |
| `a` | `[4.761904761904762, -1.1904761904761927, 6.111111111111112, -1.9047619047619035]` | identical |
| `theta` | `[null, 1.0471975511965979, 1.4454684956268313, 0.5053605102841573]` | identical |
| `tau` | `[null, 2.0943951023931953, 1.6961241579629618, 2.636232143305636]` | identical |
| `q` | `[0.0, 0.5, 0.2, 0.75]` | identical |
| `comparison_valid` | `[false, true, true, true]` | identical |
| `angle_valid_fraction` | `0.75` | `0.75` |

Zero-step quantity: determined. The true-zero pair is snapped to exactly `0.0`, so the zero-step rule applies at `t = 1` and the step is unresolved, as the mathematical reading required.

Noise-floor quantity: the definition is now complete. For this noiseless held-out trajectory the declared zero-noise branch (`sigma = 0`) gives `e = 0`; efficiency is not abstained (`L = 5.0 > 0`), and exact-zero abstention applies at `t = 1` only (`min(a, b) = 0`), which coincides with the null angle there. If the trajectory were instead assigned to a `sigma = 0.05` cell, `e` would be that cell's training percentile, still requiring the training artifact by design; the definition, not the trajectory, is what the freeze supplies.

## Task E. Witness case W-15

`W-15` exists in `witness_results.json`: the suite reports `n_cases = 15`, `n_passed = 15`, and W-15 has six checks, all passed. I also executed `witnesses.case_numerical_zero_tolerance` directly in this session and all six checks returned true: gudhi, persim, and brute force give exactly `0.0` for the true-zero non-identical pair; a `5e-13` distance is snapped to exactly `0.0`; a `2e-12` distance is preserved (`2.000177801164682e-12`); and gudhi and brute force agree above the tolerance. The case uses the public metric functions, and the true-zero pair is exactly my held-out pair.

## Worked-example re-check (Task D)

The section 6 analytic tables are unchanged (`h = 0.25`, `d = 1,1,1`, `m = 0.125, 0.375, 0.625`, `nu = 4,4,4`, `L = 3`, `R = 1`, `eta = 1/3`, `a_1 = a_2 = 0`, `theta_1 = pi`, `tau_1 = 0`, `q_1 = 0`, `theta_2 = 0`, `tau_2 = pi`, `q_2 = 1`), and the new note matches the D1 finding exactly. The implementation-level t = 1 values are still conditioning-limited (`theta_1 = 3.1415926237874707`, `tau_1 = 2.98e-08`, `q_1 = 1.11e-16`) because `c = 1.9999999999999998` is far above the snap tolerance and is preserved. Task D remains PASS.

## Residual findings after revision 2

| ID | Finding | Severity | Status relative to original audit |
|---|---|---|---|
| R1 | The declared numerical-zero snap makes the frozen distance a tolerance-pseudometric, so the unqualified invariants `R <= L` and `0 <= eta <= 1 when L > 0` (interface 3.2; ledger `diagnostics.R.observable_status` and `diagnostics.eta.observable_status`; plan WP-2.2 verification) can fail inside the `1e-12` tolerance band. Witnessed in this session with `A = {(0,1)}`, `B = {(1e-12, 1+1e-12)}`, `C = {(2e-12, 1+2e-12)}`: raw distances are `d(A,B) = 1.000088900582341e-12`, `d(B,C) = 1e-12`, `d(A,C) = 2e-12`, and the raw triangle inequality holds (`2e-12 <= 2.0000889e-12`). After the snap, `d(B,C) = 0.0` while `d(A,B)` and `d(A,C)` are preserved, so the frozen path has `L = 1.000088900582341e-12`, `R = 2e-12`, `R > L`, and `eta = 1.99982221464054 > 1`. This is a new inconsistency introduced by the repair, not a remaining ambiguity: the snap policy is clear, but the invariant statements need a tolerance qualification. It does not affect the held-out trajectory (distances are `0` or `>= 0.5`) or pilot-scale data, and it is a corner case inside the declared tolerance band. Possible repairs: qualify the invariants as holding up to the numerical-zero tolerance, or snap path aggregates consistently with the legs. | Material (narrow, corner case; not blocking) | New in revision 2 |
| R2 | The percentile convention for `e` is not specified; the implementation uses `np.percentile` default linear interpolation. Different standard quantile definitions of "the 95th percentile" of a finite sample give different `e`. | Cosmetic (definition complete otherwise; can change `e` in principle) | Residual from A2 |
| R3 | Ledger `verification.how_met` (line 453) states "the repaired set was re-audited", while `g0_record.status` is still `pending_verification`, and the two companion audits in the verification directory list the pre-repair hashes (`consistency_audit.md` lines 15 to 17; `numerical_verification.md` lines 43 to 44). This re-verification is the first audit of the revision-2 hashes. | Cosmetic (status wording) | New observation |

Additional minor notes, not counted as findings: the interface "Machine-readable outputs" paragraph does not name the `timestamps` key carried by `as_json()`; the pilot specification line 41 retains the older, less explicit phrasing "For each training-only static-noise calibration" but is compatible with the per-cell population now frozen in the ledger, interface, and preregistration draft.

## Task B re-check (completeness)

Re-read against the current files. All 11 WP-0.1 actions remain present and jointly covered, with the same locations as in the original checklist. The two items that carried specification gaps now pass without qualification: item 6 (zero-step) is fully determined through interface 3.4, policy 6, and the new policy 13 numerical-zero convention, and the noise-floor policy that complements item 5 now names its calibration population and zero-noise regime. Task B remains **PASS**.

## Task C re-check (claims and language)

The ledger `claims_to_estimands` block is unchanged from the original audit and still matches the plan section 2 table row by row: no status change, omission, addition, softening, or strengthening. The language scan was re-run on the three current files (`assumption_ledger.yaml`, `metric_interface.md`, `preregistration_draft.md`): every occurrence of the seven target phrases is a prohibition, a quotation of a rejected or unsupported claim, or a benign technical use; no violation was found, including in the updated preregistration section 8. A fresh character-level scan found no em dash or en dash in any of the three files. Task C remains **PASS**.

## Final verdict (revision 2)

| Task | Verdict revision 2 | Note |
|---|---|---|
| A. Held-out computation | **PASS** | Zero-step and noise-floor quantities are now determined; documented reading and implementation agree on every held-out quantity. One material corner-case invariant issue remains (R1), outside the held-out trajectory. |
| B. WP-0.1 completeness | **PASS** | All 11 actions covered; both former gaps closed. |
| C. Claim statuses and language | **PASS** | Statuses unchanged; language clean; no em or en dashes. |
| D. Worked example | **PASS** | Analytic tables unchanged; the new D1 note matches my finding. |
| E. Witness W-15 | **PASS** | Exists, six of six checks pass in the saved suite and when executed directly. |

**WP-0.1 second-reader acceptance test: PASS on revision 2, with 0 blocking and 1 material (narrow) residual finding (R1) and 2 cosmetic residuals (R2, R3).** The R1 issue does not affect the held-out acceptance computation or pilot-scale distances; it falsifies the unqualified `R <= L` and `0 <= eta <= 1` statements only for inputs whose distances fall inside the declared `1e-12` numerical-zero band.

## Reproduction commands for this re-verification

```
python3 /tmp/opencode/sr_rev2.py        # W-15 direct execution, held-out (doc + impl),
                                        # worked example, residual R<=L probe
```

The W-15 direct execution calls `witnesses.case_numerical_zero_tolerance` imported from the current `src/tk_pilot/witnesses.py` (hash `3fa010ec...`) and checks all six returned checks. The residual probe uses both my independent raw brute force and the public snapped metric functions. The saved `witness_results.json` (hash `10c32adb...`) was read, not rewritten.

End of audit (revision 2).


