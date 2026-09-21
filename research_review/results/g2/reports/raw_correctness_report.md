# WP-3.1 raw-data correctness ladder report (conditional on G1)

This report is the WP-3.1 artifact for gate G2. The work is conditional on gate G1. At runtime the G1 packet `research_review/results/phase1/decision_packet_G1.md` was `template_with_pending_items` with 25 pending marker(s) and sha256 `8989feaeafe17c633255505e01e96cf15d65f990e5dfc1bbbd5c8189c41dc528`. Per the coordinator note, these outputs are labeled conditional and are to be read only after the written G1 record exists.

## 0. Run provenance

- exact command: `/usr/bin/python3 scripts/run_wp31_ladder.py --out research_review/results/g2 --workers 3`
- working directory: `/home/hugo_souto/Stuff/Research/Topological_Kinematics`
- started (UTC): 2026-09-21T02:49:48.779753+00:00
- finished (UTC): 2026-09-21T02:54:16.078231+00:00
- wall time: 242.2 s
- worker processes: 3 (maximum allowed 3)
- peak RAM main process: 219.7 MB; peak child RSS: 142.5 MB
- jobs: 70 total, 0 failed
- geometry replication against the public generator: {'A': True, 'B': True}
- saved-file hash verification mismatches: 0

Environment: gudhi=3.12.0, joblib=1.5.3, matplotlib=3.10.8, numpy=2.4.3, pandas=3.0.1, persim=0.3.8, pyarrow=24.0.0, scikit-learn=1.8.0, scipy=1.17.1, python=3.12.3, platform=Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39.

Input hashes are in `reports/tables/artifact_hashes.csv` and are summarized here.

| input file | sha256 |
| --- | --- |
| research_review/Topological_Kinematics_Research_Plan.md | 8fd06530e2c26e81eb6d6e257dd9522b12a3c92300dbc86177327bf59ff38a2a |
| research_review/Pilot_Experiment_Specification.md | 491c91e074219ded7a84a1dc3fae957d61805ad291cd8b0822b000fc94c9c202 |
| research_review/results/phase1/implementation_contract.md | c8f48782514974b55a6e3fb1d747824ad408dd15927e09df70d48e07e688bf3d |
| research_review/results/phase1/decision_packet_G1.md | 8989feaeafe17c633255505e01e96cf15d65f990e5dfc1bbbd5c8189c41dc528 |
| configs/tk_pilot.yaml | 1862b1bb58c4ddede8946782e6d2f55d6a4e87b752ad163a03560baaaa297091 |
| src/tk_pilot/generators.py | 1bc14dfca766573c704e4edda622c00fcac5b55f584bae0c3bc447f65a78ab00 |
| src/tk_pilot/persistence.py | 5ec7b5296185fab3997ac0abd049a4db5c7a00862fb93468c12fae1ff8b3c333 |
| src/tk_pilot/diagram_metrics.py | 0f28f01f4b3013f4ea399ba064bb1042c8d81b8aa1a8eeb6dcdd6f46de128596 |
| src/tk_pilot/path_diagnostics.py | a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f |
| src/tk_pilot/features.py | 44be21c2518d47202565c2197aa22f4e26c945f283bce15dcf54645832bed555 |
| scripts/run_wp31_ladder.py | b17fb9b7f97195ee74ed520d4ad31f2701343e37f180e0c48e54ac34be28f254 |

## Check verdicts

| check | title | verdict |
| --- | --- | --- |
| check1_static | Static controls and sigma = 0 exact-zero rule | PASS |
| check2_ramp | Smooth ramp deformation response | PASS |
| check3_topology | Topology-changing class programs | RESIDUAL |
| check4_null | Noisy raw null processes | RESIDUAL |
| check5_sampling | Sampling and filtration-resolution sensitivity | PASS |
| check6_translation | Rigid translation invariance | PASS |

## Check 1: static controls

Verdict: **PASS**. Declared rule: at sigma = 0 every adjacent distance must be exactly 0 for both degrees; at sigma = 0.05 the Spearman trend is nonsignificant at 1 percent and the adjacent versus lag-8 KS test does not reject exchangeability at 1 percent. sigma = 0 nonzero cases: 0. Training-style static 95th percentiles at sigma = 0.05: A=0.05715, B=0.0536091.

| family | seed | sigma | degree | mean | p95 | max | nonzero | rho | p | ks p | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 11 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| A | 11 | 0 | 1 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| A | 11 | 0.05 | 0 | 0.037318 | 0.0575466 | 0.0714756 | 128 | 0.107203 | 0.228418 | 0.742266 | PASS |
| A | 11 | 0.05 | 1 | 0.0657608 | 0.0988049 | 0.129085 | 128 | 0.0687633 | 0.440559 | 0.812179 | PASS |
| A | 12 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| A | 12 | 0 | 1 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| A | 12 | 0.05 | 0 | 0.0376872 | 0.0564342 | 0.0701367 | 128 | 0.0488693 | 0.583832 | 0.757589 | PASS |
| A | 12 | 0.05 | 1 | 0.0706188 | 0.108963 | 0.126601 | 128 | -0.0136851 | 0.878148 | 0.975287 | PASS |
| B | 11 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| B | 11 | 0 | 1 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| B | 11 | 0.05 | 0 | 0.0330082 | 0.0579373 | 0.077534 | 128 | 0.094643 | 0.287942 | 0.95085 | PASS |
| B | 11 | 0.05 | 1 | 0.0342954 | 0.0547622 | 0.0889978 | 128 | 0.0234448 | 0.792796 | 0.846099 | PASS |
| B | 12 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| B | 12 | 0 | 1 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | PASS |
| B | 12 | 0.05 | 0 | 0.0303381 | 0.0494204 | 0.0840061 | 128 | 0.00790837 | 0.929402 | 0.51923 | PASS |
| B | 12 | 0.05 | 1 | 0.033968 | 0.0513964 | 0.0704681 | 128 | -0.0202802 | 0.820255 | 0.572805 | PASS |

Raw adjacent distances: `reports/tables/static_adjacent_distances.csv`. Figure: `reports/figures/fig_check1_static.png`.

## Check 2: smooth ramp deformation

Verdict: **PASS**. Stride-4 subsample exactness against the stride-1 masters: {'A_11': True, 'A_12': True, 'B_11': True, 'B_12': True}.

| family | seed | C_ls | f_ls | R2_ls | C_max | rho | mean overlap | mean separated | switch or onset | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 11 | 0.422074 | 0.0154306 | 0.356371 | 0.9998 | 0.791159 | 0.0255584 | 0.0339665 | 2.02246 | PASS |
| A | 12 | 0.478452 | 0.011211 | 0.447954 | 0.997711 | 0.633852 | 0.0235828 | 0.0300455 | 2.0539 | PASS |
| B | 11 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.954484 | PASS |
| B | 12 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 1.00682 | PASS |

Family A seed 11: z_merge=2r=1.84502, plateau=0.180843, measured switch=2.02246, line slope=0.999438, max d/|dz|=0.9998, separated ratio=0.999063, bound violations=0, verdict components (monotone/bound/switch): PASS/PASS/PASS.
Family A seed 12: z_merge=2r=1.87953, plateau=0.184226, measured switch=2.0539, line slope=0.993658, max d/|dz|=0.997711, separated ratio=0.989927, bound violations=0, verdict components (monotone/bound/switch): PASS/PASS/PASS.
Family B seed 11: 2w=0.845257, onset in [0.921461, 0.954484], offset=0.109228 (one 32x32 grid spacing is 0.258065), persistence rho=0.920863, local decreases=9/93, net increase=0.874151.
Family B seed 12: 2w=0.899354, onset in [0.977873, 1.00682], offset=0.107465 (one 32x32 grid spacing is 0.258065), persistence rho=0.957681, local decreases=8/89, net increase=0.829865.

Raw response rows: `reports/tables/ramp_response.csv`; fits: `reports/tables/ramp_fits.csv`; transitions: `reports/tables/ramp_transitions.csv`. Figure: `reports/figures/fig_check2_ramp.png`.

## Check 3: topology-changing class programs

Verdict: **RESIDUAL**.

| family | seed | class | expected z | expected frame | measured first frame | measured first z | delta frames | card before | card after | event alignment | cardinality criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 11 | return | 1.99093 | 53 | 54 | 2.0773 | 1 | 63 | 63 | PASS | RESIDUAL |
| A | 11 | ramp | 2.02586 | 74 | 75 | 2.08204 | 1 | 63 | 63 | PASS | RESIDUAL |
| A | 11 | jump | 2.15677 | 61 | 61 | 3 | 0 | 63 | 63 | PASS | RESIDUAL |
| A | 12 | return | 2.37865 | 56 | 56 | 2.42115 | 0 | 63 | 63 | PASS | RESIDUAL |
| A | 12 | ramp | 2.06375 | 73 | 74 | 2.11967 | 1 | 63 | 63 | PASS | RESIDUAL |
| A | 12 | jump | 2.20528 | 64 | 64 | 3 | 0 | 63 | 63 | PASS | RESIDUAL |
| B | 11 | return | 0.71498 | 32 | 34 | 0.860979 | 2 | 0 | 1 | PASS | PASS |
| B | 11 | ramp | 0.845257 | 32 | 35 | 0.954484 | 3 | 0 | 1 | PASS | PASS |
| B | 11 | jump | 0.837751 | 61 | 61 | 3 | 0 | 0 | 1 | PASS | PASS |
| B | 12 | return | 0.87057 | 37 | 39 | 1.01243 | 2 | 0 | 1 | PASS | PASS |
| B | 12 | ramp | 0.899354 | 36 | 39 | 1.00682 | 3 | 0 | 1 | PASS | PASS |
| B | 12 | jump | 0.772416 | 61 | 61 | 3 | 0 | 0 | 1 | PASS | PASS |

The Family A H0 finite cardinality is exactly n_points - 1 for every frame (Rips connectivity at large filtration scale), so the literal cardinality-change criterion is recorded as RESIDUAL for Family A; its merge and separation transition is verified in the largest finite H0 death and in the H1 channel. Raw per-frame cardinalities: `reports/tables/class_cardinality.csv`. Events: `reports/tables/class_transitions.csv`. Figure: `reports/figures/fig_check3_topology.png`.

## Check 4: noisy raw null processes

Verdict: **RESIDUAL**. Training-style static calibration at sigma = 0.05: A=0.05715, B=0.0536091; calibration maxima: A=0.0714756, B=0.0840061. Declared rule: sigma = 0 requires exact zeros. For sigma > 0, the primary threshold is the pooled static sigma = 0.05 floor at sigma = 0.05 and the leave-one-out static floor at the same sigma otherwise. A run fails only on a strong nonstationary trend or a permutation test showing temporal clustering of exceedances at 1 percent; it is RESIDUAL when the trend test at 1 percent fails or the exceedance count above the primary floor exceeds the 99 percent binomial bound. The permutation test holds the marginal exceedance rate fixed, so a null process whose whole noise scale sits above a mis-transferred floor is reported as RESIDUAL rather than as a temporal event.

| family | config | seed | sigma | mean | p95 | max | rho | p | e_primary | n>primary | cluster p | 99% bound | max run | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | static_z0.5 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | static_z0.5 | 13 | 0.05 | 0.0376995 | 0.0561365 | 0.0829911 | -0.118774 | 0.181769 | 0.05715 | 6 | 0.22039 | 13 | 2 | PASS |
| A | static_z0.5 | 13 | 0.1 | 0.0543943 | 0.0880806 | 0.181717 | 0.0107123 | 0.904475 | 0.0902598 | 6 | 0.22039 | 13 | 2 | PASS |
| A | snapshot_z1.0 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | snapshot_z2.0 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | snapshot_z1.0 | 13 | 0.05 | 0.0388584 | 0.0605919 | 0.076846 | 0.125879 | 0.156828 | 0.05715 | 13 | 1 | 13 | 1 | PASS |
| A | snapshot_z2.0 | 13 | 0.05 | 0.0399864 | 0.0654135 | 0.086495 | 0.159706 | 0.0717467 | 0.05715 | 12 | 0.678161 | 13 | 2 | PASS |
| A | snapshot_z1.0 | 13 | 0.1 | 0.0566638 | 0.100362 | 0.167017 | 0.0457334 | 0.608226 | 0.0902598 | 12 | 0.678161 | 13 | 2 | PASS |
| A | snapshot_z2.0 | 13 | 0.1 | 0.0603801 | 0.106658 | 0.143184 | -0.0521253 | 0.55899 | 0.0902598 | 19 | 0.958521 | 13 | 2 | RESIDUAL |
| A | static_z0.5 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | static_z0.5 | 14 | 0.05 | 0.0358637 | 0.0571255 | 0.0821294 | 0.0687232 | 0.440826 | 0.05715 | 7 | 0.283858 | 13 | 2 | PASS |
| A | static_z0.5 | 14 | 0.1 | 0.046948 | 0.0902598 | 0.13721 | 0.116474 | 0.190439 | 0.0880806 | 8 | 0.370815 | 13 | 2 | PASS |
| A | snapshot_z1.0 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | snapshot_z2.0 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| A | snapshot_z1.0 | 14 | 0.05 | 0.0368284 | 0.0576785 | 0.0725273 | 0.0678248 | 0.446837 | 0.05715 | 8 | 0.370815 | 13 | 2 | PASS |
| A | snapshot_z2.0 | 14 | 0.05 | 0.0376512 | 0.0622468 | 0.0726959 | 0.069078 | 0.438465 | 0.05715 | 10 | 0.037981 | 13 | 3 | PASS |
| A | snapshot_z1.0 | 14 | 0.1 | 0.0525562 | 0.0865033 | 0.107081 | 0.0586889 | 0.510511 | 0.0880806 | 6 | 1 | 13 | 1 | PASS |
| A | snapshot_z2.0 | 14 | 0.1 | 0.0551687 | 0.0977327 | 0.124335 | 0.116145 | 0.191702 | 0.0880806 | 9 | 0.438781 | 13 | 2 | PASS |
| B | static_z0.5 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | static_z0.5 | 13 | 0.05 | 0.0327846 | 0.0619415 | 0.0990731 | -0.0458309 | 0.607461 | 0.0536091 | 10 | 0.54023 | 13 | 2 | PASS |
| B | static_z0.5 | 13 | 0.1 | 0.0605662 | 0.099975 | 0.122081 | -0.0046609 | 0.958357 | 0.109071 | 1 | 1 | 13 | 1 | PASS |
| B | snapshot_z1.0 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | snapshot_z2.0 | 13 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | snapshot_z1.0 | 13 | 0.05 | 0.0599741 | 0.104888 | 0.133878 | -0.166926 | 0.0596652 | 0.0536091 | 66 | 0.706147 | 13 | 6 | RESIDUAL |
| B | snapshot_z2.0 | 13 | 0.05 | 0.053528 | 0.113875 | 0.227014 | -0.237611 | 0.00691973 | 0.0536091 | 49 | 0.01999 | 13 | 8 | RESIDUAL |
| B | snapshot_z1.0 | 13 | 0.1 | 0.0959537 | 0.162386 | 0.225765 | -0.0145807 | 0.870241 | 0.109071 | 41 | 0.021989 | 13 | 7 | RESIDUAL |
| B | snapshot_z2.0 | 13 | 0.1 | 0.097046 | 0.168886 | 0.249319 | -0.0747118 | 0.401948 | 0.109071 | 43 | 0.984508 | 13 | 3 | RESIDUAL |
| B | static_z0.5 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | static_z0.5 | 14 | 0.05 | 0.0306126 | 0.048192 | 0.080172 | 0.223354 | 0.0112681 | 0.0536091 | 3 | 0.0524738 | 13 | 2 | PASS |
| B | static_z0.5 | 14 | 0.1 | 0.0654014 | 0.109071 | 0.164322 | 0.228224 | 0.00956908 | 0.099975 | 9 | 0.438781 | 13 | 2 | RESIDUAL |
| B | snapshot_z1.0 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | snapshot_z2.0 | 14 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | n/a | 13 | 0 | PASS |
| B | snapshot_z1.0 | 14 | 0.05 | 0.0401463 | 0.0684811 | 0.0952017 | 0.178764 | 0.0434938 | 0.0536091 | 19 | 0.0389805 | 13 | 4 | RESIDUAL |
| B | snapshot_z2.0 | 14 | 0.05 | 0.0546756 | 0.0934962 | 0.120514 | 0.163117 | 0.065813 | 0.0536091 | 60 | 0.509745 | 13 | 6 | RESIDUAL |
| B | snapshot_z1.0 | 14 | 0.1 | 0.0762891 | 0.123962 | 0.154798 | -0.00150501 | 0.986548 | 0.099975 | 22 | 0.409795 | 13 | 3 | RESIDUAL |
| B | snapshot_z2.0 | 14 | 0.1 | 0.0940093 | 0.160616 | 0.242381 | 0.0419023 | 0.638622 | 0.099975 | 46 | 0.125437 | 13 | 6 | RESIDUAL |

Raw adjacent distances and per-row threshold flags: `reports/tables/null_adjacent_distances.csv`; run summaries: `reports/tables/null_summary.csv`. Figure: `reports/figures/fig_check4_null.png`.

## Check 5: sampling and filtration-resolution sensitivity

Verdict: **PASS**. The Family A bound is the adapted delta-dense statement d_B at most 2 delta, where delta is the one-sided maximum distance from a dropped point to the retained set.

| family | seed | variant | points | mean d0 vs full | max d0 vs full | max d0/delta | max d0/(2 delta) | H0 cards | H1 cards | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 11 | points32 | 32 | 0.179102 | 0.179102 | 0.990369 | 0.495185 | 31..31 | 2..10 | PASS |
| A | 11 | points16 | 16 | 0.353029 | 0.353029 | 0.980785 | 0.490393 | 15..15 | 2..6 | PASS |
| A | 12 | points32 | 32 | 0.182452 | 0.182452 | 0.990369 | 0.495185 | 31..31 | 2..11 | PASS |
| A | 12 | points16 | 16 | 0.359632 | 0.359632 | 0.980785 | 0.490393 | 15..15 | 2..5 | PASS |
| B | 11 | grid16 | 256 | 0.108429 | 0.244016 | n/a | n/a | 0..1 | 0..0 | PASS |
| B | 12 | grid16 | 256 | 0.0869908 | 0.211906 | n/a | n/a | 0..1 | 0..0 | PASS |

Raw per-frame rows: `reports/tables/sampling_resolution.csv`; summaries: `reports/tables/sampling_summary.csv`. Figure: `reports/figures/fig_check5_sampling.png`.

## Check 6: rigid translation invariance

Verdict: **PASS**. Tolerance is 1e-7 times max(1, filtration range) for Family A, degrees 0 and 1.

| seed | sigma | degree | frames | max distance | filtration range | tolerance | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | 0 | 0 | 129 | 0 | 1.53634 | 1.53634e-07 | PASS |
| 11 | 0 | 1 | 129 | 0 | 1.53634 | 1.53634e-07 | PASS |
| 11 | 0.05 | 0 | 129 | 0 | 1.55289 | 1.55289e-07 | PASS |
| 11 | 0.05 | 1 | 129 | 0 | 1.55289 | 1.55289e-07 | PASS |
| 12 | 0 | 0 | 129 | 0 | 1.53338 | 1.53338e-07 | PASS |
| 12 | 0 | 1 | 129 | 0 | 1.53338 | 1.53338e-07 | PASS |
| 12 | 0.05 | 0 | 129 | 0 | 1.53329 | 1.53329e-07 | PASS |
| 12 | 0.05 | 1 | 129 | 0 | 1.53329 | 1.53329e-07 | PASS |

Raw per-frame distances: `reports/tables/translation_controls.csv`; summary: `reports/tables/translation_summary.csv`. Figure: `reports/figures/fig_check6_translation.png`.

## Cross-cutting findings

1. Contiguity requirement. `gudhi.RipsComplex` silently misreads non-contiguous point arrays; a strided slice such as `frame[::2]` yielded a complex on half the points in a direct probe. The frozen generator subsamples with `np.ascontiguousarray`, so this ladder passes contiguous arrays everywhere. The observation is recorded because future point subsampling must copy before extraction.
2. Configuration transfer of the static floor. The training-style floor is calibrated on static z = 0.5; frozen snapshots at other z values, and even other static seeds in Family B, can have a different noise response scale. That is a calibration-transfer limit rather than a temporal event: the permutation clustering test finds no serial dependence. The check 4 table reports the primary counts (pooled static floor at sigma = 0.05, leave-one-out static floor at sigma = 0.10), the clustering p-value, and the secondary counts.
3. Family B discrete onset. The first finite H0 bar appears slightly above the continuum prediction 2w because the two grid maxima split only on the discrete grid; the offset is reported against one grid spacing.
4. Family A bounded response. The least-squares fit with intercept is reported for completeness, but the overlap regime makes it a poor upper envelope. The reported maximum-ratio C is the empirical Lipschitz constant, and it is consistent with the separated-regime expectation that the last merge death moves exactly with z.

## Blockers and residual items

No failed jobs, hash mismatches, or missing artifacts.
Checks not at PASS: check3_topology (RESIDUAL), check4_null (RESIDUAL). Residuals are explained in the corresponding sections; none is an unrepaired extraction failure.

## Artifact inventory

Artifacts by category: diagram_meta=70, diagram_sequence=70, input=11, raw_control=70, raw_control_meta=70, report_artifact=35. Full hashes: `reports/tables/artifact_hashes.csv`. Figures produced: fig_check1_static.png, fig_check2_ramp.png, fig_check3_topology.png, fig_check4_null.png, fig_check5_sampling.png, fig_check6_translation.png.

