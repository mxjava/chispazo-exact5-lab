# V323 maxT multiplicity audit — 2026-11-20

## Scope
Independent re-analysis of the authentic GitHub Actions artifact from workflow run 44616113802, artifact 14573549829, head commit f4ac48aa94e8b67c0311758ae21a0aa8e1449839. The ZIP SHA-256 is bf91b34039b05e77d7e0519b03493f3d3dc6a3e705a500961f3e13db032f082b. The expert-score CSV SHA-256 is f41c379f737886e1d01df7100b4cd6094aa8adec4428c2447f639b538ecd12b9.

The analysis independently rebuilt all 10 V323 candidates from the 28-expert per-contest score matrix and applied a joint circular moving-block bootstrap (block length 30, 5,000 resamples, seed 20261120). Candidate-wise centered bootstrap distributions were used for a single-step maxT one-sided family-wise error adjustment across the static candidate and all nine rolling candidates. A max-absolute-t critical value provides simultaneous 95% intervals.

## Results

| Candidate | Mean log-lift | maxT adjusted one-sided p | Simultaneous 95% CI |
|---|---:|---:|---:|
| Static full Bayes | -0.000330346 | 0.99960 | [-0.000864158, +0.000203465] |
| Rolling W100, eta=.25 | -0.013307579 | 1.00000 | [-0.017554243, -0.009060915] |
| Rolling W100, eta=.5 | -0.010726251 | 1.00000 | [-0.014616418, -0.006836084] |
| Rolling W100, eta=1 | -0.009987280 | 1.00000 | [-0.013774842, -0.006199718] |
| Rolling W250, eta=.25 | -0.005789271 | 1.00000 | [-0.008486599, -0.003091943] |
| Rolling W250, eta=.5 | -0.003115591 | 1.00000 | [-0.005124556, -0.001106627] |
| Rolling W250, eta=1 | -0.002497986 | 1.00000 | [-0.004324146, -0.000671825] |
| Rolling W500, eta=.25 | -0.001243223 | 1.00000 | [-0.002398919, -0.000087528] |
| Rolling W500, eta=.5 | -0.000591219 | 1.00000 | [-0.001308690, +0.000126251] |
| Rolling W500, eta=1 | -0.000422392 | 1.00000 | [-0.000972675, +0.000127890] |

Targets: 10,087 (2163–12249); experts: 28. Max-absolute-t 95% critical value: 2.46082234.

## Interpretation
1. No candidate has positive mean log-lift.
2. No candidate provides evidence of positive lift after family-wise multiplicity adjustment; adjusted one-sided p-values are approximately 1.
3. The W100 grid and W250 grid are significantly harmful in the simultaneous intervals; W500 is near-uniform but not better than uniform.
4. Static full Bayes is statistically indistinguishable from zero in this simultaneous interval, consistent with the source report's posterior collapse to the uniform expert.
5. This is a diagnostic on the canonical sequence, not a certified Chispazo Clásico-only result: row-level official modality remains unresolved.
6. The candidate family does not include V294. This audit neither changes nor tests the frozen V294 incumbent.
7. The bootstrap is not an anytime-valid e-process and cannot satisfy the prospective promotion gate.

## Decision
`V323 = RESEARCH_ONLY_NO_EDGE`. Reject the tested adaptive forgetting policies as improvements. Do not tune V294 from this result. The useful engineering conclusion is negative but actionable: short-memory adaptive expert mixtures amplify historical noise and degrade log score; the 500-row variants retreat toward uniform rather than discovering an edge.

## Reproduction
1. Download artifact 14573549829 from workflow run 44616113802.
2. Verify ZIP SHA-256 above.
3. Extract `v264_replay/v264_expert_log_likelihoods.csv`.
4. Verify its SHA-256 above.
5. Run `python scripts/audit_v323_maxT.py --scores <CSV> --out <JSON> --resamples 5000 --seed 20261120`.

The generated JSON is `reports/V323_MAXT_MULTIPLICITY_AUDIT_20261120.json`.
