# Foundations for the Topological Kinematics audit

This note records the source-grounded findings from the four supplied papers and the co-author's email. It is a foundations review, rather than the full research plan. Page numbers below refer to the printed page numbers in the supplied PDFs, with section and equation numbers included so that the claims remain checkable.

## Executive assessment

The proposal contains a viable research question, but its basic trajectory and scalar speed are already established. The co-author's own email correctly identifies this boundary. In particular, Kramár et al. explicitly define

\[
s_\star(t_i)=\frac{d_\star(\operatorname{PD}(f_i),\operatorname{PD}(f_{i+1}))}{\Delta t}
\tag{Kramár et al., Eq. (16)}
\]

and interpret it as an average speed in persistence-diagram space (Section 6, printed pp. 9--11). Giusti and Lee develop paths of persistence diagrams, an isometric Banach-space embedding, bounded-variation paths, and path signatures (Sections 4--6, printed pp. 9--19). Xian et al. define time-varying persistence modules and crocker stacks, and prove a continuity statement for the stack (Sections 4, 6, and 7, printed pp. 10--12 and 25--32). Cohen-Steiner, Edelsbrunner, and Morozov define vineyards, in which individual persistence points are tracked through a parameterized family (Sections 3--4, printed pp. 3--7).

The potential contribution is a rigorously delimited, domain-independent diagnostic study of diagram-valued paths that does all of the following: (i) distinguishes metric speed from a genuine metric derivative and states the needed regularity; (ii) treats cumulative length and endpoint displacement with sampling and noise bounds; (iii) characterizes a directional or turning observable as a comparison-angle or other explicitly chosen surrogate, with a fallback set-valued definition when optimal matchings are nonunique; (iv) studies rate-of-change-of-speed and any stronger acceleration notion only under a specified lift or tangent object; and (v) tests whether these quantities add predictive or scientific information beyond consecutive diagram distances and standard summaries. Whether this is a new contribution or an incremental synthesis must be decided by the simulation and application gates.

The direction, acceleration, and identification parts are unresolved design questions, and they contain the material mathematical risk. In a general persistence-diagram metric space there is no subtraction \(D_{t+h}-D_t\), no canonical orientation of a geodesic, and often no unique optimal matching. A scalar finite difference of distances is a valid rate-of-change-of-speed diagnostic, but it is not automatically a full acceleration. Different data-generating systems can also have the same persistence-diagram path, even when their physical dynamics differ. Any identification claim must be restricted to the chosen diagram-valued representation and its equivalence classes.

## Source map and precise relevance

| Source | Exact results relevant to the proposal | What it establishes, and what it leaves open |
|---|---|---|
| Cohen-Steiner, Edelsbrunner, Morozov (2006), *Vines and vineyards by updating persistence in linear time*, Sections 2--4, printed pp. 2--7, especially the Stability Theorem on p. 3 and the vineyard construction on pp. 6--7 | A tame function has a persistence diagram; \(d_B(D_p(f),D_p(g))\leq\|f-g\|_\infty\) for continuous tame functions on a triangulable space (Stability Theorem, p. 3). Under a homotopy \(f_t\), off-diagonal points trace vines; births/deaths on the diagonal create open, half-open, or closed vines, and pairing changes occur at knees (Section 4, pp. 6--7). | Evolving persistence information and point tracking are established. The algorithm maintains a reduced-matrix pairing in worst-case \(O(n)\) per simplex-order transposition (Introduction, pp. 1--2; Section 3, pp. 3--5). The paper does not give a metric calculus of the entire diagram-valued path, and it does not make a canonical second derivative in diagram space. Vines can be ambiguous at knees and are more detailed than the proposed untracked diagram path. |
| Kramár et al. (2016), *Analysis of Kolmogorov Flow and Rayleigh--Bénard Convection using Persistent Homology*, Sections 3--7 and 8--10, printed pp. 4--17 | They map each scalar-field snapshot to persistence diagrams, compare diagrams with bottleneck and \(p\)-Wasserstein metrics (Definition 5.1, printed p. 7), use stability \(d_B(\operatorname{PD}(f),\operatorname{PD}(g))\leq\sup_x|f(x)-g(x)|\) (Eq. (10), p. 8), and define the average speed in diagram space by Eq. (16), printed p. 10. They apply a second persistence computation to the point cloud of diagrams using \(f(x)=d(x,X)\) (Eq. (7), p. 5; Section 7, pp. 11--15). | This is the closest direct precedent for scalar topological speed, path geometry, recurrent trajectories, and symmetry quotienting. The authors explicitly show that the speed profile and its derivative depend on the metric: bottleneck emphasizes the largest change while \(W_1,W_2\) aggregate all changes (Section 6, pp. 9--11). The RPO becomes a closed loop after a continuous symmetry is quotiented by persistence invariance (Section 9, pp. 15--16). Their Theorem 7.3 gives a sampling guarantee: if \(Y\) is a \(\delta\)-dense subsample of a metric point cloud \(X\), then \(d_B(\operatorname{PD}(X,d),\operatorname{PD}(Y,d))<\delta\) (printed p. 14). They do not define direction, turning, acceleration, or a domain-independent descriptor family. |
| Xian, Adams, Topaz, Ziegelmeier (2021 version supplied; arXiv v2), *Capturing Dynamics of Time-Varying Data via Topology*, Sections 3--4 and 6--8, printed pp. 6--12 and 25--35 | A time-varying metric space is a map \(t\mapsto X_t\) continuous in Gromov--Hausdorff distance (Section 4.1, printed p. 10). A crocker stack is \(f_V(t,\epsilon,\alpha)=\operatorname{rank}(V_t(\epsilon-\alpha)\to V_t(\epsilon+\alpha))\) (Definition 4.1, printed p. 11). Persistent homology gives \(d_B(\operatorname{PH}(\operatorname{VR}(X)),\operatorname{PH}(\operatorname{VR}(Y)))\leq 2d_{GH}(X,Y)\) (Section 6.3, printed p. 26). Their Lemma 7.3 extends this to an \(L^p\) time-integrated bound, and Theorem 7.5 gives the crocker-stack erosion inequalities under \(d^\infty_{GH}(X,Y)\leq\delta/2\) (printed pp. 31--32). | The paper provides the right continuity/stability vocabulary for dynamic summaries and warns that ordinary crocker plots can change by an arbitrarily large amount under an arbitrarily small Gromov--Hausdorff perturbation (Example 2, printed p. 30). It also states that crocker-stack continuity is not continuity in the Euclidean norm used for vectorized machine-learning inputs (p. 32). It does not supply a kinematic derivative or acceleration of the entire diagram path. |
| Giusti and Lee (2023 version supplied; arXiv v2), *Signatures, Lipschitz-free spaces, and paths of persistence diagrams*, Sections 3--7, printed pp. 7--25 | For ordinary diagrams, the metric pair is \((\Omega,d,\Delta)\), where \(\Omega=\{(b,d):b\leq d\}\), \(d\) is Euclidean distance, and \(\Delta\) is the diagonal (Eq. (3.1), printed p. 7). The quotient \((\widetilde\Omega,\widetilde d,*)\) collapses the diagonal, and the Lipschitz-free space is completed under the partial **1-Wasserstein** norm (Definitions 4.1--4.2, printed pp. 9--10). Theorem 4.2 gives an isometric embedding of finite diagrams for this 1-Wasserstein/quotient metric, not an isometry for arbitrary \(W_p\) or bottleneck distance. Bounded-variation paths are defined in that Banach space (Definition 5.1, p. 12). The signature is defined by iterated integrals (Definition 5.2, p. 13); its kernel is tree-like equivalence (Theorem 5.1, p. 14); the normalized signature is injective, universal, and characteristic on the quotient path space (Theorems 5.3--5.4, p. 15). Persistence moments are injective and Lipschitz on bounded persistence measures (Propositions 6.1--6.2 and Theorem 6.1, printed pp. 16--17), with factorial truncation control (Lemma 6.1, p. 17). The composition of a truncated signature with the moment map is Lipschitz on paths of bounded variation (Theorem 6.2, p. 18). | This is the strongest existing analytic framework for paths of persistence diagrams and a possible foundation for a restricted kinematics project. The isometric Banach lift is only for the specified partial-\(W_1\) geometry, and an isometric embedding alone does not provide a computable or canonical derivative: vector-valued differentiability of a lifted path requires additional regularity (and, in general, a Radon--Nikodym/differentiability property of the target Banach space). The Lipschitz-free space has no explicit finite-dimensional representation (Section 4, printed p. 11; Section 5.3, p. 15). The practical moment/signature feature is stable and injective for static bounded diagrams, and path-signature methods are reparameterization invariant. That invariance is useful for shape-of-path analysis but removes timing information needed for speed and acceleration unless time or a parameterization is retained as an additional coordinate. The paper does not define acceleration, turning, or a physical identification theorem. |

## Cohen-Steiner, Edelsbrunner, and Morozov: vineyards

The paper begins from stability of persistence diagrams and treats a continuous change of a function as a homotopy. Its Stability Theorem states that, for a triangulable space and continuous tame functions, the bottleneck distance between the dimension-
\(p\) diagrams is bounded by the uniform function error (printed p. 3). The computational contribution is persistence-pair maintenance: after a simplex transposition, the reduced matrix and the auxiliary change-of-basis structure can be updated in worst-case linear time in the number of simplices. The algorithmic details are Sections 3 and 4, printed pp. 3--6.

The vineyard is a 1-parameter family of diagrams drawn in \(\overline{\mathbb R}^2\times[0,1]\). Each off-diagonal point traces a vine. Vines may start or end on the diagonal, or connect off-diagonal points at the endpoints. Under a smooth homotopy, the traces are smooth except where pairings change, and these events occur at knees in pairs (Section 4, printed pp. 6--7). The application to a protein-folding trajectory uses a pairwise-distance scalar function on a fixed triangulation and tracks the dimension 0 and 1 vineyards over 201 frames (printed pp. 7--8). The authors emphasize that vines provide an unambiguous beginning and end for individual features, but their discussion is feature tracking, not a coordinate-free velocity or acceleration of the multiset-valued diagram.

This distinction matters for Topological Kinematics. If the proposed object is merely a sequence \(D_t\) of diagrams and no class matching is assumed, it is not a vineyard. That is a real advantage for data where classes cannot be tracked, but it also removes the pointwise correspondence from which a vector velocity could be formed. If the proposed method adds optimal matching between adjacent diagrams, it must explain how it differs from vines and how it handles ties, diagonal matches, and knees.

## Kramár et al.: direct precedent for diagram speed and recurrent geometry

Kramár et al. use scalar snapshots from Kolmogorov flow and Rayleigh--Bénard convection. In Section 3 (printed pp. 4--6), each snapshot is converted to persistence diagrams, and the sequence of diagrams is viewed as a point cloud in the metric space \(\mathrm{Per}\). They define the distance-to-cloud function

\[
f(x)=d(x,X)=\min_{x_i\in X}d(x,x_i),
\tag{7}
\]

and apply persistent homology a second time to this scalar function. This is an important precedent for using the geometry of diagram-valued data itself, rather than only analyzing each diagram independently.

Definition 5.1 (printed p. 7) defines the bottleneck distance and the degree-\(p\) Wasserstein distances by optimizing bijections between persistence points, including diagonal copies. Equation (10) on printed p. 8 gives the standard stability bound in the scalar-function setting. The same page notes invariance under homeomorphisms of the domain, \(\operatorname{PD}(f\circ g)=\operatorname{PD}(f)\), which is why translations and other symmetries can collapse in diagram space. The authors explicitly caution that their piecewise-constant numerical approximations do not necessarily preserve exact symmetry; with an \(L^\infty\) error bound \(\epsilon\), Eq. (11) gives a bottleneck error bound of \(2\epsilon\) between symmetry-related approximations.

Section 6 (printed pp. 8--11) is the most direct source for the proposal. Kramár et al. state in Eq. (16), printed p. 10,

\[
s_\star(t_i)=\frac{d_\star(\operatorname{PD}(f_i),\operatorname{PD}(f_{i+1}))}{\Delta t},
\qquad \star\in\{B,W^1,W^2\},
\]

and call this an average speed in persistence-diagram space. They explain that bottleneck speed measures the largest feature change, whereas Wasserstein speeds aggregate changes across all features, with \(W_2\) tending to suppress small fluctuations relative to \(W_1\). Their numerical examples show that the derivatives of these three scalar speeds can have different signs at the same time (printed pp. 10--11). This is an empirical warning against treating “the” topological acceleration as metric independent.

The same section shows why path length and endpoint displacement are useful but insufficient. Distance matrices reveal recurrence and periodicity, but a periodic speed profile does not prove that the trajectory is a closed curve. In the Rayleigh--Bénard example, coarse sampling creates gaps that can generate a spurious loop in the second persistence calculation; the authors require much faster sampling before interpreting the loop as a dynamical structure (Sections 7.2--7.3, printed pp. 13--17). Theorem 7.3 and Remark 7.4 give a way to control the loss from a dense subsample, but this theorem concerns the persistence diagram of a point cloud in a metric space, not the consistency of finite-difference acceleration.

In Section 8 (printed pp. 14--15), seven symmetry classes of equilibria are recovered by clustering persistence diagrams in bottleneck distance and cross-checked with Fourier amplitudes. In Section 9 (printed pp. 15--16), a stable relative periodic orbit with continuous drift becomes a closed loop in \(\mathrm{Per}\), because persistence is invariant under that symmetry. In Section 10 (printed pp. 16--18), under-sampling an almost-periodic Rayleigh--Bénard orbit creates disconnected pieces and artificial loops; a high-rate sample followed by a \(\delta\)-dense, \(\delta\)-sparse subsample recovers a dominant loop with the error region predicted by Theorem 7.3. These examples support a sampling-validation phase before any higher-order descriptor is interpreted.

## Xian et al.: dynamic summaries and continuity limits

Xian et al. define a continuous time-varying metric space as a map from time into compact metric spaces, continuous in Gromov--Hausdorff distance (Section 4.1, printed p. 10). Applying persistent homology at each time yields a time-varying persistence module; stability gives continuity of that module when the metric-space path is continuous. Their crocker plot records a rank or Betti number at each time and scale. An \(\alpha\)-smoothed crocker plot records the rank of the map from scale \(\epsilon-\alpha\) to \(\epsilon+\alpha\), and the crocker stack records this for all \(\alpha\geq0\) (Definition 4.1, printed p. 11).

The paper is especially relevant for stability. Example 2 (printed p. 30) has two dynamic metric spaces whose Gromov--Hausdorff distance is arbitrarily small, while their Betti numbers at a selected scale differ by an amount that grows with the number of points. Thus an unsmoothed Betti or crocker plot is not stable in the ordinary matrix norm. Lemma 7.3 (printed p. 31) gives

\[
d_b^p(\operatorname{PH}(\mathrm{VR}(X)),\operatorname{PH}(\mathrm{VR}(Y)))
\leq 2d_{GH}^p(X,Y)
\]

for the time-integrated bottleneck distances, including the supremum version. Lemma 7.4 (printed p. 32) gives the erosion inequalities for the rank functions when the time-uniform bottleneck distance is at most \(\delta\), and Theorem 7.5 transfers these inequalities to crocker stacks under \(d^\infty_{GH}(X,Y)\leq\delta/2\). The authors explicitly state that this is not continuity in the Euclidean norm used to vectorize stacks (printed p. 32).

For Topological Kinematics, the lesson is that “stability” must specify both the input perturbation and the output topology. A bound on each \(D_t\) does yield a first-order bound on a metric speed, but it does not automatically yield a useful bound on a second finite difference. If the descriptor uses \(h=t_{i+1}-t_i\), pointwise diagram errors of size \(\varepsilon_i\) produce a speed error of order \((\varepsilon_i+\varepsilon_{i+1})/h\), and a speed finite-difference error of order \((\varepsilon_{i-1}+2\varepsilon_i+\varepsilon_{i+1})/h^2\). This scaling should be stated and tested rather than hidden inside a “stable acceleration” claim.

## Giusti and Lee: the strongest path-space foundation

Giusti and Lee address exactly the problem of treating persistence diagrams as points on a path, but their objective is stable and characteristic representation for learning, not kinematic descriptors. For ordinary diagrams they use the metric pair \((\Omega,d,\Delta)\) with Euclidean ground metric, collapse the diagonal to a basepoint, and complete the free vector space under the partial 1-Wasserstein norm (Sections 3--4, printed pp. 7--11). Theorem 4.2 gives the isometric inclusion of finite diagrams into the corresponding Lipschitz-free Banach space. This is valuable for the partial-\(W_1\) geometry, but it does not give an isometry for arbitrary \(W_p\) or bottleneck distance, nor does it by itself give a computable or differentiable lifted path. Metric speed exists for suitable absolutely continuous metric paths; a Banach-valued derivative of the lift requires additional regularity and differentiability assumptions on the target space.

They define \(p\)-variation and bounded-variation paths in the resulting Banach space (Definition 5.1 and Proposition 5.1, printed p. 12). The path signature is an iterated integral of the Banach-valued path (Definition 5.2, p. 13). Theorem 5.1 (p. 14) identifies the kernel of the signature as tree-like equivalence. The normalized signature is an injective, universal, and characteristic feature map on the quotient path space (Theorems 5.3--5.4, p. 15). Thus there is already a very strong theory for path-level temporal information.

The crucial practical limitation is also explicit. The Lipschitz-free space is infinite dimensional and has no useful explicit basis in the general persistence-diagram setting (Section 4, printed p. 11; Section 5.3, p. 15). Giusti and Lee therefore introduce persistence moments. The moment map excludes pure-birth moments because they are not Lipschitz under partial Wasserstein distance (Example 6.1, printed p. 16), and Theorem 6.1 (p. 17) proves that the retained moment map is Lipschitz and injective for bounded persistence measures. Lemma 6.1 (p. 17) bounds truncation error, and Theorem 6.2 (p. 18) gives Lipschitz continuity of the truncated path signature composed with moments on paths with a fixed variation bound. The discrete signature construction is Definition 6.2 and the resulting feature map is described in Section 6.3 (printed p. 19).

Their application (Sections 7.1--7.5, printed pp. 21--24) estimates parameters of the 3D D'Orsogna swarm model from paths of diagrams. They use 500 simulations, 200 time points, Vietoris--Rips homology through dimension 2, and signatures truncated at level 3. Signature methods generally outperform crocker plots, and moments are competitive with higher-dimensional static vectorizations. The heterogeneous train/test experiments require normalization because agent subsampling makes diagrams sparser and shifts birth coordinates (Section 7.4, printed p. 23). This is directly relevant to overlapping-window and variable-sample-size data: raw diagram distances can reflect sampling design instead of system evolution.

Theorem 5.3 and Corollary 6.1 are not acceleration theorems. Signatures are invariant under nondecreasing reparameterizations, as noted after Definition 5.2 (printed p. 13). That is beneficial for comparing unparameterized path shape, but it deliberately discards timing. A kinematics paper must either keep the time parameter, augment the path with time, or separate shape descriptors from speed-sensitive descriptors.

## Nearest-prior-art boundary

The four supplied papers imply the following novelty map.

1. “Persistence diagrams vary in time” is established by vineyards, time-varying metric spaces, Kramár et al.'s fluid examples, and Giusti--Lee's path-space formalism.

2. “Consecutive diagram distance divided by the time step is topological velocity/speed” is already present as Kramár et al.'s Eq. (16), and the email itself points to newer application-specific uses. It cannot be the principal novelty claim.

3. “A stable path representation for learning” is already developed through crocker-stack continuity and signatures/moments. A new vectorization by itself would likely be incremental.

4. A coherent kinematics may contain a new layer if it formalizes which observables are intrinsic to a discrete metric path, which depend on a lift or matching, and which are only proxies, then demonstrates a useful distinction that incumbent summaries miss. The minimum convincing package is a metric-error and sampling analysis plus an empirical test of incremental information. A direction or turning construction and a stronger acceleration construction are optional dormant branches, not assumed contributions. Generic formulas for speed, path length, endpoint displacement, and efficiency are valid and potentially useful, but they are routine metric diagnostics and contain no extra information beyond the full distance sequence unless a specific task shows parsimony, interpretability, or predictive value.

5. The most promising differentiation is a theorem-plus-falsification paper. The theorem should state assumptions under which the descriptors are well-defined and stable; the experiments should construct paths with equal speed but different turns, equal endpoints but different intermediate histories, repeated/returning paths, and synthetic perturbations that expose matching and sampling failures. The empirical application should then show incremental information beyond Eq. (16), signatures, persistence landscapes/images, and ordinary domain-specific summaries.

## Mathematical warnings for the proposed descriptors

### Speed

For a curve \(D:[0,T]\to(\mathcal D,d)\), the intrinsic metric speed is the metric derivative

\[
|D'|(t)=\lim_{h\to0}\frac{d(D_{t+h},D_t)}{|h|},
\]

when the limit exists. The adjacent-distance quantity in the email is a finite-interval average and is already Kramár et al.'s Eq. (16). A research theorem should state whether it studies the metric derivative, an upper metric derivative, or a discrete estimator. The distinction matters for irregular data and for windows whose diagram path is only piecewise continuous.

### Length and net displacement

For any metric \(d\), the discrete length \(L_h=\sum_i d(D_{t_i},D_{t_{i+1}})\) and displacement \(R=d(D_0,D_T)\) are valid. The efficiency ratio \(R/L_h\) lies in \([0,1]\) by the triangle inequality when \(L_h>0\). It is a useful descriptive statistic, but it is inflated by diagram noise and depends on time discretization. A continuum result should use metric length and prove convergence of \(L_h\) under an absolute-continuity or bounded-variation assumption. Kramár et al.'s sampling theorem can support a separate finite-sample error analysis for the persistence diagram of a metric point cloud, but it is not a general raw-data-to-diagram sampling theorem for this pipeline.

### Direction and turning

The proposed comparison angle

\[
\cos\theta_t=\frac{a^2+b^2-c^2}{2ab},
\quad a=d(D_{t-1},D_t),\;b=d(D_t,D_{t+1}),\;c=d(D_{t-1},D_{t+1}),
\]

is a legitimate comparison-angle statistic when \(a,b>0\), but it is not automatically the angle between tangent vectors. In a general metric space there may be no tangent cone, no geodesic joining the diagrams, and many optimal matchings. The angle is also numerically ill-conditioned when \(a\) or \(b\) is near the noise floor. It has no orientation in a general metric space, so it distinguishes approximate continuation from reversal only as a scalar triangle-shape proxy. The paper should call it a comparison angle, define its degenerate cases, and prove a stability bound away from \(a,b=0\). A stronger notion of turning requires a restricted geometry, for example a Banach lift, a chosen optimal-transport interpolation, or a tangent-cone construction.

### Acceleration

The email's scalar quantity \((v_t-v_{t-1})/\Delta t\) is a rate of change of metric speed. It does not detect a constant-speed change of direction and therefore is not a full acceleration. If the intended object is acceleration in a lifted Banach space, Giusti--Lee's isometric Lipschitz-free embedding gives a principled starting point, but the lift is analytically defined and not directly computable. If the intended object is acceleration in a Wasserstein geometry, one must specify a tangent object, a connection, or a chosen optimal coupling; these are not canonical for arbitrary persistence diagrams, especially when features can be matched to the diagonal or when optimal matchings are nonunique.

Finite differences amplify error. If \(d(D_i,\widetilde D_i)\leq\varepsilon_i\), then by the triangle inequality

\[
|\widetilde v_i-v_i|\leq\frac{\varepsilon_i+\varepsilon_{i+1}}{h},
\qquad
|\widetilde a_i-a_i|
\leq\frac{\varepsilon_{i-1}+2\varepsilon_i+\varepsilon_{i+1}}{h^2},
\]

for uniform step \(h\). Thus a bound that is harmless for diagrams can be unusable for acceleration as \(h\) decreases. Smoothing, local polynomial estimation, confidence bands, or a continuum regularity assumption are required before claiming a stable second-order descriptor.

### Windowing and parameterization

The proposed pipeline computes \(D_t\) from consecutive or overlapping windows. Overlap makes neighboring diagrams share observations, which can mechanically reduce their distance and induce serial dependence. Window width, stride, embedding lag, point-cloud sampling, and filtration scale all affect the path. If time-delay embedding is used inside a window, the resulting diagram changes both because the underlying process changes and because the window shifts through the signal. The paper should treat window width and stride as estimand-defining design parameters, report sensitivity to them, and distinguish physical time from filtration scale.

### Identification

Persistent homology is stable but not injective on the original data-generating state. Domain symmetries are intentionally quotiented out, as Kramár et al. exploit for translations and relative periodic orbits. More generally, many nonisometric point clouds or scalar fields can share a persistence diagram, and multiple physical paths can induce the same diagram path. Giusti--Lee's injectivity results concern the diagram or persistence-measure object, and their normalized signature is injective only on a tree-like-equivalence quotient of bounded-variation paths. They do not identify the original physical trajectory. Accordingly, “detects a transition” must mean “detects a transition in the selected diagram-valued representation,” and any claim about a physical mechanism needs an external validation target.

## Verified source links

The links below are primary or publisher records for the supplied sources.

1. Cohen-Steiner, Edelsbrunner, Morozov, *Vines and vineyards by updating persistence in linear time*, SCG 2006, DOI [10.1145/1137856.1137877](https://doi.org/10.1145/1137856.1137877), publisher record [ACM Digital Library](https://doi.org/10.1145/1137856.1137877).

2. Kramár et al., *Analysis of Kolmogorov flow and Rayleigh--Bénard convection using persistent homology*, Physica D 334 (2016), 82--98, DOI [10.1016/j.physd.2016.02.003](https://doi.org/10.1016/j.physd.2016.02.003), [ScienceDirect record](https://www.sciencedirect.com/science/article/pii/S0167278916000270). The supplied manuscript is also indexed at [arXiv:1505.06168](https://arxiv.org/abs/1505.06168).

3. Xian, Adams, Topaz, Ziegelmeier, *Capturing Dynamics of Time-Varying Data via Topology*, supplied as [arXiv:2010.05780](https://arxiv.org/abs/2010.05780). The supplied PDF is the v2 manuscript dated 28 June 2021; its front matter retains a placeholder journal DOI, so the arXiv record is the verified primary link for this version.

4. Giusti and Lee, *Signatures, Lipschitz-free spaces, and paths of persistence diagrams*, supplied as [arXiv:2108.02727](https://arxiv.org/abs/2108.02727). The supplied PDF is v2 dated 16 November 2023; no journal DOI is given in the PDF, so the arXiv record is the verified primary link for the supplied version.

5. The proposal itself is in [email.pdf](../email.pdf), especially pp. 1--6. The email explicitly proposes speed, acceleration, turning, path length, net displacement, trajectory efficiency, and local instability, and explicitly acknowledges that trajectories and consecutive Wasserstein distance are not themselves new.

## Research-plan gates implied by these foundations

Before an application is attempted, the project should pass four mathematical gates. First, construct exact synthetic diagram paths, including paths with births/deaths at the diagonal, nonunique matchings, constant speed with changing direction, and equal endpoints with different histories. Second, define the admissible path class and prove convergence of discrete speed and length to metric derivatives and metric length. Third, choose one primary direction for higher-order structure: a comparison-angle proxy with explicit conditioning bounds, or a restricted Banach/transport lift with a genuine second derivative. Fourth, quantify perturbation and windowing errors, and benchmark against Kramár's Eq. (16), signatures, crocker stacks, persistence landscapes/images, and application-specific baselines.

If these gates pass, the idea supports a coherent paper centered on the geometry and limits of diagram-valued kinematics. If the direction and acceleration gates fail, the strongest publishable subset is still a stability-aware framework for metric speed, length/displacement, recurrence, and path-shape descriptors, with the failure of intrinsic acceleration proved as a substantive negative result.
