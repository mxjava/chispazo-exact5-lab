# V316 — Identity-resolved temporal persistence result (2026-11-19)

Status: COMPLETED — NO REJECTION; RESEARCH ONLY; NO PREDICTIVE EDGE.

## Frozen execution

- Preregistration: PREREGISTRATION_V316_IDENTITY_TEMPORAL_PERSISTENCE.md.
- Executed workflow: https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44444415214
- Executed commit: 20b087ab77a523dd51758096bef5f39798c5bf28.
- Current V316 implementation blob at the executed commit and current research branch: d3d0ef0c16caff73ac22dd8bef834d5cecae5dbf (identical).
- Artifact: exact5-v316-identity-temporal-persistence, ID 14492367500.
- Artifact ZIP SHA-256: bbdd2587974c1c71c564bd0b59072c2e37a0a94e83b967fb3a8fa195c7ec8269.
- Source SHA-256: 5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a.
- Classic-only sample: N=7,723, contests 1363–12248.
- Frozen family: 8,140 statistics (20 aggregate-overlap lag values, 560 number-identity/lag cells, 7,560 pair-identity/lag cells).
- Null: independent uniform 5-of-28 sequences, 1,999 simulations, PCG64 seed 3162026, add-one Monte Carlo p-value.

## Result

- Observed global maximum absolute standardized statistic: 3.7079616438589245.
- Null 95th percentile: 5.853084531895807.
- Null replicates at least as extreme as observed: 1,998 of 1,999.
- Add-one Monte Carlo p-value: 0.9995.
- Runtime: 85.9127 seconds.
- Strongest cell, descriptive only: pair {13,25} at lag 18, |z|=3.70796.

The observed maximum is below the 95th percentile of the null maximum distribution, and 1,998/1,999 null replicates were at least as extreme. The frozen global family therefore does not reject independent uniform 5-of-28 sampling.

The descriptive strongest pair is not a signal, a hot/cold pair, or a candidate feature. It was selected as the maximum over the entire 8,140-cell family and is ordinary under the calibrated null.

## Interpretation and limits

V316 found no evidence of identity-specific temporal persistence in its preregistered family. This does not prove that every conceivable physical or operational mechanism is absent. It does show that this frozen, broad family did not reveal a historical departure from the specified null.

No forecasting advantage, causality, or betting edge is established. Do not use pair {13,25}, lag 18, or any V316 cell to select combinations. Do not retune the family or rerun with alternative seeds to seek significance.

## Validation

- V316 workflow completed successfully; isolated ORIGEN test step passed; full frozen 1,999-replicate computation passed; report artifact uploaded.
- The implementation uses packed-bit pair counts and the test suite includes direct nested-loop pair-count reference checks, label-permutation invariance, injected-persistence checks, exact 5-of-28 probability checks, and matrix-contract rejection.
- A later commit changed custody-only code/tests and workflow path filters; it did not change the V316 implementation or its preregistered statistical family.
- V294 remains frozen; canonical history remains protected; no write or merge to main. PR #8 remains draft/unmerged.

## Decision

Close V316 as a completed negative historical falsification. Do not create another retrospective number/pair/lag search by changing windows or statistics. The next high-information path remains authenticated physical sphere-level records with pre-close timestamps and sphere-ID ↔ printed-number mapping, followed by a separately preregistered physical mechanism test and prospective validation.
