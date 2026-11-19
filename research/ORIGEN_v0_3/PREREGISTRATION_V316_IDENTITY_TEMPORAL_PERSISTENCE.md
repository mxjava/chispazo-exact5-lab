# V316 — Identity-resolved temporal persistence omnibus

Status: PREREGISTERED DESIGN; no V316 computation has been run.
Scope: retrospective global-null falsification on the protected Classic-only stream. This is not a forecasting model.

## 1. Question and motivation

V313 tested the mean number of shared values between draws at lags 1–20. That statistic can miss identity-specific persistence: an unusual tendency for particular labels or particular pairs to recur at a given lag even when the total overlap count is ordinary.

V316 tests that missing, explicitly defined family. It is a new experiment and does not amend, reinterpret, or replace V313.

## 2. Frozen data contract

- Stream: Classic only, sorted by contest.
- Source: `data/history/Chispazo_through_12249.csv`; expected source SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Expected Classic count at preregistration: N=7,723, contests 1363–12248. If source digest, count, or boundaries differ, abort and investigate; do not silently adapt.
- Each draw is a 28-dimensional binary vector with exactly five ones.
- Lags: every integer lag 1 through 20, inclusive.
- No De las Tres rows in features, warm-up, or scoring.

## 3. Null model

The null is a sequence of independent, identically distributed uniform 5-subsets of {1,...,28}. Every Monte Carlo replicate has exactly N draws and the same five-of-28 constraint.

For a fixed number i, p1 = 5/28. For a fixed unordered pair {i,j}, p2 = 5/189.

Under independent draws at distinct times:
- number persistence probability: q1 = p1^2;
- pair persistence probability: q2 = p2^2;
- expected total overlap at any positive lag: 25/28.

The null simulator must sample each draw uniformly without replacement. It must not simulate 28 independent Bernoulli variables.

## 4. Frozen statistic family

For each lag l in {1,...,20}:

A. Aggregate overlap:
- O_l = mean over t of |D_t intersect D_(t+l)|.
- S_A,l = |O_l - 25/28| / sqrt(Var_null(O_l)).
- The null variance and all cross-lag dependence are calibrated by the complete-sequence Monte Carlo maximum; the implementation must document its scaling formula.

B. Number identity persistence:
- C_i,l = sum over t of 1[i in D_t and i in D_(t+l)] for each of 28 labels.
- Standardize each count against mean (N-l)q1 and binomial marginal variance (N-l)q1(1-q1). This standardization is a scale for the omnibus statistic, not an assumption that overlapping time-pairs are independent.

C. Pair identity persistence:
- C_(i,j),l = sum over t of 1[{i,j} subset D_t and {i,j} subset D_(t+l)] for all 378 unordered pairs.
- Standardize each count against mean (N-l)q2 and binomial marginal variance (N-l)q2(1-q2). Again, the binomial variance is only a scale; inferential calibration is by full-sequence Monte Carlo.

The single primary statistic is the maximum absolute standardized value across all:
- 20 aggregate lag statistics;
- 28 × 20 = 560 number-lag cells;
- 378 × 20 = 7,560 pair-lag cells.

Total frozen family size: 8,140 statistics. No cell, label, pair, or lag may be removed after results are inspected.

## 5. Monte Carlo calibration

- Replicates: 1,999 independent null sequences, each length N=7,723.
- Generator: NumPy PCG64.
- Seed: 3162026.
- Add-one Monte Carlo p-value: (1 + number of replicate maxima >= observed maximum) / 2,000.
- Report observed maximum, null 95th percentile, p-value, simulation count, seed, source digest, and runtime.
- The full 8,140-cell maximum must be recomputed for every replicate. Do not calibrate cells independently and then select a minimum p-value.
- Use deterministic, tested vectorized or batched computation. Any optimization must be checked against a deliberately simple reference implementation on small synthetic sequences.
- If the full frozen computation cannot complete reliably, report BLOCKED_COMPUTATION. Do not reduce the family, lag range, sample size, or replicate count after seeing results.

## 6. Tests required before the full run

1. Exact shape, binary-domain, and five-of-28 validation.
2. Direct nested-loop reference equality for aggregate, number, and pair persistence counts on seeded small sequences.
3. Exact null expectation checks for q1 and q2.
4. Seeded simulator reproducibility and per-draw uniqueness.
5. Permutation invariance to ordering of labels, with corresponding remapping of cell identities.
6. No leakage across modality boundaries.
7. Full maximum statistic must equal the maximum of the independently materialized component statistics.
8. A deliberately injected persistence defect must increase the relevant statistic; a uniform-null fixture must not cause indexing or overflow.
9. Integer-width adversarial test with repeated counts above 127.
10. Full canonical source digest and sample-boundary assertions.

## 7. Decision rule and interpretation firewall

- One global Monte Carlo p-value for the one max-statistic family; alpha=0.05.
- A rejection is evidence of historical identity-resolved temporal departure from this null only.
- A rejection is not causal evidence, not evidence of a stable mechanism, and not a prospective betting edge.
- A non-rejection means this prespecified family did not detect such departure; it does not prove all mechanisms absent.
- Any follow-up subgroup, alternative lag, different statistic, or physical covariate is a new family and requires a new preregistration before computation.
- No parameter tuning, repeated peeking, or rerunning with a new seed to seek significance.

## 8. Invariants

- V294 remains frozen.
- The canonical history remains byte-for-byte unchanged.
- No writes to `main`; research branch only.
- V313, V314, and V315 results remain unchanged.
- No prediction or combination may be described as advantaged based on this retrospective test.
- Prospective evidence gates remain mandatory: at least 100 chronological untouched Classic draws, positive preregistered prequential lift, Holm-adjusted p<0.05 where multiple confirmatory claims are made, Exact5 anytime e-value >=20, two sealed pre-close outputs, independent custody, and verified hashes.

## 9. Status

This file freezes the hypothesis family and analysis plan only. It does not certify that the implementation exists, tests pass, computation ran, or any signal was found. Implementation must be isolated and reviewed against the tests above before the single confirmatory run.
