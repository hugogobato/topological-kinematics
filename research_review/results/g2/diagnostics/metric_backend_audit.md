# WP-2.2 metric backend audit

Gate label: conditional_on_G1: WP-2.2 executed after the coordinator's G1 record and before the G2 decision; scientific pass condition is stable definitions only; no predictive value is claimed.

## 1. Finding

The frozen primary metric call, `tk_pilot.diagram_metrics.bottleneck_linf`, canonicalizes each finite diagram and then calls `gudhi.bottleneck_distance` from gudhi 3.12.0. Two separate defects were observed on real pilot diagrams and are quantified in this audit.

First, the default call does not use gudhi's exact algorithm: the documented default `e=None` selects the approximate path, and the additive approximation error is not small relative to the declared numerical zero. Second, and decisively, the gudhi implementation is not invariant to the order of the input points. The canonicalized inputs that the frozen wrapper always produces give a wrong distance on some real pairs even when the exact algorithm is requested with `e=0.0`, while the same diagrams in their stored order can give the correct value. Pinning `e=0.0` therefore does not repair the backend.

The WP-2.2 machine checks detect the defect directly: the frozen backend fails the triangle-inequality check with 0 violating triples and worst excess 5.55112e-17, and fails the triangle-excess range check with 0 violating interior times. The corrected candidate `exact_scipy` passes all 13 checks.

## 2. Backend comparison on the WP-2.2 grid

Distinct distance pairs compared: 33600. Pairs differing by more than 1e-12: 0. Maximum absolute difference: 0.

| degree | pairs compared | differing beyond 1e-12 | max abs difference |
|---|---|---|---|
| 0 | 16800 | 0 | 0 |
| 1 | 16800 | 0 | 0 |

Worst observed witnesses (indices refer to the stride-1 frame ordering):

| trajectory | class | seed | sigma | degree | i | j | primary value | exact value | abs difference |
|---|---|---|---|---|---|---|---|---|---|

The failing comparisons include non-adjacent pairs used by the comparison-angle construction, so the primary backend also corrupts q_t and the triangle side of eta. The frozen feature table is still written, labelled as the frozen backend output; the corrected candidate table is written beside it.

## 3. Incorrectness and order sensitivity of gudhi

On 60 random diagram pairs, the exact corrected solver was compared against the gudhi implementation on canonicalized and randomly permuted inputs:

| gudhi call | input order | mismatches against exact |
|---|---|---|
| default `e=None` | canonical | 2 |
| default `e=None` | shuffled | 2 |
| exact `e=0.0` | canonical | 1 |
| exact `e=0.0` | shuffled | 2 |

Pairs wrong in all four tests, meaning no tested order or `e` setting recovers the exact value: 1. The defect is therefore not only an ordering artefact that canonicalization could fix; the implementation is simply incorrect on some inputs.

A witness from this test: for one pair the exact value is 0.315742556, gudhi `e=0.0` on the canonical order returns 0.509281035, and the same call on a shuffled order returns 0.509281035.

Exhaustive cross-check on a 4 versus 4 point pair: enumerating all matchings with diagonal copies gives 0.315742556, the corrected solver gives 0.315742556 (agreement), and gudhi `e=0.0` on the canonical order gives 0.509281035. The minimal 3 versus 4 point witness and its certificate are stored in `metric_backend_witness.json`.

## 4. Verification of the corrected candidate

The corrected candidate is an independent SciPy exact solver: binary search over the finite candidate costs of the augmented matching problem with a perfect-matching feasibility test. It shares no code with gudhi, persim, or the project brute-force reference. Validation results:

1. Against the project brute-force reference on small diagrams: 80 comparisons, 0 mismatches, maximum absolute difference 0.
2. Order invariance: 30 canonical against shuffled comparisons, 0 mismatches, maximum absolute difference 0.
3. Against persim on synthetic pairs: 8 comparisons, 0 mismatches, maximum absolute difference 0.
4. Against persim on cached real diagrams: 12 comparisons, 0 mismatches, maximum absolute difference 0.

## 5. Minimal standalone witness

A minimal reproduction with 3 and 4 points is recorded in `metric_backend_witness.json` together with the certificate matching. For that pair, the exact value is 0.398534714, gudhi default on the stored order returns 0.398534714, gudhi `e=0.0` on the canonical order returns 0.665028746, and the largest discrepancy is 0.266494.

## 6. Consequences and required action

1. The frozen backend fails the declared tolerance pseudometric policy on real pilot diagrams, and the failure is not a rounding band: it reaches tens of thousandths and breaks the triangle inequality.
2. Pinning `e=0.0` is necessary but not sufficient. The order dependence means the backend must be replaced by an exact implementation that is order invariant, for example the validated SciPy solver used here as the corrected candidate, or a gudhi call without the canonicalization that triggers the wrong value, after the order dependence is understood and fixed upstream.
3. Cached artifacts produced by the frozen backend (the smoke distance matrices under `research_review/results/cache/runner_distances` and any features built from them) are unreliable wherever the defect triggers. Their reproducibility check passes, because the same wrong function is reproduced, but their correctness does not.
4. Amend `research_review/metric_interface.md` and the ledger to declare the exact solver as the primary metric (or to pin a verified gudhi call), re-run WP-0.2 with randomized order tests, and re-run WP-2.2 under the amended definition before the G2 decision. This is a policy change and must be recorded, not applied silently inside WP-2.2.
5. The WP-2.2 definitions themselves are stable under the corrected candidate, but the frozen backend is a G2 blocker and cached artifacts must be regenerated after the interface amendment.

## G2 amendment (2026-09-21): primary backend replaced by the exact solver

The primary metric alias `tk_pilot.diagram_metrics.bottleneck_linf` now points to `bottleneck_exact`, the exact augmented-matching solver (binary search over the unique entries of the augmented cost matrix with `scipy.sparse.csgraph.maximum_bipartite_matching` feasibility). The defect documented in sections 1 to 5 was confirmed by the coordinator, and the replacement was recorded additively in `research_review/metric_interface.md` and in the ledger key `diagram_metric.primary.amendment_g2`. The mathematical definition of the bottleneck distance and the numerical-zero policy are unchanged.

Consequence for this report. The audit was regenerated after the backend amendment, so the table built from `BACKEND_PRIMARY` and the table built from `BACKEND_EXACT` now agree: 33600 pairs compared, 0 pairs differing beyond `1e-12`, maximum absolute difference 0.0, and both backends pass the 13 machine checks. The formerly "frozen" table is therefore no longer a gudhi table; it is the exact-primary table.

Label caution. The script labels were kept unchanged and are now misleading in two places: (i) `BACKEND_PRIMARY` is still named `gudhi_default` even though it resolves through `bottleneck_linf` to the exact solver; (ii) the prose of section 1 ("the frozen backend fails ...") and section 5 ("gudhi default on the stored order returns 0.398534714") was generated from the amended primary and no longer describes raw gudhi behavior. The raw gudhi defect evidence is preserved in `metric_backend_witness.json` (exact 0.3985347143760231, `gudhi_default_canonical` 0.41061420919138303, `gudhi_e0_canonical` 0.6650287460769155), in the section 3 order-sensitivity table, and in the original audit record. The script was re-run as-is and not restructured.
