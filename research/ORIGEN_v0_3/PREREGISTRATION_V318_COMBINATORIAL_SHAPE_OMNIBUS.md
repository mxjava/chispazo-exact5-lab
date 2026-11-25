# V318 — preregistered combinatorial-shape omnibus falsification

Date: 2026-11-19
Status: FROZEN BEFORE EXECUTION; RETROSPECTIVE ONLY; NO PREDICTION.

## Question

Does the Classic-only historical stream show a departure from independent uniform sampling of five distinct numbers from 1..28 in predeclared, draw-internal combinatorial shape summaries not directly tested as a joint family by V313–V316?

This is a result-only test. It cannot identify physical sphere mass, machine, sphere set, loading order, or causal mechanism.

## Frozen data and null

- Source: `data/history/Chispazo_through_12249.csv`, canonical SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Modality: Classic only, derived by the existing versioned modality adapter; expected 7,723 draws, contests 1363–12248.
- Outcome per contest: unordered set of five distinct integers in 1..28.
- Null: independent draws, each uniformly distributed over all C(28,5)=98,280 unordered five-number sets.
- Simulations: 1,999 complete sequences, NumPy PCG64 seed 3182026, add-one Monte Carlo p-value.

## Frozen feature families

For each unordered five-set, calculate:
1. Sum of the five numbers.
2. Range (maximum minus minimum).
3. Number of odd values.
4. Number of primes (prime set fixed as 2,3,5,7,11,13,17,19,23).
5. Number of adjacent consecutive pairs in sorted order (difference exactly one).
6. Number of values in 1..14.
7. Three-band occupancy profile: counts in 1..9, 10..19, and 20..28.

No feature, bin, family, split, or simulation seed may be added or removed after seeing the result.

## Statistic and calibration

For each feature family, enumerate the full 98,280-set universe once to obtain exact category probabilities. In the observed Classic stream, calculate the absolute standardized residual for every category with positive null variance:
`abs(observed_count - n*p) / sqrt(n*p*(1-p))`.

The single primary statistic is the maximum residual over every category in all seven feature families. Each Monte Carlo replicate is a complete iid uniform 5-of-28 sequence of length n; recompute the same global maximum. The global add-one p-value is `(1 + number(null_max >= observed_max))/2000`. This single maximum calibration controls the frozen combined search family; no post-hoc category selection is used for inference.

Family-specific maximum z and Monte Carlo p-values are descriptive only.

## Decision

- `NO_REJECTION`: global p >= 0.05.
- `HISTORICAL_SHAPE_DEPARTURE_ONLY`: global p < 0.05. This is not a predictive edge, not causal evidence, and not a license to select a winning category or number.
- Any source, modality, matrix, or simulation integrity failure: `BLOCKED_INTEGRITY`.

No model tuning, portfolio generation, V294 modification, or prospective claim follows from a rejection. Any future predictive hypothesis requires a new preregistration and untouched prospective custody.

## Limits

This test does not test all possible conditional dependencies, and a non-rejection does not prove perfect randomness. It tests only the seven fixed summaries above. The Classic modality reconstruction is structurally supported but remains subject to the documented row-by-row official-source limitation.