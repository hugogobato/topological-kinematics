# Topological Kinematics Literature Reading List

This list is a compact reading order for the proposed diagnostic study. The four foundational supplied papers were read in full for the foundations memo, and the three supplied recent preprints were checked for direct overlap. Page numbers below refer to the supplied versions unless otherwise stated.

## Required primary sources

1. **Kramár et al. (2016), “Analysis of Kolmogorov Flow and Rayleigh–Bénard Convection using Persistent Homology.”** DOI: [10.1016/j.physd.2016.02.003](https://doi.org/10.1016/j.physd.2016.02.003). Read Definition 5.1 p. 7, stability Eq. (10) p. 8, speed Eq. (16) p. 10, and Section 6 pp. 9–11. This is the nearest direct precedent for inter-frame persistence-diagram speed and speed changes. Sections 8–10 pp. 14–18 show the intended dynamical use and sampling concerns.

2. **Cohen-Steiner, Edelsbrunner, and Morozov (2006), “Vines and vineyards by updating persistence in linear time.”** DOI: [10.1145/1137856.1137877](https://doi.org/10.1145/1137856.1137877). Read the stability theorem on printed p. 3, Sections 3–4 pp. 3–7, and the protein-folding application pp. 7–8. This establishes parameterized diagram trajectories and tracking, so it bounds any trajectory-level novelty claim.

3. **Chad Giusti and Darrick Lee (2021), “Signatures, Lipschitz-free spaces, and paths of persistence diagrams.”** [arXiv:2108.02727](https://arxiv.org/abs/2108.02727). Read Eq. (3.1) p. 7, the quotient construction pp. 9–10, Definition 4.2 and Theorem 4.2 pp. 10–11, signatures and tree-like equivalence Sections 5 pp. 12–15, and moments/truncation/application Sections 6 pp. 16–25. The exact theorem scope is partial 1-Wasserstein on the quotient diagram space. Signatures are reparameterization invariant unless time is added.

4. **Lu Xian, Henry Adams, Chad M. Topaz, and Lori Ziegelmeier (2021), “Capturing Dynamics of Time-Varying Data via Topology.”** DOI: [10.3934/fods.2021033](https://doi.org/10.3934/fods.2021033); [arXiv:2010.05780](https://arxiv.org/abs/2010.05780). Read dynamic metric spaces Section 4.1 p. 10, crocker-stack Definition 4.1 p. 11, metric stability Section 6.3 p. 26, and Lemmas 7.3–7.4 plus Theorem 7.5 pp. 31–32. Example 2 p. 30 is a warning about visual instability.

5. **Omid Khormali (2025), “Hierarchical Persistence Velocity for Network Anomaly Detection: Theory and Applications to Cryptocurrency Markets.”** [arXiv:2512.14615](https://arxiv.org/abs/2512.14615). Read Sections 3.2–3.4 pp. 4–7, the source-reported stability theorem pp. 8–14, and the Ethereum experiment pp. 15–18. This is a different filtration-scale birth/death velocity for each diagram, but it is relevant nearest prior art for rate-based topological indicators.

6. **Naman Malhotra, Jay Ambadkar, Abhinav Gupta, Kushal Kasivel, Abbas Schwarz, Kamillo Ferry, and Anthea Monod (2026), “Tracking Representation Dynamics in Large Language Models with Persistent Homology.”** [arXiv:2606.19542](https://arxiv.org/abs/2606.19542). Read the consecutive-checkpoint activity definition pp. 3–4, empirical comparisons pp. 5–7 and 11, and implementation details p. 13. Treat this as a recent preprint application precedent.

7. **José de Jesús Bernal-Alvarado, David Delepine, and Carlos Pinedo Guadarrama (2026), “Structural Divergence of the Roman–Byzantine Trade Network, 0–1453 CE: Persistent Homology, Topological Velocity, and Criticality Indicators of Imperial Collapse.”** [arXiv:2607.05695](https://arxiv.org/abs/2607.05695). Read definitions and composite indicator Eqs. (11)–(15) p. 10, results pp. 15 and 21–22, and limitations p. 26. Treat the explicit inter-decade W₂ velocity as a direct recent collision, not as settled peer-reviewed theory.

## Proposal and internal audit

8. **email.pdf.** Read the six-page scan with the OCR/images in the audit workspace. Extract the exact proposed quantities, the author’s acknowledgement that trajectory and consecutive Wasserstein speed are established, and the request for synthetic tests before applications. Do not use the email as a novelty source.

9. **foundations.md.** Page-level source map, metric-scope warnings, derivative/identification caveats, and verified DOI/URL list. Use it before drafting any literature sentence.

10. **dynamic_prior_art.md.** Neighbor map for supplied recent preprints and adjacent persistence-dynamics methods. Treat recent preprints as evidence of overlap or possible comparator, not as settled priority without checking the primary version.

11. **email_proposal_audit.md and topological_kinematics_witness.py.** Audit of definitions and executable finite-metric witnesses. Use for G0 edge cases: zero steps, equal-speed paths with different order, triangle bounds, and near-zero angle instability.

## Baselines to implement before G3

The minimum comparison set is the complete pairwise distance-matrix recurrence, consecutive speed history, raw-data features where available, persistence-diagram moments, and a path signature with and without an explicit time channel. Use the same trajectory splits and tuning budget for every representation. The distance-matrix and signature baselines are essential because L, R, η, and local triangle summaries contain no information beyond the observed distance matrix.

## Reading policy

Read the exact theorem and equation before paraphrasing it. Record metric, domain, assumptions, and page locator in the citation ledger. A source that establishes stability does not automatically establish differentiability, acceleration, causal identification, or physical direction.
