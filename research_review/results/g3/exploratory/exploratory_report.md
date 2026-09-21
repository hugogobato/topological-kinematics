# Exploratory stage report

Run id `exploratory-777492e6d431`; config sha256 `777492e6d431ca1d0b3b43146aa94c61e9081068a96245ac36618a6004ca12ff`; config source file; rows 10800; wall 839.7 s; peak RAM 292454400 bytes.

The incumbent rule is frozen: the incumbent is the best non-compact representation by equal-weight cell-averaged validation macro balanced error, with ties broken by lower validation end-to-end cost, then lower postprocessed dimension, then contract order. The eligible comparator set contains every non-compact representation whose validation error is at most 0.02 above the incumbent's validation error. Delta is compact minus incumbent on the exploratory test split, with the paired cluster bootstrap over (family, class, base_seed) clusters.

## Calibration

Floors are the 95.0th percentile of adjacent distances on training static-noise trajectories at sigma = 0.05, stored in calibration.json. At sigma = 0 the floor is exactly zero and only exact-zero abstention applies.

## Degree H0

### Validation ranking and incumbent

| rank | representation | val_error | feature_dim | val_cost |
|---|---|---|---|---|
| 1 | raw_geometry_flat | 0.0000 | 378.33 | 2.2315 |
| 2 | moments_summary | 0.0000 | 12.00 | 4.2764 |
| 3 | moments_flat | 0.0000 | 454.00 | 4.2764 |
| 4 | complete_distances | 0.0000 | 3.621e+03 | 4.5676 |
| 5 | compact | 0.0028 | 13.00 | 4.5676 |
| 6 | raw_geometry_summary | 0.0083 | 10.00 | 2.2315 |
| 7 | moment_signature_time | 0.0111 | 56.00 | 4.2765 |
| 8 | speed_history | 0.0139 | 80.67 | 4.5676 |
| 9 | moment_signature | 0.0222 | 42.00 | 4.2764 |
| 10 | recurrence_summary | 0.0250 | 9.00 | 4.5676 |

Incumbent: `raw_geometry_flat` with validation error 0.0000. Eligible comparators: `raw_geometry_flat`, `moments_summary`, `moments_flat`, `complete_distances`, `raw_geometry_summary`, `moment_signature_time`, `speed_history`.

### Delta against the incumbent

Delta 0.0000 with paired 95 percent interval [0.0000, 0.0000] (half width 0.0000, 120 clusters, 2000 resamples, seed 20260907).

| family | delta | Bonferroni low | Bonferroni high | clusters |
|---|---|---|---|---|
| A | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0.0000 | 0.0000 | 0.0000 | 60 |

### Per-cell errors

| family | sigma | stride | degree | compact | incumbent | delta | n |
|---|---|---|---|---|---|---|---|
| A | 0 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| A | 0 | 2 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| A | 0 | 4 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| A | 0.05 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| A | 0.05 | 2 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| A | 0.05 | 4 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0 | 2 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0 | 4 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0.05 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0.05 | 2 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |
| B | 0.05 | 4 | 0 | 0.0000 | 0.0000 | 0.0000 | 60 |

### Validity and coverage

| representation | valid_fraction | coverage |
|---|---|---|
| compact | 0.2012 | 0.5000 |
| speed_history | 1.0000 | 0.5000 |
| complete_distances | 1.0000 | 0.5000 |
| recurrence_summary | 1.0000 | 0.5000 |
| raw_geometry_flat | 1.0000 | 0.5000 |
| raw_geometry_summary | 1.0000 | 0.5000 |
| moments_flat | 1.0000 | 0.5000 |
| moments_summary | 1.0000 | 0.5000 |
| moment_signature | 1.0000 | 0.5000 |
| moment_signature_time | 1.0000 | 0.5000 |

### Parsimony

Worst-case dimension ratio 0.6154, worst-case cost ratio 0.0540, parsimony ratio 0.6154 (fourfold threshold applies).

### Costs

| representation | feature_dim | extraction_s | distance_s | feature_s | prediction_s | end_to_end_test_s |
|---|---|---|---|---|---|---|
| compact | 13.00 | 2.0645 | 0.0021 | 2.0129 | 6.266e-06 | 3.9953 |
| speed_history | 80.67 | 2.0645 | 0.0021 | 2.0129 | 1.226e-05 | 3.9953 |
| complete_distances | 3.621e+03 | 2.0645 | 0.0021 | 2.0129 | 2.999e-05 | 3.9953 |
| recurrence_summary | 9.00 | 2.0645 | 0.0021 | 2.0129 | 1.141e-05 | 3.9953 |
| raw_geometry_flat | 378.33 | 2.0645 | 0.0021 | 2.0129 | 1.303e-05 | 2.0007 |
| raw_geometry_summary | 10.00 | 2.0645 | 0.0021 | 2.0129 | 1.134e-05 | 2.0007 |
| moments_flat | 454.00 | 2.0645 | 0.0021 | 2.0129 | 1.493e-05 | 3.9926 |
| moments_summary | 12.00 | 2.0645 | 0.0021 | 2.0129 | 5.393e-06 | 3.9926 |
| moment_signature | 42.00 | 2.0645 | 0.0021 | 2.0129 | 6.421e-06 | 3.9926 |
| moment_signature_time | 56.00 | 2.0645 | 0.0021 | 2.0129 | 1.678e-05 | 3.9926 |

### Route recommendation

Recommended route: none. Frozen-route statuses: superiority PIVOT, parsimony PIVOT. Size projection: n_clusters = 200 (resolvable True, projected half-width reaches the target at this size).

Superiority reasons: the compact representation is noninferior but neither frozen route's advantage is established; noninferiority margin met (upper endpoint below 0.02).

Parsimony reasons: the compact representation is noninferior but neither frozen route's advantage is established; noninferiority margin met (upper endpoint below 0.02).

## Figures

`/home/hugo_souto/Stuff/Research/Topological_Kinematics/research_review/results/g3/exploratory/figures/fig_stride_curves_degree0.png`
`/home/hugo_souto/Stuff/Research/Topological_Kinematics/research_review/results/g3/exploratory/figures/fig_confusion_compact_degree0.png`

## Notes

Static, translation, and matched-speed controls are computed only when the stage configuration enables them; they stay outside the three-class accuracy calculation. The eligible comparator set and the route are recommendations only and must be frozen in the route freeze record before confirmatory test seeds are opened.

