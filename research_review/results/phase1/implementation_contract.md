# WP-1.1/WP-1.2 implementation contract (frozen interfaces)

This document freezes the module boundaries, data schemas, and numerical conventions for the
pilot package `src/tk_pilot/`. It is written under the authority of
`research_review/Pilot_Experiment_Specification.md` (numeric constants and protocol),
`research_review/assumption_ledger.yaml` and `research_review/metric_interface.md` (metric, clock,
edge-case policies). If this contract disagrees with those documents, they govern and the
disagreement is recorded in `research_review/results/phase1/EXECUTION_LOG.md`.

Every agent implementing a module must follow this contract exactly. Do not change shared
signatures without recording the change in the execution log.

## 0. Environment and restrictions

- Python 3.12.3; numpy 2.4.3, scipy 1.17.1, gudhi 3.12.0, persim 0.3.8, scikit-learn 1.8.0,
  pandas 3.0.1, joblib 1.5.3, matplotlib 3.10.8, pytest 9.0.3, PyYAML 6.0.1.
- No new third-party dependencies. No network access inside library code or tests.
- CPU budget: 8 logical CPUs total. Library code must accept a `workers` argument and tests must
  run single-process and finish in under 60 seconds each file.
- Determinism: every stochastic step is driven by a seeded `numpy.random.Generator`. Persisted
  artifacts are bitwise reproducible. Use `np.float64` for all geometry and distances.
- Results must never be gitignored. Do not add results, figures, memos, or caches to
  `.gitignore`. Code modules are the only things agents in this phase write under `src/tk_pilot/`.
- Ruff/mypy are not installed; keep type hints and docstrings consistent with existing modules.
  Do not add code comments; docstrings are allowed.

## 1. Frozen scientific conventions (do not modify)

- Primary metric: bottleneck distance with L-infinity ground norm, diagonal cost `(d - b)/2`,
  implemented by `tk_pilot.diagram_metrics.bottleneck_linf` (gudhi 3.12.0). Essential classes are
  stripped with recorded counts. Empty finite diagrams are valid.
- Coefficients F2. Family A: Euclidean Vietoris-Rips H0/H1 with the edge-length filtration.
  Family B: cubical H0/H1 of sublevel sets of `-f` (i.e. `CubicalComplex(top_dimensional_cells=-f)`).
- Primary degree H0; H1 is a predeclared secondary channel reported separately (same protocol).
- Clock: master grid `u = j/128`, `j = 0..128`; strides 1, 2, 4 subsample frames and keep the
  horizon `[0, 1]`. Speeds are timestamped at interval midpoints; speed-change uses the midpoint
  denominator. See `path_diagnostics.py`.
- Three scientific classes with latent control `g(u)` and `z(u) = 0.5 + 2.5 g(u)`:
  return (triangular pulse), ramp (clipped linear), jump (step at midpoint `m`).
- Noise `sigma in {0, 0.05}`. Abscissa units: Family A coordinate units, Family B field amplitudes.
- Controls (outside the three-class accuracy calculation): static `z(u)=0.5` with and without
  noise; rigid translation of a Family A realization; matched-speed ordering construction;
  scale sensitivity (reported, not an invariance).

## 2. Package layout and file ownership

```
src/tk_pilot/__init__.py        [A1]
src/tk_pilot/generators.py      [A1]
src/tk_pilot/splits.py          [A1]
src/tk_pilot/persistence.py     [A2]
src/tk_pilot/features.py        [A4]
src/tk_pilot/signatures.py      [A4]
src/tk_pilot/models.py          [A5]
src/tk_pilot/evaluate.py        [A5]
src/tk_pilot/run.py             [A5]
configs/tk_pilot.yaml           [A1]
tests/test_generators.py        [A1]
tests/test_persistence.py       [A2]
tests/test_features.py          [A4]
tests/test_models_evaluate.py   [A5]
scripts/run_smoke.py            [A5, thin wrapper calling run.py]
```

Existing modules `diagram_metrics.py`, `path_diagnostics.py`, `witnesses.py`, `witness_figures.py`
are frozen G0 artifacts: do not modify them.

## 3. Seed derivation (frozen)

`family_id`: A=0, B=1. `label_id`: return=0, ramp=1, jump=2, static=3, translation=4,
matched_forward=5, matched_folded=6.

- Latent RNG: `np.random.default_rng([base_seed, family_id, label_id, 101])`; draws the latent
  parameters once per `(base_seed, family, label)` and is shared by all sigmas and strides.
- Noise RNG: `np.random.default_rng([base_seed, family_id, label_id, 202, sigma_tag])` with
  `sigma_tag = int(round(sigma * 1000))`. At `sigma = 0` no noise is drawn or added.
- Stride variants are exact subsamples of the stride-1 master realization
  (`frames[::stride]`, `timestamps[::stride]`).
- Trajectory id: `f"{family}_{label}_{base_seed}_sigma{sigma_tag}"`.

## 4. `generators.py` (A1)

```python
@dataclass(frozen=True)
class Trajectory:
    trajectory_id: str
    family: str            # "A" or "B"
    label: str             # return|ramp|jump|static|translation|matched_forward|matched_folded
    base_seed: int
    sigma: float
    stride: int
    timestamps: np.ndarray # (n,) float64, u = j/128 subsampled
    frames: np.ndarray     # A: (n, 64, 2) float64; B: (n, 32, 32) float64
    z: np.ndarray          # (n,) latent separation per retained frame
    latent: dict           # JSON-safe parameters (a, b, m, phi, r, phases, A1, A2, w, ...)

def build_trajectory(family: str, label: str, base_seed: int, sigma: float,
                     stride: int = 1) -> Trajectory
def build_control(control: str, family: str, base_seed: int, sigma: float,
                  stride: int = 1) -> Trajectory
def save_trajectory(traj: Trajectory, cache_dir: Path) -> Path
def load_trajectory(family: str, label: str, base_seed: int, sigma: float,
                    stride: int, cache_dir: Path) -> Trajectory
```

Details.

- Master realization: grid `u = j/128`, `j = 0..128` (129 frames). Always generated at stride 1
  level; `build_trajectory(..., stride=s)` returns `frames[::s]`, `timestamps[::s]`, `z[::s]`.
- Latent draws: `a ~ U[0.15, 0.25]`, `b ~ U[0.75, 0.85]`, `m = (a+b)/2`.
  Family A: `phi ~ U[0, 2pi)`, `r ~ U[0.9, 1.1]`, phases `p1, p2 ~ U[0, 2pi)`.
  Family B: `A1, A2 ~ U[0.9, 1.1]`, `w ~ U[0.35, 0.45]`.
- Class programs (identical to the pilot specification):
  return: `0` outside `[a,b]`; `(u-a)/(m-a)` on `[a,m]`; `(b-u)/(b-m)` on `(m,b]`.
  ramp: `clip((u-a)/(b-a), 0, 1)`. jump: `1[u >= m]`. static: `g(u) = 0` for all `u`.
- Family A frame construction: 32 equally spaced angles per circle, fixed phases `p1`, `p2` over
  time; centers `(-z/2, 0)`, `(z/2, 0)`; radius `r`; whole configuration rotated by `phi`; then
  additive isotropic Gaussian noise std `sigma`. 64 points per frame.
- Family B: fixed 32x32 grid on `[-4,4]^2`; `f = A1*exp(-((x+z/2)^2+y^2)/(2w^2)) +
  A2*exp(-((x-z/2)^2+y^2)/(2w^2))`; additive pixel noise std `sigma`.
- Controls:
  - `static`: z constant 0.5.
  - `translation` (Family A only): identical Family A static realization plus a time-dependent
    translation `tau(u) = (0.5*sin(2*pi*u), 0.25*cos(2*pi*u))` applied to all points; diagrams
    must be invariant within `1e-7 * max(1, filtration range)`. Family B translation is not
    required.
  - `matched_forward` and `matched_folded`: explicit z-level sequences with identical consecutive
    step magnitudes and identical endpoints but different intermediate order. Use 5 frames at
    times `[0, 0.25, 0.5, 0.75, 1.0]`; forward z = `[0.5, 1.0, 1.5, 1.0, 0.5]`,
    folded z = `[0.5, 1.0, 0.5, 1.0, 0.5]`. (Both have |dz| = 0.5 per step; L and R are matched
    up to the metric's non-linearity in z.) Implement them as a Trajectory whose frames come from
    the same latent parameters (phi, r, phases, noise) as the matching seed, with `z` overridden.
    Keep them outside the 3-class accuracy calculation.
- `save_trajectory` stores `frames`, `timestamps`, `z`, `latent` in a compressed npz plus a
  `meta.json` (JSON-safe latent dict) and a `sha256` of the frames bytes. `load_trajectory`
  is exact.

## 5. `persistence.py` (A2)

```python
def finite_diagram(raw_intervals) -> tuple[np.ndarray, int]
def family_a_diagram(points: np.ndarray, degree: int) -> tuple[np.ndarray, int]
def family_b_diagram(field: np.ndarray, degree: int) -> tuple[np.ndarray, int]
def trajectory_diagrams(frames, family, degrees=(0, 1)) -> dict[int, list[np.ndarray]]
def trajectory_essential_counts(frames, family, degrees=(0, 1)) -> dict[int, list[int]]
def save_diagram_cache(traj: Trajectory, cache_dir: Path) -> Path
def load_diagram_cache(traj: Trajectory, cache_dir: Path) -> dict
def pool_window(frames, family, length: int, stride: int) -> tuple[np.ndarray, np.ndarray]
def diagrams_for_windows(frames, family, length, stride, degrees=(0,1)) -> dict
```

Details.

- `family_a_diagram`: `st = gudhi.RipsComplex(points=points).create_simplex_tree(max_dimension=2)`;
  `st.compute_persistence(homology_coeff_field=2, min_persistence=0.0)`;
  `intervals = np.asarray(st.persistence_intervals_in_dimension(degree), dtype=float)`.
- `family_b_diagram`: `cc = gudhi.CubicalComplex(top_dimensional_cells=-field)`;
  `cc.compute_persistence(homology_coeff_field=2, min_persistence=0.0)`;
  `intervals = np.asarray(cc.persistence_intervals_in_dimension(degree), dtype=float)`.
- `finite_diagram`: drop rows with non-finite death, count them, validate `birth <= finite death`,
  canonically sort lexicographically by `(birth, death)`, return float64 `(m, 2)` array and the
  essential count. Reuse `tk_pilot.diagram_metrics.strip_essential` semantics (no import cycles:
  importing from `diagram_metrics` is allowed).
- `trajectory_diagrams`: one persistence computation per frame per degree (do not rebuild the
  complex twice; compute H0 and H1 from a single `compute_persistence` call when possible).
- Cache layout: `{cache_dir}/{family}/{label}/{base_seed}/sigma{sigma_tag}/stride{stride}/`
  containing `diagrams.npz` (keys `d0_000`, `d1_000`, `d0_001`, ..., one array per frame),
  `essential.npz`, `meta.json` with frame count, timestamps, degree list, gudhi version, and
  `SHA256SUMS`. `load_diagram_cache` verifies hashes and returns
  `{"diagrams": {0: [...], 1: [...]}, "essential": {0: [...], 1: [...]}, "meta": {...}}`.
- `pool_window` (WP-2.1 separate observation map): trailing windows of `length` frames at output
  stride `stride`; window timestamp = end-of-window time; Family A pools by concatenating points,
  Family B by averaging fields. Return `(frames, timestamps)`. Lengths 1, 3, 5 and strides 1, 2, 4
  are the only supported combinations; these results are never pooled into the primary
  frame-level claim.

## 6. `features.py` and `signatures.py` (A4)

```python
REPRESENTATIONS = (
    "compact", "speed_history", "complete_distances", "recurrence_summary",
    "raw_geometry_flat", "raw_geometry_summary",
    "moments_flat", "moments_summary",
    "moment_signature", "moment_signature_time",
)

def cell_floor(adjacent_distances_by_trajectory) -> float
def build_representations(traj, diagrams, degree, metric, floor_e=None,
                          timestamps=None) -> dict[str, np.ndarray]
def signature_level2(path: np.ndarray) -> np.ndarray
def signature_level2_time(path: np.ndarray, timestamps: np.ndarray) -> np.ndarray
```

Details.

- `build_representations` receives one trajectory and its cached diagrams for one degree, and
  returns a dict mapping representation name to a 1-D float64 vector. All representations use the
  same retained frames. Distances are computed with the frozen metric; for stride s the distance
  matrix is the stride-1 matrix subsampled at indices `0, s, 2s, ...` when a cached stride-1
  matrix is supplied, otherwise computed directly. Include an optional argument
  `distance_matrix=None` to avoid recomputation; if `None`, compute the full pairwise matrix.
- `compact` (12 features): `L`, `R`, `eta`; mean, std, max of `nu`; mean signed speed-change,
  mean absolute speed-change, max absolute speed-change; mean `cos(theta)` over valid angles;
  angle-valid fraction; efficiency-valid flag (`L > 2 (T-1) e`). This resolves the inherited
  "six speed and speed-change summaries" ambiguity by adding the mean signed speed-change to the
  five named quantities (recorded in the deviations log). `eta` is NaN when `L = 0`.
- `speed_history`: all adjacent speeds, then the same six speed/speed-change summaries.
- `complete_distances`: strictly-upper triangle of the frame-by-frame distance matrix in
  row-major temporal order. `recurrence_summary`: mean and minimum distance at lags 1, 2, 4, 8 plus
  endpoint displacement `R`.
- `raw_geometry_flat` / `raw_geometry_summary`: Family A per frame: pairwise-distance quantiles
  0.1, 0.5, 0.9, the two covariance eigenvalues, mean nearest-neighbor distance; Family B per
  frame: mean, std, max, mean gradient energy. Flat = concatenated histories; summary = temporal
  mean and std of each per-frame quantity.
- `moments_flat` / `moments_summary`: per frame moments `sum_i b_i^a p_i^j` for `(a, j)` in
  `[(0,1), (1,1), (2,1), (0,2), (1,2), (0,3)]` with `p = death - birth`; empty diagram -> zeros;
  flat = concatenated histories, summary = temporal mean and std.
- `moment_signature`: signature through level 2 (levels 1 and 2 concatenated, dimension 42 for
  d=6) of the piecewise-linear path through the six moment coordinates.
  `moment_signature_time`: the same with `u` appended as a seventh coordinate (dimension 56).
  Implement the exact level-2 signature of a piecewise-linear path in `signatures.py` with
  `signature_level2(path)` = `[S1, S2]` where `S1 = sum_k dx_k` and
  `S2 = sum_{k} [ outer(dx_k, S1_{<k}) + 0.5 * outer(dx_k, dx_k) ]` with `S1_{<k}` the sum of
  increments before segment `k` (Chen's identity); flatten row-major. Coordinate scaling for the
  signature is fit on training data only by the model pipeline; the feature function does not
  scale.
- Missing values are NaN and are handled by the model pipeline with training-only median
  imputation plus a missing mask per feature column. `valid_fraction` per trajectory is the
  angle-valid fraction for `compact` and 1.0 for other representations.
- Unit tests must include an analytic check of `signature_level2` on a straight path
  (`S1 = total displacement`, `S2 = 0.5 * outer(D, D)`) and on a two-segment L-shape.

## 7. `models.py`, `evaluate.py`, `run.py` (A5)

```python
# models.py
LEARNER_GRIDS = {
    "logistic": {"C": [0.01, 0.1, 1.0, 10.0]},
    "svm_rbf": {"C": [0.01, 0.1, 1.0, 10.0], "gamma_scale": [0.1, 1.0, 10.0]},
}
def preprocess_fit(X_train) -> dict
def preprocess_apply(pre, X) -> np.ndarray
def fit_select_predict(X_train, y_train, X_val, y_val, X_test=None,
                       feature_costs=None, seed=20260907) -> dict

# evaluate.py
def macro_balanced_error(y_true, y_pred) -> float
def cell_table(...) -> pd.DataFrame
def equal_weight_cell_average(table, representation, split) -> float
def paired_cluster_bootstrap(table, reference, candidate, n_resamples=2000,
                             seed=20260907) -> dict
def decide(delta_ci, parsimony_ratio, family_bounds, thresholds) -> dict
```

Details.

- Preprocessing: per-column training median imputation, training mean/std standardization
  (`ddof=0`), plus a missing-mask column per original feature that had any training missingness.
  Applied to validation and test with training statistics only. Constant columns map to zero.
- Learners: `LogisticRegression(C=c, max_iter=5000, solver="lbfgs")` and
  `SVC(kernel="rbf", C=c, gamma=g/d)` with `d` the postprocessed dimension. Deterministic
  (`random_state` fixed). Select the learner by validation macro balanced error; ties broken by
  measured prediction seconds, then by learner name for determinism.
- `fit_select_predict` returns `{"predictions": ..., "learner": ..., "val_error": ...,
  "feature_dim": ..., "prediction_seconds": ..., "model": ...}`.
- `evaluate` implements the pilot specification exactly: macro balanced error within each
  `(family, sigma, stride, degree)` cell, equal-weight average over cells, paired bootstrap of
  whole `(family, class, base_seed)` clusters (2000 resamples, seed 20260907), Bonferroni family
  bounds over 2 families, and the two-route GO rule. Route selection and the eligible comparator
  set are inputs, frozen before confirmatory test evaluation.
- `run.py` CLI: `python -m tk_pilot.run --stage {smoke,exploratory,confirmatory} --config
  configs/tk_pilot.yaml [--workers N] [--outdir DIR] [--max-trajectories N]`.
  - `smoke`: seed 11 only, both families, three classes, `sigma in {0, 0.05}`, stride 1, plus
    controls; writes the results table, timings, peak RAM, and figures under
    `research_review/results/phase1/smoke/`. Must finish in under 20 minutes with 2 workers.
  - `exploratory`: training 1000-1039, validation 2000-2019, exploratory test 3000-3039; both
    families, three classes, `sigma in {0, 0.05}`, strides 1, 2, 4; degree H0 primary and H1
    secondary; caches raw frames, diagrams, distance matrices; writes the results table, bootstrap
    intervals, figures, and `exploratory_report.md` under `research_review/results/g3/exploratory/`.
  - `confirmatory`: new test seeds starting at 10000 with a frozen size from
    `{200, 500, 1000, 2000}` base-seed clusters and the frozen route; writes under
    `research_review/results/g3/confirmatory/`.
  - Results table columns exactly: `run_id, base_seed, family, class, sigma, stride, degree,
    metric, representation, learner, split, true_label, predicted_label, valid_fraction,
    feature_dim, extraction_seconds, feature_seconds, prediction_seconds, peak_ram_bytes, status`
    (write Parquet when `pyarrow` is available, otherwise `metrics.csv.gz`, plus a `metrics.parquet`
    name record in the manifest). Also write `manifest.json` with environment versions, worker
    count, peak RAM, wall time, config hash, and per-stage grid.
  - Cache directories default to `research_review/results/cache/`; outputs are never gitignored.
- The runner must expose the raw controls required by WP-3.1 and the matched-speed controls for
  the C3 diagnostic comparison, storing them outside the 3-class accuracy calculation.

## 8. Configuration (`configs/tk_pilot.yaml`, A1)

Keys with frozen values: `master_grid: {n: 128}`, `strides: [1, 2, 4]`, `sigmas: [0.0, 0.05]`,
`classes: [return, ramp, jump]`, `families: [A, B]`, `seed_namespaces: {train: [1000, 1039],
validation: [2000, 2019], test_exploratory: [3000, 3039], test_confirmatory_start: 10000}`,
`degrees: {primary: 0, secondary: 1}`, `metric: bottleneck_linf`, `representations: [...]` from
section 6, `learner_grids` from section 7, `bootstrap: {n_resamples: 2000, seed: 20260907}`,
`decision: {superiority_upper: -0.05, noninferiority_upper: 0.02, parsimony_ratio: 4.0,
family_deterioration: 0.05, target_half_width: 0.01}`, `noise_floor: {sigma_calibration: 0.05,
percentile: 95.0, angle_factor: 2.0, efficiency_factor: 2.0}`.

## 9. Cross-module invariants to test

1. `diagrams_for_windows(..., length=1, stride=1)` equals `trajectory_diagrams`.
2. Stride-subsampled distance matrix equals the submatrix of the stride-1 matrix.
3. `build_representations` compact features reproduce `path_diagnostics` values for a random
   small trajectory (compare L, R, eta, speed summaries).
4. Family A diagram is invariant under rigid translation within `1e-7 * max(1, range)`.
5. `signature_level2` straight-line and L-shape analytic values are exact to `1e-12`.
6. No NaNs in feature vectors except the documented undefined compact entries.
7. Feature dimensions are constant within a cell across trajectories.

## 10. Integration rule

Any agent that needs a signature not listed here must record the addition in
`research_review/results/phase1/EXECUTION_LOG.md` with a one-line reason, then implement it.
Agents must run `python -m pytest tests/ -q` (their own file at minimum) before reporting done and
report the exact command and result in their final message.
