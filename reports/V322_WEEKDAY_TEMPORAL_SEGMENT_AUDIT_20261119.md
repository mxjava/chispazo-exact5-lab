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

The file contains 989 targets for each weekday.

| Weekday | Mean log-lift | 95% moving-block bootstrap CI | Positive fraction |
|---|---:|---:|---:|
| Monday | -0.008715 | [-0.015066, -0.002291] | 47.02% |
| Tuesday | -0.006832 | [-0.011618, -0.001956] | 46.51% |
| Wednesday | -0.007714 | [-0.012597, -0.003947] | 47.02% |
| Thursday | -0.002680 | [-0.008370, 0.001568] | 49.34% |
| Friday | +0.000686 | [-0.006481, 0.005980] | 49.24% |
| Saturday | -0.005293 | [-0.009536, -0.000113] | 46.92% |
| Sunday | -0.007447 | [-0.012521, -0.002031] | 46.61% |

Bootstrap: chronological moving blocks of length 30, 3,000 resamples per weekday, fixed seed 20261119 plus weekday offset. These are exploratory, unadjusted intervals. The Friday point estimate is slightly positive but its interval crosses zero widely; it is not evidence of a Friday edge. Several weekday estimates are materially negative.

## Chronological stability

The 6,923 scored targets were divided into four chronological groups of near-equal size.

| Period | N | Mean log-lift | Positive fraction | Cumulative log-lift |
|---|---:|---:|---:|---:|
| Oldest quarter | 1,731 | -0.005258 | 46.74% | -9.1015 |
| Second quarter | 1,731 | -0.008502 | 46.33% | -14.7164 |
| Third quarter | 1,731 | -0.003573 | 49.45% | -6.1843 |
| Newest quarter | 1,730 | -0.004378 | 47.57% | -7.5742 |

The newest quarter remains negative. The apparent improvement in the third quarter did not persist in the newest quarter.

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
