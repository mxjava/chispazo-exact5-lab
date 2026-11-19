# V323 adaptive expert mixture — executed replay results

Date: 2026-11-19
Research branch commit at replay: `f4ac48aa94e8b67c0311758ae21a0aa8e1449839`
Workflow run: `44616113802`
Artifact: `v323-adaptive-replay-f4ac48aa94e8b67c0311758ae21a0aa8e1449839`

## Execution and integrity

- V264 historical replay completed successfully.
- V323 adaptive grid completed successfully.
- CI: 242 passed, 2 skipped; compileall passed.
- Scored targets: 10,087 (contests 2163–12249).
- Expert matrix: 28 experts.
- Canonical source: `data/history/Chispazo_through_12249.csv`.
- The replay does not modify the canonical history, V294, or main.

Important scope limitation: this replay consumes the full canonical sequence as the current V264 implementation does. Since row-level official modality assignment is still unresolved, these results are a canonical-sequence diagnostic, not a certified Clásico-only estimate. Do not use them to claim a Clásico-specific edge.

## V264 baseline diagnosis

- Mean log-lift: -0.0003303464.
- Cumulative log-lift: -3.3322045102.
- E-value: 0.0357142857143.
- Final posterior mass on uniform expert: 1.0.
- Top-30 probability mass lift: 0.9999999999999997 (effectively exactly uniform).

The static Bayesian mixture therefore collapsed to the uniform expert; it did not demonstrate an advantage.

## V323 adaptive grid

All ten candidates were evaluated on the same 10,087 targets. The nine rolling candidates use the fixed grid of windows 100, 250, 500 and temperatures 0.25, 0.5, 1.0. The static full-history Bayesian mixture is included as a comparator. Uniform is the zero-log-lift reference.

| Candidate | Mean log-lift | Cumulative log-lift | 95% circular block CI |
|---|---:|---:|---:|
| Static full Bayes | -0.000330346 | -3.3322 | [-0.000806098, +0.000013829] |
| Rolling W500, η=1.0 | -0.000422392 | -4.2607 | [-0.000887110, -0.000070256] |
| Rolling W500, η=0.5 | -0.000591219 | -5.9636 | [-0.001182014, -0.000136778] |
| Rolling W500, η=0.25 | -0.001243223 | -12.5404 | [-0.002163875, -0.000380036] |
| Rolling W250, η=1.0 | -0.002497986 | -25.1972 | [-0.003848040, -0.001264304] |
| Rolling W250, η=0.5 | -0.003115591 | -31.4270 | [-0.004488910, -0.001759993] |
| Rolling W250, η=0.25 | -0.005789271 | -58.3964 | [-0.007831118, -0.003715216] |
| Rolling W100, η=1.0 | -0.009987280 | -100.7417 | [-0.012715672, -0.007303569] |
| Rolling W100, η=0.5 | -0.010726251 | -108.1957 | [-0.013527129, -0.007807621] |
| Rolling W100, η=0.25 | -0.013307579 | -134.2336 | [-0.016536283, -0.010070239] |

Intervals use a corrected circular moving-block bootstrap: block length 30, 3,000 resamples, fixed seeds, each replicate truncated to exactly 10,087 observations. Intervals are unadjusted for the nine-candidate search and are diagnostic, not confirmatory.

## Key interpretation

1. No adaptive candidate beat the uniform reference (zero log-lift); all nine rolling candidates had negative mean and negative cumulative log-lift.
2. The least damaging rolling candidate was W500, η=1.0, but its 95% interval remained below zero. It is not an edge.
3. Shorter windows performed progressively worse. W100 candidates accumulated approximately -100.7 to -134.2 log-lift units.
4. The static full-history mixture had a near-zero score for most targets because its posterior concentrated entirely on uniform. Its bootstrap interval crosses zero.
5. For W500, η=1.0, all four chronological quartile means were negative; the newest quartile mean was -0.00006616. No stable positive regime emerged.
6. The numerical sign metric now treats values within ±1e-12 as zero, avoiding false positive counts from floating-point residue when the mixture is effectively uniform.

## Engineering corrections included

- V264 now actually populates the per-expert export; the first replay exposed that the file had been created but left empty. This was fixed and the replay completed.
- V323 now reports a uniform zero-log-lift reference explicitly.
- Sign diagnostics use a 1e-12 numerical tolerance and separately report positive, negative, and numerical-zero fractions.
- Entropy calculation handles underflowed zero weights without NaN.
- Bootstrap now uses circular blocks and truncates every replicate to the original sample length. This corrects the earlier padding bias.

## Decision

`V323 = RESEARCH_ONLY_NO_EDGE`.

Do not promote a rolling window, change V294, or make a 5/5 claim. The next necessary work is:
- resolve official row-level modality for the canonical history;
- produce a Clásico-only score matrix using a predeclared and verified filter;
- add multiplicity-aware comparison across the fixed grid;
- evaluate a frozen candidate prospectively on future draws, with 3/5, 4/5, 5/5 and proper probability-score metrics.

The research result is useful: the tested adaptive forgetting policies made the existing expert ensemble worse, rather than recovering signal.
