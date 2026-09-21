# G3 simulation gate: independent verification report

Auditor: independent verification pass for the G3 simulation gate (WP-3.4), adversarial and
read-only. Working directory: `/home/hugo_souto/Stuff/Research/Topological_Kinematics`. Date:
2026-09-21. No source artifact was modified, no git operation was performed, and the verification
used one worker process per script with a total runtime under 15 s (well inside the two-process and
twenty-minute constraints). The two deliverables are this file and
`research_review/results/g3/verification/g3_verification.json`.

## 1. Artifact integrity

The exploratory metrics table has 10,800 rows (7,200 test and 3,600 validation, all `status = ok`,
degree 0, ten representations, 12 test cells with 60 trajectories each). The top-level copy
`research_review/results/g3/metrics.parquet` is byte-identical to
`research_review/results/g3/exploratory/metrics.parquet` (both SHA256
`cf1123dceb46fa591ca20cef5f9d290ef3ab98412a0ee7f78d669eda4a604790`), and that hash equals the
`exploratory_metrics_sha256` recorded in `g3_decision.json`. The split manifest contains 600 unique
trajectory identifiers (240 train, 120 validation, 240 test) with no duplicate identifiers and the
frozen seed namespaces 1000-1019, 2000-2009, and 3000-3019.

## 2. Verdict summary

| Check | Verdict | One-line result |
|---|---|---|
| 1. Per-cell macro errors | PASS | compact and raw_geometry_flat are 0.0 in all 12 test cells; speed_history equal-weight test error 0.0152778 |
| 2. Paired cluster bootstrap | PASS | 2000 resamples, seed 20260907, 120 clusters: delta 0.0, interval [0, 0]; Bonferroni family bounds [0, 0] for A and B |
| 3. Incumbent selection rule | PASS | incumbent raw_geometry_flat; full validation ranking and the seven-member eligible set reproduce exactly |
| 4. Parsimony ratios | PASS | dimension ratios 0.6154 to 0.9231, cost ratios 0.0544 to 0.9675, all below the fourfold threshold; cheapest eligible comparator cheaper than compact in all 12 cells |
| 5. Independent raw ceiling probe | PASS | one seed per class at sigma 0.05 and stride 4: nearest centroid on a raw-frame scalar separates 3 of 3 classes in both families; extended Family A 60 of 60, Family B 47 of 60 |
| 6. Confirmatory seeds closed | PASS | no seed at or above 10000 anywhere in the cache or results; `confirmatory_seeds_opened` is false |
| 7. Memo numeric spot checks | PASS with 2 minor residuals | 20 of 24 claims exact, 2 with caveats, 2 residuals (Family B onset wording, campaign wall time) |
| 8. Decision rule application | PASS | `evaluate.decide` returns PIVOT for both frozen routes; no simulation GO is claimed anywhere |

Proposed final status: PIVOT, in agreement with the recorded decision. No check failed.

## 3. Check details

### Check 1. Per-cell macro balanced errors (PASS)

Command: `python3 /tmp/opencode/g3_audit/check_metrics.py` (2.9 s, imports the frozen
`tk_pilot.evaluate` for the rule-faithful recomputation), with an independent manual
recomputation in `python3 /tmp/opencode/g3_audit/check_independent.py` (2.7 s).

Recomputed with `evaluate.cell_table(test, split="test")` over 12 cells of 60 trajectories: compact
error 0.0 in all 12 cells and raw_geometry_flat error 0.0 in all 12 cells, so the twelve-cell zero
pattern is confirmed. The independent manual macro-error implementation (mean over the classes
present of the per-class misclassification rate) reproduces the same zeros, and a direct row check
shows 720 of 720 test predictions correct for compact and 720 of 720 for raw_geometry_flat.

Equal-weight test macro error by representation:

| Representation | Test equal-weight error | Validation equal-weight error |
|---|---|---|
| compact | 0.0000000 | 0.0027778 |
| raw_geometry_flat (incumbent) | 0.0000000 | 0.0000000 |
| raw_geometry_summary | 0.0000000 | 0.0083333 |
| complete_distances | 0.0041667 | 0.0000000 |
| moment_signature_time | 0.0041667 | 0.0111111 |
| moments_summary | 0.0055556 | 0.0000000 |
| moments_flat | 0.0069444 | 0.0000000 |
| moment_signature | 0.0125000 | 0.0222222 |
| speed_history | 0.0152778 | 0.0138889 |
| recurrence_summary | 0.0458333 | 0.0250000 |

speed_history is nonzero in 5 of 12 test cells: A sigma 0.05 strides 1, 2, 4 give 0.016667,
0.066667, 0.016667; B sigma 0 gives 0.05 at stride 1; B sigma 0.05 gives 0.033333 at stride 1. All
other speed_history cells are zero.

### Check 2. Paired cluster bootstrap and Bonferroni bounds (PASS)

Frozen recomputation: `evaluate.paired_cluster_bootstrap(test, reference="raw_geometry_flat",
candidate="compact", n_resamples=2000, seed=20260907)` and
`evaluate.family_deterioration_bounds(...)` with the same settings. Result: delta 0.0, percentile
interval [0.0, 0.0], 120 clusters, 12 cells, and all 2000 bootstrap deltas exactly 0.0 (one unique
value). Family bounds: A delta 0.0, interval [0.0, 0.0], 60 clusters; B delta 0.0, interval
[0.0, 0.0], 60 clusters, using the two-sided Bonferroni level 0.05/2 = 0.025.

An independent numpy reimplementation (count arrays, same seed, no call into `tk_pilot.evaluate`)
reproduces delta 0.0, interval [0, 0], the same 120 clusters, and both family bounds [0, 0]. The
recorded values in `analysis_degree0.json` match exactly.

Residual observation R1: because both methods are perfect in every cell, the interval is degenerate
by construction. It is not an informative precision statement, only a structural consequence of the
ceiling. The decision rule's precision check is satisfied trivially (half-width 0 at most 0.01).

### Check 3. Incumbent selection rule (PASS)

The frozen rule is the best non-compact representation by equal-weight cell-averaged validation
macro balanced error, with ties broken by lower validation end-to-end cost, then lower postprocessed
dimension, then contract order. Recomputing the validation cell table and the ranking gives exactly
the recorded order:

| Rank | Representation | Val error | Val cost (s) | Feature dim | Contract order |
|---|---|---|---|---|---|
| 1 | raw_geometry_flat | 0.0000000 | 2.231536 | 378.333 | 4 |
| 2 | moments_summary | 0.0000000 | 4.276446 | 12.000 | 7 |
| 3 | moments_flat | 0.0000000 | 4.276447 | 454.000 | 6 |
| 4 | complete_distances | 0.0000000 | 4.567595 | 3621.333 | 2 |
| 5 | compact | 0.0027778 | 4.567583 | 13.000 | 0 |
| 6 | raw_geometry_summary | 0.0083333 | 2.231536 | 10.000 | 5 |
| 7 | moment_signature_time | 0.0111111 | 4.276468 | 56.000 | 9 |
| 8 | speed_history | 0.0138889 | 4.567586 | 80.667 | 1 |
| 9 | moment_signature | 0.0222222 | 4.276445 | 42.000 | 8 |
| 10 | recurrence_summary | 0.0250000 | 4.567597 | 9.000 | 3 |

The best non-compact representation is raw_geometry_flat (rank 1), so the incumbent is confirmed.
Within the zero-error tie group raw_geometry_flat is the cheapest at 2.231536 s. Note that
raw_geometry_summary has a marginally lower recorded cost (2.231535865 versus 2.231536400) but a
validation error of 0.0083333, so it never enters the tie-break at zero error. The eligible
comparator set (validation error at most 0.02 above the incumbent's 0.0) is exactly raw_geometry_flat,
moments_summary, moments_flat, complete_distances, raw_geometry_summary, moment_signature_time, and
speed_history, matching `analysis_degree0.json`. moment_signature (0.0222222) and recurrence_summary
(0.025) are correctly excluded.

### Check 4. Parsimony computation (PASS)

Recomputed from the metrics table (per-cell median of `feature_seconds + prediction_seconds`, plus
`extraction_seconds` for non-raw representations; `distance_seconds` is not carried in the metrics
table, which explains the sub-percent differences below). The per-cell dimension ratio is the
smallest eligible feature dimension over compact's 13, and the cost ratio is the smallest eligible
cost over compact's per-cell cost.

| Cell | Dim ratio (recomputed) | Dim ratio (recorded) | Cost ratio (recomputed) | Cost ratio (recorded) | Cheapest comparator |
|---|---|---|---|---|---|
| A sigma 0 stride 1 | 0.9231 | 0.9231 | 0.2439 | 0.2438 | raw_geometry_summary |
| A sigma 0 stride 2 | 0.9231 | 0.9231 | 0.1484 | 0.1483 | raw_geometry_flat |
| A sigma 0 stride 4 | 0.9231 | 0.9231 | 0.0844 | 0.0844 | raw_geometry_summary |
| A sigma 0.05 stride 1 | 0.9231 | 0.9231 | 0.4250 | 0.4249 | raw_geometry_summary |
| A sigma 0.05 stride 2 | 0.9231 | 0.9231 | 0.2652 | 0.2650 | raw_geometry_summary |
| A sigma 0.05 stride 4 | 0.9231 | 0.9231 | 0.1672 | 0.1670 | raw_geometry_flat |
| B sigma 0 stride 1 | 0.6154 | 0.6154 | 0.1865 | 0.1858 | raw_geometry_summary |
| B sigma 0 stride 2 | 0.6154 | 0.6154 | 0.0933 | 0.0931 | raw_geometry_summary |
| B sigma 0 stride 4 | 0.6154 | 0.6154 | 0.0544 | 0.0540 | raw_geometry_flat |
| B sigma 0.05 stride 1 | 0.6154 | 0.6154 | 0.9675 | 0.9674 | raw_geometry_summary |
| B sigma 0.05 stride 2 | 0.6154 | 0.6154 | 0.9068 | 0.9066 | raw_geometry_flat |
| B sigma 0.05 stride 4 | 0.6154 | 0.6154 | 0.8530 | 0.8522 | raw_geometry_summary |

The recorded parsimony ratio 0.6153846 equals the minimum dimension ratio (Family B, 8 over 13), and
the recorded worst cost ratio 0.0540370 equals the minimum cost ratio (B sigma 0 stride 4). Both are
far below the frozen fourfold threshold 4.0. Robustness to the aggregation: the maximum dimension
ratio over cells is 0.9231 and the maximum cost ratio is 0.9675, still below 4.0, so parsimony fails
under either the implemented minimum-over-cells aggregation or a true maximum-over-cells reading.
The cheapest eligible comparator is cheaper than compact in every one of the 12 cells (all cost
ratios below 1). The selection table (1,920 rows, 120 cell-representation fits, one selected learner
each) confirms the postprocessed dimensions used here.

Residual observations R2 and R3: `run.py` aggregates the ratio as the minimum over cells, so the
memo's "worst-case" wording is inaccurate (it is the most favorable cell); and the per-cell compact
cost varies from about 0.49 s to 9.9 s because extraction timings are reused from cache-hit timing
files, so the minimum cost ratio is timing-sensitive. Neither changes the below-threshold conclusion.

### Check 5. Independent raw-data ceiling probe (PASS)

Command: `python3 /tmp/opencode/g3_audit/check_raw_probe.py` (5.7 s, one process). The probe calls
`tk_pilot.generators.build_trajectory` directly and never reads a cached diagram, distance matrix,
or feature table. The scalar is computed from raw frames only: per frame, Family A uses the maximum
pairwise Euclidean distance of the 64 points and Family B uses the field peak separation (twice the
field-weighted standard deviation in x of the clipped 32 by 32 field); the trajectory scalar is the
temporal variance of the per-frame separation across the 33 frames at sigma 0.05 and stride 4.

Required probe (one test seed per class, seed 3000): Family A scalars return 0.648954, ramp
0.982412, jump 1.516038; Family B scalars return 0.041159, ramp 0.084242, jump 0.131343. A
nearest-centroid rule on that single scalar classifies 3 of 3 classes correctly in both families,
with each class's scalar closer to its own centroid than to either other centroid.

Extended probe (centroids fitted on train seeds 1000-1019, evaluated on test seeds 3000-3019):
Family A 60 of 60; Family B 47 of 60 with the single variance scalar and 52 of 60 with a
three-scalar variant (mean, variance, maximum absolute frame-to-frame change). The ceiling claim is
therefore corroborated at the required minimal level, and it is consistent with the actual
raw_geometry_flat representation's 0 error in all 12 cells.

Adversarial detail: the naive temporal mean and temporal maximum of the separation do not separate
ramp from jump for Family A across the seed population (mean gap -0.0004 with pooled sd 0.168; max
gap 0.04 with pooled sd 0.12), even though both happen to separate seed 3000. The temporal variance
is the robust choice (gaps 0.27 with pooled sd 0.039 and 0.60 with pooled sd 0.043). A one-seed-per-
class probe alone is a weak test; the extended probe and the actual study table carry the weight.

### Check 6. No confirmatory seed opened (PASS)

Command: `python3 /tmp/opencode/g3_audit/check_claims.py` (2.1 s). Scanning all directories under
`research_review/results` finds 50 numeric seed directories, exactly 1000-1019, 2000-2009, and
3000-3019; no path component anywhere has five or more digits. The metrics table and the split
manifest stop at seed 3019. The 176 `degree1.npz` files also belong to seeds 3000-3019. Searching
the g3 artifacts for the literal `10000` returns only the frozen namespace declaration, the
`untouched_confirmatory_seed_start` field, and the memo sentence about the new protocol.
`g3_decision.json` records `status: PIVOT`, `confirmatory_authorized: false`, and
`confirmatory_seeds_opened: false`. The flag is confirmed.

### Check 7. Spot checks of numeric claims in the gate memo (PASS with residuals)

Twenty-four claims were checked against the artifacts: 20 pass exactly, two pass with caveats (the
H1 176 count has an unrecorded "about 300" denominator, and the pre-outcome Amendment 1 claim is
verified by file timestamps rather than by a log), and two are residuals. The requested categories
all pass: rows (10,800), wall time (839.7 s in `manifest.json`), peak RAM (292,454,400 bytes, 292.5
MB decimal), validation ranking (top four at zero error, compact at 0.0027778), coverage fractions
(compact valid_fraction 0.2011877 and all other representations 1.0; coverage 0.5 for all ten
representations), and nulls verdicts (static_null RESIDUAL, matched_ordering PASS, time_reparam
PASS, raw_preserving PASS, coarse_sampling PASS, adversarial_matrix RESIDUAL). Additional checks
pass: the 20/10/20 grid reduction, the delta and Bonferroni bounds, the seven-member eligible set,
the 0.615/0.054 parsimony ratios, the matched-ordering 20 of 20 plus 5 of 5 separation, the exact
degeneracy of the static null at sigma 0, the zero rotation and translation distances, the coarse
sampling verdicts, the 13 of 13 WP-2.2 checks with the triangle inequality on 21,216 triples, the
Family A slopes 0.999438 and 0.993658, the pre-outcome Amendment 1 timestamp (protocol written at
00:17 local, first run started at 01:13), and the 176 H1 distance-matrix files.

Two residuals are recorded. R5: the memo's supporting "Family B finite-H0 onset at z about 0.89"
does not match the measured onset windows in the raw-correctness report, which are z in [0.921461,
0.954484] for seed 11 and [0.977873, 1.00682] for seed 12; the value 0.899 is the seed-12 ramp
latent z and 2w. R4: the 839.7 s wall is the runner-reported H0 pass of the final supervised run;
`exploratory_run.log` shows eight supervisor timeouts with exit code 124 from 01:13 to 05:40 local,
with the H0 artifacts written at 04:19, so the campaign-level wall time is about 4.4 h. Neither
residual changes a decision input, and both are reported rather than hidden in the memo's own
limitations section (the memo does mention the overnight compute window).

### Check 8. Decision rule application (PASS)

`evaluate.decide({"lower": 0.0, "upper": 0.0}, 0.6153846153846154, bounds, None, route)` returns
PIVOT for `route = "superiority"` and for `route = "parsimony"`. In both cases the reasons are "the
compact representation is noninferior but neither frozen route's advantage is established" and
"noninferiority margin met (upper endpoint below 0.02)". The checks are: superiority false (upper 0
is not below -0.05), noninferiority true (upper 0 is below 0.02), parsimony false (0.6154 is below
4.0), family_ok true (both family upper endpoints 0 at most 0.05), precision_ok true (half-width 0
at most 0.01), and the lower endpoint is not above zero, so INCREMENTAL-ONLY is not triggered.
`analysis_degree0.json` records PIVOT for both routes, `recommended_route` is null,
`route_recommendation.json` reports both statuses as PIVOT with no recommended route, and
`g3_decision.json` is PIVOT. No simulation GO is claimed anywhere: the only GO strings in the g3
artifacts are the pre-existing C1 and C2 operational claim statuses in `claims_matrix.yaml`, which
are not a gate authorization, and the historical G1 CONDITIONAL GO and G2 PASS records, which do not
authorize confirmatory seeds. `confirmatory_authorized` and `confirmatory_seeds_opened` are both
false.

## 4. Residual gaps

R1. The [0, 0] bootstrap interval is degenerate because both methods are perfect in every cell; all
2,000 resampled deltas are exactly zero. It should be read as "no observed difference at ceiling",
not as a precise zero estimate, and the decision rule's precision check is satisfied structurally.
No decision impact.

R2. The parsimony aggregation is a minimum over cells (most favorable cell) while the memo calls it
worst case. The true maximum over cells is 0.9231 (dimension) and 0.9675 (cost), still below the
fourfold threshold. No decision impact.

R3. Cost ratios depend on cached timing reuse, so the exact 0.054 is not platform-stable; the
qualitative conclusion (raw geometry is cheaper in every cell) is robust because raw geometry skips
diagram extraction and distance work by construction. No decision impact.

R4. The memo's 839.7 s wall time omits the roughly 4.4 h supervised campaign with repeated exit-124
timeouts. Reporting residual only.

R5. The Family B onset wording (0.89 versus measured 0.92 to 1.01) and the H1 "about 300"
denominator (176 files exist; 240 test-only H1 masters expected, 360 with validation) are minor
imprecisions in supporting claims. No decision impact.

R6. The crude single-scalar Family B probe is imperfect across the full test population (47 of 60);
the required minimal probe passes and the actual raw geometry representation is at zero error, so
the ceiling claim stands. No decision impact.

## 5. Adversarial observations

1. The ceiling is a task-design property, not a property of the compact diagnostics: a scalar
computed from raw frames alone already separates the classes at the required probe, and the raw
geometry baseline is at zero error everywhere.
2. Compact test accuracy is perfect even though its angle validity fraction falls to 0.002 to 0.06
at sigma 0.05 (mean 0.2012 over the test split). The perfect score therefore does not come from the
angle or ordering channel, which supports the memo's C5 INDETERMINATE reading rather than any
positive diagnostic claim.
3. The [0, 0] interval and the zero `required_clusters` in the size recommendation are degenerate
consequences of the ceiling; a future protocol needs a difficulty pilot that enforces non-ceiling
accuracy, exactly as the memo's recommended new protocol states.
4. The incumbent tie-break uses measured end-to-end validation cost, which is cache and platform
sensitive; within the zero-error group raw_geometry_flat is cheapest, so the incumbent is stable to
small timing perturbations, but the rule is not bitwise reproducible across platforms.
5. No confirmatory seed was opened and the route is unresolved; the suggested superiority route with
200 clusters in `route_recommendation.json` is a suggestion only and authorizes nothing.

## 6. Proposed final status

PIVOT, confirming the recorded decision. The frozen decision function returns PIVOT for both route
choices on the recorded statistics, and every decision input reproduces independently: twelve
zero-error cells for both methods, delta [0, 0] with Bonferroni bounds [0, 0], parsimony ratio
0.6154 far below the fourfold threshold, incumbent raw_geometry_flat, and the frozen route
unresolved. The confirmatory stage is not authorized and no seed at or above 10000 was opened.
INCREMENTAL-ONLY would require the lower interval endpoint to be strictly above zero, which the
frozen rule does not support; the memo's note that INCREMENTAL-ONLY is a defensible alternative
policy reading is honest, but it is not the rule output. The audit finds no disagreement with the
recorded PIVOT. The recommended next step is to adopt the memo's new protocol only after a
difficulty pilot demonstrates a non-ceiling regime, with the route and comparator set frozen in
writing before any confirmatory seed is opened.

## 7. Reproduction

Scripts (all read-only with respect to the repository; they write only under
`/tmp/opencode/g3_audit` and the two verification deliverables):

```
cd /tmp/opencode/g3_audit
python3 check_metrics.py         # checks 1 to 4 and 8, frozen functions plus metrics recomputation (2.9 s)
python3 check_independent.py     # independent macro error and bootstrap reimplementation (2.7 s)
python3 check_raw_probe.py       # check 5, raw generator probe (5.7 s)
python3 check_claims.py          # checks 6 and 7, seed scan and memo claims (2.1 s)
python3 assemble_verification.py # writes g3_verification.json (0.1 s)
```

Each script runs as a single process. The machine-readable companion file
`research_review/results/g3/verification/g3_verification.json` carries the full check evidence,
residuals, adversarial observations, and the proposed status.
