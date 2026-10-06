# Difficulty pilot: matched-budget reversible-versus-drift protocol

Status: COMPLETE. Date: 2026-10-06. Coordinator: main agent. Stage: post-PIVOT difficulty
pilot, outside the frozen three-class pilot and outside the confirmatory block. No seed at or
above 10000 was touched; the confirmatory block is still intact.

## 1. What was built

1. `src/tk_pilot/matched_budget.py`. New two-class generator that reuses the frozen Family A
   and Family B raw maps, the frozen noise conventions, and the frozen exact metric. The latent
   level is `z(u) = 0.5 + cumulative signed steps` on the 129-frame master grid. Both classes
   share the same window `[a, b]`, the same mirrored step profile, the same multiset of latent
   step magnitudes, and the same latent path length `B`; `reversible` uses `+` steps for the
   first half and `-` steps for the second half, and `drift` uses `+` steps throughout. The
   classes therefore differ only in the direction order, not in how much the latent system
   moves. The net latent displacement is 0 for `reversible` and `B` for `drift`.
2. `src/tk_pilot/next_protocol_pilot.py`. Difficulty-pilot harness with its own seed
   namespace (4000 to 4299), a per-cell training-only noise floor calibrated from static
   trajectories at the cell's own noise level, the frozen exact metric, the frozen path
   diagnostics, and the frozen learner grid. Representations screened: `compact`,
   `speed_history`, `raw_geometry_flat`, `raw_geometry_summary`, `moments_summary`, and
   `moment_signature_time`.
3. `tests/test_matched_budget.py`. Invariants: the two classes share the step multiset and
   latent path length, the reversible endpoint returns exactly to its start while the drift
   endpoint moves by exactly `B`, stride variants sub-sample one master realization, and
   noise-free realizations are deterministic.

## 2. What was run

| Tag | Grid | Seeds (train/val/test) | Cells | Trajectories |
|---|---|---|---|---|
| `smoke` | A, B=1.0, sigma=0.05, stride 1 | 4/2/3 | 1 | 18 |
| `stage1a` | A; B in {0.1,0.25,0.5,1.0}; sigma in {0.05,0.1,0.2}; stride 1 | 12/6/10 | 12 | 672 |
| `stage1b` | A and B; B in {0.5,1,2,3}; sigma in {0.05,0.1}; strides {1,8} | 8/4/8 | 32 | 1,280 |
| `stage1c` | A and B; B in {0.05,0.1,0.25}; sigma in {0.2,0.4}; strides {1,4,16} | 8/4/8 | 36 | 1,440 |
| `stage2a` | A and B; B in {0.1,0.25,0.5}; sigma=0.2; stride 1 | 40/20/60 | 6 | 1,440 |

`stage2a` is the powered confirmation run: 120 test trajectories per family-and-budget cell.
All other stages are screening sweeps with 16 to 32 test trajectories per cell.

## 3. Results

### 3.1 Powered run (`stage2a`, test macro balanced error)

| Family | Budget B | compact | raw_geometry_flat | speed_history | raw_geometry_summary | moments_summary |
|---|---|---|---|---|---|---|
| A | 0.10 | 0.5000 | 0.0500 | 0.5083 | 0.0750 | 0.4500 |
| A | 0.25 | 0.4917 | 0.0000 | 0.4667 | 0.0167 | 0.2000 |
| A | 0.50 | 0.4000 | 0.0000 | 0.3667 | 0.0000 | 0.0333 |
| B | 0.10 | 0.5083 | 0.1000 | 0.5167 | 0.3417 | 0.5000 |
| B | 0.25 | 0.3750 | 0.0000 | 0.4417 | 0.0417 | 0.1833 |
| B | 0.50 | 0.1917 | 0.0000 | 0.1417 | 0.0000 | 0.0083 |

### 3.2 Screening sweep

Across 87 distinct cells in `stage1a` to `stage1c`, `raw_geometry_flat` has the strictly lower
test error in 56 cells, the two tie in 17, and compact is strictly lower in 13, all of which are
small-test-set cells with both methods at chance level (errors between 0.25 and 0.75). None of
the compact "wins" survives the powered run: at every `stage2a` setting raw geometry dominates.

### 3.3 The non-ceiling regime

The protocol requires the strongest baseline to fall below ceiling before the comparison is
meaningful. That regime exists: at `B = 0.1` and `sigma = 0.2`, `raw_geometry_flat` reaches
0.0500 on Family A and 0.1000 on Family B, so the task is not saturated. In exactly that
regime the compact diagnostics sit at chance, 0.5000 and 0.5083. There is no setting in the
explored space where the baseline is below ceiling and the compact diagnostics are
noninferior.

## 4. Why the compact channel fails

1. **The angle channel is gated off where it is needed.** The compact angle valid fraction is
   essentially zero in the low-budget cells (about 6.6e-05 in the powered run), because
   adjacent H0 diagram distances sit below the twice-the-floor threshold. A per-seed angle
   diagnostic at `B = 1, sigma = 0.05` with the floor removed confirms that the channel is not
   just gated but weak: the mean cosine differs by about 0.02 between classes, and the minimum
   cosine is near -1 for both classes because the bottleneck path is not smooth enough for the
   law-of-cosines statistic to track the latent reversal cleanly.
2. **A single reversal is averaged away.** The compact vector carries the mean valid cosine,
   while the only order difference of this DGP is one reversal out of 127 interior steps. One
   step contributes about 1/127 of the mean, far below the sampling noise of a 12-feature
   vector.
3. **The endpoint cue lives in raw geometry, not in the H0 diagram.** Matching the latent
   movement budget leaves the net displacement `R` as the true class signal: drift ends away,
   reversible returns. Raw framewise features track the separation trend across all frames, so
   their effective signal-to-noise ratio grows with trajectory length. The H0 bottleneck
   distance between the first and last diagram is a single noisy endpoint comparison, and it is
   numerically small while the point-cloud components overlap (about 0.047 at `B = 0.25` in
   the earlier probe, at or below the calibrated floor). The compact representation therefore
   sees a weaker version of the same cue that raw geometry sees more robustly.

## 5. Pilot gate outcome

FAIL for the GO route of the proposed protocol as written. The protocol's own difficulty
requirement is that the strongest raw baseline fall below ceiling and that the compact
diagnostics remain competitive there; the powered run shows the baseline below ceiling
(0.05 to 0.10) with the compact diagnostics at chance (0.50 to 0.51). A pre-registered
confirmatory run of this protocol would spend the untouched seeds and return
INCREMENTAL-ONLY or KILL, not GO or PIVOT. The confirmatory block was not opened.

## 6. Options for the co-authors

1. **Record the decision and narrow the program.** The matched-budget pilot is a second
   independent operationalisation that fails to favor the compact diagnostics. Together with
   the three-class ceiling, this supports the methods-note option from the report: the exact
   metric solver, the witness, the correctness ladder, the deterministic interface, and the
   decision-rule implementation are the durable contribution.
2. **Change the contrast, not the machinery.** Drop "persistent drift" and test an order-only
   hypothesis in which both classes share their endpoints, their movement budget, and the
   multiset of visited levels, differing only in the temporal order of the excursions. This is
   the only way to remove the net-displacement cue entirely. It is a new hypothesis, not the
   original reversible-versus-drift hypothesis.
3. **Change the observation map.** The H0 bottleneck endpoint distance is insensitive below
   the connectivity transition. A Wasserstein endpoint distance, an H1 channel near the
   transition, or a scale-normalized filtration could raise the diagram-space signal. Any
   such change requires a fresh pre-registration and a fresh correctness pass.
4. **More seeds at the frontier.** The `B = 0.1, sigma = 0.2` cells are the decisive ones.
   They could be repeated with 200 or more test seeds per family to narrow the compact
   interval around chance, but the point estimate is already 0.5 with 120 test trajectories,
   and no mechanism suggests it would move toward the baseline's 0.05 to 0.10.

## 7. Artifacts

1. Generators and harness: `src/tk_pilot/matched_budget.py`,
   `src/tk_pilot/next_protocol_pilot.py`, `tests/test_matched_budget.py`.
2. Pilot outputs: `research_review/results/next_protocol/{smoke,stage1a,stage1b,stage1c,stage2a}/`
   with `summary.csv` and `metrics.json` per tag. Results are not gitignored.
3. Nothing was committed; the user controls the commit. No confirmatory seed was opened.
