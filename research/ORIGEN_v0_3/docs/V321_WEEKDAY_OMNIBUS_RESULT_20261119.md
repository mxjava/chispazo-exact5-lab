# V321 — Weekday omnibus result (2026-11-19)

## Decision

**NO_HISTORICAL_ASSOCIATION_DETECTED.** The preregistered global weekday omnibus did not reject the null at alpha = 0.05. Do not build a weekday-based selector from these data and do not claim predictive advantage.

## Frozen protocol

- Input: V320 Classic atlas rebuilt from the canonical history.
- Source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Classic observations: 7,723; weekday counts 1,103 / 1,103 / 1,103 / 1,103 / 1,104 / 1,104 / 1,103.
- Fixed family: sum, range, odd count, prime count, consecutive pairs, low 1–9, middle 10–18, high 19–28, low 1–14, max gap.
- Statistic: eta-squared by weekday; global maximum across the ten features.
- Null: shuffle weekday labels while preserving their observed counts.
- Monte Carlo: 1,999 permutations, NumPy PCG64, seed 3212026; plus-one p-values; single-step max-T familywise adjustment.
- Preregistration: `research/ORIGEN_v0_3/PREREGISTRATION_V321_WEEKDAY_OMNIBUS.md`.

## Results

- Global maximum eta-squared: **0.0016345641** (approximately 0.1635% of variance for the maximising feature).
- Global p-value: **0.3240** (647 exceedances / 1,999; plus-one correction).
- Decision: **NO_HISTORICAL_ASSOCIATION_DETECTED**.
- Largest observed feature eta-squared: max_gap 0.00163456; its familywise adjusted p-value is 0.3240.
- Other feature familywise adjusted p-values: range 0.5235; consecutive_pairs 0.5210; prime_count 0.9625; odd_count 0.9930; mid_10_18 0.9985; sum, low_1_9, high_19_28 and low_1_14 all 1.0000.

## Interpretation and next action

This is a historical association test only. It does not test or establish a prospective predictive edge, nor does it identify a physical mechanism. The weekday hypothesis for this fixed ten-feature family is closed unless genuinely new independent evidence justifies a new preregistration. Do not tune this family against the same historical sample.

Continue with a different, independently motivated hypothesis and maintain a strict expanding-window comparison against uniform probability before any prospective claim. V294 remains frozen. Do not modify main or the canonical history.

## Reproducibility

- Workflow run: `44541495186` (V321 workflow job succeeded; generated and uploaded result artifact).
- Artifact ID: `14538892065`.
- Artifact ZIP SHA-256: `2b1f38e9a289ba67d11499db05c52940fa9116a09049a7c898def9ffce377c46`.
- Artifact contains `v321_weekday_omnibus.json` and `v320_atlas_manifest.json`.
- A subsequent output-format correction ensures the JSON file ends with a valid newline; the final workflow must be green after that correction before this report is treated as the final reproducibility record.
