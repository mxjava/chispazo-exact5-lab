# V318 — combinatorial-shape omnibus result

Status: COMPLETED — NO REJECTION — RESEARCH ONLY — NO PREDICTIVE EDGE.

## Provenance
- Preregistration: `PREREGISTRATION_V318_COMBINATORIAL_SHAPE_OMNIBUS.md` (committed before execution).
- Implementation: `src/origen/v318_combinatorial_shape.py`.
- Tests: `tests/test_v318_combinatorial_shape.py`.
- Workflow: https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446819621
- Executed commit: `31d0a2f0c6ce78227fd434142b7a854744b18a7f`.
- Workflow result: success; full ORIGEN test suite at that commit passed (140 tests); canonical replay and artifact upload passed.
- Artifact: `exact5-v318-combinatorial-shape`, ID `14493333027`.
- Artifact ZIP SHA-256: `8f624f6c32769fe022262049a9e7afb7688d29d588630a5dfde2548651e22445`.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.

## Frozen test
- Classic-only: 7,723 draws, contests 1363–12248.
- Null: independent uniform 5-of-28, exact universe C(28,5)=98,280.
- Seven fixed feature families and 184 positive-probability categories.
- 1,999 full-sequence Monte Carlo replicates; PCG64 seed 3182026; add-one global max-statistic p-value.

## Primary result
- Observed global maximum absolute standardized residual: 2.7721135789.
- Null 95th percentile: 4.4836559043.
- Null replicates at least as extreme: 1,570 / 1,999.
- Global Monte Carlo p-value: 0.7855.
- Decision: `NO_REJECTION`.

## Descriptive family results (not separate confirmatory tests)

| Feature | Observed max | Null 95th percentile | Descriptive p |
|---|---:|---:|---:|
| Sum | 2.7721 | 4.3941 | 0.7050 |
| Range | 2.4619 | 3.0522 | 0.2715 |
| Odd count | 1.2774 | 2.5519 | 0.6970 |
| Prime count | 1.0306 | 2.6228 | 0.8345 |
| Adjacent consecutive pairs | 1.0532 | 2.5138 | 0.7640 |
| Low numbers 1–14 | 1.8629 | 2.6224 | 0.2995 |
| Three-band occupancy | 1.4957 | 3.0050 | 0.9365 |

## Interpretation
The observed global maximum is below the null 95th percentile, and 1,570 of 1,999 null replicates were at least as extreme. The frozen omnibus does not reject independent uniform 5-of-28 sampling for these seven result-shape summaries.

This does not prove perfect randomness and does not test every conditional mechanism. It provides no number-level signal, no physical explanation, no causal result and no prospective advantage. No category is selected or promoted.

## Integrity and disposition
- No change to V294 or canonical history.
- No writes to `main` and no model promotion.
- Classic modality mapping remains structurally derived and not row-by-row verified against every official act.
- The physical-mass line remains blocked pending authentic sphere-level weighing strips, mapping, calibration and pre-close timestamps.