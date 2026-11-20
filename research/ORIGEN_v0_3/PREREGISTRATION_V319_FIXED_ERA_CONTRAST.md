# V319 — fixed historical era contrast

Date: 2026-11-19
Status: FROZEN BEFORE EXECUTION; RETROSPECTIVE REGIME-DIFFERENCE TEST; NOT CAUSAL.

## Question

Does the Classic-only result distribution differ before versus after the fixed 2022-03-10 boundary already used in V265's physical-regime scanner?

The boundary is inherited from the prior V265 research configuration; it is not re-estimated or optimized in V319. This is a contrast between historical eras, not proof that a machine change caused any difference. No machine/estuche metadata is present in the canonical outcomes file.

## Data and null

- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Classic-only rows from the versioned modality adapter.
- Era A: Classic draws with date strictly before 2022-03-10.
- Era B: Classic draws with date on or after 2022-03-10.
- Null: both eras are independent uniform 5-of-28 draws; the two sample sizes are fixed at their observed values.
- Monte Carlo: 1,999 pairs of full independent uniform sequences, PCG64 seed 3192026, add-one global max-statistic p-value.

## Frozen feature family

One combined family consists of:
- 28 individual-number inclusion proportions;
- 378 pair co-inclusion proportions;
- all 184 positive-probability categories from the seven V318 combinatorial-shape features: sum, range, odd count, prime count, consecutive adjacent-pair count, low 1..14 count, and three-band occupancy.

For each category, calculate the absolute difference in era proportions divided by the null standard error `sqrt(p*(1-p)*(1/n_A + 1/n_B))`, with p computed exactly from the full 98,280-set universe (or the exact 5-of-28 inclusion probability for number/pair cells). The primary statistic is the maximum across the full combined family. Calibrate it with the same complete two-era simulation.

Family-specific p-values are descriptive only. No category is selected for prediction.

## Decision

- `NO_ERA_DIFFERENCE_DETECTED` if global p >= 0.05.
- `HISTORICAL_ERA_DIFFERENCE_ONLY` if global p < 0.05. This is not causal, not a machine-effect finding, and not predictive evidence.
- `BLOCKED_INTEGRITY` for source, modality, or simulation integrity failure.

No model tuning, portfolio generation, V294 modification, or prospective claim follows from a rejection. A causal equipment hypothesis requires actual equipment and sphere metadata; any predictive hypothesis requires separate preregistration and untouched prospective custody.

## Limits

This fixed split test cannot determine which operational variable changed, and a non-rejection does not prove the two regimes are identical. The modality reconstruction remains structurally derived rather than row-by-row verified against every original draw act.