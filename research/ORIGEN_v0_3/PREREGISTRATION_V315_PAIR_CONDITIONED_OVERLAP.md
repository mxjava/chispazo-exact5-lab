# V315 — Pair-conditioned next-draw overlap falsification

Status: PREREGISTERED before V315 computation. Research-only; no forecast claim.

## Question
Does the next Classic draw's overlap with a pair selected in the immediately preceding Classic draw differ systematically from independent uniform 5-of-28 sampling?

This is a targeted transition test: rather than testing only average overlap between complete draws, it asks whether particular prior pairs are associated with unusual next-draw overlap outcomes.

## Unit and family
For each adjacent pair of Classic draws (D_t, D_{t+1}), enumerate the 10 unordered number-pairs contained in D_t. For each such prior pair P, classify the next draw by K=|P intersect D_{t+1}|, where K is 0, 1, or 2.

There are 378 possible prior pairs and 3 overlap categories, yielding 1,134 cells. The test statistic is the maximum absolute standardized deviation across all cells from the independent-uniform expectation.

Under the null, conditional on any fixed prior pair, the next independent uniform 5-subset has:
- P(K=0) = C(26,5)/C(28,5)
- P(K=1) = 2*C(26,4)/C(28,5)
- P(K=2) = C(26,3)/C(28,5)

Each prior pair occurs in expectation across 5/28*4/27 of preceding draws. The marginal cell expectation is (N-1)*(5/189)*P(K=k). Because pair instances and cells are dependent, inferential calibration is by full-sequence Monte Carlo, not independent-cell approximations.

## Statistic and calibration
- Classic only, using the existing structural modality map.
- All 378 prior pairs x 3 overlap categories; no pair selection after seeing data.
- For each cell, standardize observed count against its exact null marginal mean and variance under independent sequences. Use the maximum absolute standardized deviation as omnibus statistic.
- Calibrate the maximum with 1,999 full independent uniform 5-of-28 sequences of the same length; recompute the entire statistic for each replicate.
- NumPy PCG64 seed 3152026; add-one Monte Carlo p-value.
- Report null 95th percentile, p-value, and strongest cell as descriptive only.
- Report the strongest cell in four chronological blocks, descriptive only.

## Interpretation firewall
A rejection would indicate historical pair-conditioned transition structure, not causality or a predictive edge. A non-rejection does not prove the physical draw process is perfectly random. Any prospective claim still requires pre-close sealed predictions, independent custody, >=100 untouched Classic draws, positive prequential log-lift, Holm-adjusted p<0.05 and Exact5 anytime e-value >=20.

## Invariants
V294 frozen; canonical history byte-for-byte unchanged; no writes to main; no promotion. Do not change V313/V314 results or their preregistrations.
