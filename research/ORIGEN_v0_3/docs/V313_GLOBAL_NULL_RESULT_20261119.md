# V313 global null falsification — frozen retrospective result (2026-11-19)

## Provenance
- Branch: `research/origen-v0.3-engine-20261118`
- Corrected implementation commit: `203edaabad7a71928339c3b44e14b4680402b58f`; regression-test commit: `fa33d4d4a73a96b4fd02329302c03a25decfed3e`.
- Corrected isolated workflow run: `44437475593` — completed successfully; isolated tests PASS and full V313 replay PASS.
- Corrected artifact: `exact5-v313-global-null-falsification`, artifact ID `14489552572`.
- Corrected artifact SHA-256: `cec8075188d26d88e7710fad9652b43e146f47851c16323354341ba97ec364dd`.
- **Superseded/invalidated:** the first V313 artifact (run `44437090300`, artifact `14488723162`) used NumPy int8 dot-product accumulation for pair counts. Counts above 127 overflowed. Its pair statistic and p-value are invalid and must not be cited. The number and temporal calculations were unaffected.
- The fix casts the binary matrix to int64 before pair accumulation and adds a regression test with 2,000 repeated co-occurrences.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a` (unchanged).
- Stream: Classic only, 7,723 draws, contests 1363–12248. Contest 12249 is excluded as De las Tres by the documented modality mapping.

## Frozen test configuration
- 1,999 Monte Carlo simulations.
- NumPy PCG64 seed: 3132026.
- Null: independent uniform 5-subsets from 1..28.
- Primary families: individual-number balance, pair co-inclusion balance, temporal overlap lags 1..20.
- Holm family-wise alpha: 0.05.

## Results

| Primary statistic | Observed | Null 95th percentile | Monte Carlo p | Holm-adjusted p |
|---|---:|---:|---:|---:|
| Maximum number-balance z | 1.72005 | 3.11646 | 0.9155 | 1.000 |
| Maximum pair-balance z | 3.09767 | 3.80672 | 0.5370 | 1.000 |
| Maximum temporal-overlap deviation | 0.019771 | 0.027365 | 0.4455 | 1.000 |

## Interpretation
None of the three preregistered global families rejects the independent-uniform null. The corrected pair statistic is below its simulated 95th percentile; its Monte Carlo p-value is 0.537. The temporal statistic is also below its null 95th percentile. There is no statistically supported global historical imbalance or temporal-overlap departure in these tests.

This is a historical falsification result, not a prediction. It does not prove every possible conditional or physical mechanism absent; it does show that these broad global statistics did not detect one. It provides no basis for claiming a betting edge or changing V294.

## Limitations and next evidence
- Monte Carlo resolution is 1/2000 = 0.0005; no family was close to rejection, so increasing simulations would not change the substantive conclusion.
- The pair-count overflow was caught by independent artifact review after the first green run. The first artifact is explicitly invalidated; the corrected rerun and regression test are the authoritative V313 result.
- Contest-to-modality labels remain structurally derived and are not a row-by-row audit against every original draw act.
- No official per-sphere individual mass records, physical sphere-ID-to-number mapping, calibration chain, or timestamped remapping/incident history has been received.
- No sealed pre-close predictions or independent prospective custody exist.
- The physical-bias workstream therefore remains `BLOCKED_PROVENANCE`; predictive classification remains `NO_EDGE_EVIDENCE`.

## Decision
- Keep V294 frozen.
- Do not tune or promote V313; it is a global null falsification diagnostic, not a predictive model.
- Do not rerun the same frozen test to seek a more favorable result.
- Next legitimate work: obtain the original signed weighing strips and draw-act annexes for the 28 spheres, establish the physical-ID/number mapping and metrology/timestamp chain, then preregister a separate physical-covariate test before inspecting linked outcomes.
