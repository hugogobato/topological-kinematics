# Independent numerical verification of the Phase 0 witness suite (gate G0)

> **Revision note.** Sections 1 to 6 below are the revision-1 audit record and are preserved unchanged. A re-verification of revision 2 is appended in section 7. Where the two sections disagree on hashes, versions, or case counts, section 7 is the current record.

Verifier artifact pair (this file and the script next to it):

| artifact | sha256 |
|---|---|
| `research_review/results/phase0/verification/independent_checks.py` | `644066a66141e478453ad6e9db6f97479954ec7dfde0e6536ad7f565823172e2` |

Verdict: **10/10 top-level checks PASS, no discrepancy found in behavior on the declared input domain.** One extra out-of-domain robustness finding (E1, `strip_essential` with `death = -inf`) and one artifact-completeness observation (O1, W-09 does not serialize the cosine-anomaly flag for its plus-side instance) are recorded below. Neither affects any stored witness result or any quantity defined on declared inputs.

The verification was performed adversarially: all reference computations were written from scratch in the verifier and use only the standard library, `numpy`, `gudhi`, and `persim`. `tk_pilot` was imported only for the three cross-check tasks that require it (policy behavior of the code under test, the falsification sweep of that code, and the determinism run). The reference side never imports the code under test.

## 1. Environment and commands

Environment observed by the verifier (identical to `environment.json` and the ledger):

```
python 3.12.3 (/usr/bin/python3), numpy 2.4.3, scipy 1.17.1, matplotlib 3.10.8,
gudhi 3.12.0, persim 0.3.8, pytest 9.0.3, yaml 6.0.1, ripser absent
```

Exact commands run from the project root:

```
/usr/bin/python3 research_review/results/phase0/verification/independent_checks.py
```

This single command executes checks 1 through 10 and the extra probe E1, prints one PASS/FAIL line per top-level check, and exits 0 on success (observed exit code 0). The raw transcript of the final run is the output of that command. Two standalone reproduction commands quoted in sections 5 and 6 were also run:

```
/usr/bin/python3 -c "import numpy as np, gudhi; D=np.array([[0.0,10.0]]); print(repr(float(gudhi.bottleneck_distance(D,D))))"
/usr/bin/python3 -c "import numpy as np, sys; sys.path.insert(0,'src'); from tk_pilot.diagram_metrics import strip_essential, as_diagram; print(strip_essential(np.array([[0.0,-np.inf]]))); as_diagram(np.array([[0.0,-np.inf]]))"
```

An earlier development run of the verifier exposed two defects in the verifier itself, both fixed before the final run: the independent bijection enumerator initially refused a 4+4 self-distance (8 augmented points) and check 8(j) initially built arrays whose `min(a,b)` was exactly `2e`, so the strict `>` correctly returned False. The final run is clean; the defects never involved the code under test.

## 2. Hashes of audited files

Every file below was hashed with `hashlib.sha256` in the verification session. The 14 `input_sha256` entries recorded in `environment.json` all match the current files (0 mismatches), so the results under test were produced by the code and documents now on disk.

| file | sha256 |
|---|---|
| `research_review/assumption_ledger.yaml` | `5de8eba33543795c64edd7bad433de3f32ffd525b795ea679d8b20ba4fd677f7` |
| `research_review/metric_interface.md` | `5eb194a63cd124a8054b0ff8aaa9a734b8379fa7d3d107c519c66bde79e24b9c` |
| `src/tk_pilot/diagram_metrics.py` | `5bb48c6396beabb7c3529637c490fbcfaa25a47f5bc6e38da3cf244a57f3b199` |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` |
| `src/tk_pilot/witnesses.py` | `bf85e8c53e96f980d3be3c940319e5d6670e1ed9c0bfab893acc65914b58294c` |
| `src/tk_pilot/witness_figures.py` | `a5129ab3715398134498232c1917027ec8db2173cae8170b2684f2847e23d2a3` |
| `scripts/run_witness_suite.py` | `564efbb023ef27aa06e5f2c550568b11ef55e2fa85178a62d8357262dc61f97f` |
| `tests/test_diagram_metrics.py` | `7e7cbc913e49ac0c992aa5662d30e1139a8f9553636abbe5a3ccb7f95a7abced` |
| `tests/test_path_diagnostics.py` | `09f755f9e91b3f0d48a87626cb976e1284a2748f703a374b30d1284a3c06279b` |
| `tests/test_witnesses.py` | `cb73c5185380f5ad73f99c92f6e4cbcd6ef56a288cab9370d76362e9e0ec0785` |
| `research_review/results/phase0/witness/witness_results.json` | `2332637a7c99bf130b1d2d543b3dcc88e0ee2c25f88ca6a0532815428e139fde` |
| `research_review/results/phase0/witness/environment.json` | `b2da0b72db9bdd169f7836ea9821a092e348e13bcb225aa01e61e2b182fb26a4` |
| `research_review/results/phase0/witness/witness_summary.txt` | `58789fe05a3a9e7b7ad81c2dca08c543077a225139a6374e4b1b6a488d00ae35` |
| `research_review/results/phase0/witness/run.log` | `bb567fa267ba92a734972bd85e0d6f62a5dbd97bcff770f2a3e426fb9fec9c8a` |
| `.../figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` |
| `.../figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` |
| `.../figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` |
| `.../figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` |

## 3. Check results

### Check 1: JSON integrity, environment metadata, audited hashes (PASS)

`witness_results.json` parses, contains exactly 14 cases with IDs `W-01` through `W-14` in order, all 14 case-level `passed` fields are boolean `true`, all 90 check entries carry a boolean `passed` field, each case-level `passed` equals the conjunction of its checks, and the summary (`n_cases=14`, `n_passed=14`, `n_failed=0`, `all_passed=true`, per-category counts) is internally consistent. `environment.json` parses and records exactly the ledger versions; the live imports in this session match them (`numpy 2.4.3`, `scipy 1.17.1`, `matplotlib 3.10.8`, `gudhi 3.12.0`, `persim 0.3.8`, `pytest 9.0.3`, `yaml` present, `ripser` absent), `python` starts with `3.12.3`, `executable` is `/usr/bin/python3`, and `seed` is 20260920. All 14 recorded `input_sha256` values match the current files.

### Check 2: W-01 analytic recomputation (PASS)

For `{(s, s+10)}` against `{(0, 10)}` with shifts `(0, 0.3, 4.9, 5.0, 5.1, 9.0)`, the analytic value `min(|shift|, 5)` is `(0, 0.3, 4.9, 5.0, 5.0, 5.0)`, and the stored `analytic_min_shifts` array matches it exactly. The stored `gudhi`, `persim`, and `bruteforce` arrays reproduce the same values to a maximum deviation of `7.216e-16`, at the `0.3` shift where `|10.3 - 10| = 0.3000000000000007` in binary floating point. Independent re-calls of `gudhi` and `persim` on the same inputs and the verifier's own enumeration agree with the stored arrays (max stored-versus-recomputed deviation `0.0` for `persim` and `bruteforce`, `2.108e-308` for `gudhi`). The tiny `gudhi` difference is the documented denormal behavior on the identical `shift = 0` instance: the raw library call returned `2.1078633181545124e-308` while the stored value is exactly `0.0` from the identity shortcut. The tolerance is `1e-9`.

### Check 3: independent exact bottleneck versus gudhi (PASS)

The verifier's own exact bottleneck enumerates bijections on the augmented point sets (each side padded with diagonal copies, cost `(death - birth)/2` to a diagonal copy, zero between diagonal copies), written from scratch and independent of the repository implementation. It reproduces 10 hand cases exactly (empty operands, diagonal points, cardinality mismatch, permuted identity, singleton shift). On 120 random pairs with cardinalities 0 to 4 per side and total at most 7, including empty diagrams, on-diagonal points, and duplicate points, the maximum deviation from `gudhi.bottleneck_distance` is `2.220e-16`, the maximum deviation from `persim.bottleneck` is `0.0`, `gudhi` symmetry deviation is `0.0`, verifier symmetry deviation is `0.0`, and the verifier returns exactly `0.0` for `d(X, X)` on every sampled diagram. Raw `gudhi` returns a nonzero denormal for `d(X, X)` on 82 of 120 pairs, with maximum absolute value `2.224e-308`; a separate probe of 200 identical random singletons returned nonzero denormals on all 200 pairs (maximum `2.223654220471299e-308`). This independently reproduces the ledger's `numerical_zero` note and supports the identity shortcut as the reason stored identical-diagram distances are exactly `0.0`. No mismatch with the raw diagrams was found.

### Check 4: W-06 recomputation (PASS)

From the stored timestamps `(0, 0.25, 0.5, 0.75, 1.0)` and birth coordinates, the verifier recomputed adjacent distances `(1, 1, 1, 1)`, `L = 4`, `R = 0`, speeds `(4, 4, 4, 4)`, speed-change rates `(0, 0, 0)`, comparison angles path A `(pi, 0, pi)`, path B `(0, 0, 0)`, and turns path A `(0, pi, 0)`. Every stored value matches with deviation `0.0` (stored fields: `path_a_angles`, `path_b_angles`, `path_a_speeds`, `path_a_length`, `path_a_displacement`). Speed-change rates and turns are not stored in `details`; the stored checks assert them with deviation `0.0`, and the verifier independently reproduced those expected values. The library-angle conditioning figure recomputed from raw `gudhi` distances is `2.9802322387695312e-08`, identical to the stored `max_angle_deviation` (absolute difference `0.0`). The distances follow from the stored coordinates because all birth shifts are at most 2 and the case lifespan is 10, so `min(|ds|, 5) = |ds|`; this reduction is stated in the case definition.

### Check 5: W-09 recomputation and the 3.2e-5 explanation (PASS)

For the Euclidean sweep with points `(0,0)`, `(1,0)`, `(1 +/- eps, 0)`, using the same input convention as the witness (the passed adjacent second distance is the literal `eps`, while `c` is recomputed as `||p2 - p0||`), the verifier reproduced all four stored rows exactly (deviation `0.0` on `theta_plus`, `theta_minus`, `angle_jump`, and the configuration perturbation):

| eps | theta_plus | theta_minus | angle_jump |
|---|---|---|---|
| `1e-4` | `3.141592184262351` | `1.1534692335346162e-06` | `3.1415910307931174` |
| `1e-6` | `3.141579826537291` | `0.0` | `3.141579826537291` |
| `1e-8` | `3.1414824041364877` | `3.2445518884509834e-05` | `3.1414499586176032` |
| `1e-10` | `3.141592653589793` | `0.0` | `3.141592653589793` |

For the diagram-space instance with `eps = 1e-8`, the verifier's own exact bottleneck gives `c_plus = 1.0000000100000008` and `c_minus = 0.99999999`, hence `z_plus = -1.000000082740371` (clipped to `-1`, `theta_plus = pi`) and `z_minus = 0.9999999994736442`, which gives `theta_minus = 3.2445518884509834e-05`, matching the stored value exactly.

Numerical explanation of why the minus side is about `3.2e-5` rather than exactly `0`: the exact value of `z` is `1`, but in double precision `z_minus = 1 - 5.263558e-10`. Cancellation in `a^2 + b^2 - c^2` at the `1e-16` level is amplified by `arccos` near `1`, where `arccos(1 - delta) ~ sqrt(2 delta) = 3.244552e-05`. The plus side is protected by the clip: `z_plus` falls below `-1` and `arccos(-1) = pi` exactly. This is the conditioning behavior the ledger predicts, not an error.

Observation O1: `z_plus = -1.000000082740371` has `|z| > 1 + 1e-12`, so the code's cosine-anomaly flag is `True` for the plus-side diagram instance (the triangle inequality is violated at the `8e-16` roundoff level), but W-09 does not serialize `cosine_anomaly` in its details. The flag is computed and returned by the code; only the witness record does not surface it. W-10 separately verifies the flag for a genuine non-metric triple.

### Check 6: W-13 recomputation (PASS)

From the stored timestamps and the case's singleton births `(0, 1, 0.5, 2, 1)`, the verifier recomputed adjacent distances `(1, 0.5, 1.5, 1)`, speeds `(10, 2.5, 5, 10.000000000000002)`, midpoints `(0.05, 0.2, 0.44999999999999996, 0.6499999999999999)`, speed-change rates `(-49.99999999999999, 10.000000000000002, 25.000000000000014)`, `L = 4`, `R = 1`, `eta = 0.25`, comparison angles `(0, 0, 0)`, turns `(pi, pi, pi)`, raw cosines `(1, 1, 1)`, and triangle excess `(0.666..., 0.5, 0.8)`. Every stored `raw_diagnostics` field matches with deviation `0.0`. Exact rational arithmetic confirms the mathematical rates are `-50`, `10`, and `25`, and the midpoint spacings are `3/20`, `1/4`, and `1/5`. The 95th-percentile floor recomputed by hand with linear interpolation and by `numpy.percentile` is `1.4249999999999998`, matching the stored `noise_floor_e` exactly. The angle-validity flags `(False, False, False)`, the efficiency flag `False`, and the zero-floor flags `(True, True, True)` all match. Doubling the clock leaves `L` and `R` invariant, halves every speed, and quarters every speed-change rate with deviation `0.0`; order-preserving relabeling leaves `L` and `R` unchanged. All three non-increasing timestamp series were rejected with `ValueError` by both the verifier's own predicate and the code's `validate_timestamps`.

### Check 7: falsification sweep over 540 random finite metric paths (PASS)

The verifier generated 540 finite metric paths, 180 per kind: Euclidean point paths in dimensions 1 to 8 (with duplicate consecutive points and near-collinear runs mixed in), graph shortest-path metrics from random positive-weight complete graphs (Floyd-Warshall implemented in the verifier), and random finite persistence diagrams under the L-infinity bottleneck (cardinalities 0 to 4, empty diagrams, on-diagonal points, duplicate consecutive diagrams, plus structured near-degenerate singleton paths with perturbations from `1e-12` to `1e-6`). For every path, all frozen scalar quantities were recomputed independently and compared to the code under test, and the following properties were searched for violations:

```
R <= L                              (tolerance 1e-9, raw extremes reported)
0 <= eta <= 1 when L > 0            (tolerance 1e-12)
all valid angles in [0, pi]         (tolerance 1e-12)
valid angles require a > 0 and b > 0
speeds >= 0                         (tolerance 1e-12)
|raw cosine| > 1 + 1e-12 implies cosine_anomaly
triangle excess in [0, 1] when a + b > 0   (tolerance 1e-9)
```

Observed extremes: `max(R - L) = 3.553e-15` (positive on 11 of 540 paths, floating-point roundoff from `gudhi`, all within the `1e-9` tolerance), `eta` in `[0, 1]`, valid angles in `[0, pi]`, minimum speed `0.0`, triangle excess in `[-2.04396e-16, 1]`, 7 zero-length paths, 4 cosine anomalies observed, and a maximum code-versus-independent formula deviation of `3.553e-15`, traced to the Euclidean `length` field where `numpy.sum` uses pairwise summation and the verifier used left-to-right summation. Violation counts were zero for every property, and zero formula mismatches. No counterexample was found.

### Check 8: policy cross-check against the ledger (PASS)

All eleven sub-checks match the ledger text: (a) essential classes with `death = +inf` are stripped and counted (`1` and `2` in the two probes) leaving the empty diagram; (b) identical diagrams, including a permuted copy and the both-empty case, return exactly `0.0`; (c) `as_diagram` raises `ValueError` for raw diagrams containing `+inf`, `-inf`, or `NaN`; (d) a constant path gives `L = 0.0` and `eta = None`; (e) zero steps (`b = 0` and `a = 0`) give `NaN` angles and invalid flags; (f) the non-metric triple `(1, 1, 3)` gives raw cosine `-3.5`, anomaly `True`, clipped angle `pi`, while a within-tolerance roundoff triple `(1, 1, 2(1+1e-13))` gives raw cosine `-1.0000000000003997`, no anomaly, and angle `pi`; (g) nonpositive and non-finite timestamp series all raise `ValueError`; (h) at `e = 0` only exact-zero steps are unresolved; (i) with `T = 4` intervals and `e = 1.0` the threshold is `6.0`, and `L = 6.0 - 1e-9` and `L = 6.0` both give `valid = False` while `L = 6.0 + 1e-9` gives `valid = True`, matching `L > 2(T-1)e` with `T` the number of intervals; (j) the strict angle predicate `min(a,b) > 2e` returns `(False, False, True)` on the constructed boundary arrays; (k) the W-13 path's efficiency flag agrees with the ledger predicate.

### Check 9: determinism and reproducibility (PASS)

Two consecutive calls of `tk_pilot.witnesses.run_all(seed=20260920)` produced byte-identical JSON-serializable output under the verifier's own sanitizer. The first run's 14 case records also match the stored `witness_results.json` cases exactly, with no differing case IDs. Two-run wall time was `8.63 s`. This confirms the stored artifact is reproducible from the audited code with the recorded seed.

### Check 10: figures (PASS)

All four PNG files exist, are nonempty, carry the PNG signature `89 50 4E 47 0D 0A 1A 0A`, start with an `IHDR` chunk, and end with a zero-length `IEND` chunk. Observed dimensions and sizes: `fig_singleton_bottleneck.png` 960x630 / 71210 bytes, `fig_equal_speed_paths.png` 1440x600 / 81465 bytes, `fig_angle_instability.png` 960x630 / 47402 bytes, `fig_random_path_checks.png` 1440x600 / 82756 bytes. Regenerating all four figures into a temporary directory with the audited `witness_figures` code produced byte-identical files (matching sha256 for all four), so the stored figures are reproducible and were not edited after generation.

## 4. Discrepancies and observations

No discrepancy was found between the ledger text and the observed behavior on the declared input domain. Two items are recorded for completeness.

E1 (extra finding, out-of-domain robustness, low severity): `strip_essential` silently classifies a bar with `death = -inf` as an essential class and drops it, counting it in `n_essential`, instead of rejecting it. Minimal reproduction:

```
>>> strip_essential(np.array([[0.0, -np.inf]]))
(array([], shape=(0, 2), dtype=float64), 1)
>>> as_diagram(np.array([[0.0, -np.inf]]))
ValueError: non-finite diagram coordinates are not allowed; ...
```

The ledger defines essential classes as `death = +inf`, and the declared input object requires `death` finite (`metric_interface.md` section 2, item 1), so this input is out of domain and no stored witness uses it. The related path `as_diagram` correctly rejects the same input, and `NaN` deaths are correctly rejected by `strip_essential`, so this is a narrow validation gap rather than a declared-behavior violation.

O1 (artifact completeness): the W-09 plus-side diagram instance has `z = -1.000000082740371`, so the code computes `cosine_anomaly = True`, but W-09's serialized details omit the flag. The behavior is correct per policy; only the witness record does not expose it.

O2 (documented behavior, independently reproduced): raw `gudhi.bottleneck_distance` returns denormal values (up to `2.224e-308`) for identical diagram inputs, which is exactly why the ledger prescribes the identity shortcut. The wrapper and the verifier's own implementation both return exact `0.0` for identical canonical diagrams. This is a confirmation, not a discrepancy.

Floating-point nuance: `max(R - L)` was `+3.553e-15` on 11 of 540 random paths and the minimum triangle excess was `-2.04396e-16`; these are `gudhi` roundoff at the last-bit level, inside the `1e-9` tolerance. The mathematical statements `R <= L` and `q in [0, 1]` hold for exact distances.

## 5. Falsification attempts that failed to find a counterexample

The following searches were run and produced no counterexample beyond the stated floating-point tolerances:

1. **Bottleneck implementation search.** 120 random diagram pairs with unequal cardinality (0 to 4 points per side, total at most 7), including empty diagrams, on-diagonal points, and duplicated points, plus 10 hand-computed cases, compared against the verifier's independent bijection enumeration with diagonal copies. Maximum deviation from `gudhi` `2.220e-16`, from `persim` `0.0`, symmetry exact, self-distance exactly `0.0`.
2. **Path-diagnostic property search.** 540 random finite metric paths across three metric families (Euclidean in dimensions 1 to 8, Floyd-Warshall graph metrics from positive complete graphs, and L-infinity bottleneck diagram paths with degenerate and near-degenerate structure). Searched for `R > L`, `eta` outside `[0, 1]`, angles outside `[0, pi]`, valid angles at zero steps, negative speeds, unflagged raw cosines with `|z| > 1 + 1e-12`, triangle excess outside `[0, 1]`, and any deviation between the code and the verifier's independent formulas. Zero violations; the only nonzero deviations were floating-point roundoff at the `1e-15` level.
3. **Stored-value search.** Exact independent recomputation of every stored W-01, W-06, W-09, and W-13 number. Deviations were `0.0` everywhere except W-01, where the analytic-versus-stored deviation is `7.216e-16`, explained by the binary representation of `0.3` and `10.3`.
4. **Determinism search.** Two independent runs of the full 14-case suite with the recorded seed, plus comparison to the stored JSON. No nondeterminism, no drift from the stored artifact.
5. **Figure reproduction search.** Regeneration of all four figures in a clean temporary directory and byte comparison with the stored files. All four matched.
6. **Policy edge-case search.** Exercised stripping and counting, exact-zero identity, non-finite rejection, `L = 0`, zero steps, cosine anomaly and clipping, nonpositive timestamps, exact-zero abstention, and both sides of the efficiency threshold. All matched the ledger; the only gap found is E1 above.

## 6. Limitations

This audit covers the frozen finite-metric definitions and the stored witness artifacts only. It does not cover the frame-to-diagram extraction pipeline (gate G2), predictive value (G3), applications (G4), or theory (G5), and it does not audit `gudhi` internals. The verifier's exact bottleneck reference was itself validated against 10 hand cases and 120 `gudhi`/`persim` comparisons, so a common-mode error is conceivable only if the elementary bijection formulation, the hand cases, and both libraries all share the same mistake. Reference comparisons use `1e-9` tolerances for floating-point equality and report raw extremes alongside every pass.

# 7. Re-verification of revision 2

## 7.1 What changed and the status of prior findings

Revision 2 repaired two findings from the revision-1 audit and introduced one declared numerical-zero policy plus a new witness case.

Prior finding E1 (`strip_essential` silently classified `death = -inf` as an essential class): **resolved.** `strip_essential([[0.0, -inf]])` now raises `ValueError: death coordinates must be finite or +inf; -inf is invalid`, `NaN` deaths still raise, and `death = +inf` remains a counted essential class (`finite` part empty, `n_essential = 1`). `as_diagram` still rejects all raw non-finite input. Direct evidence is in check 8(a) and in the extra check E1 of the final run.

Prior observation O1 (W-09 did not serialize the plus-side cosine anomaly): **resolved.** W-09 now stores `diagram_plus_raw_cosine = -1.000000082740371`, `diagram_plus_anomaly = true`, `diagram_minus_raw_cosine = 0.9999999994736442`, `diagram_minus_anomaly = false`, and adds an explicit check that the roundoff anomaly near `pi` is flagged. The verifier independently recomputed both raw cosines and both flags and they match exactly (check 5). The `z_plus` value still exceeds `-1` in magnitude beyond `1 + 1e-12`, so the anomaly flag is correct and is now visible in the artifact.

Prior observation O2 (raw `gudhi` returns denormals for true-zero distances): **still true and now handled by policy.** The revision-2 numerical-zero convention snaps any computed distance at or below `NUMERICAL_ZERO = 1e-12` to exactly `0.0` in the gudhi wrapper, the persim wrapper, the 2-Wasserstein wrapper, and the brute-force reference. The verifier independently reimplemented the snap and confirmed the stored W-01 and W-15 values equal the independently snapped references exactly. Raw gudhi denormals were reproduced again (`2.1078633181545124e-308` for the identical W-01 instance; nonzero denormals on 82 of 120 random pairs with maximum `2.224e-308`).

No prior finding remains unresolved.

## 7.2 Commands

The verifier was updated for revision 2 (15-case expectations, independent snap policy, W-09 anomaly fields, `-inf`/`NaN` stripping, direct W-15 verification, snap events and default-wrapper comparison in the sweep, and canonicalization of the diagram metric). The final command and its result:

```
/usr/bin/python3 research_review/results/phase0/verification/independent_checks.py
EXIT=0
SUMMARY: 10/10 top-level checks passed; failed=none
EXTRA findings: 1/2 clean; notes=['E2']
```

The verifier script hash for this revision is `045b4a17d1307f5b7da30bbb153cf7920b11684fc6ba7a8c9926f64d029332b6`.

## 7.3 New check results

**Check 1 (PASS).** `witness_results.json` has 15 cases, IDs `W-01` through `W-15` in order, 97 checks all with boolean `passed`, case-level consistency, summary `15/15`, per-category consistent (`policies` now has 2 cases), environment versions and seed unchanged, and 0 of the 14 recorded `input_sha256` entries mismatch the current files.

**Check 2 (PASS).** W-01 analytic values and stored arrays still agree to `7.216e-16`. The stored values now equal the independently snapped references exactly for all three backends (deviation `0.0`). Raw gudhi on the identical `shift = 0` instance is `2.1078633181545124e-308` and is snapped to the stored `0.0`.

**Check 3 (PASS).** 120 random pairs, 10 hand cases: maximum deviation of the independent exact enumerator from raw gudhi `2.220e-16`, from canonical gudhi `2.220e-16`, from persim `0.0`; symmetry exact; independent `d(X, X)` exactly `0.0`; 6 true-zero non-identical pairs; the public wrappers agree with the independently snapped exact value to `2.220e-16`. A new library-level observation (O3) is documented here: raw `gudhi.bottleneck_distance` is order-sensitive on some inputs. On the recorded 4-point witness pair the exact value is `0.8980590011828029` (confirmed by the bijection enumerator, by a threshold/perfect-matching algorithm, by persim, and by gudhi on canonical input), while raw gudhi on the unsorted input returns `0.8994791936886859`. Scanning all 576 point permutations gives two distinct raw values, `{0.899479193688686: 72, 0.898059001182803: 504}`; 72 permutations overestimate by `1.42e-3`. The code's `as_diagram` lexsort canonicalization selects the exact value, so the public API is deterministic and correct; the observation concerns the raw library call, not a code defect.

**Check 4 (PASS).** W-06 recomputation still matches stored values with deviation `0.0`, and the library-angle conditioning number is again exactly `2.9802322387695312e-08`.

**Check 5 (PASS).** The W-09 sweep reproduces the stored `theta_plus`, `theta_minus`, and `angle_jump` exactly for all four epsilons. The diagram-space values are `z_plus = -1.000000082740371` (anomaly true) and `z_minus = 0.9999999994736442` (anomaly false), matching the newly serialized fields; the `1 - z_minus = 5.263558e-10` and `sqrt(2 delta) = 3.244552e-05` explanation of the minus-side angle stands.

**Check 6 (PASS).** W-13 recomputation still matches every stored field with deviation `0.0`; the exact rational rates are `-50`, `10`, `25`; the floor is `1.4249999999999998`; dilation and relabel invariance and timestamp rejection all hold.

**Check 7 (PASS).** The falsification sweep was re-run over 540 paths (180 Euclidean in dimensions 1 to 8, 180 Floyd-Warshall graph metrics from positive complete graphs, 180 bottleneck diagram paths), now with the declared snap policy independently reimplemented in the verifier's diagram metric and with a comparison of the code's default wrapper against the independently snapped path. The sweep recorded 22 snap events, the default wrapper and the independent path agree to `0.0`, and all violation counts are zero: `R > L = 0`, `eta` range `= 0`, angle range `= 0`, valid-with-zero-step `= 0`, negative speeds `= 0`, cosine-flag mismatches `= 0`, excess range `= 0`, formula mismatches `= 0`. Raw extremes: `max(R - L) = 3.553e-15` (11 of 540 paths, floating-point roundoff, inside the `1e-9` tolerance), `eta` in `[0, 1]`, angles in `[0, pi]`, minimum speed `0.0`, excess in `[-2.04396e-16, 1]`, and maximum code-versus-independent formula deviation `3.553e-15` (Euclidean `length`, `numpy.sum` pairwise summation versus left-to-right summation).

**Check 8 (PASS, twelve sub-checks).** All prior policies still match, now with (a) `-inf`/`NaN` rejection and (l) the numerical-zero policy. Direct W-15 verification from the verifier's own computation: the true-zero non-identical pair `[[0,1],[2,3]]` versus `[[0,1],[2,3],[5,5]]` has mathematical distance exactly `0.0` (confirmed by both the bijection enumerator and the threshold/perfect-matching algorithm, because the extra point lies on the diagonal); the gudhi, persim, brute-force, and 2-Wasserstein wrappers all return exactly `0.0`; a `5e-13` singleton shift has exact value `5e-13` and is snapped to exactly `0.0` by all four wrappers; a `2e-12` shift has exact value `2.000177801164682e-12` and is preserved by gudhi and brute force with equality to `1e-15`; `NUMERICAL_ZERO` is exactly `1e-12`.

Boundary observation: a singleton shift of exactly `1e-12` computes to `1.000088900582341e-12` through gudhi (cancellation in the death coordinate), which is above the tolerance, so it is preserved rather than snapped. This is consistent with the declared wording "a computed distance at or below `1e-12`" and is recorded as a nuance, not a discrepancy.

**Check 9 (PASS).** Two runs of `run_all(seed=20260920)` produce identical JSON-serializable output, and the first run matches the stored 15-case `witness_results.json` exactly, so the stored W-15 record is reproducible from the audited code.

**Check 10 (PASS).** All four PNGs remain valid and nonempty and regenerate byte-for-byte; their hashes are unchanged from revision 1.

**Extra E1 (PASS).** The revision-1 finding is resolved as described in section 7.1.

**Extra E2 (NOTE, new bounded observation).** The declared snap policy makes the snapped distance function fail the exact triangle inequality at the `1e-12` scale. Concrete witness using only public functions:

```
D0 = {(0, 10)}, D1 = {(9e-13, 10 + 9e-13)}, D2 = {(2e-12, 10 + 2e-12)}
d(D0, D1) = 0.0                       (raw 9.006e-13 snapped at NUMERICAL_ZERO = 1e-12)
d(D1, D2) = 1.0999999999999998e-12
d(D0, D2) = 2.000177801164682e-12
L = 1.0999999999999998e-12, R = 2.000177801164682e-12, eta = 1.8183434556042568
R - L = 9.001778011646823e-13
```

So under the snapped metric `R <= L` and `0 <= eta <= 1` hold only up to about `2 * NUMERICAL_ZERO = 2e-12`. The violation is bounded by the declared tolerance, is far inside the suite's `1e-9` floating-point tolerance, and does not affect any stored witness or any declared-input quantity at the pilot's coordinate scale. It is reported because the ledger states `R <= L` and `eta <= 1` as exact triangle-inequality consequences, and after revision 2 those statements are exact for the unsnapped metric but only approximate for the public snapped metric.

## 7.4 Revision-2 hashes

All hashes recomputed with `hashlib.sha256` in this session. The four figure hashes and `path_diagnostics.py`, `witness_figures.py`, `run_witness_suite.py`, `test_path_diagnostics.py`, and `test_witnesses.py` are unchanged from revision 1.

| file | sha256 |
|---|---|
| `research_review/assumption_ledger.yaml` | `bc466438ccb360c6a219474837d3bb10f4b4c5c4369a78fb36f949d3eba2425b` |
| `research_review/metric_interface.md` | `48e9d5977ccc681b8350d6695fa202373dbbe4001defe4561b51c3d2aa07b7ca` |
| `research_review/preregistration_draft.md` | `7cb03316256937d9797b0f068103349f91a20d9139f813786f03d95f18bf0eaf` |
| `research_review/witness_note.md` | `b4902f1bd83290e76dfae5dbbf58e1490d8ffa9e13f884d8452edf0bc15e35e8` |
| `src/tk_pilot/diagram_metrics.py` | `4d22315d5ea871d8d6afa321c70e7a593a7b149cc1d8654b93047b053b288044` |
| `src/tk_pilot/path_diagnostics.py` | `a67eb36041d0724ac8d859ec715928542b90a1af7614bbf2fcef9ca752c5b37f` |
| `src/tk_pilot/witnesses.py` | `3fa010ec2c80ad3bda4bbb490634af801868a26ce04b95121a21c783fea1130b` |
| `src/tk_pilot/witness_figures.py` | `a5129ab3715398134498232c1917027ec8db2173cae8170b2684f2847e23d2a3` |
| `scripts/run_witness_suite.py` | `564efbb023ef27aa06e5f2c550568b11ef55e2fa85178a62d8357262dc61f97f` |
| `tests/test_diagram_metrics.py` | `48e2d5a4ef33f2cd84fc17d11c7b03afa9a4a7026b661d90ec23b608fc98f3dc` |
| `tests/test_path_diagnostics.py` | `09f755f9e91b3f0d48a87626cb976e1284a2748f703a374b30d1284a3c06279b` |
| `tests/test_witnesses.py` | `cb73c5185380f5ad73f99c92f6e4cbcd6ef56a288cab9370d76362e9e0ec0785` |
| `research_review/results/phase0/witness/witness_results.json` | `10c32adb7eb0f30406fff3b7a8eecc9a7eff3688450e6f546e7e0b4f65df2dee` |
| `research_review/results/phase0/witness/environment.json` | `b600ce7d6d9ac79f448983e87fd3c92acbfb5720895fa25c244a9c5a7f395597` |
| `research_review/results/phase0/witness/witness_summary.txt` | `7f696d93f719657310112f131073fa571ce17584619bfacde01e34e0807215be` |
| `research_review/results/phase0/witness/run.log` | `6232b20f97d405150b58693eb374e8b61ce5d0365bd3cc7f268548ebffec8b32` |
| `.../figures/fig_singleton_bottleneck.png` | `1c54eb98781d1bced47310e00d2fd2859beed0913bff1763d69f317c718f32dd` |
| `.../figures/fig_equal_speed_paths.png` | `833ca76eef7b14ed78e79be9f8559208c024440171dc6f958a55594db3462b2e` |
| `.../figures/fig_angle_instability.png` | `f8dd4040e014044ac0b99e5a9e286522c5081884d30ee0552f749e9308946435` |
| `.../figures/fig_random_path_checks.png` | `90cfe355c919c47ce0131656fc08ef9ee379c9c37576dfa98d6e9dcab8fac744` |
| `research_review/results/phase0/verification/independent_checks.py` | `045b4a17d1307f5b7da30bbb153cf7920b11684fc6ba7a8c9926f64d029332b6` |

## 7.5 Final verdict for revision 2

Prior findings E1 and O1 are resolved. The new numerical-zero policy is implemented consistently across all four public metric backends, is independently reproduced by the verifier, and is directly confirmed by W-15: mathematical zero returns exactly `0.0`, `5e-13` is snapped, and `2e-12` is preserved. The suite now has 15 cases and 97 checks, all passing and exactly reproducible from the audited code with seed 20260920. The re-run falsification sweep over 540 paths found no violation of `R <= L`, efficiency bounds, angle ranges, validity conditions, or anomaly-flag consistency at the suite's `1e-9` tolerance, and the public default wrapper agrees with the independently snapped metric on every diagram path. Two bounded observations are recorded: O3 (raw `gudhi` order sensitivity, neutralized by the code's canonicalization) and E2 (snap-induced triangle-inequality violation at the `1e-12` scale, bounded by the declared `NUMERICAL_ZERO` and inside all suite tolerances). No unresolved discrepancy remains on the declared input domain.

Final verdict line: **Revision 2 re-verification PASS (10/10 top-level checks, exit 0); prior findings E1 and O1 resolved; new bounded observations O3 and E2 recorded; no unresolved discrepancy on the declared input domain.**
