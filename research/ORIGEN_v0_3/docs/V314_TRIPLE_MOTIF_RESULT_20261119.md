# V314 — Triple motif reverse-engineering result (2026-11-19)

## Provenance and integrity
- Preregistration: `PREREGISTRATION_V314_TRIPLE_MOTIF.md`.
- Implementation: `src/origen/v314_triple_motif.py`.
- Branch: `research/origen-v0.3-engine-20261118`.
- Executed commit: `7073ae1215f5074f4b56072eb4892b2230872eb9`.
- GitHub Actions run: `44438128053` — success.
- Isolated ORIGEN tests: PASS.
- Full canonical V314 replay: PASS.
- Artifact ID: `14489319430`.
- Artifact SHA-256: `72e6c708806dde80e973dca7ff65d10d27f1d798ebf72b36a78b89c2c4ba2cd9`.
- Source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a` (protected canonical file).
- Classic stream: 7,723 draws, contests 1363–12248.

## Frozen test
- All 3,276 unordered triples from 1..28.
- Null probability per triple: 5/1638 = 0.0030525030525.
- Max absolute standardized triple-count deviation.
- 1,999 Monte Carlo sequences; NumPy PCG64 seed 3142026; add-one p-value.
- Chronological four-block breakdown of the single full-history maximum, descriptive only.

## Result
- Observed maximum z: 3.3881441901.
- Null 95th percentile of the maximum: 4.6257833315.
- Monte Carlo p-value: 0.9825.
- Winning historical triple: 10, 24, 26.
- Observed count: 40; null expected count: 23.574481.
- Chronological block counts: 9/1931, 8/1931, 8/1931, 15/1930.

## Interpretation
The apparent excess for 10-24-26 is not unusual after calibrating the maximum across all 3,276 triples. Its observed max statistic is below the null 95th percentile and the Monte Carlo p-value is 0.9825. The motif does not survive family-wise max-statistic calibration. Its block counts are descriptive and do not establish a stable effect.

V314 therefore finds no statistically supported higher-order triple motif in this historical Classic stream. This is not evidence of a predictive edge and does not justify selecting 10-24-26 for a future ticket.

## Decision and next step
- Do not promote the winning triple or tune around it.
- V313 and V314 both fail to detect their preregistered broad global structures.
- Next inverse-engineering step should use authenticated physical sphere records and dated equipment/maintenance changes. Without sphere IDs, number mapping, 28 individual weights, calibration and timestamps, the mechanical extraction process cannot be reconstructed from outcome numbers alone.
- V294 remains frozen; canonical history remains unchanged; main remains untouched.
