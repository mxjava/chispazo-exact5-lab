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

## Interpretation

Primary statistic: mean best-hit count across targets. Secondary statistics: number of targets with a best line >=4/5 and exact 5/5. Each Monte Carlo replicate independently samples 30 distinct combinations for every target. Empirical upper-tail p-values are diagnostic only; they are not prospective evidence or anytime-valid e-values and do not correct for model/portfolio search performed outside the replicate loop. If candidate selection used any evaluated outcomes, repeat the complete selection process inside each null replicate.

At least 100 intact prospective Classic targets, preregistration, multiplicity control, independent custody and existing evidence gates remain mandatory. This tool never promotes production; state remains research-only.
