# Changelog

## 0.3.0
- Added chronological and expanding-window evaluation splits.
- Added paired prequential log-score summaries and exact sign testing.
- Applied Holm-Bonferroni to the complete declared family, including ORIGEN's internal sign test.
- Added adversarial-null empirical benchmarking.
- Added frame diversity diagnostics.
- Added SHA-256 manifests and tamper verification.
- Added MetaObserver search-path audit for preregistration ordering and post-outcome adaptation.
- Added CLI interfaces, examples, and 28 unit tests.
- Kept research-only classification; no automatic prediction, promotion, or repository mutation.

## 0.3.1 research hardening (2026-11-19)
- Added pre-close custody record verification with exact schema, candidate-specification hash binding, independent generator/custodian identities, strict UTC ordering, and hash-linked ledger verification.
- Added adversarial tests for altered bytes, record mutation, duplicate targets, deleted/reordered ledger entries, invalid timestamps, and exclusive file creation.
- Implemented the preregistered V316 identity-resolved temporal persistence omnibus: 8,140 statistics across 20 lags, all 28 number identities, all 378 pair identities, and aggregate overlap.
- V316 uses packed-bit pair counts with an independent nested-loop reference oracle; frozen source digest, Classic sample count/boundaries, PCG64 seed 3162026, and 1,999 null simulations are enforced.
- Added an isolated GitHub Actions workflow for the V316 confirmatory historical falsification run. Its output remains research-only and cannot establish prospective predictive edge.
- No change to V294, canonical history, or main; PR remains draft and unmerged.

- Completed frozen V316: 7,723 Classic draws, 8,140-cell maximum family, 1,999 simulations, seed 3162026; observed max |z|=3.70796 vs null 95th percentile 5.85308, Monte Carlo p=0.9995. No rejection and no predictive edge. Report: docs/V316_IDENTITY_PERSISTENCE_RESULT_20261119.md.
