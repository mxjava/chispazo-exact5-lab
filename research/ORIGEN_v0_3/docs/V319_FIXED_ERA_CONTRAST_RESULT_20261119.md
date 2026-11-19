# V319 — fixed-era contrast result

Status: COMPLETED — NO ERA DIFFERENCE DETECTED — RESEARCH ONLY.

## Provenance
- Preregistration: `PREREGISTRATION_V319_FIXED_ERA_CONTRAST.md`.
- Implementation: `src/origen/v319_fixed_era_contrast.py`.
- Workflow: https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44447156133 — success.
- Executed commit: `1130cb00e188f882f25b2166974fa0554aa17957`.
- Isolated ORIGEN suite: 146 tests passed in 17.027 seconds; full fixed-seed replay and artifact upload passed.
- Artifact: `exact5-v319-fixed-era-contrast`, ID `14493417947`.
- Artifact ZIP SHA-256: `bc875e33d863f79b25e47aaf3ab2fdef9df6ab8f00a31e08c0fe9596a55b87f0`.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.

## Frozen split and sample
- Boundary: 2022-03-10 (inherited from V265; not proof of machine identity).
- Before boundary: 6,075 Classic draws, contests 1363–8952, last date 2022-03-09.
- On/after boundary: 1,648 Classic draws, contests 8954–12248, first date 2022-03-10.
- Family size: 590 categories across number identity, pair identity and seven V318 shape summaries.
- Null: two independent uniform 5-of-28 sequences with the observed era sample sizes; 1,999 replicates, PCG64 seed 3192026.

## Primary result
- Observed global max |z|: 4.3319774324.
- Null 95th percentile: 6.8491440991.
- Null replicates at least as extreme: 363/1,999.
- Global add-one Monte Carlo p-value: 0.1820.
- Decision: `NO_ERA_DIFFERENCE_DETECTED`.

## Descriptive family maxima

| Family | Observed max | Null 95th percentile | Descriptive p |
|---|---:|---:|---:|
| Number identity | 2.2583 | 3.1536 | 0.5145 |
| Pair identity | 3.1847 | 3.8781 | 0.4400 |
| Sum | 4.3320 | 6.8491 | 0.1725 |
| Range | 1.7903 | 3.1330 | 0.8265 |
| Odd count | 1.0087 | 2.6498 | 0.8610 |
| Prime count | 0.9165 | 2.6332 | 0.8975 |
| Consecutive pairs | 0.9942 | 2.7002 | 0.8095 |
| Low 1..14 count | 0.9432 | 2.6611 | 0.8740 |
| Three-band occupancy | 1.8498 | 3.0712 | 0.7485 |

## Interpretation
The combined 590-category maximum does not reject the uniform two-era null (p=0.182). The largest descriptive component was the sum-family maximum, but its observed statistic is below its own null 95th percentile and it is not an individually confirmatory result.

This does not prove the eras are identical, and it does not identify any machine or sphere-set change. The boundary is only a fixed historical comparison point inherited from V265. No causal or predictive conclusion follows.

## Disposition
- No number, pair, or shape category is promoted.
- No change to V294, canonical history, or `main`.
- Actual machine, estuche, sphere identity and weighing records remain absent from the canonical result history.