# Pilot experiment specification

This appendix makes the first experiment in the [research plan](Topological_Kinematics_Research_Plan.md) executable. These are proposed experimental choices, not definitions supplied by the co-author or validated empirical findings. Only the small metric witness script has been run. The modules and commands below are implementation targets, not existing software.

## Question and scope

Can the email's compact metric-path diagnostics distinguish a return, sustained change, and abrupt change as reliably as stronger representations, with a demonstrable reduction in representation or computation cost? Start with offline classification of independent complete trajectories. Do not claim early warning, physical identification, or universal utility from this experiment. These simple generators deliberately give raw geometric baselines a strong opportunity to win. Failure limits this formulation; it does not disprove the wider possibility of useful topological dynamics.

## 1. Raw generators and independent labels

Use physical time u in [0,1], initially sampled at u=j/128, j=0,...,128. Every resolution experiment subsamples the SAME master realization at strides 1, 2, or 4, giving 129, 65, or 33 frames with the same horizon. Train separate fixed-dimensional models at each resolution.

For each independent seed draw a start time a uniformly in [0.15,0.25], an end time b uniformly in [0.75,0.85], and m=(a+b)/2. Put z(u)=0.5+2.5g(u). The three labels are assigned from these latent control programs before any persistence calculation:

| Class | Control g(u) |
|---|---|
| Return | Zero outside [a,b]; (u-a)/(m-a) for a<=u<=m; (b-u)/(b-m) for m<u<=b |
| Ramp | clip((u-a)/(b-a),0,1) |
| Jump | 1 if u>=m, otherwise 0 |

The return and ramp have deliberately different accumulated latent movement. Do not call this a matched-speed experiment. The existing singleton-diagram script supplies a separate equal-speed correctness control. A later independently preregistered control can match movement budgets; it must not be selected because it favors a descriptor.

**Family A, point clouds.** Draw a fixed orientation phi uniformly on [0,2pi), a radius r uniformly in [0.9,1.1], and 32 equally spaced angles on each of two circles with independently randomized phase offsets. At time u, their centers are (-z(u)/2,0) and (z(u)/2,0), and both have radius r. Rotate the entire configuration by phi. Add independent isotropic Gaussian coordinate noise with standard deviation sigma. There are 64 points per frame. Keep the circle sampling phases fixed over time; a later resampling control redraws them at every frame. Random orientation/radius/phase and observation noise vary across independent seeds, so test trajectories are not copies of a single template.

**Family B, scalar fields.** On a fixed 32 by 32 grid in [-4,4]^2, evaluate

`f_u(x,y)=A1*exp(-((x+z(u)/2)^2+y^2)/(2*w^2)) + A2*exp(-((x-z(u)/2)^2+y^2)/(2*w^2)) + noise`.

Draw A1,A2 independently uniformly in [0.9,1.1] and w uniformly in [0.35,0.45], fixed within each trajectory. Pixel noise is independent Gaussian with standard deviation sigma. Here sigma is in field-amplitude units, whereas Family A uses coordinate units; analyze the families separately before equal-weight aggregation. Changing peak or circle separation changes geometry. Whether the selected persistence channel resolves the intended change is a G2 check, not an assumed theorem.

**Controls.** Include z(u)=0.5 static trajectories with and without observation noise. A time-dependent rigid translation of the identical Family A point realization must leave its Vietoris--Rips diagrams unchanged up to numerical tolerance. Do not demand this of a shifted scalar field on a cropped grid. Scaling coordinates changes persistence coordinates and is not an invariance: report it as sensitivity. A separate scale-normalized analysis would change the observation map and must normalize every comparator identically. Keep these controls outside the three-class accuracy calculation and report them separately.

## 2. Persistence and measurement conventions

Use coefficient field F2. For Family A compute Euclidean Vietoris--Rips H0 and H1 with the edge-length filtration convention. For Family B compute cubical H0 and H1 of the sublevel sets of -f. Primary analysis uses finite H0 bars in both families; H1 is a predeclared secondary channel, reported separately. If finite H0 is uninformative in a family, report that failure rather than selecting a degree on its test labels. Drop essential infinite-death bars, record their counts, and retain all finite bars without label-dependent persistence thresholds.

The primary diagram metric is bottleneck with L-infinity ground norm. W2 with the same ground norm is a sensitivity branch after the cheap pilot; do not transfer bottleneck stability constants to W2. Empty finite diagrams are valid. Store exact filtration and library version metadata. Numerical correctness tolerance for the rigid-translation control is 1e-7 times max(1, filtration range); inspect failures before loosening tolerance.

The first experiment uses a single frame as its window. This is an explicit restricted instance of the email's pipeline. Before any application, add trailing-window pooling with lengths 1, 3, 5 frames and strides 1, 2, 4: concatenate Family A points, or average Family B fields, over each window. Report both window support in physical time and output stride. This changes the observation map and cardinality, so do not pool its results into the primary frame-level claim.

Use actual timestamps in speeds. Timestamp a speed at the midpoint of its interval; divide successive speed differences by the difference of these midpoint timestamps. For each training-only static-noise calibration, let e be the 95th percentile of adjacent diagram distances. Abstain on efficiency when L<=2(T-1)e and on comparison angles when min(a,b)<=2e. At zero noise retain exact-zero abstention. These are conservative operational floors, not coverage guarantees. Record validity fractions and report performance with and without these floors; no selective deletion of test trajectories. Do not discard straight or reversal angles merely to obtain a Lipschitz theorem.

## 3. Representations and fair learners

All representations receive the same complete trajectory. Fit centering/scaling and imputation using training data only. Retain missing-feature masks for every representation that needs them. No latent z, generator identity, or test labels may enter a feature.

| Representation | Fixed construction within each resolution |
|---|---|
| Compact email diagnostics | L,R,eta; mean, standard deviation, maximum of speed; mean absolute and maximum absolute speed-change; mean cosine comparison-angle; angle-valid fraction; efficiency-valid flag. Missing numeric features use a training median plus mask. Report the speed/L/R/eta ablation separately. |
| Speed history | Entire adjacent speed vector, plus the same six speed and speed-change summaries |
| Complete distances | Flattened upper triangle of the full diagram-distance matrix in temporal order; also include a recurrence-summary baseline with mean and minimum distances at lags 1,2,4,8 and endpoint displacement |
| Raw geometry | Family A: framewise pairwise-distance quantiles 0.1,0.5,0.9, covariance eigenvalues, and nearest-neighbor distance mean. Family B: framewise mean, standard deviation, maximum, and gradient-energy mean. Flatten temporal histories; also compare their temporal mean/std summaries. |
| Persistence moments | Per frame, sums of b^i*p^j for p=death-birth, j>=1 and i+j<=3 (six coordinates). Flatten histories and compare mean/std summaries. These finite moments are not claimed injective. |
| Moment signatures | Piecewise-linear path of the six moment coordinates, signature through level 2, both without time and with u as an extra coordinate. Fit coordinate scaling on training data. This is an explicit finite-vector comparator, not subtraction of unmatched diagrams or a borrowed bottleneck stability theorem. |

Run multinomial logistic regression with C in {0.01,0.1,1,10} and RBF SVM with C in the same set and gamma in {0.1/d,1/d,10/d}, where d is the postprocessed feature dimension. Use identical validation rules for all representations. Predict multiclass labels by the fitted classifier, not a binary threshold. Select the best learner for each representation by validation macro balanced error, breaking ties by lower measured prediction cost. Select the incumbent representation on validation, then freeze it before test evaluation. Also retain all individual incumbent results so a small raw or moment baseline cannot be hidden behind a large matrix comparator.

## 4. Stages, seeds, and precision

1. **Correctness and resource pilot:** both families, all three classes, sigma in {0,0.05}, seed 11, master stride 1: 12 trajectories plus static/translation controls. Subsample their saved frames for strides 2 and 4. Run one trajectory first and measure wall time and peak RAM before the remaining pilot. This stage checks construction and costs, not comparative accuracy.
2. **Exploratory implementation study:** independent base seeds 1000--1039 for training, 2000--2019 for validation, and 3000--3039 for exploratory testing, each crossed with both families, three classes, sigma in {0,0.05}, and strides 1,2,4. Seed namespaces include family and class; all noise/resolution variants from one base seed stay in the same split. Cache raw trajectories, diagrams, and distances. If profiling projects excessive cost, reduce the exploratory grid before running it and record the change; do not reduce cells after seeing outcomes.
3. **Confirmatory study:** freeze every choice after Stage 2, retain training/validation data, and use new test seeds starting at 10000. Choose ONE test size in advance from {200,500,1000,2000} base-seed clusters, using exploratory paired error variance and a target confidence-interval half-width of 0.01 for a 0.02 noninferiority margin. Estimate cost before scheduling a large run. If even the largest affordable size cannot resolve the margin, label the result INDETERMINATE. Do not repeatedly peek and stop when significance appears. This cap is a precision feasibility check, not a request to run thousands of experiments now.

Evaluate macro balanced error within each family/noise/resolution cell, then average those cells equally. Use a paired bootstrap of whole base-seed clusters, 2000 resamples, bootstrap seed 20260907; preserve the pairing of all methods and all correlated noise/resolution variants. Report per-class confusion matrices and family-specific error differences. Uncertainty is conditional on the frozen fitted models; do not call it uncertainty over retraining. Study training-sample efficiency separately if that is the proposed advantage.

## 5. Predeclared pilot decision

Let delta be compact-diagnostic error minus the validation-selected incumbent error. The following thresholds are pragmatic simulation design choices, not established application utility thresholds.

**GO to application feasibility** requires correctness and nuisance checks, adequate precision, and either (a) the upper endpoint of a paired 95% interval for delta is below -0.05, or (b) that endpoint is below 0.02 and the compact representation achieves at least a fourfold reduction in feature dimension or measured end-to-end prediction cost relative to the cheapest competitor whose validation macro balanced error lies within 0.02 of the best validation result. Freeze this eligible comparator set before opening test results. Include diagram extraction in end-to-end cost and separately report distance/feature/classifier costs. A tiny raw-data or speed-summary incumbent that ties the method at lower cost defeats the parsimony argument. Neither route may hide a family-specific deterioration above 0.05; use simultaneous family bounds with Bonferroni-adjusted intervals. Freeze the superiority-versus-parsimony claim after exploration and before confirmation, rather than choosing the favorable route afterward.

An interval too wide to decide gives **INDETERMINATE**, not failure. Reliable domination by a simpler incumbent gives **INCREMENTAL-ONLY** for this diagnostic task. A reproducible but narrower useful result gives **PIVOT**, with a new protocol and untouched test seeds. Broken extraction, circular labels, or leakage requires repairing and rerunning the affected stage. No outcome of these two toy families alone establishes a universal kinematics or kills all possible applications.

## 6. Artifacts and implementation contract

Implement `src/tk_pilot/{generators,persistence,features,models,evaluate,run}.py`, package installation metadata, and `configs/tk_pilot.yaml`. Intended commands are `python -m tk_pilot.run --stage smoke`, `--stage exploratory`, and `--stage confirmatory`; these commands do not exist yet. The first implementation package must make the smoke command run without assuming a preexisting package.

Save configuration, environment versions, independent split manifest, raw control paths, diagram arrays, distance matrices, feature definitions, fitted preprocessing, validation choices, test predictions, failures, and timing/RAM measurements. The result table fields are `run_id,base_seed,family,class,sigma,stride,degree,metric,representation,learner,split,true_label,predicted_label,valid_fraction,feature_dim,extraction_seconds,feature_seconds,prediction_seconds,peak_ram_bytes,status`. Save the gate memo and bootstrap intervals beside this table. Preserve experiment outputs; do not gitignore them.

Start with one process. Set numerical-library threads to one per worker and expand only within measured free-core and RAM limits, leaving capacity for other work. Route long sweeps to checkpointed independent shards only after the pilot. Colab notebooks, if later created, must be self-contained, zip five or more outputs, and include the user's safe `files.download` fallback. No full sweep or notebook has been created by this planning task.
