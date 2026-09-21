# WP-2.1 window-to-diagram interface evidence

**Conditional status.** This artifact belongs to WP-2.1, which the coordinator conditions on gate G1 before the G2 decision. The G1 packet at `research_review/results/phase1/decision_packet_G1.md` was inspected at run time and its recorded status was: unresolved (pending items present) (25 pending markers). Every verdict below is conditional on G1 and none of it is a G2 decision.

**Exact run command** (from the repository root): `python3 scripts/run_wp21_interface.py`

**Run start (UTC):** 2026-09-21T02:54:20Z

**Wall time:** 541.0 s of the 25 minute (1500 s) cap. The timer starts at module load, before the numerical imports, and stops after every diagram computation and after the data artifacts are written, before this report and the checksum file are written. Interpreter startup before module load is excluded.

**Peak process RAM:** 214.1 MiB, measured as `ru_maxrss` of `RUSAGE_SELF` in a single worker process. The WP-2.1 cap is at most two worker processes; serial execution was retained because the measured workload fits the runtime budget.

**Environment:** Python 3.12.3, numpy 2.4.3, gudhi 3.12.0, Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39.

**Per-check wall time:** determinism_seconds 14.1 s, resampling_seconds 80.5 s, windows_seconds 446.2 s.

## Check 1 and Check 2: determinism and window equivalence

Verdict: PASS. Each declared trajectory was diagram-computed twice into separate temporary caches, loaded back with checksum verification, and compared per degree and frame by `np.array_equal` and by sha256 over the canonical array bytes. In the same process, `diagrams_for_windows(frames, family, length=1, stride=1)` was compared against `trajectory_diagrams(frames, family)`.

| trajectory | n_frames | cache arrays bitwise equal | cache sha256 equal | essential counts equal | window(1,1) bitwise equal | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A_return_1000_sigma0 | 129 | true | true | true | true | PASS |
| B_jump_1000_sigma50 | 129 | true | true | true | true | PASS |

- A_return_1000_sigma0: degree 0 cache sha256 `1a96e5b3be2eecd2a677cd452bc75885e6c10d5ad7826fa6dbf211d0d268f2e3` in both caches; degree 0 window call max component difference 0.
- A_return_1000_sigma0: cache file bytes equal for diagrams.npz: true.
- A_return_1000_sigma0: cache file bytes equal for essential.npz: true.
- A_return_1000_sigma0: cache file bytes equal for meta.json: true.
- B_jump_1000_sigma50: degree 0 cache sha256 `7b45be52a607d28bc6563906f8376fd04892f25d481e3d3b8287b381368284ae` in both caches; degree 0 window call max component difference 0.
- B_jump_1000_sigma50: cache file bytes equal for diagrams.npz: true.
- B_jump_1000_sigma50: cache file bytes equal for essential.npz: true.
- B_jump_1000_sigma50: cache file bytes equal for meta.json: true.

## Check 3: extraction uncertainty under raw resampling

Verdict: REPORTED (descriptive). Degree 0, stride 1, seeds [1000, 1001, 1002], `bottleneck_linf`. Baselines: frozen-phase 64-point Family A return trajectories, sigma 0; Family B jump trajectories, sigma 0.05.

| family | condition | variant | seed | n_frames | adjacent_mean | adjacent_p95 | endpoint_distance | changed_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | A_phase_redraw | phase_redraw_per_frame | 1000 | 129 | 0.0398277 | 0.0744096 | 0.0290279 | 1 |
| A | A_point_count | points32 | 1000 | 129 | 0.0293189 | 0.0666213 | 0.209909 | 1 |
| A | A_point_count | points48 | 1000 | 129 | 0.0303231 | 0.0703727 | 0.209909 | 1 |
| B | B_pixel_noise | sigma0.10 | 1000 | 129 | 0.080133 | 0.132269 | 0.126056 | 1 |
| B | B_grid_subsample | grid16x16 | 1000 | 129 | 0.0521532 | 0.114113 | 0.0681262 | 1 |
| A | A_phase_redraw | phase_redraw_per_frame | 1001 | 129 | 0.0389618 | 0.0672446 | 0.0207602 | 1 |
| A | A_point_count | points32 | 1001 | 129 | 0.0324535 | 0.0618389 | 0.186342 | 1 |
| A | A_point_count | points48 | 1001 | 129 | 0.0333531 | 0.0629717 | 0.186342 | 1 |
| B | B_pixel_noise | sigma0.10 | 1001 | 129 | 0.0795997 | 0.147459 | 0.176309 | 1 |
| B | B_grid_subsample | grid16x16 | 1001 | 129 | 0.0488381 | 0.0938587 | 0.0950721 | 1 |
| A | A_phase_redraw | phase_redraw_per_frame | 1002 | 129 | 0.0372094 | 0.069454 | 0.0355003 | 1 |
| A | A_point_count | points32 | 1002 | 129 | 0.0333793 | 0.0651153 | 0.177238 | 1 |
| A | A_point_count | points48 | 1002 | 129 | 0.0310272 | 0.0651153 | 0.177238 | 1 |
| B | B_pixel_noise | sigma0.10 | 1002 | 129 | 0.0807566 | 0.146878 | 0.131466 | 1 |
| B | B_grid_subsample | grid16x16 | 1002 | 129 | 0.0476282 | 0.0889753 | 0.0940002 | 1 |

Column semantics: adjacent statistics are within-sequence adjacent bottleneck distances of the variant diagrams; endpoint_distance is the bottleneck distance between the variant and baseline final diagrams; changed_fraction is the fraction of frames whose finite degree-0 diagram arrays are not elementwise identical.

Interpretation notes: the 48-point variant keeps three of every four points around each circle because 32 points per circle are not divisible by three, and the stated 48-point target governs; the phase-redraw variant uses the local seed namespace [seed, 0, 0, 303] and shares the baseline latent geometry so that only the circle phases change; no scientific pass or fail threshold is predeclared for these uncertainty measurements.

## Check 4: per-window metadata and pooled observation map

Verdict: PASS. Trailing-window end indices follow `ends = arange(length - 1, n_frames, stride)`, so every window uses only frames at or before its end timestamp. Pooled results are reported as a separate observation map and are never mixed with the frame-level claim.

### A_return_1000_sigma0 (A family)

| length | stride | output count | first end frame | first end time | last end frame | last end time | input support (frames) | pooled cardinality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 129 | 0 | 0 | 128 | 1 | [0, 128] | points_concatenated [64, 2] |
| 1 | 2 | 65 | 0 | 0 | 128 | 1 | [0, 128] | points_concatenated [64, 2] |
| 1 | 4 | 33 | 0 | 0 | 128 | 1 | [0, 128] | points_concatenated [64, 2] |
| 3 | 1 | 127 | 2 | 0.015625 | 128 | 1 | [0, 128] | points_concatenated [192, 2] |
| 3 | 2 | 64 | 2 | 0.015625 | 128 | 1 | [0, 128] | points_concatenated [192, 2] |
| 3 | 4 | 32 | 2 | 0.015625 | 126 | 0.984375 | [0, 126] | points_concatenated [192, 2] |
| 5 | 1 | 125 | 4 | 0.03125 | 128 | 1 | [0, 128] | points_concatenated [320, 2] |
| 5 | 2 | 63 | 4 | 0.03125 | 128 | 1 | [0, 128] | points_concatenated [320, 2] |
| 5 | 4 | 32 | 4 | 0.03125 | 128 | 1 | [0, 128] | points_concatenated [320, 2] |

### B_jump_1000_sigma50 (B family)

| length | stride | output count | first end frame | first end time | last end frame | last end time | input support (frames) | pooled cardinality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 129 | 0 | 0 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 1 | 2 | 65 | 0 | 0 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 1 | 4 | 33 | 0 | 0 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 3 | 1 | 127 | 2 | 0.015625 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 3 | 2 | 64 | 2 | 0.015625 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 3 | 4 | 32 | 2 | 0.015625 | 126 | 0.984375 | [0, 126] | field_averaged [32, 32] |
| 5 | 1 | 125 | 4 | 0.03125 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 5 | 2 | 63 | 4 | 0.03125 | 128 | 1 | [0, 128] | field_averaged [32, 32] |
| 5 | 4 | 32 | 4 | 0.03125 | 128 | 1 | [0, 128] | field_averaged [32, 32] |

### Pooled diagnostics at length 3, stride 2

| trajectory | observation map | count | L | R | eta |
| --- | --- | --- | --- | --- | --- |
| A_return_1000_sigma0 | frame level | 129 | 3.36808 | 0 | 0 |
| A_return_1000_sigma0 | pooled (3, 2) | 64 | 2.17554 | 0 | 0 |
| B_jump_1000_sigma50 | frame level | 129 | 5.49985 | 0.422671 | 0.0768515 |
| B_jump_1000_sigma50 | pooled (3, 2) | 64 | 1.68677 | 0.423801 | 0.25125 |

The pooled rows are a different observation map (Family A point concatenation or Family B field averaging with pooled cardinality in the preceding table), so their L, R, and eta values are not comparable to the frame-level values and are not pooled into the frame-level claim. Undefined eta values appear as null in the JSON artifacts and as undefined in this table.

## What is verified

Within one environment and one process, the frozen extraction pipeline recomputes bitwise identical diagrams for the two declared trajectories, including cache file checksums, and the length 1 stride 1 trailing-window call reproduces the frame-level call exactly. The pooling grid emits the formula-expected number of trailing windows with end times inside the physical horizon, and declared pooled cardinalities are consistent with the frozen pooling rule. Resampling uncertainty is measured for the declared variants.

## What is not verified

1. Cross-machine or cross-version bitwise reproducibility is not tested; only same-environment, same-process reruns are covered. 2. Three seeds per condition are descriptive and do not estimate a sampling distribution over latent draws. 3. The resampling checks cover degree 0 only; the H1 secondary channel is not tested here. 4. No stability, separability, event-detection, or application claim is tested, and no G2 or G3 verdict is issued. 5. The pooled observation map is reported, not evaluated against the frame-level map.

## Artifact hashes

| artifact | sha256 |
| --- | --- |
| determinism.json | b041721848ad45db77719c46350ed64f5c1667236463a9d2c15cc4d0834455d2 |
| resampling.csv | 3b04c18b46d6ec8f3c50c0ed8d21ac51e009fc01627fab77474d5281ff70175b |
| resampling_details.json | 8e55b837c8097bb0b7f6655e8de3c434fa14bd6879f7a514a5b05647d0f62ef0 |
| run_manifest.json | 5a530c34b53eaa4301e6ae7b5b750a8cd46b71a79c733c18c9f2fcd12638a891 |
| window_metadata.json | eb6787c6d5bb65d31248b9606f8c89db86656c741c540a8c5164c5cfc86a8855 |

The `SHA256SUMS` file also lists the sha256 of this report. Verify with `sha256sum -c SHA256SUMS` from the output directory.

## Gate labeling

This artifact is labeled conditional on G1 as instructed. It does not record, replace, or preempt the coordinator's G1 or G2 decision, and it does not modify any file outside `scripts/run_wp21_interface.py` and `research_review/results/g2/interface/`.
