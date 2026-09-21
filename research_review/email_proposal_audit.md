# Topological Kinematics: proposal reconstruction and preflight audit

## Scope and source state

The root source is `email.pdf`, a six-page Gmail printout dated 3 September 2026. It has no text
layer, so the reconstruction below was made from rendered pages 1--6. Supplied source PDFs were
converted to text in `/tmp/tk_review/`; this note does not silently merge versions. The tiny metric
angle witness is reproducible with
`rtk python3 research_review/topological_kinematics_witness.py`.

## Exact proposal reconstructed from the email

The proposed input is temporal data \(X(t)\), divided into consecutive or overlapping windows
\(W_0,\ldots,W_T\). Each window is mapped to a topological object \(X_t\), possibly through a
time-delay embedding, then persistent homology in dimension \(k\) produces diagrams
\(D_t^{(k)}\). For a fixed \(k\), the sequence \(D_0,\ldots,D_T\) is regarded as a path through a
metric space of persistence diagrams rather than as unrelated snapshots. The intended output is a
domain-independent kinematic vocabulary: position, speed/velocity, acceleration, direction/turning,
path length, net displacement, trajectory efficiency, and structural instability. The email explicitly
withdraws novelty claims for the mere existence of diagram trajectories and for consecutive
Wasserstein distance as velocity (pp. 2--3).

The proposed operational pipeline is as follows. First choose the temporal windows and a fixed
construction \(W_t\mapsto X_t\); then compute diagrams in the homological dimensions of interest
(pp. 3--4). Choose a diagram metric \(d\), for example a Wasserstein or bottleneck distance, and
define local scalar speed
\[
  \nu_t=\frac{d(D_t,D_{t+1})}{t_{t+1}-t_t}.
\]
Define cumulative path length and endpoint displacement by
\[
  L=\sum_{t=0}^{T-1}d(D_t,D_{t+1}),\qquad R=d(D_0,D_T),
\]
and trajectory efficiency by \(\eta=R/L\) when \(L>0\), with the intended range
\(0\leq\eta\leq1\) (p. 4). A first scalar acceleration is proposed as

\[
  a_t^{\mathrm{speed}}=\frac{\nu_t-\nu_{t-1}}{\Delta t}.
\]

For a three-point directional surrogate, set
\[
 a=d(D_{t-1},D_t),\quad b=d(D_t,D_{t+1}),\quad c=d(D_{t-1},D_{t+1}),
\]
and use
\[
 \cos\theta_t=\frac{a^2+b^2-c^2}{2ab}.
\]
The email proposes interpreting this as whether the trajectory continues in roughly the same
direction or bends sharply, while acknowledging that persistence-diagram space is not a vector space
and that a Wasserstein/geodesic/tangent-cone treatment may be needed (pp. 4--5). Finally, local
instability descriptors should distinguish stable evolution, rapid transitions, sustained directional
change, oscillatory/reversible restructuring, and sudden shocks; stability under diagram perturbations
should be proved; synthetic cases should be used before real temporal data (pp. 5--6).

The email gives one valid elementary stability calculation. If
\(d(D_t,\widetilde D_t)\leq\varepsilon_t\), then
\[
 |d(D_t,D_{t+1})-d(\widetilde D_t,\widetilde D_{t+1})|
 \leq\varepsilon_t+\varepsilon_{t+1},
\]
and hence the finite-difference speed error is at most
\((\varepsilon_t+\varepsilon_{t+1})/(t_{t+1}-t_t)\) (p. 5).

## Mapping of the supplied literature

`morozov-vineyards-socg06.pdf` is Cohen-Steiner, Edelsbrunner, and Morozov, “Vines and Vineyards
by Updating Persistence in Linear Time” (SCG 2006). It defines and computes vines for one-parameter
families, tracks individual persistence points, and discusses stability. It directly predates the
proposed path viewpoint; it does not supply the proposed speed/acceleration/turning package.

`1-s2.0-S0167278916000270-am.pdf` is Kramár et al., “Analysis of Kolmogorov Flow and Rayleigh--Bénard
Convection using Persistent Homology,” Physica D 334 (2016), 82--98, DOI 10.1016/j.physd.2016.02.003.
The abstract and introduction state that persistence diagrams are computed along flow time series,
metrics compare diagrams, and a second persistent-homology analysis is applied to the time series of
diagrams. This is a direct precedent for temporal diagram paths and distance-based rates, although it
does not present the proposed general kinematics.

`2010.05780v2.pdf` is Xian, Adams, Topaz, and Ziegelmeier, “Capturing Dynamics of Time-Varying Data
via Topology” (arXiv:2010.05780). It surveys vineyards, crocker plots, multiparameter rank functions,
and introduces crocker stacks with continuity. It is a broad dynamic-TDA framework and a relevant
baseline for summaries, not a vector-like calculus for diagram paths.

`2108.02727v2.pdf` is Giusti and Lee, “Signatures, Lipschitz-Free Spaces, and Paths of Persistence
Diagrams” (arXiv:2108.02727). Its abstract explicitly regards diagram paths, embeds diagrams into a
Lipschitz-free Banach space, studies bounded-variation paths, and uses path signatures. This is the
closest mathematical precedent for adding linear/path-space structure, and it makes a claim of a
new path space itself untenable. It may provide a route for a carefully defined directional or
acceleration surrogate, but a Banach embedding does not automatically give a canonical inner-product
angle or physical acceleration.

`2512.14615v2.pdf` is Khormali, “Hierarchical Persistence Velocity for Network Anomaly Detection:
Theory and Applications to Cryptocurrency Markets” (arXiv:2512.14615). The email characterizes it as
a velocity-based descriptor measuring rates at which persistent features appear or disappear. It is
evidence that the word “velocity” and rate-based topological descriptors already occur in applied TDA;
its object and application differ from a complete metric-path kinematics.

`2606.19542v1.pdf` is Malhotra et al., “Tracking Representation Dynamics in Large Language Models
with Persistent Homology” (arXiv:2606.19542). The email reports consecutive Wasserstein distances
between diagrams at training checkpoints and an interpretation as topological activity/velocity.
Thus the scalar consecutive-distance quantity cannot be claimed as new by itself.

`2607.05695v1.pdf` is Bernal-Alvarado, Delepine, and Pinedo Guadarrama, “Structural Divergence of the
Roman--Byzantine Trade Network, 0--1453 CE: Persistent Homology, Topological Velocity, and Criticality
Indicators of Imperial Collapse” (arXiv:2607.05695). The email quotes an explicit scalar definition
\(W(t)=W_2(D_t,D_{t+\Delta t})/\Delta t\), another direct precedent for consecutive Wasserstein
velocity.

Primary-source checks performed on 7 September 2026 found the Kramár record and DOI at ScienceDirect,
the Xian and Giusti--Lee records at arXiv, and an author/repository record for the SCG paper. The local
PDFs provide the full text needed for the claims above. The two 2026 applied papers are treated as
supplied manuscripts in this preliminary audit; their identity and exact theorem-level support should
be checked separately before publication claims.

## Preflight findings

The broad idea is coherent as an exploratory research direction, but the email does not yet specify a
complete mathematical model. The correct preliminary verdict is `INDETERMINATE for the full
domain-independent kinematics`, with a sound restricted component consisting of fixed diagram space,
fixed metric, and scalar metric-path observables. The email itself recognizes that direction and
acceleration need additional geometric thought; the audit therefore treats these as design gaps and
interpretation limits, not as false claims.

**TK-1 | material definition gap / method-target mismatch.** The window map \(W_t\mapsto X_t\),
filtration, coefficient field, homological degree, diagram class, metric, and timestamp convention are
left as “appropriate” or examples. The distance \(d(D_t,D_{t+1})\) is only meaningful after these are
frozen. Overlapping windows make adjacent diagrams statistically dependent, and changing window size,
delay, or filtration scale changes the path. A domain-independent theorem cannot be stated until the
observation map and all tuning parameters are part of the model.

**TK-2 | material geometry/design gap.** A metric space supplies distances and metric derivatives,
but no canonical subtraction \(D_{t+1}-D_t\), velocity vector, or ambient acceleration vector. The
scalar \(a_t^{\mathrm{speed}}\) is a valid change-in-speed diagnostic as defined, but it does not
encode directional acceleration or constant-speed turning. The three-point law-of-cosines expression
is a valid comparison angle of the metric triangle. It need not represent an ambient direction in an
arbitrary metric, and geodesics or optimal matchings in persistence-diagram space may be nonunique.

**TK-3 | convention and domain caveat, not a false claim.** For a straight Euclidean path
\(D_{t-1}=(0,0),D_t=(1,0),D_{t+1}=(2,0)\), the proposed formula gives \(a=b=1,c=2\) and
\(\theta=\pi\). This is the ordinary interior angle of the metric triangle, so it is mathematically
valid. If the intended “turning” convention assigns zero to a straight path, the reported quantity
must be \(\tau=\pi-\theta\) or the convention must be stated explicitly. When \(a=0\) or \(b=0\),
the denominator \(2ab\) vanishes, so the statistic requires a stationary-step convention.

**TK-4 | counterexample-supported stability limitation.** In a persistence-diagram subspace, take
singleton diagrams \(D_s=\{(s,s+M)\}\) with fixed \(M>0\), so bottleneck distance is \(|s-s'|\)
for shifts smaller than \(M/2\). Keeping \(s_{t-1}=0,s_t=1\), compare
\(s_{t+1}=1+\epsilon\) with \(\widetilde s_{t+1}=1-\epsilon\). Their diagram perturbation is
\(2\epsilon\), while the comparison angle tends from \(\pi\) to 0 as \(\epsilon\to0\), because the
second step tends to zero. The script reports, at \(\epsilon=10^{-8}\), perturbation
\(1.9999999989\times10^{-8}\) and angle jump \(3.1414872865\). Thus the witness rules out uniform
continuity on a class in which adjacent step lengths are allowed to vanish. If \(a,b\geq\delta>0\)
and side lengths are bounded, the cosine expression is locally Lipschitz, while the angle is uniformly
Hölder-\(1/2\) because \(\arccos\) is Hölder-\(1/2\) on \([-1,1]\). An interior arccos margin, for
example \(|\cos\theta|\leq1-\rho\), is sufficient for a Lipschitz angle bound. These are sufficient
regularity conditions, not a claim that an interior margin is necessary in every persistence-diagram
model.

**TK-5 | valid but scale-sensitive stability.** The email’s speed inequality follows directly from
the reverse triangle inequality and is correct for a fixed metric and fixed timestamps. It amplifies
diagram error by \(1/\Delta t\); finite differences of speed add another time-step factor. Path-length
and endpoint bounds are direct, while efficiency-ratio bounds require \(L\) bounded away from zero.
A persistence-stability theorem can propagate raw-data perturbations only after the filtration and norm
assumptions are fixed. Window overlap, data noise, and metric choice must be included in the error model.

**TK-6 | interpretation limit, not a defect in descriptive TDA.** Persistence diagrams are generally
noninjective summaries of the underlying temporal data. Two latent trajectories can therefore have the
same diagram path and different latent dynamics. This is acceptable if the scientific estimand is the
diagram-path descriptor, and it becomes a limitation only if the paper claims recovery of latent events
or dynamics. Any statement that descriptors “identify transitions” must define an event label or ground
truth and compare against baselines.

**TK-7 | time-scale ambiguity.** Path length and endpoint displacement are unchanged by relabeling the
timestamps of the same sampled diagram sequence, but they are not generally invariant under resampling
the same continuous curve. The speed and speed-change statistic depend on the clock. The theory must
distinguish physical time, sample index, and window-center time, and state whether clock invariance or
physical-rate interpretation is intended.

## Reproducible finite checks

The saved script uses singleton persistence diagrams \(D_s=\{(s,s+M)\}\) with \(M=10\). For the
shifts used in the check, matching the off-diagonal points is optimal under bottleneck distance, so
the diagram subspace is isometric to a line. The two paths with birth coordinates

\[
 A=(0,1,2,1,0),\qquad B=(0,1,0,-1,0)
\]

both have consecutive bottleneck distances \((1,1,1,1)\), path length \(L=4\), endpoint displacement
zero, and identical scalar speeds. Their comparison-angle sequences are respectively
\((\pi,0,\pi)\) and \((0,\pi,0)\). Thus endpoint displacement, path length, and scalar speed do not
determine the intermediate history, while a comparison statistic can expose a difference. This is a
finite witness about information content, not a proof that a proposed statistic has scientific utility.

The same script checks one perturbed path against the elementary bounds. With perturbations
\((0.001,-0.002,0.0005,-0.001,0.002)\) and \(\Delta t=0.25\), the four observed speed errors are
\((0.012,0.010,0.006,0.012)\), equal to or below the corresponding triangle-inequality bounds.
The path-length error is (0.002), below its bound (0.010), and the endpoint error is (0.001), below
its bound (0.003). These are finite numerical checks only, not general proofs.

## Sound restricted component and minimal repair choices

The portion that can be developed without silently changing the idea is a discrete metric-path theory.
Freeze a diagram space \((\mathcal D_k,d)\), fixed filtration and coefficients, a fixed window/embedding
map, and timestamps. Then local speed, total variation \(L\), endpoint displacement \(R\), and
\(\eta=R/L\) are well-defined diagnostics. The triangle inequality proves \(R\le L\); perturbations
\(d(D_t,\widetilde D_t)\le\varepsilon_t\) give

\[
 |\widetilde R-R|\le\varepsilon_0+\varepsilon_T,\qquad
 |\widetilde L-L|\le\sum_{t=0}^{T-1}(\varepsilon_t+\varepsilon_{t+1}),
\]

and the displayed speed bound. If \(L\ge L_{\min}>0\), the efficiency ratio has a corresponding
local perturbation bound. These are direct metric results; they do not need a vector velocity.

There are two honest routes for directional quantities. One route labels the law-of-cosines statistic
as a comparison angle/excess and proves the appropriate Hölder or Lipschitz stability under explicit
step-length and angle regularity conditions,
with no claim that it is an intrinsic direction. The other adds an explicit structure, for example a
chosen Lipschitz-free/Banach embedding or a selected Wasserstein geodesic/matching, and defines
direction and acceleration in that structure. The latter is a material refinement that requires the
co-author’s scientific choice; it should not be silently assumed.

## Go/no-go recommendation to parent agent

Proceed with a narrower, independently defensible paper component on stable metric-path diagnostics
(\nu,L,R,\eta), metric-error propagation, sampling/window sensitivity, and synthetic falsification.
Treat “canonical domain-independent turning/acceleration” as an open design problem. Before planning
that component, require the assumption ledger to freeze the data-to-diagram map, metric, time scale,
diagram class, and whether claims concern the observed diagram path or the latent system. The supplied
literature makes the path viewpoint and scalar distance velocity established background; novelty must
come from the stability theory, principled finite-sample/window analysis, or a genuinely new directional
construction plus validated downstream utility.
