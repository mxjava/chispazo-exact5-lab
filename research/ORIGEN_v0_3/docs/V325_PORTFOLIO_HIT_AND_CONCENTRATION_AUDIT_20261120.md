# V325 — Top-30 portfolio hit and concentration audit

## Reproducibility

- Replay: [GitHub Actions run 44841835566](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44841835566), success.
- Artifact: `14680519319`; ZIP SHA-256 `f17cd97ca799919bf7c7225c015830d316a6a89975e6db483514ae999c7129cb`.
- Source history SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- 7,723 structurally assigned Classic draws; 800 warmup; 6,923 scored targets (2163–12248); 30 unique combinations per target.
- Candidate portfolios are generated before target overlap is inspected. Ties at the top-30 boundary are resolved uniformly without replacement with PCG64 seed 3252026.

## Hit counts

| Portfolio | Exact 3/5 lines | Exact 4/5 lines | Exact 5/5 lines | At least 4/5 lines |
|---|---:|---:|---:|---:|
| Uniform expectation | 5,346.52 | 243.02 | 2.113 | 245.14 |
| V322 expanding | 5,384 | 242 | 3 | 245 |
| V324 rolling 400 | 5,129 | 224 | 0 | 224 |
| V324 rolling 800 | 5,134 | 243 | 1 | 244 |
| V324 rolling 1600 | 5,345 | 220 | 3 | 223 |

V322 expanding and rolling 1600 each found three exact 5/5 matches in the retrospective top-30 stream. Under the uniform 30-line reference, the expectation is 2.113 exact 5/5 hits over 6,923 targets; a Poisson approximation gives (P(X\ge3)\approx0.354). This is not statistically persuasive and does not establish predictive edge.

### Retrospective 5/5 locations

- V322 expanding: contest 5501 (2016-07-30), `02-03-05-07-23`, portfolio position 5; contest 8782 (2021-12-14), `09-14-19-20-23`, position 20; contest 9304 (2022-09-01), `03-05-09-13-27`, position 25 in a rank tie spanning 25–29.
- V324 rolling 800: contest 11364 (2025-06-27), `03-06-09-14-19`, position 25.
- V324 rolling 1600: contest 3022 (2009-10-16), `07-08-18-26-28`, position 27; contest 5295 (2016-01-06), `02-11-13-17-26`, position 28; contest 5808 (2017-06-02), `02-11-16-19-23`, position 14.
- V324 rolling 400: no exact 5/5 portfolio hit.

## Root-cause diagnostic: candidate concentration

The top-30 portfolios are much more correlated than random portfolios. Exact uniform reference expectations for a random 30-line portfolio are 27.923 unique numbers, 208.909 unique unordered pairs, and mean pairwise line overlap 0.8929.

| Portfolio | Unique numbers (mean) | Unique pairs (mean) | Mean pairwise overlap |
|---|---:|---:|---:|
| Uniform random expectation | 27.923 | 208.909 | 0.893 |
| V322 expanding | 25.913 | 130.314 | 1.300 |
| V324 rolling 400 | 17.094 | 74.742 | 2.182 |
| V324 rolling 800 | 19.609 | 86.742 | 1.963 |
| V324 rolling 1600 | 22.749 | 101.459 | 1.760 |

This explains an important weakness: the model portfolios produce a similar or slightly higher total number of 3/5 hits in some variants, but those hits are concentrated in fewer target draws. The rolling-400 portfolio is especially concentrated. The top-30 score ranking is not a sufficiently diverse coverage strategy.

## Decision and next test

V325 does not support a 5/5 predictive claim. The small difference between three observed 5/5 hits and 2.113 uniform-expected hits is compatible with chance; 4/5 totals are essentially at the uniform expectation. These are retrospective prequential results, not authenticated pre-close forecasts.

V326 is a separately labeled exploratory test: keep each model PMF unchanged, take its fixed top-100 candidate pool, then greedily select 30 candidates maximizing new pair coverage (ties by PMF rank). Measure whether this reduces concentration and improves hit counts. The pool size and greedy rule are fixed before that replay; do not retune them based on V326 results.

V294 remains frozen. No canonical append, no write to `main`, no promotion. Production remains `RESEARCH_ONLY_NO_EDGE`.
