# V313 — Global draw-mechanism falsification plan

Status: DESIGN ONLY. No V313 model, signal, or edge is claimed. This protocol is intended to stop low-yield feature tweaking and test the draw mechanism at the right statistical level.

## 1. Research question

Before building another number-ranking model, test whether the observed Classic process is compatible with independent uniform sampling of 5 distinct numbers from 1..28. Separate:
- marginal inclusion imbalance (individual numbers);
- pair co-inclusion imbalance;
- selected higher-order structure;
- temporal dependence between consecutive draws;
- operational/physical covariates, only when primary records prove they were available before sales close.

The null is not "numbers look evenly frequent in one chart". The null is a sequence of independent, uniformly selected 5-subsets of {1,...,28}.

## 2. Exact null probabilities

For any fixed number i:
- P(i included) = 5/28.

For any fixed pair {i,j}:
- P(i and j both included) = (5/28)(4/27) = 5/189.

For any fixed triple {i,j,k}:
- P(all three included) = (5/28)(4/27)(3/26) = 5/1638.

Within a draw, inclusion indicators are dependent because exactly five numbers are selected. Tests must respect this fixed-size sampling; treating 28 indicators as independent Bernoulli variables is invalid.

## 3. Primary tests (pre-specified family)

A. Global number-balance omnibus:
- Statistic: maximum standardized absolute deviation of the 28 inclusion counts from N*5/28, with variance computed under the fixed-size hypergeometric null.
- Calibration: Monte Carlo randomization under independent uniform 5-of-28 draws, preserving N and the exact five-number constraint.
- Output: observed statistic, null quantile, Monte Carlo p-value and simulation seed.

B. Global pair-balance omnibus:
- Statistic: maximum standardized absolute deviation across all 378 pairs from N*5/189.
- Calibration: same draw-level randomization, recomputing the maximum over all 378 pairs in every replicate. This directly accounts for pair multiplicity and within-draw dependence.

C. Temporal dependence omnibus:
- Pre-register lag set 1..20 and statistics before examining results: overlap count, number of shared values, and pair co-inclusion transitions.
- Simulate full independent sequences with the same N and recompute the maximum across all lags/statistics. Do not select a lag after seeing a peak.

D. Higher-order motifs:
- Triples (3,276) are exploratory unless a max-statistic test is pre-registered with adequate Monte Carlo precision. No isolated small p-value may be promoted.

## 4. Segmentation and stability

- Primary stream: Classic only, with the already documented modality boundary.
- Secondary sensitivity: pre/post equipment or procedure changes only when official dated records identify those changes.
- Never choose a time window because it produces a signal. Window boundaries must come from documented operational events or be frozen in advance.
- Require direction and magnitude stability across chronological blocks; report all blocks, including null or contrary results.
- Do not pool De las Tres into Classic.

## 5. Multiplicity and stopping

- One primary omnibus family: number, pair and temporal tests; control family-wise error at 0.05 using Holm across the three primary p-values.
- Any follow-up per-number or per-pair claims require a separately declared family and correction.
- Fix Monte Carlo replicate count and random seed before execution; increase replicates only under a documented precision rule, never because a p-value is inconvenient.
- No repeated peeking or stopping when significance appears.
- Report effect sizes and uncertainty, not p-values alone.

## 6. Physical covariates

Physical covariates are a separate confirmatory stream and require:
- authenticated weighing strip and draw act;
- 28 individual masses with precision and units;
- stable physical sphere ID ↔ printed-number mapping;
- machine and set IDs;
- scale calibration evidence;
- timestamp proving availability before sales close;
- full change/replacement/re-weigh chain.

If any key link is missing, quarantine the row. Tolerance bands in the procedure are quality limits, not evidence of unequal extraction probabilities.

## 7. Prediction gate

A detected historical deviation is not automatically predictive or actionable. To become a candidate:
1. explain a plausible mechanism and define the exact feature before evaluation;
2. freeze model and code;
3. generate two sealed pre-close outputs with independent custody;
4. score at least 100 untouched prospective Classic draws;
5. require positive prequential log-lift, Holm-adjusted p < 0.05 and Exact5 anytime e-value >=20;
6. publish all failures and all candidate attempts.

Until then, classifications remain NO_EDGE_EVIDENCE or BLOCKED_PROVENANCE. Never output a "hot number" ranking as if a marginal frequency test were a forecast.

## 8. Stop rule for weak approaches

Do not create another frequency/EWMA/gap/transition mixture merely by changing windows, beta, weights or smoothing. V264 collapsed to uniform; V312 scored below uniform retrospectively. Re-enter that model family only if a pre-registered global falsification test identifies a stable, independently explainable structure.

## 9. Invariants

- V294 stays frozen.
- Canonical history remains byte-for-byte unchanged.
- No writes to main and no promotion from this research branch.
- Historical data is for discovery and integrity only; prospective evidence is separate.
