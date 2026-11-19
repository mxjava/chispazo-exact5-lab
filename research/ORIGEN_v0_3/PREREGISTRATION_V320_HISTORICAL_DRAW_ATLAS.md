# V320 — Historical Draw Atlas and Reverse-Engineering Protocol

Status: PREREGISTERED DESIGN / NOT YET EXECUTED
Domain: Chispazo Clásico only. De las Tres is a separate population and must never be pooled into the confirmatory Classic analysis.
Canonical input: data/history/Chispazo_through_12249.csv (read-only; byte-for-byte invariant).
Prospective observations: data/prospective/chispazo_classic_observations.csv (separate from canonical history).

## Objective

Build a deterministic, auditable atlas that assigns every eligible historical Classic draw to an exact combinatorial location and explains its descriptive structure. Separately test whether any information available before a draw improves prospective probability scores. The atlas is descriptive; a post-draw explanation is not a causal explanation and does not establish predictability.

No method can guarantee a 5/5 result in a fair random draw. The research target is to discover and independently validate a reproducible predictive edge, if one exists, while preserving a uniform-random baseline.

## A. Data gate

1. Parse contest ID, date, modality and five distinct integers in [1,28].
2. Sort numbers within each draw; reject duplicates, invalid values, malformed rows and unresolved modality.
3. Deduplicate by contest ID; flag conflicting duplicate IDs and date/order anomalies.
4. Keep Classic and De las Tres separate. Never infer missing results.
5. Freeze input SHA-256, row count, min/max contest, date range and exclusions in a manifest.
6. Do not edit or replace the canonical CSV. Any official extension is a separately sourced supplement with URL, retrieval date, raw-file hash and row-level provenance.

## B. Exact combinatorial location for every draw

Enumerate the full universe C(28,5)=98,280 exactly once. For every combination compute a fixed feature vector:
- sum and arithmetic mean;
- range (max-min);
- odd/even count;
- prime count (prime set fixed as 2,3,5,7,11,13,17,19,23);
- count of adjacent consecutive pairs;
- count in low band 1–9, middle 10–18, high 19–28;
- count of values 1–14;
- sorted gap vector and maximum gap;
- exact pair and triple identities.

For each observed draw, emit:
- exact feature vector and deterministic feature-cell IDs;
- exact combinatorial cell size and its null probability under uniform 5-of-28;
- percentile/rank against the complete 98,280-combination universe for scalar features;
- nearest archetype(s) under a preregistered, scale-normalized distance, with deterministic tie-break;
- pair/triple identities and their historical counts up to (not including) that draw when used in chronological diagnostics.

Do not call an outcome "rare" without reporting the exact null probability and multiplicity context. Do not imply that a feature caused the outcome.

## C. Historical atlas outputs

Produce one row per Classic draw with contest, date, numbers, feature vector, cell IDs, exact cell probability, ranks, archetype and validation flags. Produce aggregate tables for:
- observed vs exact-universe expected feature-cell frequencies;
- number/pair/triple occurrence counts;
- temporal gaps and recurrence intervals;
- day-of-week and within-day position only if timestamp/ordering provenance is reliable;
- transition summaries using strictly prior draws.

For every aggregate comparison, use an explicit null, report effect size and uncertainty, and correct the complete declared family for multiplicity (Holm or a preregistered max-statistic simulation). Historical descriptive summaries are not predictive evidence.

## D. Inverse-search / prospective gate

For each target draw t, candidate scores may use only information available strictly before t. Use expanding-window prequential evaluation, no random train/test split and no feature selection on the full outcome sequence. Compare every candidate against the uniform 5-of-28 baseline using per-draw log score. Report mean and cumulative log-lift, positive fraction, median, exact one-sided sign test, multiplicity correction, and empirical adversarial-null calibration.

A candidate can be called promising only if it:
1. beats uniform on a genuinely untouched chronological holdout;
2. survives the complete preregistered multiplicity correction;
3. remains stable across fixed eras and reasonable perturbations;
4. has a reproducible, frozen prospective record before outcomes are known;
5. passes an independent replay from the frozen source and manifest.

No retrospective tuning to the most recent miss or hit. No promotion of V294 or any challenger without explicit evidence gates.

## E. Required tests

- Exhaustive universe count is exactly 98,280 and each combination is unique.
- Every valid draw maps to exactly one deterministic feature vector and cell.
- Invalid numbers, duplicate numbers, malformed dates, duplicate/conflicting contests and modality leakage are rejected or quarantined.
- Cell probabilities sum to 1 across the exhaustive universe.
- Rank and archetype outputs are deterministic under row-order permutation.
- Chronological features cannot access target or future rows (poison-future test).
- Full replay reproduces byte-identical outputs and manifest hashes.
- Canonical history hash is unchanged before/after every run.
- V294 files/specification are unchanged.

## Decision labels

- DESCRIPTIVE_ATLAS_COMPLETE: historical mapping is complete; no predictive claim.
- NO_SIGNAL: tests do not reject the declared null.
- EDGE_CANDIDATE: all statistical gates pass but prospective confirmation is pending.
- EDGE_SUPPORTED: independent prospective evidence passes all preregistered gates.
- BLOCKED: provenance, integrity, sample-size or test requirements fail.

A 5/5 hit is an observed outcome, not by itself evidence of a predictive edge. The algorithm must be judged on the full prospective score stream, not selected wins.
