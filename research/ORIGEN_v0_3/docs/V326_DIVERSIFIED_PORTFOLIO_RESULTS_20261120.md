# V326 — resultados de diversificación de cartera (2026-11-20)

## Reproducibilidad
- Workflow: https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44842684515 (success).
- Artifact: 14681587578; ZIP SHA-256 `c1df469c2c98e71f56841903ff0e2b98413f9bb5e9451cb1deb232efa4ab3f37`.
- Head: `9fbb4d7f8333e34a1dceabe97e6c4bdb88451a53`.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`; 10,887 rows; 7,723 structurally assigned Classic draws; 800 warmup; 6,923 prequential targets.
- Four model variants use the same fixed PMF (V322 expanding, V324 rolling 400/800/1600). V326 selects 30 candidates from a top-100 score pool by greedy maximum new unordered-pair coverage. PCG64 seed 3262026. Portfolio is selected before target overlap is evaluated.
- Isolated tests: 271 passed. Full CI: 473 passed, 2 skipped, 28 subtests passed.

## Results

| Portfolio | Exact 3/5 lines | Exact 4/5 lines | Exact 5/5 lines | Targets with ≥3/5 | Unique numbers | Unique pairs |
|---|---:|---:|---:|---:|---:|---:|
| Uniform expectation | 5,346.52 | 243.02 | 2.113 | 3,757.43 | 27.923 | 208.909 |
| V326 expanding | 5,347 | 235 | **4** | 3,718 | 27.580 | 197.778 |
| V326 rolling 400 | 5,245 | 244 | 1 | 2,582 | 21.626 | 125.231 |
| V326 rolling 800 | 5,147 | 239 | 1 | 2,941 | 24.840 | 151.565 |
| V326 rolling 1600 | 5,290 | 249 | 3 | 3,331 | 26.830 | 175.128 |

Expanding portfolio improved diversity relative to V322's earlier mean of 25.913 unique numbers and 130.314 unique pairs, reaching 27.580 and 197.778. It nevertheless remained less diverse than a uniform random 30-line portfolio. Its mean pairwise overlap was 0.969 versus 0.893 for random portfolios.

The expanding portfolio produced four exact 5/5 hits:
- 5295 (2016-01-06): 02-11-13-17-26
- 5501 (2016-07-30): 02-03-05-07-23
- 8782 (2021-12-14): 09-14-19-20-23
- 9304 (2022-09-01): 03-05-09-13-27

The uniform reference expects 2.113 exact 5/5 lines over 6,923 draws. A Poisson approximation gives (P(X\ge4)=0.164); four hits are not significant evidence of an edge. Exact 4/5 count (235) is below uniform expectation (243.02), and targets with at least one 3/5 (3,718) are below expectation (3,757). Therefore the four 5/5 hits do not indicate broad portfolio improvement.

Rolling 400/800/1600 all underperform the expanding variant in ≥3/5 target coverage. Rolling 400 is particularly concentrated. No rolling model is selected.

## Interpretation and decision
- V326 demonstrates that a fixed pair-coverage selection rule can increase the diversity of the V322 expanding portfolio without changing the PMF.
- It does not demonstrate predictive edge: exact 5/5 count is statistically compatible with chance; 4/5 and target-level coverage do not improve; all results are retrospective prequential reconstruction, not independently authenticated pre-close forecasts.
- The rule was designed after observing V325 results on the same historical stream. This is exploratory/post-hoc and not an independent confirmation. Do not report the 4/5 count as validation.
- Do not continue tuning top-pool size, greedy objective, or seed against this same historical sample. Freeze V326 as a completed exploratory ablation. The next valid test is prospective, pre-registered, with portfolios and score snapshots committed before the draw close, independently timestamped and custodied.
- V294 remains frozen. No write to main, no canonical append, no promotion. Production remains `RESEARCH_ONLY_NO_EDGE`.
