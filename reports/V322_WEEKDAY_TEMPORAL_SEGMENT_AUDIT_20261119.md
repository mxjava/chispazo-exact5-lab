# V322 weekday and temporal segmentation audit — 2026-11-19

## Scope

Independent descriptive segmentation of the already-exported V322 prequential score file (6,923 targets, contests 2163–12248; source score SHA256 `8f816e8c1635c8fcdf13e070e30972faba3a90890a8b4637050da91a324bf26a`). This does not retrain or retune the model. V294 and canonical history remain untouched.

The score export was independently structurally audited earlier. The reproducible audit implementation added in this branch also performs a one-to-one contest join and verifies date and winning combination against canonical history before reporting segments.

## Overall result

- Targets: 6,923
- Mean log-lift: -0.00542775
- Positive log-lift fraction: 47.52%
- Cumulative log-lift: -37.57633

Negative log-lift means the model assigned less probability to realized outcomes than the uniform reference, on average.

## Weekday segmentation

The file contains 989 targets for each weekday. Intervals below were recomputed using the corrected circular moving-block bootstrap (block length 30, 3,000 resamples, fixed seed offsets). The previous non-circular/padded intervals are superseded.

| Weekday | Mean log-lift | Corrected 95% CI | Positive fraction |
|---|---:|---:|---:|
| Monday | -0.008715 | [-0.015207, -0.002514] | 47.02% |
| Tuesday | -0.006832 | [-0.011703, -0.001866] | 46.51% |
| Wednesday | -0.007714 | [-0.012310, -0.003136] | 47.02% |
| Thursday | -0.002680 | [-0.008120, +0.002542] | 49.34% |
| Friday | +0.000686 | [-0.005652, +0.007096] | 49.24% |
| Saturday | -0.005293 | [-0.010150, -0.000511] | 46.92% |
| Sunday | -0.007447 | [-0.012666, -0.002123] | 46.61% |

The Friday point estimate is positive but its interval is wide and crosses zero. Thursday also crosses zero despite a negative point estimate. Neither is evidence of a weekday edge. Five weekday intervals remain negative under the corrected bootstrap.

## Chronological stability

The 6,923 scored targets were divided into four chronological groups of near-equal size.

| Period | N | Mean log-lift | Corrected 95% CI | Positive fraction | Cumulative log-lift |
|---|---:|---:|---:|---:|---:|
| Oldest quarter | 1,731 | -0.005258 | [-0.009913, -0.000304] | 46.74% | -9.1015 |
| Second quarter | 1,731 | -0.008502 | [-0.012791, -0.003953] | 46.33% | -14.7164 |
| Third quarter | 1,731 | -0.003573 | [-0.007685, +0.000533] | 49.45% | -6.1843 |
| Newest quarter | 1,730 | -0.004378 | [-0.007718, -0.000652] | 47.57% | -7.5742 |

All four point estimates are negative. The third quarter interval crosses zero; the newest quarter remains negative. The apparent improvement in the third quarter did not persist in the newest quarter.

## Overall reference

- Targets: 6,923
- Mean log-lift: -0.00542775
- Positive log-lift fraction: 47.52%
- Cumulative log-lift: -37.57633
- Corrected circular-block 95% CI for mean: [-0.007630, -0.003326]

## Interpretation and decision

1. No weekday exhibits a robust positive segment. Friday is the only positive point estimate, but its block-bootstrap interval includes zero and the effect is tiny.
2. Monday, Tuesday, Wednesday, Saturday and Sunday show negative intervals in this exploratory analysis. This points to model misspecification or overconfident probability allocation, not a usable segment to promote.
3. The chronological groups are all negative. The newest group does not confirm a recent recovery.
4. No weekday-specific parameters are promoted. Selecting Friday after inspecting seven groups would be multiple-comparison/data-mining risk.
5. V322 remains `RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE`; the live prospective evidence requirement remains unmet.

## Reproducibility

Added `src/v322/segment_audit.py` and `tests/test_v322_segment_audit.py`. The script requires score and canonical-history CSVs, verifies contest/date/winning-number identity, then emits weekday and chronological segment statistics with moving-block bootstrap intervals. It is explicitly classified as exploratory and cannot promote a model.

Suggested invocation:

```bash
python -m src.v322.segment_audit --scores v322_hierarchical_partition_scores.csv --history data/history/Chispazo_through_12249.csv --out v322_segment_audit.json
```

## Guardrails

- No changes to `data/history/Chispazo_through_12249.csv`.
- No changes to frozen V294.
- No writes to `main`, no merge or promotion.
- No claim of 5/5 prediction or prospective advantage.
