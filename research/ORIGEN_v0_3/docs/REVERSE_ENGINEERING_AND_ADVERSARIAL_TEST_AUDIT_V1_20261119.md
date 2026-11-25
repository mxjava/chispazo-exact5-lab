# Exact5 ORIGEN — reverse-engineering and adversarial test audit v1

Date: 2026-11-19
Branch: `research/origen-v0.3-engine-20261118`
Status: independent source-level audit; findings are not predictive evidence
Scope: V312 static mixture, V313 global-null falsification, V314 triple motif, V315 pair-conditioned transition, shared matrix/modality adapter.

## Executive result

This audit reconstructs the numerical contracts from the implementation rather than accepting report labels. It separates (a) algorithmic correctness, (b) preregistration fidelity, (c) data/provenance correctness, and (d) predictive evidence.

The current CI is useful but its tests are mostly smoke/reproducibility/shape checks. They do not yet independently prove all probability normalizations, count maps, matrix-domain constraints, or full preregistration-to-code equivalence.

No change to V294, canonical history, or `main` is made by this audit.

## Reverse-engineered contracts

### V312 — exact-set probability

For each expert, the implementation maps 28 feature values to standardized logits, exponentiates to positive item weights, and assigns each unordered 5-set S:

`P(S) = product(w_i for i in S) / e_5(w_1,...,w_28)`

where `e_5` is the fifth elementary symmetric polynomial computed by descending dynamic programming. The final distribution is fixed:

`P_mix(S) = 0.5 / C(28,5) + 0.5 * mean(P_expert(S), 27 experts)`.

The code therefore intends a normalized probability over all 98,280 unordered sets and a pointwise floor of half-uniform. Existing tests check expert count, a constant-signal special case, one combination's floor, modality exclusion and one-step future-row invariance. They do not yet sum the distribution over all 98,280 sets against an independent oracle.

### V313 — null generator and omnibus statistics

The null generator creates iid rows by assigning independent continuous random keys to 28 labels and selecting the five smallest; ties have probability zero. This is a valid uniform 5-of-28 sampler.

The implementation computes:
- maximum absolute standardized inclusion-count deviation over 28 labels;
- maximum absolute standardized pair-count deviation over 378 pairs;
- maximum absolute deviation of mean overlap for lags 1..20.

The pair count correctly widens the int8 matrix to int64 before dot products, preventing the previously discovered overflow. The current implementation's temporal statistic is specifically a max over lag-wise mean-overlap deviations.

**Preregistration fidelity issue to resolve before treating V313 as a complete implementation of its full design document:** the V313 preregistration text also names pair co-inclusion transitions among temporal statistics, while the executable temporal statistic currently evaluates only mean overlap by lag. The accepted historical V313 report must not be retroactively relabeled; any expanded family needs a new preregistration/version, its own maximum-statistic calibration, and a new result.

### V314 — triple family

The code enumerates all C(28,3)=3,276 unordered triples. Each valid 5-number draw contributes exactly C(5,3)=10 triple incidences. The statistic is the maximum absolute standardized deviation over the full family, calibrated by Monte Carlo simulations of independent uniform 5-of-28 draws. The current tests check family size, a repeated-draw fixture, theoretical probability, deterministic replay and Classic-only filtering. They do not yet independently cross-check the optimized lookup/bincount map against a simple reference enumerator on many randomized and adversarial fixtures.

### V315 — pair-conditioned next-draw overlap

Each transition from draw t to t+1 contributes one event for each of the ten unordered pairs in draw t, categorized by whether the next draw contains 0, 1 or 2 members of that pair. There are 378 prior pairs x 3 categories = 1,134 cells. The max statistic is calibrated by full-sequence uniform Monte Carlo. Existing tests verify dimensions, ten events per transition, finite statistics and deterministic Classic-only replay. They do not yet compare every cell with a simple independent nested-loop oracle over randomized fixtures.

## Findings and severity

1. **High — V313 design/code family mismatch.** The preregistration document names pair co-inclusion transitions among temporal statistics; the implementation uses only mean overlap by lag. This is a specification-completeness defect, not proof that the already reported p-values are numerically wrong for the narrower implemented statistic. Keep V313's published result scoped to the implemented statistic. Create a separately preregistered extension before adding omitted metrics.
2. **Medium — missing exhaustive V312 normalization oracle.** The elementary-symmetric-polynomial denominator is mathematically appropriate, but tests do not independently sum expert probability over all 98,280 sets. Add exhaustive normalization tests for representative nonconstant features/betas and the fixed mixture.
3. **Medium — optimized V314/V315 count maps lack broad independent-oracle tests.** Existing tests assert totals and dimensions; these can pass even if events are assigned to wrong cells. Add slow, clear reference implementations in tests and compare exact vectors on seeded randomized fixtures.
4. **Medium — matrix validators mostly assume binary inputs.** V313/V314/V315 matrix-level guards check dimensions and row sums but do not universally enforce entries in {0,1}. Production paths build matrices from validated number lists, so this is defense-in-depth for internal APIs and future reuse. Add malformed-matrix tests and explicit binary checks where appropriate in a separately reviewed patch.
5. **Medium — modality mapping remains structurally inferred.** The adapter explicitly labels the mapping as pending row-level primary-source audit. The split is internally coherent but not equivalent to verification against every official draw act. Preserve this provenance limitation.
6. **High for predictive interpretation — none of these historical tests establishes a forecast advantage.** V312's retrospective score is negative; V313–V315 did not reject their implemented global nulls. CI success proves code ran, not an edge.

## Required adversarial test battery

A. V312 probability engine:
- Exhaustively sum one expert distribution over all 98,280 sets for at least three nonconstant signals and beta values; require tight numerical tolerance around 1.
- Exhaustively sum the 27-expert mixture and verify normalization, positivity, and the half-uniform floor.
- Verify permutation invariance of chosen-number order and invariance to adding a constant to all feature values.
- Test very large finite feature magnitudes, constant vectors, NaN, infinities, wrong vector length, invalid chosen values and duplicate chosen values; require deterministic fail-closed behavior or mathematically valid output.

B. V313 null and statistics:
- Verify every simulated row is binary with exactly five ones, and seeded output is reproducible.
- Compare inclusion and pair statistics to a simple Python reference on small matrices.
- Include a regression fixture with pair counts above 127 and independently assert exact int64 pair counts.
- Reject non-binary matrices, wrong dimensions, wrong row sums and too-short sequences.
- Test Holm adjustment against hand-calculated p-value vectors, including ties and p=1.

C. V314 triple index:
- Compare the complete 3,276-cell vector to a straightforward combinations-based reference over many seeded random sequences.
- Assert each valid draw contributes exactly ten counts; assert no lookup index is negative.
- Test repeated identical draws, boundary labels 1 and 28, row permutations and malformed matrices.

D. V315 transition index:
- Compare all 1,134 cells to a straightforward nested-loop reference over seeded random sequences.
- Independently verify expected overlap probabilities sum to one and match direct hypergeometric enumeration.
- Test category boundaries 0, 1 and 2, first/last transition handling, row permutations and malformed matrices.

E. End-to-end temporal integrity:
- Perturb all De las Tres rows; Classic predictions and scores must remain byte-identical.
- Append future Classic rows; already emitted earlier scores must remain byte-identical.
- Shuffle input rows; either canonicalize with an explicit documented rule or reject; never silently depend on incidental order.
- Duplicate or remove a contest; fail closed at the canonical ingestion boundary.
- Recompute all source, code, config and output hashes independently.

## Acceptance criteria for a reverse-engineering release

- Every optimized numerical kernel has an independent, intentionally simple reference oracle.
- Every preregistered statistic has an explicit code-to-spec traceability row.
- Every family and multiplicity correction is frozen before any new computation.
- Invalid matrices and corrupted provenance fail closed.
- Focused adversarial tests, full ORIGEN suite, full repository CI and independent artifact/hash inspection all pass.
- No predictive claim until the prospective gates in the continuity protocol pass.

## Next decision

Do not silently patch the accepted V313 design or change its historical report. First add the independent reference tests for V312/V314/V315 and binary-domain checks under a new, separately reviewed research commit. Then preregister a V316 temporal extension if pair co-inclusion transition statistics remain scientifically justified. V316 must be calibrated as a single max family across every lag and every metric actually tested; no metric may be added after seeing results.
