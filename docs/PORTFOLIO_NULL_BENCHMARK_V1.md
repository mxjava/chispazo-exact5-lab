# Matched random-null benchmark for 30-line Classic portfolios

This tool scores already-frozen 30-line Classic portfolios against the same official draw targets and compares best-hit-per-target with independently sampled random portfolios of 30 distinct combinations.

## Inputs

- JSON schema `EXACT5_FROZEN_PORTFOLIOS_V1`, one record per target.
- Separate externally retained JSON map from target number to registration SHA-256.
- Official-results CSV with `CONCURSO,MODALITY,R1..R5,SOURCE_URL,VERIFICATION`.

Each record includes target, `CLASSIC`, UTC registration and sales-cutoff timestamps, commit SHA, exactly 30 distinct canonical lines, and canonical `registration_sha256`. Registration must precede cutoff. The external hash map is separate; the tool cannot authenticate its custodian.

## Run

```bash
python -m src.portfolio_benchmark --portfolios frozen_portfolios.json --trusted-hashes trusted_hashes.json --draws official_draws.csv --out benchmark.json --replicates 5000 --seed 20261126
```

## Interpretation

Primary statistic: mean best-hit count across targets. Secondary statistics: number of targets with a best line >=4/5 and exact 5/5. Each Monte Carlo replicate independently samples 30 distinct combinations for every target. Empirical upper-tail p-values are diagnostic only; they are not prospective evidence or anytime-valid e-values and do not correct for a model/portfolio search performed outside the replicate loop. If the candidate was selected after examining target outcomes, the full selection process must be repeated inside every null replicate.

At least 100 intact prospective targets, preregistration, multiplicity control, independent custody and existing evidence gates remain mandatory. This tool never promotes production; state remains research-only.
