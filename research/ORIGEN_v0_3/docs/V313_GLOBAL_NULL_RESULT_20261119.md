# V313 global null falsification — frozen retrospective result (2026-11-19)

## Provenance
- Branch: `research/origen-v0.3-engine-20261118`
- Commit containing the executable isolated workflow: `e5ec17ac2e7d6ab5f75a9acdb49f11b5982d45f1`
- GitHub Actions run: `44437090300` — completed successfully.
- Isolated unit tests: PASS.
- V313 preregistered global null falsification: PASS.
- Artifact: `exact5-v313-global-null-falsification`, artifact ID `14488723162`.
- Artifact SHA-256: `ef43f2fee1a4ba7be50c84f0f84b4a1f9a3c8ee4527b623dc2ab7486e83fd999`.
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
| Maximum pair-balance z | 20.86811 | 21.64806 | 0.6620 | 1.000 |
| Maximum temporal-overlap deviation | 0.019771 | 0.027365 | 0.4455 | 1.000 |

## Interpretation
None of the three preregistered global families rejects the independent-uniform null. The pair statistic is below its simulated 95th percentile; its Monte Carlo p-value is 0.662. The temporal statistic is also below its null 95th percentile. There is no statistically supported global historical imbalance or temporal-overlap departure in these tests.

This is a historical falsification result, not a prediction. It does not prove every possible conditional or physical mechanism absent; it does show that these broad global statistics did not detect one. It provides no basis for claiming a betting edge or changing V294.

## Limitations and next evidence
- Monte Carlo resolution is 1/2000 = 0.0005; no family was close to rejection, so increasing simulations would not change the substantive conclusion.
- Contest-to-modality labels remain structurally derived and are not a row-by-row audit against every original draw act.
- No official per-sphere individual mass records, physical sphere-ID-to-number mapping, calibration chain, or timestamped remapping/incident history has been received.
- No sealed pre-close predictions or independent prospective custody exist.
- The physical-bias workstream therefore remains `BLOCKED_PROVENANCE`; predictive classification remains `NO_EDGE_EVIDENCE`.

## Decision
- Keep V294 frozen.
- Do not tune or promote V313; it is a global null falsification diagnostic, not a predictive model.
- Do not rerun the same frozen test to seek a more favorable result.
- Next legitimate work: obtain the original signed weighing strips and draw-act annexes for the 28 spheres, establish the physical-ID/number mapping and metrology/timestamp chain, then preregister a separate physical-covariate test before inspecting linked outcomes.
