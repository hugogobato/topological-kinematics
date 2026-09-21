# Fresh-eyes final audit of the Phase 0 / G0 freeze

**Date.** 2026-09-20 (session date; the frozen run was generated 2026-09-21T00:05:36Z).

**Auditor.** Fresh-eyes final auditor, independent of the three prior verification rounds. No project file was modified except this report. Temporary scripts were written to `/tmp/opencode/` only.

**Scope.** Verify the G0 decision record against the frozen artifact set, reproduce the witness suite and unit tests, independently recompute the new W-03 and W-15 values, audit the numerical-zero policy and its pseudometric consequence, check cross-document consistency and decision-rule equivalence, verify the witness note numbers, recompute all hashes, and search for stale or overreaching claims.

---

## 1. Audited revision and file hashes

All sha256 values below were recomputed in this session with `hashlib.sha256`.

### 1.1 Inputs hashed by `environment.json` (the runner's `HASHED_INPUTS`, 16 entries)

| File | sha256 |
|---|---|
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` |
| `research_review/assumption_ledger.yaml` | `f1279ead1915054b18209e2ab6e16902a712241ae606c44a623b247457d3a7f0` |
| `research_review/metric_interface.md` | `15bcf67bb0f76861018fa031034649c998262bccfb7a51f2f4ad5ff3a127bd55` |
| `research_review/preregistration_draft.md` | `d7bb54eb6ea1ae8870c3a71855d131faa0a8b5065b30b7c3b723c2ab85fc57ee` |
| `research_review/witness_note.md` | `6df4e151401c90cf1c2b5e2ca2168556621632df30e2dc991eeab5badf3c87e0` |
| `research_review/results/phase0/G0_decision.md` | `adbc63ea69e3e204ea5ab95a4a46b5d096abcffdf12cb2430d242c22ea4980ea` |
| `research_review/topological_kinematics_witness.py` | `c70e1c486465f91b8d91a663a081db779ce7438e0330b860732e0062557479d9` |
| `src/tk_pilot/diagram_metrics.py` | `4d22315d5ea871d8d6afa321c70e7a593a7b149cc1d8654b93047b053b288044` |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` |
| `src/tk_pilot/witnesses.py` | `3c992fd087f67bb4dc7554b05598e720fad953e4ce1b58cc1efaf37fd1e1b544` |
| `src/tk_pilot/witness_figures.py` | `a5129ab3715398134498232c1917027ec8db2173cae8170b2684f2847e23d2a3` |
| `scripts/run_witness_suite.py` | `e9cda7ae9bc4ceb5e60c6dfaf903f27822c89647b9d1f06117d5e78f7acb8738` |
| `tests/test_diagram_metrics.py` | `48e2d5a4ef33f2cd84fc17d11c7b03afa9a4a7026b661d90ec23b608fc98f3dc` |
| `tests/test_path_diagnostics.py` | `09f755f9e91b3f0d48a87626cb976e1284a2748f703a374b30d1284a3c06279b` |
| `tests/test_witnesses.py` | `cb73c5185380f5ad73f99c92f6e4cbcd6ef56a288cab9370d76362e9e0ec0785` |

### 1.2 Witness outputs and figures (not hashed by `environment.json`)

| File | sha256 |
|---|---|
| `.../witness/witness_results.json` | `581ce1e2810029d6106d29691e2e73d39bff634835ecdf7acb0fb47a1b39ca40` |
| `.../witness/witness_summary.txt` | `7f696d93f719657310112f131073fa571ce17584619bfacde01e34e0807215be` |
| `.../witness/environment.json` | `ac98e45ee353f7d3db714ccd03bca7d944017c07ce7df498d6db09bd109c74ac` |
| `.../witness/run.log` | `af1b24fe90c67ad1b4640b6a5d4a79efc8c1fdff230f905f85dec4dbbbd737ba` |
| `.../witness/figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` |
| `.../witness/figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` |
| `.../witness/figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` |
| `.../witness/figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` |

### 1.3 Verification artifacts (not hashed by `environment.json`; expected)

| File | sha256 |
|---|---|
| `.../verification/numerical_verification.md` | `d09d7fb1fedcfd428ff9cd659b43c84c4ec17b6dc7f6cf3a18f76fba4e2fa53e` |
| `.../verification/second_reader_audit.md` | `798177e4f5365c440f88eb2a3313374317a6e601810d04e3744e7574805cd549` |
| `.../verification/consistency_audit.md` | `b399b8c1054b6d55bced92b48bbc81d17db495cb306ab93d4a39f110031bc660` |
| `.../verification/independent_checks.py` | `045b4a17d1307f5b7da30bbb153cf7920b11684fc6ba7a8c9926f64d029332b6` |

**Hash stability result.** All 16 `environment.json` input hashes recompute exactly; zero mismatches. The archived revision-2 hash tables inside the three verification reports do not match the frozen files for `src/tk_pilot/witnesses.py`, `scripts/run_witness_suite.py`, `witness_results.json`, `environment.json`, and `run.log`; this is finding F3, and it is expected that the verification reports themselves are not hashed by `environment.json`.

---

## 2. Commands run

```
/usr/bin/python3 -c "<sha256 check against environment.json input_sha256>"        # all 16 OK
/usr/bin/python3 scripts/run_witness_suite.py --out /tmp/opencode/final_witness  # 15/15, then crash (F2)
/usr/bin/python3 scripts/run_witness_suite.py --out /tmp/opencode/final_witness2 # repeat, EXIT=1 (F2)
/usr/bin/python3 -m pytest                                                        # 34 passed in 10.94s
/usr/bin/python3 /tmp/opencode/audit_checks.py                                    # own bottleneck enumerator, W-03, W-15, R-L
/usr/bin/python3 /tmp/opencode/verify_note_and_bound.py                           # witness note numbers, pseudometric probes
/usr/bin/python3 -c "<run_all(seed=20260920) compared case-by-case to frozen JSON>"  # equality True
```

---

## 3. Task 1: G0 decision record against the artifact set

Every sentence of `G0_decision.md` was checked against the artifacts.

1. **Decision and scope.** The PASS, the restriction to the finite-metric operational model, and the authorization limited to WP-1.1 and WP-1.2 all match plan lines 97, 105-115 and the `g0_record` scope and status in `assumption_ledger.yaml` (lines 466-481). Supported.
2. **What G0 does not cover.** Matches the ledger and interface scope paragraphs and the plan gate map. Supported.
3. **Evidence item 1 (WP-0.1 artifacts).** All three documents exist with the described content. Supported.
4. **Evidence item 2 (WP-0.2 artifacts and 15/15).** The files exist; the frozen `witness_results.json` summary is `n_cases = 15, n_passed = 15, n_failed = 0, all_passed = true`; the frozen `environment.json` records the package versions and 16 input hashes. Supported (also re-reproduced in this session, section 4).
5. **Evidence item 3 (independent numerical verification).** The report and script exist; the report's top-level verdict is 10/10 PASS with a 540-path sweep. The two bounded observations described in the decision (raw library input-order sensitivity covered by W-03; numerical-zero tolerance making the metric a pseudometric at 1e-12) are both present in the report. Supported, with the caveat that its stated counts and hashes are stale relative to the frozen files (F3), and its "no violation" statement is tolerance-qualified (F6).
6. **Evidence item 4 (second-reader audit).** The report exists and its revision-2 verdict is PASS with one narrow material residual (R1) that the final freeze attempted to repair by adding the 2e-12 qualification. The decision's claim that the zero-step and calibration-population gaps were repaired and the acceptance test passes is accurate. Supported, subject to F1.
7. **Evidence item 5 (consistency audit).** The report exists; the revision-2 verdict is PASS with the GO-rule equivalence confirmed and the inherited count ambiguity recorded in the deviations log. The decision's sentence matches the report and the deviations log entry. Supported.
8. **Pass criteria applied.** Matches plan WP-0.1 ("PASS if all terms are total or explicitly undefined with a policy; FAIL if a proposed quantity changes meaning across datasets") plus the WP-0.2 verification items; each listed degenerate case has a witness (W-02, W-08, W-09, W-13, W-14). Supported.
9. **Recorded limitations.** All four limitation sentences are consistent with the frozen documents and this session's computations. Supported.

**Unsupported sentences.** None in the pass/decision sense. One precision issue is recorded as F6 (the sweep sentence omits the tolerance qualifier that the verifier itself used).

---

## 4. Task 2: witness suite and unit tests reproduced

**Suite.** The mandated command `scripts/run_witness_suite.py --out /tmp/opencode/final_witness` printed 15 `[PASS]` lines and `summary: 15/15 cases passed; wall 6.99 s`, then crashed before writing the JSON artifacts (F2). A direct `run_all(seed=20260920)` call returned 15/15, and its sanitized case records are exactly equal to the cases stored in the frozen `witness_results.json`. The fresh transcript is identical to the frozen `run.log` except that the four `figure:` lines are missing because of the F2 crash.

**Unit tests.** `/usr/bin/python3 -m pytest` reports `34 passed in 10.94s` (17 diagram-metric, 13 path-diagnostic, 4 witness tests).

**Independent W-03 recomputation** (own enumerator written from scratch, plus persim and raw library calls):

| Quantity | Value |
|---|---|
| Own exact bottleneck enumerator | `0.8980590011828029` |
| `persim.bottleneck` | `0.8980590011828029` |
| Public canonicalizing API (`bottleneck_gudhi`) | `0.8980590011828029` |
| Public API with rows reversed | `0.8980590011828029` (invariant) |
| Raw `gudhi.bottleneck_distance` on the as-given order | `0.8994791936886859` |
| Raw value overestimate | `1.420192505883e-3` (about 1.4e-3, as the witness note states) |
| All 576 row permutations of the raw call | exactly two values, `{0.899479193688686: 72, 0.898059001182803: 504}` |

All seven W-03 checks are supported by this recomputation.

**Independent W-15 recomputation** (own enumerator and all four public wrappers):

| Probe | Own computation | Public result |
|---|---|---|
| True-zero non-identical pair `[[0,1],[2,3]]` vs `[[0,1],[2,3],[5,5]]` | `0.0` | `0.0` from gudhi, persim, brute-force, and 2-Wasserstein wrappers |
| Singleton shift `5e-13` | raw `5e-13`, snapped `0.0` | `0.0` from all four wrappers |
| Singleton shift `2e-12` | `2.000177801164682e-12` | preserved by all four wrappers |

The raw primary backend does return a denormal `1.686290654524293e-308` for the true-zero pair, exactly as the policy text states.

---

## 5. Task 3: numerical-zero policy end-to-end and the pseudometric consequence

The policy itself is verified end-to-end: snap at or below `1e-12`, preserve above, true zero returns exactly `0.0` through every public backend. The three-point E2 arithmetic in `numerical_verification.md` is correct: `R - L = 2.000177801164682e-12 - 1.0999999999998e-12 = 9.001778011646823e-13 <= 2e-12`. The second-reader triple also satisfies the single-triangle bound: `R - L = 9.99911099417659e-13 <= 2e-12`.

However, the blanket "up to `2 * NUMERICAL_ZERO`" wording now frozen in three documents is false as a general path statement, and it is also wrong when attached to `eta`. This is finding F1, with these minimal reproductions through the public API (`compute_path_diagnostics` with the default snapped metric):

1. **`eta` exceeds 1 by far more than 2e-12 at T = 2 intervals** (the second-reader R1 witness): `A = {(0,1)}`, `B = {(1e-12, 1+1e-12)}`, `C = {(2e-12, 1+2e-12)}`. Adjacent distances `[1.0000889005823406e-12, 0.0]`, `L = 1.0000889005823406e-12`, `R = 1.9999999999999996e-12`, `eta = 1.9998222146405402`.
2. **`R - L` exceeds 2e-12 at T = 4 intervals:** singleton diagrams at births `[0, 2^-40, 2*2^-40, 3*2^-40, 3*2^-40 + 2e-12]` (lifespan 10) give snapped adjacent distances `[0, 0, 0, 2.000177801164682e-12]`, `L = 2.000177801164682e-12`, `R = 4.728661906483467e-12`, `R - L = 2.7284841053187847e-12`, `eta = 2.364120781527531`.

The correct general statements are `R - L <= T * NUMERICAL_ZERO` for a path with `T` intervals (the observed 2.73e-12 is within the `T = 4` bound of 4e-12) and `eta <= 1 + T * NUMERICAL_ZERO / L`; the single-triangle bound `2 * NUMERICAL_ZERO` remains valid. The three affected locations are ledger lines 164-167 and 177-180, interface lines 51 and 111, and witness note line 36. The E2 witness cited by interface policy 13 does exhibit the single-triangle bound correctly, so the pointer is right; the overreach is the general wording around it. Severity is material, not blocking: every affected input lies inside the declared 1e-12 numerical band, no stored witness case is affected, and pilot-scale distances are unaffected.

---

## 6. Task 4: cross-document consistency

**Numerical zero.** Ledger `diagram_metric.primary.numerical_zero` (lines 104-113), interface policy 13 (line 111), preregistration section 8 (line 102, by reference to the interface convention), and witness note lines 34 and 36 agree on `NUMERICAL_ZERO = 1e-12`, snap at or below, NaN/null handling, and the W-15 coverage. The only defect is the shared overreach F1.

**Calibration population.** Ledger `policies.near_zero_floor` (lines 288-300), interface policy 7 (line 105), and preregistration section 8 (line 100) all state the same population (adjacent distances on training-split static-noise trajectories at `sigma = 0.05`, per `(family, degree, resolution, metric)` cell), the same no-pooling rule, the same zero-noise regime (`sigma = 0`, `e = 0`, exact-zero abstention under the numerical-zero convention), and the same abstention formulas (`L <= 2(T-1)e`, `min(a, b) <= 2e`). The ledger and interface additionally fix `numpy.percentile` default linear interpolation; the preregistration omits that convention (F8, cosmetic).

**Abstention and zero-step.** Ledger `zero_step` and policy 12, interface 3.4 and policy 6/12, preregistration section 8, and witness note cases W-08 and W-13 state the same rules: undefined angle on `a = 0` or `b = 0`, counted unresolved, never dropped, never imputed; abstention never deletes a trajectory.

**Stale counts.** No occurrence of "14 cases", "14/14", "four policies", or "W-01 to W-14" remains in the four core documents or in the G0 decision; all refer to 15 cases. The stale counts that do exist are in the archived verification reports: `numerical_verification.md` says "97 checks" and "14 recorded `input_sha256` entries", while the frozen `witness_results.json` contains 100 checks and `environment.json` records 16 inputs; `consistency_audit.md` revision-2 sections say 14 hashed inputs. These are historical snapshots (F3).

**Cross-reference paths.** A regex scan of all path tokens in the ledger, interface, preregistration, witness note, G0 decision, pilot specification, and plan found every referenced file existing on disk, including the three verification reports, `independent_checks.py`, the witness evidence files, and `pyproject.toml`. The brace-expansion tokens in the G0 decision and pilot specification are notation, and `configs/tk_pilot.yaml` is an explicitly declared future implementation target ("these commands do not exist yet"), so no broken cross-reference was found.

---

## 7. Task 5: decision-rule equivalence (preregistration sections 2 and 7 vs pilot section 5)

Verified directly against the frozen texts. The GO conditions are equivalent: correctness and nuisance checks, adequate precision, route (a) superiority (`< -0.05`) or route (b) parsimony (`< 0.02` plus fourfold dimension or end-to-end cost reduction against the cheapest comparator within 0.02 of the best validation error), the 0.05 simultaneous Bonferroni family safeguard, the eligible-comparator freeze before opening test results, the weak-incumbent rule, the route freeze after exploration and before confirmation, and the INDETERMINATE / INCREMENTAL-ONLY / PIVOT / repair consequence statements.

H3 is stated as a non-binding stability diagnostic that "cannot by itself deny a GO"; this matches the pilot rule, which does not include stability as a GO condition. H4 is stated as the pilot's family safeguard and is part of GO; this matches the pilot's "Neither route may hide a family-specific deterioration above 0.05". The frozen-route clause in section 2 ("frozen after the exploratory stage and before the confirmatory test seeds are opened") matches the pilot's freeze sentence.

Two wording carve-outs do not change the GO conditions: (i) the H3 sentence adds "it may motivate a narrowed claim or a PIVOT at the discretion of the analysis review", which is not in the pilot but cannot deny an otherwise-satisfying GO; (ii) H1 says "strongest validation-selected incumbent" where the pilot says "validation-selected incumbent". Both were already recorded in the consistency audit (R1) as cosmetic. **Equivalence confirmed.**

---

## 8. Task 6: witness note numeric claims against `witness_results.json` and `run.log`

| Claim in the note | Verified value |
|---|---|
| "executes 15 cases and all 15 pass" | summary `15/15`, all `passed = true`, 15 `[PASS]` and 0 `[FAIL]` lines |
| W-01 shifts 0 to 9, transition at `M/2 = 5` | shifts `[0, 0.3, 4.9, 5.0, 5.1, 9.0]`, transition `5.0` |
| W-03 60 pairs, mismatch, order regression | `n_pairs = 60`; mismatch case `5.0`; order pair as in section 4 |
| W-04 40 triples, W-05 40 pairs | `n_triples = 40`, `n_pairs = 40` |
| W-06 L = 4, R = 0, speed 4, angles A `(pi, 0, pi)`, B `(0, 0, 0)` | exactly as stated |
| W-07 straight `theta = pi`, `tau = 0`; reversal `theta = 0`, `tau = pi` | exactly as stated |
| W-08 zero step null, `L = 0` null efficiency, excess null only when `a + b = 0` | exactly as stated |
| W-09 eps `{1e-4, 1e-6, 1e-8, 1e-10}`, jump about `pi` at `eps = 1e-8` with perturbation `2e-8` | jump `3.1414499586176032`, perturbation `2e-8` |
| W-10 non-metric raw cosine `-3.5` flagged; roundoff clipped without flag | `-3.5`, anomaly `true`; roundoff `-1.0000000000003997`, anomaly `false` |
| W-11 150 Euclidean, 50 graph, discrete 0/1, `R <= L`, `0 <= eta <= 1` | counts match; ranges inside `[0, 1]` |
| W-12 ratios 0.59, 0.997, 0.998, 0.955 | `0.5855481935357151`, `0.9974076240581549`, `0.9976472081187753`, `0.9549023930486897` (consistent one-to-three-decimal rounding) |
| W-13 irregular clock, rejection, floors | expected speeds/midpoints/rates, rejections, floor `1.4249999999999998` all match |
| W-14 stripping, counts, canonical order, rejection | one and two essential counts, canonical sort, rejection all match |
| W-15 true zero, 5e-13 snapped, 2e-12 preserved | as in section 4 |
| "about 7 seconds", seed 20260920 | frozen wall `7.49 s`, fresh `6.99 s`, seed recorded in JSON and environment |
| hash pointer to `environment.json` | 16 input hashes present and all matching |
| "overestimate of 1.4e-3" | `1.420192505883e-3` |

No false numeric claim was found in the witness note. Its "all blocking and material findings were repaired" sentence is overbroad given the residual items (F5).

---

## 9. Task 7: hash stability

All 16 hashes in `environment.json input_sha256` recompute exactly in this session; **zero mismatches**. The frozen outputs and figures are internally consistent with the frozen run (`run.log` reports `15/15` and `wall 7.49 s`; `witness_summary.txt` reports `15/15`; `environment.json` records the same wall time and seed 20260920). The verification report files themselves are not part of `environment.json`, as expected. The only hash concern is F3: the archived revision-2 hash tables do not describe the frozen files, so no archived verifier run covers the exact frozen `witnesses.py` and `run_witness_suite.py`; this session's checks close that gap.

---

## 10. Task 8: adversarial sweep for stale or overreaching claims

Searched the ledger, interface, preregistration, witness note, and G0 decision for novelty, utility, predictive value, extraction-correctness, causal-identification, "domain independent", "canonical kinematics", "turning direction", and gate-pass language beyond G0. Every occurrence is a prohibition, a rejection, a scope exclusion, or a disclaimed statement. Examples: ledger `claims_to_estimands` keeps C3 and C4 rejected and C5 to C10 open or unsupported; the interface's "What this interface does not define" section excludes latent causes, direction, physical acceleration, extraction, and stability; the preregistration's non-claims paragraph and the G0 decision's "What G0 does not cover" paragraph exclude G2 through G5 and all novelty and utility claims; the witness note repeatedly states it is operational correctness only. No claim of a passed gate beyond G0, no extraction-correctness claim, and no novelty or utility claim was found. One precision issue remains (F6).

---

## 11. Findings

| ID | Severity | Location | Finding and minimal reproduction |
|---|---|---|---|
| F1 | material | ledger lines 164-167 and 177-180; interface lines 51 and 111; witness note line 36 | The "up to `2 * NUMERICAL_ZERO`" qualification of `R <= L` and `0 <= eta <= 1` is valid only for a single triangle and is false as a general path statement and as an additive bound on `eta`. Repro 1 (eta): `A={(0,1)}, B={(1e-12,1+1e-12)}, C={(2e-12,1+2e-12)}` gives `L = 1.0000889005823406e-12`, `R = 1.9999999999999996e-12`, `eta = 1.9998222146405402`. Repro 2 (R-L): singleton births `[0, 2^-40, 2*2^-40, 3*2^-40, 3*2^-40+2e-12]` give `L = 2.000177801164682e-12`, `R = 4.728661906483467e-12`, `R - L = 2.7284841053187847e-12 > 2e-12`. Correct wording: single-triangle deviation `2 * NUMERICAL_ZERO`; general path `R - L <= T * NUMERICAL_ZERO` and `eta <= 1 + T * NUMERICAL_ZERO / L`. No stored witness or pilot-scale quantity is affected. |
| F2 | material | `scripts/run_witness_suite.py:207` | The runner crashes with `ValueError` on `figure.relative_to(ROOT)` whenever `--out` is outside the project root (or relative), so it writes only `run.log` and `figures/`, omits `witness_results.json`, `witness_summary.txt`, and `environment.json`, and exits 1 although all 15 cases passed. Repro: `/usr/bin/python3 scripts/run_witness_suite.py --out /tmp/opencode/final_witness2` gives `EXIT=1` and a traceback at line 207. The frozen default-path run is complete, so this is a CLI robustness defect, not an evidence defect. |
| F3 | material | archived verification reports vs frozen artifacts | The frozen `witnesses.py` (`3c992fd0...`), `run_witness_suite.py` (`e9cda7ae...`), `witness_results.json` (`581ce1e2...`), `environment.json` (`ac98e45e...`), and `run.log` (`af1b24fe...`) postdate the archived verifications, whose revision-2 hashes are `3fa010ec...`, `564efbb...`, `10c32adb...`, `b600ce7d...`, and `6232b20f...`. The reports also state 97 checks and 14 hashed inputs, while the frozen JSON has 100 checks and 16 inputs. The G0 decision cites those audits as evidence. This fresh audit reproduces the frozen state (15/15, case-level JSON equality, 34 tests, independent W-03 and W-15 values), so the gap is closed for this session, but the archived reports should not be read as verifying the frozen hashes. |
| F4 | cosmetic | `assumption_ledger.yaml` line 7 vs lines 474-475 | The artifact-level `status: pending_verification` contradicts `g0_record.status: passed` in the same file and the G0 decision's PASS. Repro: `rg "status" research_review/assumption_ledger.yaml`. |
| F5 | cosmetic | ledger line 461; witness note line 38 | "All audit findings were repaired" (ledger) and "All blocking and material findings were repaired, together with the cosmetic findings, except one inherited count ambiguity" (witness note) overstate the repair state. Residual items include the H3 discretion clause and the unpropagated `numpy.percentile` convention (F8), plus the incomplete F1 repair. |
| F6 | cosmetic | `G0_decision.md` line 13 | "found no violation on the declared input domain" omits the verifier's own qualifier "at the suite's `1e-9` tolerance"; the same item discloses the `1e-12` pseudometric deviation, and F1 shows exact violations inside that band. Repro: compare with `numerical_verification.md` section 7.3 check 7. |
| F7 | cosmetic | plan WP-2.2, plan line 121 | The plan's verification target "`R <= L`; `eta` in `[0,1]` when `L > 0`" remains unqualified although the second-reader R1 finding listed this location. The plan is unchanged (hash-pinned) and the ledger governs per the interface's conflict rule, so this is an incomplete propagation of the qualification, not a live contradiction. |
| F8 | cosmetic | preregistration line 100 vs ledger line 293 and interface line 105 | The preregistration states `e` as "the 95th percentile of that population" but omits the `numpy.percentile` default linear interpolation convention that the final freeze added to the ledger and interface. Under-specified, not contradictory; the ledger governs. |

No blocking finding was identified.

---

## 12. Verdict

**The G0 decision record is justified by the evidence.** The frozen package reproduces at 15/15 witness cases and 34/34 unit tests; the direct `run_all(seed=20260920)` record is exactly equal to the stored `witness_results.json`; the new W-03 order-sensitive values and row-order invariance were independently recomputed from scratch (`0.8980590011828029`, raw overestimate `1.420192505883e-3`, permutation counts `72/504`); the numerical-zero policy was verified end-to-end on all four public backends; the calibration-population, abstention, and zero-step rules are consistent across the ledger, interface, preregistration, and witness note; the GO rule is equivalent to the pilot specification's section 5; and all 16 input hashes match. The pass criteria of the plan are met for the restricted finite-metric operational model, and no claim beyond G0 is asserted anywhere in the audited documents.

The three material findings (F1, the overbroad 2e-12 pseudometric qualification; F2, the runner crash for external `--out`; F3, the archived verification hashes and counts not covering the frozen files) should be repaired or annotated before the G0 record is cited downstream, but none changes the meaning of a quantity across datasets, affects the frozen default-path evidence, or undermines the gate decision. Findings F4 through F8 are cosmetic.

**Finding count: 0 blocking, 3 material, 5 cosmetic. Top finding: F1, the false general `2 * NUMERICAL_ZERO` bound on `R <= L` and `0 <= eta <= 1` inside the declared tolerance band (with `eta = 1.9998` at two intervals and `R - L = 2.728e-12` at four intervals).**

---

# Final revision (post-repair)

**Date.** 2026-09-20, second session, after the repair round applied at 21:14 to 21:15 local time. **Scope.** Verify each of the eight repair items with fresh commands; re-run the witness suite in default and external output modes; re-run pytest and the W-03/W-15 spot checks; re-check the new pseudometric bounds against the original reproductions; recompute all hashes; and record per-finding dispositions. Sections 1 through 12 above are retained unchanged as the pre-repair evidence.

## R.1 Commands run in this re-verification

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 scripts/run_witness_suite.py --out /tmp/opencode/repair_ext    # EXIT=0
tar (project, excluding .git/__pycache__/.pytest_cache) to /tmp/opencode/repcheck
cd /tmp/opencode/repcheck
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 scripts/run_witness_suite.py                                   # EXIT=0, default path
cmp <frozen witness outputs> <copy witness outputs>   # witness_results.json, summary, 4 figures byte-identical
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m pytest -p no:cacheprovider                                  # 34 passed in 7.69s
/usr/bin/python3 /tmp/opencode/audit_checks.py                                                            # W-03/W-15 spot checks
/usr/bin/python3 /tmp/opencode/verify_note_and_bound.py                                                   # bound probes
<own 400-path random near-zero sweep, T in 2..8>                                                          # 0 bound violations
```

The default run was executed inside a full copy of the project at `/tmp/opencode/repcheck` so that the frozen outputs in the project tree were not rewritten. The copy's `witness_results.json`, `witness_summary.txt`, and all four figures are byte-identical to the frozen files; the copy's `environment.json` differs from the frozen one only in `generated_utc` and `wall_seconds`, and both record the same 16 input hashes. The frozen `environment.json` input hashes all match the current repaired files.

## R.2 Per-finding dispositions

| Finding | Original severity | Disposition on the final revision | Evidence |
|---|---|---|---|
| F1, pseudometric bounds overbroad | material | **Resolved**, with a new documentation caveat (N1) | Ledger R (lines 163-168), ledger eta (lines 178-181), interface section 3.2 (line 51) and policy 13 (line 111), and witness note line 36 now state the single-triangle deviation `<= 2 * NUMERICAL_ZERO`, the path bound `R - L <= T * NUMERICAL_ZERO`, and `eta <= 1 + T * NUMERICAL_ZERO / L`. Both original reproductions satisfy the new bounds: `eta = 1.9998222146405402 <= 2.9998` on the second-reader triple, and `R - L = 2.7284841053187847e-12 <= 4e-12` with `eta = 2.364120781527531 <= 3.0` on the four-interval path. The 400-path random near-zero sweep found 0 violations of either bound. |
| F2, runner crashes for external `--out` | material | **Resolved** | `scripts/run_witness_suite.py` adds `display_path` (lines 74-79), writes `witness_results.json`, `environment.json`, and `witness_summary.txt` before figure generation (lines 224-235), and catches figure exceptions (lines 236-241). External command exits 0 and writes all five artifacts and four figures; default run in the isolated copy exits 0 and writes the same. No case-result regression. |
| F3, archived audits do not cover frozen hashes | material | **Resolved**, with a wording note (N2) | G0 decision items 3 and 5 label the numerical and consistency reports "retained as historical revision-2 evidence"; item 6 cites `final_audit.md` and states that this audit recomputes hashes for the frozen revision. This appended section supplies that hash table. |
| F4, ledger top-level status | cosmetic | **Resolved** | `assumption_ledger.yaml` line 7 is `status: passed`, consistent with `g0_record.status: passed` at line 475 and with the G0 decision. |
| F5, "all findings were repaired" overstatement | cosmetic | **Resolved**, with a residual-list omission (N3) | Ledger line 462 and witness note line 38 now say blocking and material findings were repaired and list documented residuals: the inherited feature-count wording deferred to the WP-1.2 freeze and the cosmetic H3 discretion clause. |
| F6, missing tolerance qualifier | cosmetic | **Resolved** | G0 decision line 13 now says "found no violation on the declared input domain at the suite's 1e-9 tolerance, with the numerical-band deviation bounded as recorded in the ledger". |
| F7, plan WP-2.2 unqualified | cosmetic | **Resolved** | Witness note line 38 records the propagation note: the plan's WP-2.2 target states `R <= L` and `0 <= eta <= 1` without the numerical-band qualification, while the ledger and interface govern and carry the qualification. |
| F8, percentile convention absent from prereg | cosmetic | **Resolved** | Preregistration section 8 (line 100) now states `e` is "computed with numpy.percentile's default linear interpolation". |

## R.3 New and remaining findings on the final revision

| ID | Severity | Location | Finding |
|---|---|---|---|
| N1 | cosmetic | `metric_interface.md` line 111; `witness_note.md` line 36 | Both documents say the numerical verification report "exhibits both a single-triangle and a multi-interval witness" (interface wording: "deviation"). The archived report contains only the single-triangle E2 exhibit; its 540-path sweep has multi-interval paths whose maximum `R - L` is `3.553e-15` (roundoff, not a snap deviation). The multi-interval witness is in section 5 of this audit (repro 2). Fix: cite `final_audit.md` for the multi-interval witness, or reword to "exhibits a single-triangle deviation". Reproduction: search `multi-interval` in the research_review tree; `numerical_verification.md` line 220-231 shows only the three-diagram E2. |
| N2 | cosmetic | `G0_decision.md` item 4 (line 14) | The second-reader item is qualified as "the acceptance test passes on revision 2" but does not carry the explicit "retained as historical revision-2 evidence" label applied to items 3 and 5. The evidence statement itself is accurate; only the repair description "labels the three archived reports as historical" is not literally matched. |
| N3 | cosmetic | ledger line 462; witness note line 38 | The residual lists omit the pyyaml omission documented in `consistency_audit.md` F4: pyyaml appears in the ledger environment (line 42) and `environment.json` but not in the preregistration's frozen environment list (line 106). Tooling only, no decision impact. |

## R.4 Hash table for the frozen final revision

All values recomputed with `hashlib.sha256` in this session. "changed" compares against the corresponding value in sections 1.1 to 1.3 above.

| File | sha256 | Status |
|---|---|---|
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` | unchanged |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` | unchanged |
| `research_review/assumption_ledger.yaml` | `72ec74e1f89c734116a0a05267aaa809c542329afa54464ddfbc9b69f563fdea` | changed |
| `research_review/metric_interface.md` | `56d0fdd572dd1a5fe8e07e1b7d666a60f196885b3dec0d3c7f658161dbcc9777` | changed |
| `research_review/preregistration_draft.md` | `669bd3db1b434b2693bbd688d942907d0cb97acfa27eac446921dfea7e93e770` | changed |
| `research_review/witness_note.md` | `b72b3a64434191536c59391cf12c470c6c2a93bce9899639e2ef6e4a5eb072f0` | changed |
| `research_review/results/phase0/G0_decision.md` | `54b36eef75e15da08d23afa73b229ad551f2e94509e91b0c9f103f1e50bf4578` | changed |
| `research_review/topological_kinematics_witness.py` | `c70e1c486465f91b8d91a663a081db779ce7438e0330b860732e0062557479d9` | unchanged |
| `src/tk_pilot/diagram_metrics.py` | `4d22315d5ea871d8d6afa321c70e7a593a7b149cc1d8654b93047b053b288044` | unchanged |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` | unchanged |
| `src/tk_pilot/witnesses.py` | `3c992fd087f67bb4dc7554b05598e720fad953e4ce1b58cc1efaf37fd1e1b544` | unchanged |
| `src/tk_pilot/witness_figures.py` | `a5129ab3715398134498232c1917027ec8db2173cae8170b2684f2847e23d2a3` | unchanged |
| `scripts/run_witness_suite.py` | `d1bd234d733d54a7ba3d13492362d44a513eff392ae29e5363308dfde088dde3` | changed |
| `tests/test_diagram_metrics.py` | `48e2d5a4ef33f2cd84fc17d11c7b03afa9a4a7026b661d90ec23b608fc98f3dc` | unchanged |
| `tests/test_path_diagnostics.py` | `09f755f9e91b3f0d48a87626cb976e1284a2748f703a374b30d1284a3c06279b` | unchanged |
| `tests/test_witnesses.py` | `cb73c5185380f5ad73f99c92f6e4cbcd6ef56a288cab9370d76362e9e0ec0785` | unchanged |
| `research_review/results/phase0/witness/witness_results.json` | `581ce1e2810029d6106d29691e2e73d39bff634835ecdf7acb0fb47a1b39ca40` | unchanged |
| `research_review/results/phase0/witness/witness_summary.txt` | `7f696d93f719657310112f131073fa571ce17584619bfacde01e34e0807215be` | unchanged |
| `research_review/results/phase0/witness/environment.json` | `9c7c1381d23d80ddb16b0138569f0efd78e642a9a986283f72d1ddce4086f372` | changed (regenerated by the repair default run) |
| `research_review/results/phase0/witness/run.log` | `ce9b562d1d8c57ebfd72e3f1473ef84f8d128ab91224e6ddfa8b1c5f15781cfb` | changed (regenerated by the repair default run) |
| `research_review/results/phase0/witness/figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` | unchanged |
| `research_review/results/phase0/witness/figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` | unchanged |
| `research_review/results/phase0/witness/figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` | unchanged |
| `research_review/results/phase0/witness/figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` | unchanged |
| `research_review/results/phase0/verification/numerical_verification.md` | `d09d7fb1fedcfd428ff9cd659b43c84c4ec17b6dc7f6cf3a18f76fba4e2fa53e` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/second_reader_audit.md` | `798177e4f5365c440f88eb2a3313374317a6e601810d04e3744e7574805cd549` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/consistency_audit.md` | `b399b8c1054b6d55bced92b48bbc81d17db495cb306ab93d4a39f110031bc660` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/independent_checks.py` | `045b4a17d1307f5b7da30bbb153cf7920b11684fc6ba7a8c9926f64d029332b6` | unchanged |
| `research_review/results/phase0/verification/final_audit.md` | `eb2ecaccae7caa990edffe06e90bc72a4a019d646766b21c7a7108477b7c8b8b` | pre-append value; the post-append hash is reported in the session final message because this file cannot embed its own final hash |
| `research_review/results/metric_witness_results.txt` | `19771d9744b130a5b06c9360ed84f61c906c4f9d660737cc4866be1a95a74912` | unchanged |
| `pyproject.toml` | `9e41c5ff67a728e10a1ecb73e16b84dc39146622ad094ed65018c1154f6c60c5` | unchanged |

The 16 `environment.json` input hashes all match the current repaired files, including the five repaired documents, the repaired runner, and the four unchanged source modules and three test files.

## R.5 Reproduced results on the final revision

The external run (`--out /tmp/opencode/repair_ext`) exits 0 with `summary: 15/15 cases passed` and all five artifacts plus four figures. The default run in the isolated copy exits 0 with the same 15/15 and produces byte-identical `witness_results.json`, `witness_summary.txt`, and figures. `pytest` reports 34 passed. The W-03 spot checks reproduce `0.8980590011828029` from the own enumerator, persim, and the canonical public API, the raw as-given value `0.8994791936886859`, row-order invariance, and the permutation split `{0.899479193688686: 72, 0.898059001182803: 504}`. The W-15 spot checks reproduce exact `0.0` for the true-zero non-identical pair on all four public backends, snap of `5e-13`, and preservation of `2.000177801164682e-12`. The new path bounds hold on both original counterexamples and on 400 randomized near-zero paths.

## R.6 Final verdict on the final revision

**No blocking or material finding remains unresolved. The G0 decision record is justified on the final revision.** The repaired bounds are mathematically correct and consistent across the ledger, interface, and witness note; the runner is robust in both default and external output modes; the evidence statements in the G0 decision now distinguish historical revision-2 audits from this fresh audit, which is refreshed here to cover the post-repair hashes; the status and residual statements are consistent, with one documented residual list omission (N3); and the reproduced results are unchanged at 15/15 and 34/34.

Three cosmetic findings remain on the final revision: N1 (the interface and witness note misattribute the multi-interval witness to the archived numerical verification report; the witness is in section 5 of this audit), N2 (the second-reader item in the G0 decision lacks the explicit historical label while remaining factually qualified), and N3 (the residual lists omit the pyyaml omission already documented in the consistency audit). None affects a rule, a bound, a stored result, or the gate decision. F1 through F8 are resolved in substance.

---

# Hash refresh after cosmetic repairs

**Date.** 2026-09-20, third session, after the documentation-only repair of N1, N2, and N3 at 21:19 local time. **Scope.** Verify the three residual repairs by direct reads, confirm that no code changed relative to the final revision in R.4, recompute every hash in the R.4 table, and re-confirm the reproduced results. No scope change and no new audit.

## H.1 Verified repairs

| Residual | Verified change |
|---|---|
| N1 | `metric_interface.md` policy 13 now reads "The numerical verification report exhibits the single-triangle deviation, and the final audit report exhibits the multi-interval deviation." `witness_note.md` line 36 carries the same attribution. The multi-interval witness remains in section 5 of this audit. |
| N2 | `G0_decision.md` item 4 now reads "Independent second-reader audit: `research_review/results/phase0/verification/second_reader_audit.md`, retained as historical revision-2 evidence." All three archived reports now carry the label. |
| N3 | `assumption_ledger.yaml` line 462 and `witness_note.md` line 38 add "the tooling-only pyyaml omission in the pre-registration environment list" to the documented residuals. |

**No code changed.** Relative to the table in R.4, the hashes of `scripts/run_witness_suite.py`, all four `src/tk_pilot` modules, and all three test files are identical; `witness_results.json`, `witness_summary.txt`, and all four figures are also identical. Only the four repaired documents plus the regenerated `environment.json` and `run.log` changed.

**Re-confirmation.** `pytest` reports 34 passed. The frozen `run.log` reports `summary: 15/15 cases passed; wall 5.27 s` with 15 `[PASS]` lines. A default run in an isolated copy of the current revision exits 0 and produces byte-identical `witness_results.json`, `witness_summary.txt`, and figures. The refreshed `environment.json` records 16 input hashes, all matching the current files.

## H.2 Refreshed hash table

All values recomputed with `hashlib.sha256` in this session. "status" compares against the R.4 table.

| File | sha256 | Status |
|---|---|---|
| `research_review/Topological_Kinematics_Research_Plan.md` | `8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a` | unchanged |
| `research_review/Pilot_Experiment_Specification.md` | `491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202` | unchanged |
| `research_review/assumption_ledger.yaml` | `ea46fab5960c0e8648bcd61bf187e86446a1a4cc7eeaae0ac1259ce8a1220844` | changed (N3) |
| `research_review/metric_interface.md` | `7a8a25137ad82050c23d0388f46b5f46f4fc3e86d0b754cce166132687700c33` | changed (N1) |
| `research_review/preregistration_draft.md` | `669bd3db1b434b2693bbd688d942907d0cb97acfa27eac446921dfea7e93e770` | unchanged |
| `research_review/witness_note.md` | `6e30f4af98a0af0c65a56bf2c6194e3d2715ba83b609824e3de530231c63b7ad` | changed (N1, N3) |
| `research_review/results/phase0/G0_decision.md` | `44571b588492bbf01507b1ee191cb238828bcf3ca41444561c24a8c7688a31cb` | changed (N2) |
| `research_review/topological_kinematics_witness.py` | `c70e1c486465f91b8d91a663a081db779ce7438e0330b860732e0062557479d9` | unchanged |
| `src/tk_pilot/diagram_metrics.py` | `4d22315d5ea871d8d6afa321c70e7a593a7b149cc1d8654b93047b053b288044` | unchanged |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` | unchanged |
| `src/tk_pilot/witnesses.py` | `3c992fd087f67bb4dc7554b05598e720fad953e4ce1b58cc1efaf37fd1e1b544` | unchanged |
| `src/tk_pilot/witness_figures.py` | `a5129ab3715398134498232c1917027ec8db2173cae8170b2684f2847e23d2a3` | unchanged |
| `scripts/run_witness_suite.py` | `d1bd234d733d54a7ba3d13492362d44a513eff392ae29e5363308dfde088dde3` | unchanged |
| `tests/test_diagram_metrics.py` | `48e2d5a4ef33f2cd84fc17d11c7b03afa9a4a7026b661d90ec23b608fc98f3dc` | unchanged |
| `tests/test_path_diagnostics.py` | `09f755f9e91b3f0d48a87626cb976e1284a2748f703a374b30d1284a3c06279b` | unchanged |
| `tests/test_witnesses.py` | `cb73c5185380f5ad73f99c92f6e4cbcd6ef56a288cab9370d76362e9e0ec0785` | unchanged |
| `research_review/results/phase0/witness/witness_results.json` | `581ce1e2810029d6106d29691e2e73d39bff634835ecdf7acb0fb47a1b39ca40` | unchanged |
| `research_review/results/phase0/witness/witness_summary.txt` | `7f696d93f719657310112f131073fa571ce17584619bfacde01e34e0807215be` | unchanged |
| `research_review/results/phase0/witness/environment.json` | `e26428b7292521e0296b7cb61d525bc6b0da0e9090aeec2fc25ba3c7da7c0f9a` | changed (regenerated) |
| `research_review/results/phase0/witness/run.log` | `0c9f16956e0a148d3758e34e8b1f359dce1cd8b7c773f4a3b2b467c12874973b` | changed (regenerated) |
| `research_review/results/phase0/witness/figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` | unchanged |
| `research_review/results/phase0/witness/figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` | unchanged |
| `research_review/results/phase0/witness/figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` | unchanged |
| `research_review/results/phase0/witness/figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` | unchanged |
| `research_review/results/phase0/verification/numerical_verification.md` | `d09d7fb1fedcfd428ff9cd659b43c84c4ec17b6dc7f6cf3a18f76fba4e2fa53e` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/second_reader_audit.md` | `798177e4f5365c440f88eb2a3313374317a6e601810d04e3744e7574805cd549` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/consistency_audit.md` | `b399b8c1054b6d55bced92b48bbc81d17db495cb306ab93d4a39f110031bc660` | unchanged (historical revision-2 evidence) |
| `research_review/results/phase0/verification/independent_checks.py` | `045b4a17d1307f5b7da30bbb153cf7920b11684fc6ba7a8c9926f64d029332b6` | unchanged |
| `research_review/results/phase0/verification/final_audit.md` | `c6b8e8e9c731a030628693053f6973eca12f490e157dde4931a2a5603b7150f5` | pre-refresh value; the post-append hash is reported in the session final message because this file cannot embed its own final hash |
| `research_review/results/metric_witness_results.txt` | `19771d9744b130a5b06c9360ed84f61c906c4f9d660737cc4866be1a95a74912` | unchanged |
| `pyproject.toml` | `9e41c5ff67a728e10a1ecb73e16b84dc39146622ad094ed65018c1154f6c60c5` | unchanged |

## H.3 Final verdict after the hash refresh

**All three cosmetic residuals are resolved and no finding of any severity remains. The G0 decision record remains justified on this revision; all hashes refresh cleanly and the reproduced results are unchanged at 15/15 and 34/34.** One whitespace artifact (a run of spaces after the file path in the ledger residual bullet at line 462) was observed; it changes no meaning and is not recorded as a finding.
