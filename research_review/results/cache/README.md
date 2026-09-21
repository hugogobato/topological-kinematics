# Experiment cache (preserved locally, not pushed)

This directory holds the reproducible raw artifacts of the Phase 3 campaign: generated trajectory
frames (`{family}/{label}/{seed}/sigma{tag}/stride{s}/trajectory/`), finite persistence diagrams
and essential counts (`diagrams.npz`, `essential.npz`, `meta.json`, `SHA256SUMS`), full pairwise
distance matrices (`runner_distances/`), and timing records. Every entry is content-hashed.

Size is about 519 MB across about 7,200 files, so the directory is kept on disk and excluded from
the git push only for transport size. It is not gitignored: every derived table, figure, memo,
manifest, and audit that the analysis uses is committed under `research_review/results/g1`,
`research_review/results/g2`, and `research_review/results/g3`, and the cache can be rebuilt
bitwise from the frozen seeds with the package commands recorded in
`research_review/results/phase1/EXECUTION_LOG.md`.
