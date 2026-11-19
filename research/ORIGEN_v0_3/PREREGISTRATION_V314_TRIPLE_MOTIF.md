# V314 — Higher-order motif reverse-engineering test

Status: PREREGISTERED BEFORE V314 COMPUTATION. Research-only; no predictive claim.

## Question
Does the Classic sequence contain stable higher-order structure that is invisible to V313's marginal-number, pair-count and mean temporal-overlap omnibus tests?

## Primary hypothesis family
Test all 3,276 unordered triples from {1,...,28}.

For each triple T, let C_T be the number of Classic draws containing all three members. Under independent uniform sampling of five distinct numbers:
P(T subset draw) = (5/28)(4/27)(3/26) = 5/1638.
For N independent draws, C_T is Binomial(N, 5/1638), with mean N*5/1638 and variance N*p*(1-p).

Statistic: maximum absolute standardized deviation across all 3,276 triples. Monte Carlo calibration recomputes the maximum over the full family in each replicate, preserving the exact five-of-28 within-draw structure and N. This controls family-wise multiplicity within the triple family.

## Frozen calibration
- Classic only, same modality mapping and canonical source as V313.
- 1,999 Monte Carlo replicates.
- NumPy PCG64 seed: 3142026.
- Add-one p-value.
- Report 95th percentile and empirical p-value.
- No post-hoc changes to seed, replicate count, triple family, or statistic.

## Reverse-engineering interpretation
A rejection identifies a historical triple motif inconsistent with the global independent-uniform null after max-statistic calibration. It does not establish causality, a physical mechanism, or predictive advantage. Report the winning triple and direction only as a discovery lead; any per-triple inference requires a separately designed replication and multiplicity-controlled test.

## Stability audit
Report triple-count contributions by four chronological equal-sized blocks, using the same full-history winning triple selected by the omnibus statistic. This is descriptive only and cannot rescue a failed omnibus test. No block-specific model fitting.

## Prediction firewall
No prediction or betting edge is claimed. Any future candidate requires a plausible mechanism, frozen implementation, two sealed pre-close outputs, at least 100 untouched prospective Classic draws, positive prequential log-lift, Holm-adjusted p<0.05 and Exact5 anytime e-value >=20.

## Invariants
V294 remains frozen; canonical history remains byte-for-byte unchanged; no writes to main; no promotion. V313 remains unchanged and its corrected result remains authoritative.
