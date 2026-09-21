# Reproducibility status of the incumbent baselines (WP-1.1)

Agent A3, 2026-09-20. Companion artifact: `citation_ledger.yaml` (36 claims: 33 verified, 3 corrected, 0 unverifiable). Primary-source page checks used the local PDFs; implementation availability was checked against author pages, arXiv, and GitHub on 2026-09-20. Per WP-1.1, an inaccessible repository is not treated as evidence that no implementation exists.

## Bottom line

Every incumbent needed by the pilot has a usable reproduction path, but the amount of author code varies. Vineyards and Giusti-Lee have author-associated public code; Xian et al. have a partial replication repository; Kramar et al. have only the general-purpose PH engine (Perseus) plus an unpublished-looking analysis pipeline. The 2026 preprints (Malhotra et al. and Bernal-Alvarado et al.) were checked as supplementary incumbents. No baseline is fully blocked. The pilot's own baselines should be labeled as transparent reimplementations where author code is missing, which WP-1.1 already permits.

## What can be reproduced from public code

Vineyards: Dionysus 2, maintained by paper coauthor Dmitriy Morozov, implements vineyard updates under adjacent transpositions and linear homotopies (https://github.com/mrzv/dionysus and https://mrzv.org/software/dionysus2/tutorial/vineyards.html, accessed 2026-09-20). The paper itself is DOI 10.1145/1137856.1137877. A third-party PyPI package `vineyards` v1.0.x (https://pypi.org/project/vineyards/) also implements the 2006 kernel plus a kinetic point-set extension; it is not author-maintained and should be verified independently if used. The frozen pilot environment does not include Dionysus, and the implementation contract forbids new third-party dependencies, so vineyards tracking is documented availability only, not a pilot dependency.

Giusti and Lee: the paper's code is public at https://github.com/ldarrick/paths-of-persistence-diagrams with Julia code and Python notebooks for Sections 7.5-7.6 (experiments, heterogeneous splits, KME analysis, timing), accessed 2026-09-20. The published record is SIAM J. Appl. Algebra Geom. 7(4), 828-866, DOI 10.1137/22M1528471; the supplied arXiv v2 is arXiv:2108.02727v2.

Malhotra et al. (supplementary incumbent): the full pipeline is public at https://github.com/malhotranaman/tracking-representation-dynamics-with-persistent-homology, including a pure analysis package, configs, tests, metrics, and figures, accessed 2026-09-20. The paper is arXiv:2606.19542v1.

## What requires transparent reimplementation

Kramar et al. (status partial): the paper states that persistent homology was computed with Perseus, which is public at https://people.maths.ox.ac.uk/nanda/perseus/ (accessed 2026-09-20; DOI 10.1016/j.physd.2016.02.003 for the paper). No repository for the paper-specific consecutive-distance, speed-profile, or second-PH pipeline and no public copy of the flow simulation data were located on the author publication page (https://math.ou.edu/~mkramar/publications.html), the arXiv record (https://arxiv.org/abs/1505.06168), or via search on 2026-09-20. The pilot's Kramar-style baseline should therefore be a transparent reimplementation of Eq. (16) on printed p. 10 using the frozen environment's gudhi 3.12.0 and persim 0.3.8 primitives, smoke tested against analytically known bottleneck or Wasserstein values.

Xian et al. (status partial): the replication repository is public at https://github.com/lxiancode/tda-crocker with Vicsek simulation code (MATLAB) and crocker plot and stack functions (R), accessed 2026-09-20. The README refers to analysis scripts (`crocker-plot-analysis.R`, `crocker-stack-analysis.R`, `op-analaysis.R`) and a bottleneck-distance step that are not present in the repository listing, so end-to-end replication needs gap-filling. The plan does not require the Vicsek experiments; the crocker-stack comparator can be reimplemented directly from Definition 4.1 on printed p. 11 (rank of the map V_t(epsilon - alpha) -> V_t(epsilon + alpha)), with an analytic smoke test on the interval example on printed p. 29, where the rank of V(4) -> V(8) equals 2 for intervals [1,7], [2,9], [3,11], [5,10], [5,9].

Giusti-Lee signature baseline: the author repository covers the Section 7 experiments rather than a packaged library. If the WP-1.2 signature comparator is taken from Giusti-Lee style moments plus discrete signatures, reimplement or vendor the discrete kernel at the frozen feature level, and keep time augmentation explicit, because the signature is reparameterization invariant (noted after Definition 5.2 on printed p. 13).

## What is unavailable

No code or data location was found for Khormali (arXiv:2512.14615) or Bernal-Alvarado et al. (arXiv:2607.05695) on 2026-09-20; both are application-specific and neither is required as a pilot baseline. These are not-found results only. The image-only `email.pdf` has no text layer, but its attribution was verified by page rendering, so it is not a blocker.

## Smoke-test obligations before G1

WP-1.1 requires each baseline to have a smoke test and requires unavailable baselines to be reimplemented transparently or marked. The minimum set consistent with the frozen environment is: 1. a Kramar-style speed test on a two-frame sequence with an analytically known diagram distance, plus the G0 equal-speed witness; 2. a crocker-stack rank test on the printed p. 29 interval example; 3. a time-augmented signature or moment comparator test on a synthetic path with a known signature; 4. a documentation-level test that the full-distance-matrix recurrence baseline reproduces the G0 finite-metric witnesses. Vineyard vine tracking is marked as external and documented, not smoke tested in the pilot, because Dionysus is outside the frozen dependency set. Xian's Vicsek data and Kramar's flow data are not needed for the synthetic pilot and are marked unavailable.

## Consequence for the G1 decision

The prior-art verification pass criterion is met: every novelty-sensitive statement checked resolves to the exact equation, definition, or theorem on the cited page or to a corrected locator, and every citation resolves to a DOI or primary URL. The intended contribution can be stated without claiming existing results (Kramar Eq. (16) on printed p. 10 and Bernal Eqs. (11)-(12) on printed p. 10 already define diagram speed, and Malhotra Eq. (2) on printed p. 4 defines checkpoint activity without time normalization). No baseline forces an INDETERMINATE status on availability grounds, so G1 remains CONDITIONAL GO from this work package, subject to the smoke tests in the previous section passing and to WP-1.2 freezing the comparison protocol. The material caveat is attribution: because the Kramar-specific and Xian-specific pipelines are not fully released, any pilot comparison involving them must be reported as a transparent reimplementation of the published definition, never as a reproduction of the authors' code.

## Corrections inherited by the plan

Four locator or citation corrections should be folded into the plan or audit text: 1. Giusti-Lee Section 6 spans printed pp. 15-19, not pp. 16-20 (the moment and truncation results are on pp. 16-18); 2. the Giusti-Lee citation should use the 2023 SIAM record (DOI 10.1137/22M1528471) or the supplied November 2023 arXiv v2, not only the 2021 posting; 3. Khormali Theorem 4.5 is stated on printed p. 12 with proof on pp. 12-14, not across pp. 8-14; 4. foundations.md places Giusti-Lee Theorems 5.3-5.4 on printed p. 15, but their displayed statements are on printed p. 14, while p. 15 contains Remark 5.2 and the start of Section 6. All substantive claims, including Kramar Eq. (16) on printed p. 10 and Bernal Eqs. (11)-(15) on printed p. 10, verified as stated.
