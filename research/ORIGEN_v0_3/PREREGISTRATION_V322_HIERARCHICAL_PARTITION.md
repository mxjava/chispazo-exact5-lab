# V322 — Hierarchical partition-and-divide Exact5 model

Status: preregistered research design; execution pending.

## Question

Can a fixed hierarchy of disjoint combinatorial partitions assign more prequential probability to future Classic outcomes than the exact uniform 5-of-28 baseline?

## Universe and source

- Outcome universe: all C(28,5) = 98,280 unordered five-number sets.
- Canonical input: data/history/Chispazo_through_12249.csv.
- Required SHA-256: 5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a.
- Modality: existing structural Classic assignment only; row-level official verification remains pending. This limits interpretation and blocks edge certification.
- Target order: chronological by contest, as returned by the canonical history adapter.

## Fixed group-and-divide algorithm

For each target draw, the algorithm uses only earlier structurally assigned Classic draws.

1. Enumerate all 98,280 combinations.
2. Compute fixed candidate descriptors: sum bin, range bin, odd count, prime count, adjacent-pair count, low/middle/high band profile, and maximum-gap bin.
3. Construct three fixed hierarchical partition trees:
   - sum -> range -> odd count -> prime count -> adjacent count;
   - band profile -> sum -> max-gap bin -> odd count -> adjacent count;
   - range -> band profile -> prime count -> sum -> max-gap bin.
4. Each tree partitions the complete outcome universe into disjoint leaves. For every split, estimate the child conditional probability with a Dirichlet posterior predictive:
   (prior child count + alpha * exact-uniform child mass) / (prior parent count + alpha).
5. Multiply conditional probabilities down the tree to obtain leaf mass, then divide leaf mass uniformly among all combinations in that leaf.
6. Average the three normalized tree PMFs with fixed equal weights. No tree, feature, threshold, weight, or smoothing parameter is selected using target outcomes.

## Frozen constants

- Alpha = 200.0.
- Warmup = first 800 Classic observations.
- Equal tree mixture = 1/3 each.
- Primary comparison = per-target log probability against exactly 1/98,280.
- Secondary diagnostics = tie-aware expected inclusion in top 1, 5, 10, 30 and 100 ranks.
- No parameter sweep or retrospective tuning is allowed in this run.

## Evaluation

- Score each target before updating the model with that target.
- Report mean, median and cumulative log-lift, positive-log-lift fraction, rank intervals under ties, and tie-aware expected top-K inclusion.
- Compare expected top-K inclusions with n*K/98,280 under the uniform baseline.
- Preserve every target score, source hash, code hash and report hash.
- A retrospective prequential result is diagnostic only. It does not establish independent prospective edge or validate modality provenance.

## Falsification and stop rules

- Any probability normalization failure, invalid target, source hash mismatch, or chronology failure blocks the run.
- Do not infer a 5/5 signal from the best individual target or best leaf.
- Do not select or report a feature category as predictive based on its maximum historical result.
- If mean log-lift is non-positive or top-K coverage does not exceed the uniform expectation, record a negative result; do not retune on the same sample.
- A positive retrospective result requires a separately frozen prospective protocol and untouched future observations before any edge claim.

## Non-interference

V294 remains frozen. The canonical history is read-only. No writes to main, no model promotion, and no changes to prior V264/V265/V266 evidence. This experiment is confined to ORIGEN research.
