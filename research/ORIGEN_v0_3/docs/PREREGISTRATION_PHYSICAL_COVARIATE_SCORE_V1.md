# Preregistration: physical-covariate association test V1 (CLASSIC only)

Status: **PROTOCOL + SYNTHETIC TEST HARNESS ONLY**. No official sphere measurements or
independently authenticated physical records are currently available. No prediction,
causal claim, edge, or production eligibility is claimed.

## Why this is the next legitimate experiment

The existing 30-line portfolio already reaches the exact upper bound for its stated
4-or-5-hit coverage objective: 3,480 of 98,280 possible outcomes. Its 5/5 probability
cannot be improved by rearranging 30 distinct lines under a uniform 5-of-28 draw.
Historical V313, V315 and V316 global/temporal tests did not reject their preregistered
uniform nulls. Repeating those searches with new windows or seeds is not authorized.

The remaining physically motivated route requires measurements tied to the actual
28 physical balls and the machine/set used for each draw. A number-frequency anomaly
alone cannot identify a physical cause.

## Primary question and fixed family

For CLASSIC draws at 21:00 only, do preregistered, independently measured physical
attributes of the 28 balls associate with their inclusion in the five selected balls?

The fixed four-feature family is:
1. mass_g
2. diameter_mm
3. sphericity_index
4. surface_roughness_um

All four features must be recorded with measurement method, units, instrument ID,
calibration certificate, measurement time, operator, physical ball ID, printed number,
ball-set ID and machine ID. A missing feature is not silently dropped. No substitute
feature, transformed feature, directional hypothesis, or post-hoc subgroup may be
introduced after outcomes are inspected.

The schema requires 28 unique physical IDs and a one-to-one physical-ID to printed-number
mapping for every unchanged machine/ball-set epoch. If the machine, ball set, mapping,
calibration, or feature measurements change, create a new epoch. Do not pool across
epochs without retaining their separate feature vectors and draw memberships.

## Statistical model and null

For each epoch, align each of the four feature vectors to printed numbers 1..28.
For feature vector x and observed draw S (five distinct numbers), the score contribution
is:

u(S, x) = sum(x_i for i in S) - 5 * mean(x_1, ..., x_28).

Under the null, each draw is an independent uniform 5-subset of 1..28. The exact
single-draw score distribution is enumerated over all C(28,5)=98,280 outcomes.
The test combines score contributions across the preregistered equipment epochs,
preserving each epoch's own feature vector and draw count.

The standardized statistic is the absolute aggregate score divided by its exact
finite-population null standard deviation. The primary family statistic is the
maximum absolute z-score across the four fixed features. Monte Carlo calibration
uses PCG64, seed 20261125, 9,999 null replicates and add-one p-values. The implementation
also reports raw feature p-values and Holm-adjusted p-values; no feature is promoted
unless its Holm-adjusted p is below 0.05 and the family max-statistic p is below 0.05.

This is an association/diagnostic test, not a fitted predictive model. A rejected null
does not establish causality, physical tampering, or future predictive lift.

## Prospective and provenance gates

Before any real record enters the analysis:
- obtain original signed Acta, CS-11, weighing strip and draw participation file;
- capture original bytes and SHA-256 before parsing;
- verify institutional signatures, trusted timestamp, certificate chain and revocation;
- verify physical-ID to printed-number mapping and 28-ball completeness;
- verify instrument calibration and measurement traceability;
- identify machine and ball-set for each CLASSIC 21:00 draw;
- establish independent custody and pre-close timestamps;
- exclude De las Tres 15:00 entirely;
- keep the canonical historical CSV read-only.

The current code cannot perform these provenance checks. Its contest IDs, epoch IDs,
machine IDs and ball-set IDs are structural labels supplied by the caller, not
authenticated facts. It requires at least 100 draws but does not itself establish that
they are prospective, untouched, or independently sealed.

## Decision rule and multiplicity

The four-feature family and all methods above are frozen before examining linked
outcomes. The family-wise Monte Carlo p-value and Holm-adjusted feature p-values are
reported together. A result is exploratory unless the data source and custody gates
pass. No threshold, feature, epoch boundary, seed, or family may be changed to rescue
a negative result.

Even a positive physical association is insufficient for EDGE_SUPPORTED. It must lead
to a separately preregistered predictive model and then pass the standing prospective
criteria: at least 100 untouched CLASSIC draws, positive preregistered prequential lift,
Holm p<0.05, anytime e-value >=20, two independently sealed pre-close outputs, clean
hashes and authentic independent custody.

## Synthetic validation

tests/test_physical_covariate_score_v1.py uses synthetic feature vectors and synthetic
weighted draws only. The tests validate null calibration behavior, detection of a
deliberately large synthetic association, fixed feature family, CLASSIC-only routing,
unique contest IDs, five distinct values per draw and non-degenerate measurements.
Synthetic fixtures are not lottery evidence.
