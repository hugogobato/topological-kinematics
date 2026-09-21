# G1 independent verification audit

**Gate.** G1 (Phase 1 prior-art and baseline lock).

**Auditor.** Independent verifier (separate from agents A1-A6). **Date.** 2026-09-20.

**Scope.** WP-1.1 citation ledger and reproducibility memo; WP-1.2 baseline protocol, claims-to-tests matrix, and G1 decision packet; implementation contract and execution log; `src/tk_pilot/`; `configs/tk_pilot.yaml`; stored smoke evidence; fresh-cache rerun; primary-source spot checks against the local PDFs.

**Result summary.** Check 1 PASS. Check 2 PASS with residuals. Check 3 PASS with residuals. Check 4 PASS. Check 5 PASS with residuals. Proposed decision: **CONDITIONAL GO** for Phase 2 (WP-2.1 and the G2 raw-data correctness work), with four pre-G3 conditions listed in Section 7.

No repository file was modified except the two deliverables of this audit. The repository cache was not touched (temp cache used for the rerun; before/after file listing diff is empty).

## 1. Citation spot-check (Check 1): PASS

The local PDFs were re-extracted independently with `pdftotext -layout` and per-page `pdftotext -f P -l P`; page hits were located by scanning each physical page for the target statement. At least nine ledger claims were re-verified, including all claims the task required. Every required locator reproduced.

| Source | Verified claim | Independent finding |
|---|---|---|
| Kramar et al. (1-s2.0-S0167278916000270-am.pdf) | Eq. (16), printed p. 10 | Exact: `s*(t_i) = d*(PD(f_i), PD(f_{i+1}))/Delta t`, followed by "can be interpreted as an average speed in the space of persistence diagrams"; folio 10 confirmed on PDF/printed page 10 |
| Kramar | Def. 5.1 printed p. 7, Eqs. (8)-(9), and Eq. (12) printed p. 8 | Exact: bottleneck max-inf-sup bijection (8), degree-p Wasserstein with L-infinity ground norm (9), and `d_B <= d_{W_p}` (12) |
| Kramar | Theorem 7.3, printed p. 14 | Exact: `Y` a delta-dense subsample of point cloud `X` implies `d_B(PD(X,d), PD(Y,d)) < delta`; attributed to reference [28] as the ledger states |
| Giusti and Lee (2108.02727v2.pdf) | Theorem 4.2 scope, printed p. 11 | Verified: Definition 4.2 (p. 10) defines `F(Z)` as the completion of `V_fin(Z)` under the norm `||alpha||_1 = W1_partial[d](alpha+, alpha-)`; Theorem 4.2 is therefore an isometry for partial W1 only, with no W_p or bottleneck claim. The plan's Section 3 restriction is correct |
| Giusti and Lee | Corrected locator for Section 6 | Verified: Section 6 heading on printed p. 15; Example 6.1 and Definition 6.1 on p. 16; Theorem 6.1 and Lemma 6.1 on p. 17; Theorem 6.2 on p. 18; Definition 6.2 on p. 19; Section 7 starts on p. 20. The corrected span pp. 15-19 (not pp. 16-20) is right |
| Xian et al. (2010.05780v2.pdf) | Lemma 7.3, printed p. 31 | Exact: for all `1 <= p <= infinity`, `d_b^p(PH(VR(X)), PH(VR(Y))) <= 2 d_GH^p(X,Y)`; Lemma 7.4 statement at the foot of p. 31 |
| Xian et al. | Theorem 7.5, printed p. 32 | Exact: `d_GH^infinity(X,Y) <= delta/2` implies the two crocker-stack erosion inequalities for all `t, epsilon, alpha` |
| Xian et al. | Definition 4.1, printed p. 11; Section 6.3, printed p. 26; Example 2 instability, printed p. 30 | Exact: `f_V(t,epsilon,alpha) = rank(V_t(epsilon-alpha) -> V_t(epsilon+alpha))` on `[0,T] x [0,infinity) x [0,infinity)`; `d_b(PH(VR(X)),PH(VR(Y))) <= 2 d_GH(X,Y)`; Betti difference 3 at n = 4 and arbitrarily large for large n |
| Giusti and Lee | Theorems 6.1 and 6.2, printed pp. 17-18 | Exact: Theorem 6.1 states the moment map is Lipschitz and injective; Theorem 6.2 states the truncated signature composed with the moment map is Lipschitz on paths of bounded 1-variation |
| Khormali (2512.14615v2.pdf) | Corrected locator for Theorem 4.5 | Verified: statement on printed p. 12 with the exact bound `3 n_sub m / ((beta-alpha) min{P(D1),P(D2)}) d_1^1(D1,D2)`, not spread over pp. 8-14; Definition 3.1 begins on printed p. 6 |
| Bernal-Alvarado et al. (2607.05695v1.pdf) | Eqs. (11)-(15), printed p. 10; reference note [23], printed p. 26 | Exact: `W2(t,t+10)`, `Wdot(t) = W2(t,t+10)/Delta t` with `Delta t = 10 yr`, `W_cross`, `rho(t)`, and `ICT = (1/3)(chi/chi_max + xi/xi_max + Wdot_norm)`; note [23] states the Roman and Byzantine W2 units are not directly comparable |
| Malhotra et al. (2606.19542v1.pdf) | Eq. (2), printed p. 4; Appendix B.3, printed p. 13 | Exact: `C = sum_{t<=T/3} v_t / sum_t v_t` with `v_t` called a topological velocity; 64 overlapping subsamples of size 160, Vietoris-Rips to dimension 1, ripser, order-2 Wasserstein via persim |
| Cohen-Steiner et al. (morozov-vineyards-socg06.pdf) | Stability Theorem, local p. 3; vineyard and knee definitions, local pp. 5-7 | Exact: `d_B(D_p(f),D_p(g)) <= ||f-g||_infinity` at the top of local p. 3; vineyard and knee occurrences on local pp. 5-7. The local PDF has no folios, and the ledger's method note discloses this convention |
| Email (email.pdf, image only) | p. 2 literature review and p. 4 items 5-10 | Verified by rendering pages 2 and 4 at 110 dpi: "simply defining consecutive Wasserstein distance as topological velocity would not be a novel contribution", the interpolation formulas `nu_t`, `L`, `R`, `eta`, `a_t^speed`, and `cos theta_t`, and the caveat that the scalar speed difference is not a full acceleration definition |

**Locator defect found (minor).** The ledger's EMAIL2026 locator attributes "the idea of a persistence-diagram trajectory itself is definitely not new" to `email.pdf` p. 3. The rendered p. 2 contains that sentence. The substance is verified; only the page number is off by one. No other claim failed to reproduce. The ledger's stated totals (36 claims, 33 verified, 3 corrected, 0 unverifiable) match an independent count of the YAML.

**Prior-art consequence.** The withdrawals of C3 (inter-frame speed), C4 (broad diagram-trajectory novelty), and C10 (new calculus or acceleration theory) are precluded by reproduced primary sources, and the prohibited-language scan over the Phase 1 artifacts found no forbidden novelty assertion.

## 2. Baseline reproducibility (Check 2): PASS with residuals

**Executable code exists for every required baseline.**

| Baseline | Code | Test evidence |
|---|---|---|
| Kramar-style consecutive speed | `features.py` `_compact_vector` via `path_diagnostics.interval_speeds`, plus `speed_history` | `tests/test_features.py::test_compact_matches_path_diagnostics` |
| Distance-matrix recurrence | `features.py` `complete_distances`, `_recurrence_vector` | `test_complete_distances_and_recurrence_on_known_singletons`, `test_recurrence_lag_without_pairs_is_nan` |
| Persistence moments | `features.py` `_moment_row`, `moments_flat`, `moments_summary` | `test_empty_diagram_moments_are_zero`, dimension tests |
| Level-2 signatures, with and without time | `signatures.py` exact Chen identity, `moment_signature`, `moment_signature_time` | `test_signature_straight_line_analytic` and `test_signature_l_shape_by_hand` at 1e-12; dimensions 42 and 56 |
| Raw geometry, both families | `features.py` `_geometry_rows` | `test_family_b_geometry_dimensions_and_finiteness`, dimension tests |
| Runners and model pipeline | `models.py`, `evaluate.py`, `run.py` | `tests/test_models_evaluate.py` |

**Test suite rerun.** `PYTHONPATH=src python3 -m pytest tests/ -q -o addopts=""` gives 112 passed in 11.15 s.

**Stored smoke evidence is real.** `manifest.json`: 46 trajectories, 340 rows, wall 168.709 s, peak RAM 190,959,616 bytes, 4 workers, config file hash `1862b1bb...` which matches the current `configs/tk_pilot.yaml` exactly. `metrics.parquet` has all ten representations (240 scientific rows plus 100 control rows), and `selection_table.parquet` has exactly 16 hyperparameter evaluations for each of the 40 `(cell, representation)` groups. `summary.json` records the probe at 18.094 s and 123,879,424 bytes.

**Clean-cache status.** The execution log asserts a clean-cache run, and the only repository cache files carry mtimes 2026-09-20 22:21 to 22:24, consistent with a single run window; the manifest was created at 01:24:56Z (22:24:56 local). This cannot be proven from the stored artifact alone, so it was tested directly: a fresh-cache rerun in `/tmp` reproduced every feature dimension, every valid fraction, and every predicted label (Section 4). The execution-log entry timestamp (22:35) disagrees with the file creation time (22:24:56) by about ten minutes; this looks like a logging imprecision, not a result defect. The log also records 4 workers, while the smoke definition in `implementation_contract.md` Section 7 and the decision packet names 2 workers; this is an unrecorded resource deviation in the frozen artifact, although the 2-worker envelope is independently shown to pass.

**Translation control.** `summary.json` `translation_check` for base seed 11, Family A, degree 0: `max_distance = 0.0` with tolerances `1e-7` at both sigma 0 (filtration range 0.2104695) and sigma 0.05 (range 0.3685692); `passed: true` in both cases. The fresh rerun reproduces the same values (Section 4).

**Feature dimensions.** Within each scientific cell the postprocessed dimensions are constant and equal the protocol Section 7 schema (compact 13, speed_history 134, complete_distances 8256, recurrence_summary 9, raw_geometry_flat 774 for A and 516 for B, raw_geometry_summary 12 for A and 8 for B, moments_flat 774, moments_summary 12, moment_signature 42, moment_signature_time 56). The control rows differ by construction (5-frame matched controls give 10 or 30), and the extra compact column at 13 is the retained missingness mask, which is the declared postprocessing rule.

**Residuals.** 1. The stored smoke ran with 4 workers, not the frozen smoke definition of 2. 2. Bitwise reproducibility is overstated in `implementation_contract.md` Section 0: in every smoke cell the winning learners tie on validation error, so measured prediction seconds decide, and 72 of 120 `(family, sigma, representation, split)` groups selected a different learner on the rerun even though predicted labels were unchanged. This is consistent with the frozen tie-break rule, but model selections are reproducible only through the frozen record, not bitwise. 3. The historical clean-cache claim rests on the log and mtimes, not on a manifest flag.

## 3. Protocol freeze (Check 3): PASS with residuals

**What is frozen, and it matches the authority documents.** `baseline_protocol.md` fixes the six comparator families and ten representation names (identical to `implementation_contract.md` Section 6 and `configs/tk_pilot.yaml`), equal tuning at 16 configurations per `(cell, representation)`, training-only preprocessing, validation-only incumbent selection with cost and dimension tie-breaks, complete-trajectory splitting with base-seed variant clustering, trailing causal windows for any detection work, the eligible-comparator rule at 0.02, the fourfold worst-case dimension or cost ratio, the two-route decision rule with thresholds `-0.05`, `0.02`, `4.0`, `0.05`, and half-width target `0.01`, and the Bonferroni family safeguard over two families. `configs/tk_pilot.yaml` carries exactly `superiority_upper: -0.05`, `noninferiority_upper: 0.02`, `parsimony_ratio: 4.0`, `family_deterioration: 0.05`, `target_half_width: 0.01`, and bootstrap 2000 resamples with seed 20260907. The decision rule matches `Pilot_Experiment_Specification.md` Sections 5 and 7 and `preregistration_draft.md` Section 7, and `evaluate.decide` implements the two-route arithmetic with those constants.

**Freeze hashes.** Eight of the authority documents in the Appendix B tables match their recorded sha256 exactly (`Pilot_Experiment_Specification.md` `491c91...`, `preregistration_draft.md` `669bd3...`, `assumption_ledger.yaml` `ea46fa...`, `metric_interface.md` `7a8a25...`, `G0_decision.md` `44571b...`, `consistency_audit.md` `b399b8...`, `Topological_Kinematics_Research_Plan.md` `8fd065...`, `baseline_protocol.md` `1a31cb...`). `claims_to_tests.yaml` still reads `[PENDING: sha256 at the G1 freeze instant]` in the decision packet; the current hash is `a99063ed73f7d3fd31faedb0a6362aa60e173b8548c62eb2351ef3bad5d2bd12`.

**Freeze integrity defect.** The frozen `implementation_contract.md` hash `b024c04f...` in both Appendix B tables does not match the current file, whose hash is `c8f48782...`. File mtimes show the protocol was frozen at 21:35:09 while the contract was last written at 22:25:18, and the execution log was appended at 22:25:26. The behavioral changes (A5 `frozen_route`, additive return keys, runner cache layout, compact 12-feature resolution, moment scaling) are described in the execution log, so the substance is documented, but the authority-hash tables were not updated and no explicit hash-deviation row exists. The protocol's own rule requires the disagreement to be recorded in the execution log.

**Other divergences recorded.**

1. `split_manifest.csv` lacks the protocol Section 4 required `diagram_hash` column. The diagram hashes exist in the diagram cache checksum files, but the manifest row does not carry them.
2. The smoke split manifest has the same `trajectory_id` under train, validation, and test because the smoke stage deliberately reuses seed 11 in all three splits. The V2 check ("every trajectory identifier appears under exactly one split") is therefore not demonstrable at G1; it can only be checked after the exploratory namespaces run.
3. `evaluate.decide` adds statuses beyond the protocol table: it returns `CONDITIONAL GO` when the route that was not frozen happens to hold, and it assigns `PIVOT` automatically for a family deterioration and for a noninferior but non-parsimonious result. The protocol reserves `PIVOT` for the G3 memo with a new protocol and untouched seeds. It also makes the realized half-width at or below 0.01 a GO condition, whereas the protocol's adequacy row requires the size to have been chosen for a 0.01 target. The execution log records these as A5 additions, so they are not silent, but the protocol and code should be harmonized before G3.
4. `run.py` `_run_confirmatory` reads `n_clusters`, `route`, and `incumbent` straight from config (defaults 500, superiority, complete_distances) and does not require or verify a route-freeze record. The protocol steps 6 and 7 make the written freeze record a precondition for generating confirmatory seeds. This is a procedural guard gap for G3, not a G1 failure.
5. Only one of the two protocol Section 12 readings is in the execution log: the compact 12-feature resolution is present, but the fourfold reading (worst-case cell ratio against the best non-compact validation reference) is absent.

## 4. Independent rerun (Check 4): PASS

Commands run from the repository root:

1. `PYTHONPATH=src python3 -m pytest tests/ -q -o addopts=""` gave `112 passed in 11.15s`.
2. `PYTHONPATH=src python3 -m tk_pilot.run --stage smoke --workers 2 --max-trajectories 1 --config /tmp/opencode/g1_audit_config.yaml --outdir /tmp/opencode/g1_audit_smoke` exited 0 with `smoke stage complete: 340 rows, wall 248.1 s`.

Deviation from the literal requested command, recorded deliberately: `configs/tk_pilot.yaml` hard-wires `cache_dir: research_review/results/cache`, so the literal command would write into the repository cache, which the audit instruction forbids. The temp config is a byte-for-byte copy of the repository config except for `cache_dir: /tmp/opencode/g1_audit_cache` (SHA256 of the temp config differs only in that line; the `config_file_sha256` of the stored run still matches the repository config). The repository cache listing (198 files with per-file mtimes) is identical before and after the rerun, and no repository cache files were created.

Fresh-cache results: no crash, no `failure.json`; 340 rows; manifest `workers: 2`, wall 248.093 s, peak RAM 189,927,424 bytes, probe 18.715 s; translation check `passed: true` with `max_distance = 0.0` and tolerances 1e-7 at sigma 0 and sigma 0.05, matching the stored run. Against the stored `metrics.parquet`, the rerun has zero `feature_dim` mismatches, zero `valid_fraction` differences, and identical predicted labels for all 340 rows. As noted in Section 2, selected learners differ in 72 of 120 groups because the tie-break uses measured wall time.

## 5. Claims-to-tests coverage (Check 5): PASS with residuals

All ten claims of plan Section 2 appear in `claims_to_tests.yaml` as C1 through C10, each with at least one test and an explicit pass or fail rule. Statuses match the plan: C1 and C2 operational, C3, C4, and C10 withdrawn, and C5 through C9 open. The source obligations SO-01 through SO-10 map the withdrawn or restricted statements to their precluding sources and to the enforcing audit. The prohibited-language scan over the WP-1.2 artifacts, the ledger, the smoke summaries, the execution log, and the implementation contract found no forbidden novelty assertion (the only matches are the withdrawn statements and the `statement_must_not_be_claimed` fields themselves, plus the ledger quoting Khormali's own priority claim).

Residuals. 1. T-C3-02 and T-C4-01 list `research_review/results/phase1/citation_ledger.md`, which does not exist; the ledger is `citation_ledger.yaml`. 2. T-C5-01 and T-C5-02 depend on the variant `compact_ablation_no_speed_change`, which appears nowhere in `src/` or the config, so the C5 rule cannot run at G3 as written. 3. T-C2-02 and T-C8-01 are correctly deferred to the exploratory and confirmatory stages.

## 6. Decision packet PENDING items: resolved versus unresolved

| Packet item | Status | Evidence or remaining gap |
|---|---|---|
| A3 citation ledger path and result | Resolved | `citation_ledger.yaml`; 36 claims, independently spot-checked at the page level |
| Final wording check of the intended contribution sentence | Unresolved | No recorded check artifact; the sentence as written survives the prohibited-language scan, but the packet marker cannot be cleared without a written check |
| Reproducibility memo | Resolved | `reproducibility_status.md`; availability claims for the four required incumbents documented |
| Smoke manifest and report | Resolved | `smoke/manifest.json`, `summary.json`, `metrics.parquet`, `calibration.json`; dimensions, timings, and peak RAM present |
| Baseline API smoke tests, analytic signatures | Resolved by test suite | `tests/test_features.py` analytic straight path and L-shape at 1e-12; 112 tests pass; no standalone report file exists |
| Signature path-coordinate scaling verification | Resolved in substance | `features.build_representations` applies a `moment_scaling` fitted only on the calibration population, which the runner draws from the training namespace (seed 11 in smoke, 1000-1039 in later stages); time stays unscaled; `calibration.json` records `moment_scaling_cells`; logged in the execution log. Packet marker is stale |
| Freeze-time sha256 of protocol and claims-to-tests | Partially resolved | Protocol hash matches and is in both appendices; the claims-to-tests hash is still PENDING in Appendix B; this audit records `a99063ed73f7d3fd...` |
| Independent split-manifest verification | Partially resolved | Base-seed clustering holds by construction, but `diagram_hash` is missing and the smoke namespaces cannot demonstrate cross-split isolation; real check deferred to exploratory |
| Independent smoke feature-dimension rerun | Resolved | This audit, zero mismatches |
| Execution-log entries for the two recorded readings | Partially resolved | Compact 12-feature reading present; the fourfold and eligible-reference reading absent |
| Overall G1 status with evidence sentence | Recorded by this audit | Proposal: CONDITIONAL GO |
| Authorization line for Phase 2 | Recorded by this audit | Authorized for WP-2.1 and the G2 correctness work under the Section 7 conditions; confirmatory seeds remain unauthorized |

Additional packet-level defect: Appendix B repeats the stale `implementation_contract.md` hash `b024c04f...`; current is `c8f48782...`.

## 7. Proposed G1 decision: CONDITIONAL GO

The WP-1.1 pass criterion is met: every novelty-sensitive statement checked resolves to an exact equation, definition, or theorem, all required locators reproduced independently, and the one locator defect found (the email page number) does not affect any claim. The WP-1.2 pass criterion is met in substance: an independent rerun obtains identical feature dimensions and valid fractions, the comparator set and equal-tuning rules are frozen, the translation control passes at the frozen tolerance, all ten representations are present in the results table, and the smoke stage completes well inside the 20-minute envelope at 2 workers. Phase 2 (WP-2.1 and the G2 raw-data correctness ladder) may proceed.

The decision is conditional rather than unconditional because four record-keeping and enforcement gaps remain. None of them invalidates the smoke correctness evidence, but each must be repaired before the artifacts they affect are used.

1. Before G2 consumes WP-1.2 outputs: append the missing execution-log entries (the eligible-comparator reference reading and the `implementation_contract.md` hash change), freeze the `claims_to_tests.yaml` hash `a99063ed73f7d3fd...` in the decision packet Appendix B, and correct the two `citation_ledger.md` artifact paths to `citation_ledger.yaml`.
2. Before the exploratory split manifest is used: add the protocol-required `diagram_hash` column or amend protocol Section 4 explicitly, and rerun the base-seed isolation check on the real training, validation, and exploratory namespaces.
3. Before G3 confirmatory authorization: implement `compact_ablation_no_speed_change` or restate T-C5-01 and T-C5-02, record the divergence between `evaluate.decide` statuses and the protocol table (or harmonize them), and add a route-freeze guard so confirmatory seeds cannot be generated without a freeze record containing the timestamp, hashes, chosen size, route, and eligible comparator list.
4. Record in the execution log that model selection in tied cells is pinned by the frozen record, not bitwise reproducible.

## 8. Evidence hashes (sha256, 16-hex prefixes for readability)

| Artifact | sha256 prefix |
|---|---|
| `citation_ledger.yaml` | `0084f94427bb3111` |
| `reproducibility_status.md` | `40fcb48f17b862b5` |
| `baseline_protocol.md` | `1a31cb509bad64b0` |
| `claims_to_tests.yaml` | `a99063ed73f7d3fd` |
| `decision_packet_G1.md` | `8989feaeafe17c63` |
| `implementation_contract.md` (current) | `c8f48782514974b5` |
| `implementation_contract.md` (frozen in Appendix B) | `b024c04f5126c8c5` (stale) |
| `EXECUTION_LOG.md` | `c5ec4fabe2210012` |
| `smoke/manifest.json` | `59262f673de680c4` |
| `smoke/summary.json` | `cedf804166fe072b` |
| `smoke/metrics.parquet` | `43a808c8061d28c8` |
| `smoke/split_manifest.csv` | `2c2df8f32ced107b` |
| `smoke/calibration.json` | `af5e943b0b5cf1e8` |
| `src/tk_pilot/features.py` | `44be21c2518d4720` |
| `src/tk_pilot/signatures.py` | `23864ae5cc217f72` |
| `src/tk_pilot/models.py` | `7f17c51c8f9a9c1a` |
| `src/tk_pilot/evaluate.py` | `f13263a355a4f0c0` |
| `src/tk_pilot/run.py` | `82a4a261e7bb6ad2` |
| `configs/tk_pilot.yaml` | `1862b1bb58c4dded` (matches stored smoke manifest) |

Location mtimes supporting the freeze sequence: `baseline_protocol.md` 21:35:09, `claims_to_tests.yaml` 21:35:55, `decision_packet_G1.md` 21:37:00, `citation_ledger.yaml` 21:38:39, smoke outputs 22:21 to 22:24, `implementation_contract.md` 22:25:18, `EXECUTION_LOG.md` 22:25:26 (local time, 2026-09-20).

Verification artifacts of this audit: `/tmp/opencode/g1_audit_smoke/` (fresh-cache smoke run), `/tmp/opencode/g1_audit_config.yaml` (cache-redirected config), `/tmp/opencode/g1_audit_cache/`, `/tmp/opencode/tk_pdfs_g1audit/` and `/tmp/opencode/tk_pages/` (per-page PDF extracts).
