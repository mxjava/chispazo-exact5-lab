# Matched random-null benchmark for native 30-line Classic registrations

This research evaluator consumes the native immutable registration records produced by `src/pipeline/freeze_prediction.py`. It does not accept an alternative portfolio schema.

## Inputs

1. JSON object `EXACT5_NATIVE_REGISTRATIONS_V1` containing the native registration records, including target, timestamps, commit, model version, history/ranking hashes, preflight PASS, 30 lines and registration SHA-256.
2. Separate external registration-anchor JSON map: target -> registration SHA-256.
3. Separate target-cutoff JSON map: target -> `{modality, sales_cutoff_utc}`.
4. Draw CSV with `CONCURSO,MODALITY,R1..R5,SOURCE_URL,SOURCE_SHA256,VERIFICATION`.
5. Separate external draw-anchor JSON map: target -> canonical draw-record SHA-256.

The external anchors and cutoff metadata must be retained outside the files they validate. The tool checks the HTTPS Lotería Nacional domain and original source SHA format, but it cannot independently authenticate the custodian or validate a PDF/signature. The canonical draw hash must be anchored independently; a self-declared `OFFICIAL_PAGE_VERIFIED` field is not enough.

## Run

```bash
python -m src.portfolio_benchmark --registrations registrations.json --trusted-registration-hashes registration_anchors.json --target-cutoffs target_cutoffs.json --draws official_draws.csv --trusted-draw-hashes draw_anchors.json --out benchmark.json --replicates 5000 --seed 20261126
```

## Exact mathematical reference for 30 distinct random lines

The benchmark now reports an exact hypergeometric reference in addition to Monte Carlo replicates. For a uniformly sampled set of 30 distinct combinations from the 98,280 possible combinations, the probability of at least one line reaching each threshold is:

- Best line >= 3/5: 55.9077764%.
- Best line >= 4/5: 3.48147044%.
- Best line = 5/5: exactly 30/98,280 = 0.0305250305%.
- Expected best-hit count: 2.59325218.

These are random-baseline probabilities, not performance claims for the model. The exact 5/5 probability is invariant to which 30 distinct lines are selected under a uniform draw; selection strategy cannot improve it without a genuine non-uniform predictive signal.

## Interpretation

Primary statistic: mean best-hit count across targets. Secondary statistics: number of targets with a best line >=4/5 and exact 5/5. Each Monte Carlo replicate independently samples 30 distinct combinations for every target. Empirical upper-tail p-values are diagnostic only; they are not prospective evidence or anytime-valid e-values and do not correct for model/portfolio search performed outside the replicate loop. If candidate selection used any evaluated outcomes, repeat the complete selection process inside each null replicate.

At least 100 intact prospective Classic targets, preregistration, multiplicity control, independent custody and existing evidence gates remain mandatory. This tool never promotes production; state remains research-only.
