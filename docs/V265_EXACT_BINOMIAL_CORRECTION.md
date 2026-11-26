# V265 exact-binomial correction for persistence tests

## Finding

The original V265 persistence scanner used a normal approximation for the count of each fixed pair/triple across draws, then applied Holm adjustment. This is poorly calibrated for the rare-triple tail in the post-2022 sample.

For the fixed triple 04-11-15 in the canonical history through contest 12249:

- Post-cutover sample: 3,297 draws (cutover 2022-03-10).
- Observed occurrences: 25.
- Uniform-draw probability per draw: C(25,2) / C(28,5) = 300 / 98,280.
- Expected count: 10.0641.
- Two-sided exact binomial p-value: 0.0000501747.
- Conservative Bonferroni bound over 3,276 triples: 0.16437.

The previous normal-approximation report gave Holm-adjusted p=0.007907 and incorrectly marked one triple significant. The exact-binomial family-wise result does not meet 0.05. The 25 occurrences are split 12/13 across the two chronological halves, which does not establish a useful prospective signal.

## Correction

The scanner now computes two-sided exact binomial p-values for every fixed pair and triple count, then applies Holm adjustment to the complete pair and triple families. P-values are cached by unique observed count to avoid repeated exact-test calculations. Z-scores remain descriptive only.

## Interpretation and limits

This correction removes the claim that 04-11-15 is a multiplicity-adjusted anomaly. It does not prove the draw process is uniform, nor does it rule out physical or operational defects. The CSV itself still requires source-level verification before any operational conclusion. A retrospective frequency anomaly, even if confirmed, is not a predictive edge; only preregistered prospective performance can establish that.

This research change does not modify V294, the canonical history, production gates, or main.
