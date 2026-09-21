# Dynamic prior art for the Topological Kinematics proposal

## Scope and verdict

This memo audits the supplied source papers against the six-page email proposal, with page and equation references to the local PDFs. The email proposes a sequence of diagrams \(D_0,\ldots,D_T\) generated from temporal windows, interpreted as a path in a metric space, and a package of speed, acceleration, turning, path length, endpoint displacement, efficiency, and instability descriptors (email, pp. 1, 3--6).

Statements attributed to a paper are source claims and should be checked against the cited page before publication. Statements in the synthesis sections are audit conclusions or elementary deductions from the displayed definitions, not claims made by the cited authors.

The prior-art result largely confirms the email’s own caution. Persistence-diagram trajectories, metric distances between successive diagrams, and dynamic path representations are established. The scalar local speed in the email is also already present in the 2016 flow paper, in explicit form (d(D_t,D_{t+1})/\Delta t), and the two supplied 2026 papers independently call consecutive Wasserstein distances topological velocity. Path length is already the 1-variation of a diagram path in the 2023 path-signature paper. Therefore, none of the following can carry novelty by itself: treating \((D_t)\) as a trajectory, dividing consecutive diagram distance by elapsed time, summing consecutive distances, or embedding diagram paths into a path-space representation.

The strongest defensible opening is narrower: a carefully specified discrete metric-path diagnostic package, with an explicit data-to-diagram map, clock convention, metric, perturbation and sampling theory, and a falsification study against existing path signatures, vineyards, crocker stacks, entropy, and consecutive-distance baselines. No canonical, domain-independent direction, acceleration, or turning calculus is established by the supplied sources or defined in the email. The email’s comparison-angle proposal is a metric-triangle statistic, not an intrinsic tangent vector, and it is singular when either adjacent step vanishes. The formula also gives (\theta=\pi) on a straight Euclidean path if “no turn” is intended to be zero.

The online records were checked on 7 September 2026. The source records are [Cohen-Steiner, Edelsbrunner, and Morozov (2006)](https://doi.org/10.1145/1137856.1137877), [Kramár et al. (2016)](https://doi.org/10.1016/j.physd.2016.02.003), [Xian et al. (2021/2022)](https://www.aimsciences.org/article/doi/10.3934/fods.2021033), [Giusti and Lee (2021/2023)](https://arxiv.org/abs/2108.02727), [Khormali (2025)](https://arxiv.org/abs/2512.14615), [Malhotra et al. (2026)](https://arxiv.org/abs/2606.19542), and [Bernal-Alvarado, Delepine, and Pinedo Guadarrama (2026)](https://arxiv.org/abs/2607.05695). The two 2026 manuscripts should be cited as preprints, not as settled peer-reviewed results.

## Proposed objects and exact overlap targets

The email maps temporal windows (W_t) to topological objects (X_t), then computes (D_t^{(k)}) in each homological degree. For a fixed degree and a chosen metric (d), it proposes

\[
\nu_t=\frac{d(D_t,D_{t+1})}{t_{t+1}-t_t},\qquad
L=\sum_{t=0}^{T-1}d(D_t,D_{t+1}),\qquad
R=d(D_0,D_T),
\]

and efficiency (\eta=R/L) when (L>0). It then proposes a scalar speed-change quantity

\[
a_t^{\mathrm{speed}}=\frac{\nu_t-\nu_{t-1}}{\Delta t},
\]

and, for three consecutive diagrams, (a=d(D_{t-1},D_t)), (b=d(D_t,D_{t+1})), (c=d(D_{t-1},D_{t+1})), followed by

\[
\cos\theta_t=\frac{a^2+b^2-c^2}{2ab}.
\]

The email itself correctly withdraws the claims that diagram trajectories and consecutive Wasserstein velocity are new (pp. 2--3). The source audit below confirms that withdrawal and identifies the exact collision points.

## Source-by-source evidence

### Cohen-Steiner, Edelsbrunner, and Morozov, 2006: vineyards

**Source claims.** The paper defines a continuous one-parameter family of persistence diagrams and draws time-varying curves through diagram points, called vines, in the three-dimensional space of parameter, birth, and death coordinates. It gives an algorithm for updating the persistence pairing under transpositions and applies the construction to protein-folding trajectories (PDF pp. 1--2, Section 4). It also states the standard stability theorem (d_B(D_p(f),D_p(g))\leq\lVert f-g\rVert_\infty) for tame functions (PDF p. 3).

**Direct collision.** This is the earliest supplied precedent for the path-through-diagram-space viewpoint. The email’s trajectory object is therefore background. The paper is about maintaining individual feature tracks and computing the vineyard, not about a package of scalar metric kinematics. It does not define the email’s (\nu,L,R,\eta), speed acceleration, or metric-triangle turning statistic.

**Limitation relevant to the proposal.** Individual vines are not stable under small perturbations when diagram points approach and exchange. This is a warning against claiming that an optimal matching supplies a canonical identity of features or a stable vector velocity. The paper’s stable object is the diagram family, while the tracked curves can be matching-sensitive.

### Kramár et al., 2016: explicit metric speed and dynamic geometry

**Exact definitions.** For two collections of persistence diagrams, the paper defines the bottleneck distance and degree-(p) Wasserstein distance by optimal bijections, with the (L_\infty) coordinate norm (PDF p. 7, Definition 5.1):

\[
d_B(PD,PD')=\max_k\inf_{\gamma:PD_k\to PD'_k}\sup_{p\in PD_k}\lVert p-\gamma(p)\rVert_\infty,
\]

\[
d_{W_p}(PD,PD')=
\left[\max_k\inf_{\gamma:PD_k\to PD'_k}
\sum_{p\in PD_k}\lVert p-\gamma(p)\rVert_\infty^p\right]^{1/p}.
\]

They state (d_B\leq d_{W_p}) and explain that larger (p) suppresses many small changes relative to (p=1) (PDF p. 8, Section 6). For a temporal sequence of scalar fields (f_i), the paper defines the average speed in persistence-diagram space explicitly as

\[
s_\star(t_i)=\frac{d_\star(PD(f_i),PD(f_{i+1}))}{t_{i+1}-t_i},
\qquad \star\in\{B,W_1,W_2\}
\]

(PDF p. 10, Eq. (16)). This is the same mathematical object as the email’s local speed (\nu_t), up to notation and the selected metric.

**Empirical support.** The authors study Kolmogorov flow and Rayleigh--Bénard convection. For Kolmogorov flow, normalized consecutive-distance profiles under (d_B,d_{W_1},d_{W_2}) show nonuniform speed around an approximately periodic orbit, with slow regions and rapid evolution (PDF pp. 10--11, Figure 9). A (d_{W_2}) distance matrix exhibits dark diagonal bands at approximately periodic intervals, indicating recurrence in persistence-diagram space (PDF p. 11, Figure 10). For Rayleigh--Bénard convection, the distance matrix reveals that sparse sampling misses fast dynamics, and the authors explicitly caution that a speed profile alone does not establish a closed periodic orbit (PDF pp. 10--12).

**Second-level persistent homology.** They treat the temporal diagram sequence as a point cloud (X\subset\mathrm{Per}), define (f(x)=d(x,X)), and compute persistent homology of sublevel sets of this distance-to-cloud function (PDF pp. 5, 11--13, Eq. (7) and Section 7). This is a dynamic geometric analysis beyond merely plotting successive distances, but it is not the email’s proposed acceleration/turning calculus.

**Direct collision and limitations.** The email’s (\nu_t) is already an explicit published definition. Kramár et al. do not present the email’s cumulative path length or endpoint efficiency as named descriptors, and they do not define acceleration or a three-point angle. However, a claim that the local distance-over-time speed is novel is untenable. Their implementation also demonstrates the key practical limitations: metric choice changes which scales dominate, quantization creates a noise floor, and temporal under-sampling hides fast motion.

### Xian, Adams, Topaz, and Ziegelmeier, 2021/2022: dynamic TDA summaries and stability

**Exact definitions.** A time-varying metric space is a map (t\mapsto X_t) into compact metric spaces, continuous in Gromov--Hausdorff distance. A time-varying persistence module is (t\mapsto V_t), continuous in bottleneck distance. For a Vietoris--Rips construction, (V_t=PH(VR(X_t))) (PDF pp. 9--10, Section 4.1). Their crocker plot records (\operatorname{rank}V_t(\varepsilon)). Their crocker stack is

\[
f_V(t,\varepsilon,\alpha)=\operatorname{rank}\bigl(V_t(\varepsilon-\alpha)\to V_t(\varepsilon+\alpha)\bigr),
\]

with time (t), filtration scale (\varepsilon), and smoothing/persistence parameter (\alpha) (PDF p. 11, Definition 4.1).

For two time-varying metric spaces, the paper defines an integrated (p)-Gromov--Hausdorff distance

\[
d^p_{GH}(X,Y)=\left(\int_0^T d_{GH}(X_t,Y_t)^p\,dt\right)^{1/p}
\]

and an integrated (p)-bottleneck distance between the corresponding time-varying modules (PDF p. 30, Definitions 7.1--7.2). Lemma 7.3 gives

\[
d_b^p(PH(VR(X)),PH(VR(Y)))\leq 2d_{GH}^p(X,Y),
\]

and Theorem 7.5 gives the corresponding erosion-type continuity inequalities for crocker stacks (PDF pp. 30--32).

**Empirical support.** In Vicsek-model simulations, crocker plots and stacks produce more structured distance matrices and better clustering than conventional order parameters across several noise-level experiments (PDF pp. 17--21, Sections 5.2.5--5.3). This supports the value of dynamic topological summaries, but does not support a claim that the proposed kinematic descriptors are necessary or sufficient.

**Direct collision and limitations.** This paper supplies a domain-independent dynamic-TDA framework and a continuity result for a time-varying topological summary. It does not define metric speed, path length, endpoint displacement, acceleration, or turning. It explicitly distinguishes stacked diagrams from vineyards and notes that individual vines are not stable. It also warns that crocker stacks are not continuous when vectorized with an ordinary Euclidean norm (PDF p. 32). The proposal should therefore cite this work as existing dynamic background and explain why a new metric-path diagnostic adds predictive or inferential value.

### Giusti and Lee, 2021/2023: paths, variation, signatures, and stable vectorization

**Exact definitions.** Their partial (p)-Wasserstein metric matches off-diagonal points and sends unmatched points to the diagonal (PDF pp. 7--8, Eq. (3.2)). They define a path (\gamma:[0,1]\to V) in a Banach space and its (p)-variation by

\[
\lvert\gamma\rvert_{p\text{-var}}
 =\sup_{\Pi}\left(\sum_i\lVert\gamma(t_i)-\gamma(t_{i-1})\rVert^p\right)^{1/p}
\]

(PDF p. 12, Eq. (5.1)). For (p=1), this is the total variation, which is the natural continuous analogue of the email’s cumulative path length (L). They isometrically embed finite persistence diagrams into a Lipschitz-free Banach space (Theorem 4.2, PDF p. 11), define path signatures, and prove universality and characteristicness of the signature (Section 5, PDF pp. 12--15). Their persistence-moment map is stable and injective (Theorem 6.1, PDF p. 18), and the truncated signature composed with the moment map is Lipschitz on paths with bounded variation (Theorem 6.2, PDF p. 18).

**Empirical support.** In a 3D D’Orsogna swarm model, they simulate 500 trajectories, compute diagrams in dimensions 0, 1, and 2, and compare signatures of persistence moments, paths, landscapes, images, and crocker plots. Signature methods outperform crocker plots in most missing-agent and missing-time experiments; persistence moments are competitive with standard vectorizations at much lower dimension (PDF pp. 20--25, Sections 7.1--7.5). They normalize diagrams under agent subsampling because diagrams become sparser and birth coordinates shift (PDF p. 23).

**Direct collision and limitation.** Path-valued persistence diagrams and a stable, computable path representation are already explicit contributions. The email’s path-length idea is a discrete 1-variation diagnostic, so it is not novel as a mathematical operation. Giusti and Lee do not define an intrinsic acceleration or a direction in diagram space. Their Banach embedding gives subtraction only after an explicit embedding choice, and the signature is a path representation rather than a physical velocity field. This leaves room for a carefully restricted turning/acceleration construction, but not for claiming that a path-space structure itself is new.

### Khormali, 2025: a different persistence-velocity object

**Exact definitions.** Khormali’s input is a single persistence diagram (D=\{(b_i,d_i)\}_{i=1}^n), not a temporal sequence of diagrams. It defines birth and death counting measures

\[
\mu_{birth}=\sum_i\delta_{b_i},\qquad \mu_{death}=\sum_i\delta_{d_i}.
\]

For a filtration-scale subinterval (I_{j\ell}=[t_{j\ell},t_{j\ell+1})), HNAV uses

\[
V^{j,\ell}=\frac{\mu_{birth}(I_{j\ell})+\mu_{death}(I_{j\ell})}{2\Delta t_{j\ell}},
\quad
V^j=\frac1{n_{sub}}\sum_\ell V^{j,\ell},
\quad
HNAV_k=\left(\frac{V^1}{n_k},\ldots,\frac{V^m}{n_k}\right)
\]

(PDF pp. 4--5, Section 3.2). HWNAV weights each birth and death by persistence (d_i-b_i), divides by total persistence (P_k=\sum_i(d_i-b_i)), and OW-HNPV instead uses overlap weights

\[
w_{i}^{j,\ell}=\operatorname{length}([b_i,d_i)\cap[t_{j\ell},t_{j\ell+1}))
 =\max\{0,\min(d_i,t_{j\ell+1})-\max(b_i,t_{j\ell})\},
\]

\[
V^{j,\ell}=\frac1{\Delta t_{j\ell}}\sum_iw_i^{j,\ell},qquad
H_j=\frac1{P(D)}\frac1{n_{sub}}\sum_\ell V^{j,\ell}
\]

(PDF pp. 6--7, Definition 3.1). The claimed computational cost is (O(nmn_{sub})) (PDF p. 7).

The paper states Lemma 4.1 (total overlap), Lemma 4.2 (overlap perturbation), Lemma 4.3 (velocity difference), Lemma 4.4 (total-persistence perturbation), and Theorem 4.5:

\[
\lVert H_1-H_2\rVert_\infty
\leq \frac{3n_{sub}m}{(\beta-\alpha)\min\{P(D_1),P(D_2)\}} d_1^1(D_1,D_2),
\]

under positive total persistence and common filtration range (PDF pp. 8--14).

**Empirical support.** On daily Ethereum transaction graphs from May 2017 to May 2018, the method uses lower-star filtrations on the top 250 active nodes, dimensions 0, 1, and 2, and random forests with 500 trees. It compares HNAV, HWNAV, OW-HNPV, VAB, persistence landscapes, and persistence images over horizons 1--7 days, with 10-fold cross-validation repeated 10 times (PDF pp. 15--18). The reported gains are application-specific: OW-HNPV is described as stable and reaches 10.4% AUC gain at seven days, while HWNAV reaches 16.1% in the same heatmap; short horizons are often negative (PDF pp. 16--18). The arXiv record confirms the paper’s title, version date, velocity claim, and AUC headline ([arXiv record](https://arxiv.org/abs/2512.14615)).

**Direct collision and limitation.** This is not the email’s metric-path velocity. It measures feature birth/death mass across filtration scale inside each diagram, then applies the summary to temporal network snapshots. It therefore does not preempt the exact path package, but it does preempt broad claims that “topological velocity” or a rate-based descriptor is new. The claimed stability theorem is a source claim; the memo does not independently certify every proof step. The theorem’s constant grows with the number of hierarchy bins and becomes weak near (P(D)=0), so it should not be presented as a general stability theory for temporal metric paths.

### Malhotra et al., 2026: consecutive-checkpoint Wasserstein activity

**Exact definitions.** The paper computes persistent homology of activation point clouds at training checkpoints, using Euclidean Vietoris--Rips filtrations and (H_0,H_1). At each checkpoint it computes a 41-dimensional barcode summary. In the analysis framework, it computes Wasserstein distance between (H_1) barcodes at consecutive checkpoints and calls the resulting sequence topological velocity; the early-concentration statistic is

\[
C=\frac{\sum_{t\leq T/3}v_t}{\sum_tv_t}
\]

(PDF pp. 3--4, Eq. (2)). The implementation details state that diagrams are computed from 64 overlapping subsamples of 160 points, with Wasserstein order 2 used between consecutive checkpoints (PDF p. 13). The paper does not make an explicit division by elapsed checkpoint time in the displayed definition; with a fixed checkpoint schedule, the quantity is proportional to the email’s speed, but the time normalization should not be attributed to this paper without qualification.

**Empirical support.** Four models from 1B to 7B parameters, three alignment objectives, and dense early checkpoints show a rise, peak, and decay in (H_1) Wasserstein activity. The observed early concentration beats the checkpoint-order null in 11 of 12 model-objective cells (Table 1, PDF p. 11), with three-seed replication for selected models. Objective separation appears later, and topology peaks no later than a behavioral Jensen--Shannon velocity in the reported dense-window comparisons (PDF pp. 5--7 and Table 3, p. 11). The arXiv record independently confirms the paper’s title, date, and abstract claim that it tracks topology throughout fine-tuning ([arXiv record](https://arxiv.org/abs/2606.19542)).

**Direct collision and limitations.** The consecutive-diagram activity sequence is a direct recent precedent for interpreting Wasserstein changes as topological velocity. The paper does not define (L,R,\eta), acceleration, or turning. Its conclusions are conditional on model, layer, prompt set, LoRA schedule, checkpoint spacing, and overlapping subsample design. The authors correctly avoid treating overlapping subsamples as independent for confirmatory inference. This is a useful empirical template for the proposed validation protocol, not evidence of a domain-independent kinematics.

### Bernal-Alvarado, Delepine, and Pinedo Guadarrama, 2026: explicit Wasserstein velocity and composite criticality

**Exact definitions.** For consecutive decadal persistence diagrams (D_t,D_{t+10}), the paper defines

\[
W_2(t,t+10)=\inf_\gamma\left(\sum_i\lVert p_i-\gamma(p_i)\rVert^2\right)^{1/2},
\qquad
\dot W_2(t)=\frac{W_2(D_t,D_{t+10})}{10\text{ yr}}
\]

(PDF p. 10, Eqs. (11)--(12)). It also defines a same-time cross-network distance (W_{cross}(A,B,t)=W_2(D_t^A,D_t^B)), a cross-network ratio (\rho(t)), and an Integrated Criticality Threshold

\[
ICT(t)=\frac{\chi_{norm}(t)+\xi_{norm}(t)+\dot W_{2,norm}(t)}3
\]

(PDF pp. 3, 10--11, Eqs. (1), (13)--(15)).

**Empirical support.** The study reports a maximum within-series geographic velocity at 495 CE, a peak at 541 CE above the Arab-Conquest value, and a large cross-network ratio after the 1082 CE Chrysobull (PDF pp. 15, 21--22, Tables XI--XII). The arXiv record confirms the explicit inter-decade (W_2) velocity and the headline event rankings ([arXiv record](https://arxiv.org/abs/2607.05695)).

**Direct collision and limitations.** The exact scalar (W_2(D_t,D_{t+\Delta t})/\Delta t) is already published. The paper does not define an acceleration or direction in diagram space, and it explicitly warns that Roman and Byzantine velocities use different cost units and are not absolutely comparable (PDF p. 26, reference note [23]). Its ICT is a hand-built composite of normalized ingredients, so it demonstrates application-specific indicator design rather than a universal kinematics.

## Neighboring prior art found in the bounded search

The search was restricted to work directly involving time-varying persistence diagrams, diagram paths, metric tracking, or Wasserstein dynamics.

Soler et al., “Lifted Wasserstein Matcher for Fast and Robust Topology Tracking” ([arXiv:1808.05870](https://arxiv.org/abs/1808.05870)), computes optimal matchings for consecutive diagrams, constructs critical feature trajectories, detects merge/split events, and reports robustness to noise and temporal downsampling. It is feature tracking rather than a kinematic descriptor package, but it reinforces that consecutive matching and trajectory construction are established operations.

Piekenbrock and Perea, “Move schedules: fast persistence computations in coarse dynamic settings” ([Springer article](https://link.springer.com/article/10.1007/s41468-023-00156-3)), develops algorithms for computing persistence along time-varying filtrations and places vineyards in the established dynamic-computation lineage. It is computational rather than kinematic, but it reduces the novelty of a general temporal-diagram pipeline.

Bubenik and Elchesen, “Virtual persistence diagrams, signed measures, Wasserstein distances, and Banach spaces” ([arXiv:2012.10514](https://arxiv.org/abs/2012.10514)), extends diagram Wasserstein geometry to signed measures and Banach-space constructions. This is relevant if the proposed acceleration is to use subtraction or a linearized diagram representation. It does not supply the email’s acceleration or turning statistic.

Wang and Xu, “Dynamical Persistent Homology via Wasserstein Gradient Flow” ([arXiv:2412.03806](https://arxiv.org/abs/2412.03806)), studies dynamics of diagrams along Wasserstein gradient flows and maps changes back to the data space. It is a different problem from descriptive kinematics of an observed diagram path, but it is a warning against using “dynamical persistent homology” or Wasserstein motion as unclaimed novelty.

## What is and is not established

The following are source-supported facts. A one-parameter family of diagrams and feature tracks exists as vineyards. Time-varying diagram sequences can be treated as dynamic metric-space data. Consecutive bottleneck or Wasserstein distances can be interpreted as an average rate or speed after division by elapsed time. A diagram path has a total variation, and signatures can summarize it stably after a specified embedding or moment map. Applied papers already use the phrase topological velocity for filtration-scale birth/death rates and for consecutive temporal Wasserstein distances.

The following are not established by the supplied sources. There is no canonical subtraction (D_{t+1}-D_t) in the intrinsic persistence-diagram metric space. There is no canonical tangent vector, acceleration vector, or direction independent of a selected embedding, matching, geodesic, or metric. The three-point law-of-cosines quantity is only a comparison angle of a metric triangle. It does not determine an orientation, and in a general metric space a triangle does not define a unique continuation direction. The existing sources also do not prove that any of these descriptors identifies a latent physical transition in the original data-generating system.

The email’s scalar perturbation calculation is valid for a fixed metric: if (d(D_t,\widetilde D_t)\leq\varepsilon_t), then the reverse triangle inequality gives

\[
\left|d(D_t,D_{t+1})-d(\widetilde D_t,\widetilde D_{t+1})\right|
\leq\varepsilon_t+\varepsilon_{t+1},
\]

and division by (\Delta t_t) yields the corresponding speed bound. This is a generic metric fact, not by itself a novel theorem. It becomes scientifically useful only when combined with a specified data-to-diagram stability map, window-overlap error model, finite-sample analysis, and empirical discrimination from existing dynamic summaries.

## Novelty recommendation

Do not frame the contribution as “persistence diagrams move through time,” “topological velocity,” “Wasserstein speed,” or “path signatures.” Those claims collide directly with Cohen-Steiner et al., Kramár et al., Giusti and Lee, and the two 2026 supplied manuscripts.

A viable claim would be conditional and testable: for a frozen windowing map, filtration, homological degree, timestamp convention, and diagram metric, define a discrete metric-path diagnostic suite; establish finite-sample and perturbation bounds for (\nu,L,R,\eta); characterize the sampling and overlap regimes under which the diagnostics are reliable; and test whether the suite adds predictive or change-point information beyond consecutive Wasserstein distance, persistence entropy, vineyards, crocker stacks, and path-signature baselines. Direction and acceleration should be treated as separate optional work packages. The comparison-angle version should be labeled a metric-triangle excess/turning surrogate, guarded by lower bounds on adjacent step lengths and an explicit convention, unless an additional geometric structure is deliberately chosen.

The minimum decisive empirical experiment is a synthetic benchmark with known diagram paths or known ambient paths whose diagrams can be computed: constant-speed geodesic motion, accelerating motion, constant-speed turning, reversible excursions, shocks, repeated diagrams, and paths with equal endpoints but different intermediate histories. Evaluate metric choice, time resolution, window overlap, noise, subsampling, and perturbation stability. Compare the proposed descriptors to (W_p(D_t,D_{t+1})/\Delta t), cumulative 1-variation, Giusti--Lee signatures, Xian et al. crocker stacks, and Kramár et al. distance-matrix/second-PH summaries. Without a gain in a predeclared task, the extra descriptors risk being renamed versions of existing metric summaries.

## Source map for later writing

| Claim needed later | Primary source location | Use in a paper |
| --- | --- | --- |
| Diagram family and tracked features | Cohen-Steiner et al., PDF pp. 1--3, Section 4 | Establishes vineyard/path background and matching caveat |
| Bottleneck and Wasserstein metrics | Kramár et al., PDF p. 7, Definition 5.1; Giusti--Lee, PDF pp. 7--8 | Fix metric conventions and diagonal matching |
| Explicit consecutive speed | Kramár et al., PDF p. 10, Eq. (16) | Direct novelty collision for (\nu_t) |
| Dynamic summary and continuity | Xian et al., PDF pp. 9--11, Definition 4.1; pp. 30--32, Lemma 7.3 and Theorem 7.5 | Baseline dynamic TDA and stability language |
| Path variation and signatures | Giusti--Lee, PDF pp. 12, 18--19, Eqs. (5.1), Theorems 6.1--6.2 | Direct collision for path length/path representations |
| Filtration-scale velocity | Khormali, PDF pp. 4--7, Sections 3.2--3.4 | Distinguishes a different “velocity” object |
| Consecutive-checkpoint activity | Malhotra et al., PDF pp. 3--7, Eq. (2), Appendix B.3 | Recent application precedent and validation template |
| Explicit temporal (W_2) velocity | Bernal et al., PDF p. 10, Eqs. (11)--(15) | Direct collision for Wasserstein speed and composite indicators |
| Metric speed limitations in practice | Kramár et al., PDF pp. 10--12, Figures 9--10 | Supports sampling/noise/metric sensitivity tests |
