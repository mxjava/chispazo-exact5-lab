# Uniform coverage runtime (research-only)

The Exact5 predictive gate remains closed because the validated historical evidence
does not establish a positive edge. This small utility makes the software usable
without bypassing that gate: it samples distinct 5-of-28 combinations uniformly
without replacement, with a reproducible integer seed.

It is **not V294**, does not use historical frequencies, does not claim predictive
lift, and does not create a prospective registration. It does not read or mutate
the canonical history or any frozen model artifact.

## Run

```powershell
python -m src.pipeline.generate_uniform_portfolio --seed 20261122 --lines 30 --out runs/uniform_coverage_20261122.csv
```

For five lines, change `--lines 30` to `--lines 5`. Preserve the seed and CSV
unchanged if you intend to evaluate the result later. Do not call this output a
prediction or a certified Exact5 model result.

For a fair 5-of-28 draw, each exact line has probability 1/98,280. A set of 30
distinct lines has uniform exact-5 probability 30/98,280; the utility does not
increase that probability above the uniform baseline.

## Boundary with the prospective registration pipeline

The generator's CSV includes the explicit `UNIFORM_COVERAGE_NOT_PREDICTIVE` mode.
The predictive freeze command now rejects that marker instead of accepting the file
as if it were a model portfolio. The 30-line count alone is not evidence of
predictive eligibility. To enter the predictive freeze path, a separate candidate
must pass the existing preflight, provenance, commit-binding, and immutable-ledger
checks. Do not remove or rewrite the mode marker to bypass this guard.
