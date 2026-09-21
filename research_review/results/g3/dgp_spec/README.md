# Data-generating process specification (WP-3.2)

The executable DGP specification is frozen in `research_review/Pilot_Experiment_Specification.md`
section 1 and implemented in `src/tk_pilot/generators.py` under the seed derivation of the
implementation contract. The exploratory run used config `configs/tk_pilot_study.yaml` with
sha256 recorded in `../exploratory/manifest.json` and `../exploratory/config_effective.json`.

- Latent control: start `a ~ U[0.15, 0.25]`, end `b ~ U[0.75, 0.85]`, midpoint `m = (a+b)/2`,
  `z(u) = 0.5 + 2.5 g(u)` with return (triangular pulse), ramp (clipped linear rise), and jump
  (step at `m`) programs assigned before any persistence computation.
- Family A: two circles of radius `r ~ U[0.9, 1.1]` with 32 fixed-phase points each, centers at
  `(-z/2, 0)` and `(z/2, 0)`, global rotation `phi ~ U[0, 2pi)`, isotropic Gaussian noise
  `sigma in {0, 0.05}`.
- Family B: two Gaussian bumps of amplitudes `A1, A2 ~ U[0.9, 1.1]` and width `w ~ U[0.35, 0.45]`
  on a 32 by 32 grid in `[-4, 4]^2`, separated by `z(u)`, with pixel noise `sigma`.
- Master grid `u = j/128`, `j = 0..128`; strides 1, 2, 4 subsample the same realization; horizon
  fixed at [0, 1].
- Controls: static, translation, and matched-speed ordering constructions as implemented in
  `src/tk_pilot/generators.py`.

The per-seed raw trajectories and diagrams are preserved in the shared cache under
`research_review/results/cache/`; the per-trajectory predictions and costs are in
`../metrics.parquet`, and the split membership is in `../splits/exploratory_split_manifest.csv`.
