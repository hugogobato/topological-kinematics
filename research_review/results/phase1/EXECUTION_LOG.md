# Execution log: Phases 1-3 (WP-1.1 through WP-3.4)

Coordinator: orchestration session 2026-09-20. This log records decisions, contract deviations,
agent workstreams, and resource measurements. It is append-only during the night run.

## Frozen schedule

1. Package build (WP-1.1 baselines + WP-1.2 protocol + WP-2.1/2.2/3.x implementation).
2. Smoke stage (pilot Stage 1): correctness, resources, controls.
3. G1 decision (after citation ledger, baseline smoke tests, protocol freeze).
4. Raw correctness ladder (WP-3.1) + diagnostics stability (WP-2.2) -> G2 decision.
5. Exploratory stage (WP-3.2/3.3) -> freeze route + confirmatory size -> Colab shards.
6. Confirmatory stage -> G3 gate memo (WP-3.4).

## Contract deviations

| Date/time | Module | Change | Reason |
|---|---|---|---|
| 2026-09-20 | features.compact | Resolved inherited "six speed and speed-change summaries" ambiguity by adding mean signed speed-change to the five named quantities; compact is therefore 12 features | Phase 0 deviations log deferred the count to the WP-1.2 feature-schema freeze |
| 2026-09-20 | features raw_geometry | Split into `raw_geometry_flat` and `raw_geometry_summary`; moments likewise | The pilot specification requires both flatten and temporal mean/std comparisons; separate names keep feature-dimension accounting exact |
| 2026-09-20 | features + run moment signature scaling | Added `moment_scaling` to `build_representations` and fit it per cell on the predeclared training-split static-noise trajectories at sigma = 0.05, the same population used for the noise floor; the six moment coordinates are standardized before the level-2 signature | Pilot specification section 3 requires coordinate scaling fit on training data; standardizing after the nonlinear signature is not equivalent |
| 2026-09-20 | generators cache | Generator cache nests an extra `trajectory/` level under `sigma{tag}/stride{s}/` so it can coexist with the diagram cache under the same cell directory | Both caches write `meta.json` and `SHA256SUMS`; co-location in one directory would corrupt one of them. Regression test covers coexistence |

## Agent workstreams

| Agent | Work package | Deliverables | Status |
|---|---|---|---|
| A1 | WP-1.2 schema: generators, splits, config | `generators.py`, `splits.py`, `configs/tk_pilot.yaml`, tests | launched |
| A2 | WP-2.1 interface: persistence, cache, pooling | `persistence.py`, tests | launched |
| A3 | WP-1.1 citations and reproducibility | citation ledger, reproducibility memo | launched |
| A4 | WP-1.1 baselines: features, signatures | `features.py`, `signatures.py`, tests | launched |
| A5 | WP-1.2 fair learner protocol: models, evaluate, run | `models.py`, `evaluate.py`, `run.py`, tests | launched |
| A6 | WP-1.2 protocol document and claims-to-tests | `baseline_protocol.md`, `claims_to_tests.yaml`, split manifest | launched |

## Resource measurements

| Date/time | Measurement | Value |
|---|---|---|
| 2026-09-20 | Logical CPUs (lscpu) | 8 |
| 2026-09-20 | Total/available RAM | 23 GB / 20 GB |
| 2026-09-20 | Family A VR H0+H1 persistence, 129 frames | 2.9 s |
| 2026-09-20 | Family A full H0 bottleneck matrix, 129 frames | ~15.9 s |
| 2026-09-20 | Family A full H1 bottleneck matrix, 129 frames | ~2.1 s |
| 2026-09-20 | Family B cubical H0+H1 persistence, 129 fields | 0.6 s |
| 2026-09-20 | Family B full H0 bottleneck matrix | ~0.1 s |

| Date/time | Measurement | Value |
|---|---|---|---|
| 2026-09-20 22:20 | Smoke probe (1 trajectory per cell) single trajectory cost | 18.7 s, peak RAM 122 MB |
| 2026-09-20 22:35 | Full smoke stage (clean cache, 4 workers, 46 trajectories, 340 rows) | wall 168.7 s, user CPU 536 s, peak RAM 191 MB |
| 2026-09-20 22:35 | Rigid-translation control, Family A, degrees 0, sigma 0 and 0.05 | max diagram distance 0.0, tolerance 1e-7 x max(1, range), passed |

| Date/time | Measurement | Value |
|---|---|---|
| 2026-09-20 22:20 | Cache size after smoke stage | 14 MB, 198 files |

| Date/time | Module | Change | Reason |
|---|---|---|---|
| 2026-09-20 23:55 | configs/tk_pilot_study.yaml + run.py degree_families | Pre-outcome exploratory grid reduction: base seeds 20/10/20 instead of 40/20/40 (train 1000-1019, validation 2000-2009, exploratory test 3000-3019); degree 1 secondary channel restricted to Family A | The exact primary metric (G2 amendment) costs ~7.1 min per noisy Family B trajectory for H0+H1; the full grid projects to ~84 core-hours (14 h at 6 workers), which is infeasible in the overnight window. The pilot specification explicitly permits reducing the exploratory grid before running it with the change recorded; no classification outcomes had been inspected. Family B finite H1 at sigma=0 is empty, and at sigma=0.05 it is noise-dominated (median bar persistence 0.042, more than 150 bars at 32x32 resolution), so it is reported descriptively rather than through the full matrix. The confirmatory stage remains the primary inferential stage and will use new test seeds and Colab shards. |

## Decisions

| Date/time | Gate | Decision | Evidence |
|---|---|---|---|
| 2026-09-20 | G0 | passed (pre-existing) | `research_review/results/phase0/G0_decision.md` |

## Notes

- 2026-09-20 22:40: The WP-2.x and WP-3.1 agents were launched in parallel with the independent G1 audit to keep the
  critical path short. Their outputs are conditional on the written G1 record, which is issued before any G2 decision.
- The first A1 attempt returned no deliverables; the retry delivered `generators.py`, `splits.py`, the config, and tests.
  No other module was affected.

## A5 contract additions and deviations (WP-1.2)

| Date | Module | Change | Reason |
|---|---|---|---|
| 2026-09-20 | `evaluate.decide` | Added the `frozen_route` argument and made adequate precision a GO condition; the no-route unresolved case with lower endpoint at or below zero returns INDETERMINATE | WP-1.2 task freezes the route as a `decide` input; pilot section 5 lists adequate precision as a GO requirement and `baseline_protocol.md` section 6 fixes the unresolved case |
| 2026-09-20 | `evaluate` | Added `cell_table`, `equal_weight_cell_average`, and `family_deterioration_bounds` (Bonferroni over the two families) around the frozen `macro_balanced_error` and `paired_cluster_bootstrap` | The runner must assemble the per-cell table and the simultaneous family bounds; the frozen names remain unchanged |
| 2026-09-20 | `models.fit_select_predict` | The returned dict is additive over the contract keys: `val_grid`, `val_predictions`, `test_predictions`, `nominal_dim`, and split prediction-second totals; `feature_dim` is the postprocessed dimension | `baseline_protocol.md` section 7 records the postprocessed dimension as the table `feature_dim` and the SVM gamma scale; the extra keys feed the results table and cost accounting |
| 2026-09-20 | `models` | Added `select_validation_winner` as the pure selection rule used by `fit_select_predict` | Makes the validation error, prediction seconds, learner name tie-break directly testable |
| 2026-09-20 | `run.py` | Distance matrices are cached under `{cache_dir}/runner_distances/` and trajectory timings under `{cache_dir}/runner_timings/`; stride 2 and 4 subsample the stride-1 diagrams and distance matrix rather than recomputing persistence | Contract requires cached distance matrices and per-trajectory timing accounting; stride variants are exact subsamples |

## G2 primary metric backend amendment

| Date | Module | Change | Reason |
|---|---|---|---|
| 2026-09-21 | `diagram_metrics` | Added exact solver `bottleneck_exact` and pointed the primary alias `bottleneck_linf` at it; `bottleneck_gudhi` retained for audit only | WP-2.2 found the frozen `gudhi.bottleneck_distance` (gudhi 3.12.0) order dependent and incorrect on real pilot diagrams, breaking the triangle inequality; the interface amendment is recorded in `research_review/metric_interface.md` and the ledger key `diagram_metric.primary.amendment_g2` |

Witness and regeneration note. The minimal witness pair in `research_review/results/g2/diagnostics/metric_backend_witness.json` has exact value 0.3985347143760231 (project brute force, persim, and an independent SciPy binary-search solver agree); gudhi `e=None` on the canonical order returns 0.41061420919138303 and gudhi `e=0.0` returns 0.6650287460769155. The invalidated `research_review/results/cache/runner_distances/` tree was deleted and regenerated by the clean smoke rerun `PYTHONPATH=src python3 -m tk_pilot.run --stage smoke --workers 4 --outdir research_review/results/phase1/smoke`, which completed in 724.7 s with 46 trajectories, 340 rows, and both translation checks passing at max distance 0.0; afterwards `scripts/run_wp31_ladder.py --out research_review/results/g2 --workers 3` (exit 0, 70 jobs ok, wall 242.2 s, checks 1, 2, 5, 6 PASS and checks 3, 4 RESIDUAL), `scripts/run_wp21_interface.py` (exit 0, outputs regenerated), and `scripts/run_wp22_diagnostics.py --workers 2` (exit 0, wall 342.6 s, both labelled backends pass and the frozen-versus-exact table difference is now 0.0) were re-run. Diagram caches were not invalidated because persistence extraction does not call the metric.

| 2026-09-20 23:58 | Smoke | Smoke stage wall | 724.7 s with exact metric, 4 workers, peak RAM 208 MB |
