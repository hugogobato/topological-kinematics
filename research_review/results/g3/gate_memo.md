# G3 simulation gate memo (WP-3.4)

**Decision.** The predeclared simulation rule returns **PIVOT** for the frozen formulation. The
confirmatory stage is **not authorized**, no confirmatory test seed was opened, and no application
work (WP-4.1) is unlocked. The exploratory evidence, the raw-correctness ladder, the null and
stress controls, and the metric amendment are recorded below. This memo follows
`Pilot_Experiment_Specification.md` sections 4, 5 and 7 and the research plan WP-3.4.

## What was run

The exploratory grid used 20 training, 10 validation, and 20 exploratory test base seeds per
(family, class), `sigma in {0, 0.05}`, strides 1, 2, 4, degree H0 primary for both families, with
degree H1 predeclared as a secondary channel (its pass did not complete; see the limitations).
The reduction from 40/20/40 to 20/10/20 was recorded in `baseline_protocol.md` Amendment 1 before
any classification outcome was inspected, with the exact-metric cost measurement as the reason.
The primary metric is the exact augmented-matching bottleneck solver after the G2 amendment; the
defective gudhi backend is retained for audit only.

Artifacts: `exploratory/metrics.parquet` (10,800 rows), `exploratory/exploratory_report.md`,
`exploratory/analysis_degree0.json`, `exploratory/route_recommendation.json`,
`exploratory/figures/`, `../g3/splits/exploratory_split_manifest.csv`,
`reports/wp33_nulls_report.md`, `../g2/reports/raw_correctness_report.md`.

## Primary result

Every one of the twelve `(family, sigma, stride)` cells has zero macro balanced error for the
compact diagnostic representation and for the validation-selected incumbent `raw_geometry_flat`.
The paired cluster bootstrap over 120 `(family, class, base_seed)` clusters gives delta 0.0000
with a 95 percent interval of [0.0000, 0.0000]; the Bonferroni family bounds are [0, 0] for both
families. The validation ranking puts `raw_geometry_flat`, `moments_summary`, `moments_flat`, and
`complete_distances` at zero validation error, with `compact` at 0.0028. The eligible comparator
set is `raw_geometry_flat`, `moments_summary`, `moments_flat`, `complete_distances`,
`raw_geometry_summary`, `moment_signature_time`, and `speed_history`. The worst-case parsimony
ratio is 0.615 (dimension) and 0.054 (cost), both below the frozen fourfold threshold, and the
cheapest eligible comparator is cheaper than the compact representation.

Interpretation. The three-class task is at ceiling: the latent classes (triangular return,
monotone ramp, step jump) are separated perfectly by the compact diagnostics and by raw geometry
in every cell. The experiment therefore cannot discriminate between the proposed diagnostics and
the strongest simple baseline, and it cannot test the central hypothesis, which concerns
reversible restructuring versus persistent drift under conditions where speed summaries fail.
The outcome matches the plan's expectation that these simple generators give raw geometric
baselines a strong opportunity to win, and it is a task-design result rather than evidence
against topological diagnostics.

Decision-rule application. The frozen rule maps noninferiority without superiority or parsimony
to PIVOT: "a reproducible but narrower useful result gives PIVOT, with a new protocol and
untouched test seeds". Reliable domination by a cheaper incumbent would give INCREMENTAL-ONLY for
this diagnostic task; the observed tie at zero error with a cheaper incumbent is recorded as
PIVOT by the predeclared function, and INCREMENTAL-ONLY is noted as a defensible alternative
reading. Either way the confirmatory stage as designed must not run, and no simulation GO is
claimed.

## Supporting evidence

Raw-data correctness (WP-3.1, `../g2/reports/raw_correctness_report.md`): static controls are
exactly zero at sigma 0; smooth deformation gives bounded monotone responses (Family A slope
0.99 to 1.00 against latent increments, Family B finite-H0 onset at z about 0.89); topology
changes are verified through the largest finite H0 death and H1 because the literal H0
cardinality criterion is mis-specified for Rips connectivity; the noisy null shows no systematic
temporal events, with the configuration-specific calibration transfer recorded as a coverage
caveat; the sampling bound holds; rigid translation is exactly zero under the frozen tolerance.

Diagnostics (WP-2.2, `../g2/diagnostics/`): under the amended exact metric all 13 checks pass,
including the triangle inequality on 21,216 triples, eta bounds, triangle-excess range, exact-zero
abstention, and the retention of straight and reversal cases. The frozen gudhi backend failed the
same checks and was replaced (see the G2 decision).

Nulls and stress controls (WP-3.3, `reports/wp33_nulls_report.md`): the constant-diagram null is
exactly degenerate at sigma 0 and shows no systematic exceedance at sigma 0.05; the equal-speed
ordering control separates the forward and folded orderings with the comparison-angle or
triangle-shape channel in 20 of 20 Family A seeds and 5 of 5 Family B seeds while speed and L are
not matched at 1e-9 because the metric is nonlinear in the latent separation; time
reparameterization follows the predicted speed scaling; rotation and translation preserve the
diagrams and the diagnostics; coarse sampling keeps the classes separable; the adversarial
full-matrix case is reported honestly with its cost tradeoff.

## Compute and reproducibility

The degree-0 exploratory stage completed in 839.7 s wall at 8 workers with 292 MB peak RAM after
the exact-metric amendment (Family A and B H0 distance matrices, features, model selection, and
bootstrap). The exploratory caches, diagrams, distance matrices, split manifest, calibration,
selection tables, and preprocessing are preserved under `research_review/results/cache/` and
`research_review/results/g3/`. Every table in this memo is generated from the machine-readable
artifacts listed above.

## Claims scoring

C1 GO, C2 GO as operational definitions, C3 withdrawn, C4 withdrawn, C5 INDETERMINATE under this
formulation (with the WP-3.3 ordering result as a candidate new hypothesis), C6 unsupported,
C7 not identified, C8 not established, C9 unproven, C10 no. See `claims_matrix.yaml`.

## Recommended new protocol (not executed)

The PIVOT rule requires a new protocol and untouched test seeds. A candidate protocol that targets
the original hypothesis directly is a two-class reversible-versus-drift task with matched latent
movement budgets, calibrated so that the strongest raw baseline is below ceiling, for example by
reducing the signal amplitude relative to noise, coarsening the sampling to the regime where the
reversal is barely resolved, and including a difficulty pilot that verifies non-ceiling accuracy
before freezing. The WP-3.3 equal-speed ordering construction is the natural seed of that
protocol because the comparison-angle channel already separates orderings that speed summaries
cannot. Any new protocol must be pre-registered and use confirmatory seeds from 10000 upward,
which remain untouched.

## Limitations

The H1 secondary channel pass reached 176 of about 300 distance matrices before the primary PIVOT
outcome and the overnight compute window made further execution unnecessary; the H1 diagrams,
partial distance matrices, and the WP-3.1 H1 controls are preserved, and the secondary channel is
reported as not completed rather than as a negative result. The exploratory grid reduction and
the absence of a confirmatory stage are recorded. The decision thresholds are pragmatic
simulation thresholds, not application requirements. The ceiling effect limits this formulation
only; it does not disprove the wider possibility of useful topological dynamics.
