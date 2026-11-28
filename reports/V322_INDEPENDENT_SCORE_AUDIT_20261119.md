# V322 independent score-file audit — 2026-11-19

## Scope and provenance

Independent read-only audit of the V322 score CSV downloaded from GitHub Actions artifact `14558553834` (workflow run `44581344357`, source commit `d629ebabefc144da037ec8d67270c4ed68cfc6d2`). No model parameters, historical rows, or predictions were changed.

- Schema: `EXACT5_V322_HIERARCHICAL_PARTITION_V1`
- Classification in source report: `RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE`
- Historical source SHA256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`
- Score CSV SHA256 declared by source report: `8f816e8c1635c8fcdf13e070e30972faba3a90890a8b4637050da91a324bf26a`
- 6,923 scored targets; contest range 2163–12248; dates 2007-06-10 through 2026-09-12.
- Universe: 98,280 combinations.

## Independent structural checks

All 6,923 rows were unique by contest. There were no missing values in the 15 exported columns. Rank intervals were within [1, 98,280], target probabilities were in (0,1], and the exported log-lift agreed with `log(target_probability / (1/98280))` to maximum absolute error `4.24e-16`.

This validates internal arithmetic/shape consistency of the exported CSV, not the official modality assignment or source draw records. The V322 source report itself says modality is structurally assigned and awaits row-level official verification.

## Prequential results

| Metric | Observed |
|---|---:|
| Mean log-lift vs uniform | -0.0054277528 |
| Median log-lift | -0.0047881124 |
| Cumulative log-lift | -37.57633286 |
| Positive log-lift fraction | 47.5228% |
| Exact winner at rank 1 | 0 |
| Median winner rank (midpoint of tie interval) | 49,896.5 |
| Mean tie size | 33.88 |
| Median tie size | 21 |

A circular moving-block bootstrap of the per-target log-lift series (block length 30, 10,000 resamples, fixed seed 20261119) gave a percentile 95% interval for mean log-lift of **[-0.007553, -0.003347]**. No resample had a nonnegative mean. This is a dependence-aware sensitivity analysis, not a substitute for a prospective randomized test; block length and circular boundary are modeling choices.

## Top-k tie-aware inclusion totals

The CSV records fractional inclusion probabilities for winners in tie intervals. Their sums are compared with the uniform expected number of inclusions across 6,923 targets.

| k | Sum of tie-aware inclusions | Uniform expectation |
|---:|---:|---:|
| 1 | 0 | 0.0704 |
| 5 | 1 | 0.3522 |
| 10 | 1 | 0.7044 |
| 30 | 3 | 2.1132 |
| 100 | 7 | 7.0442 |

These totals do not establish edge. In particular, Top-100 is effectively identical to the uniform expectation; the small Top-5/10/30 excesses are sparse events and must be interpreted with multiplicity and uncertainty in mind.

## Decision

1. Retain `RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE`; do not promote V322.
2. Do not retune partition trees, alpha, V294, or portfolio constraints on this retrospective result.
3. Keep modality/provenance verification separate from ranking performance.
4. Require a frozen, prospective, pre-registered evaluation and a multiplicity-controlled comparison against uniform/random baselines before any edge claim.

**Bottom line:** the independent export audit passed its structural and arithmetic checks. Predictive evidence is not positive; the average log score is below uniform, and the block-bootstrap sensitivity interval is entirely negative. No 5/5 predictive capability is demonstrated.
