# Uniform coverage runtime (research-only)

The Exact5 predictive gate remains closed because the validated historical evidence
does not establish a positive edge. This utility provides a usable coverage/control
mode without bypassing that gate: it samples distinct 5-of-28 combinations uniformly
without replacement, using a versioned deterministic SHA-256 rank sampler.

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

The sampler is versioned as `Exact5UniformPortfolio/v1`. It derives a deterministic
SHA-256 counter stream from the canonical decimal seed and uses rejection sampling
for unbiased bounded integers, followed by Floyd sampling without replacement.
This avoids relying on the implementation details of Python's `random.sample`,
which are not a cross-version serialization contract. The golden-vector test pins
the output for seed `20261122`. A future algorithm change must use a new sampler
version rather than silently changing existing seed-to-portfolio mappings.

For a fair 5-of-28 draw, each exact line has probability 1/98,280. A set of 30
distinct lines has uniform exact-5 probability 30/98,280; the utility does not
increase that probability above the uniform baseline.

## Boundary with the prospective registration pipeline

The generator's CSV includes the explicit `UNIFORM_COVERAGE_NOT_PREDICTIVE` mode.
The predictive freeze command rejects that marker instead of accepting the file
as if it were a model portfolio. The 30-line count alone is not evidence of
predictive eligibility. To enter the predictive freeze path, a separate candidate
must pass the existing preflight, provenance, commit-binding, and immutable-ledger
checks. Do not remove or rewrite the mode marker to bypass this guard.

## Post-draw control evaluation

After the official result is available, score the exact CSV that was generated (do
not regenerate it). Example:

```powershell
python -m src.pipeline.evaluate_uniform_portfolio --portfolio runs/uniform_coverage_20261122.csv --contest-id 12390 --result 01 07 12 21 26 --out runs/uniform_coverage_12390_evaluation.json
```

The evaluator checks the CSV schema, non-predictive mode marker, contiguous ranks,
single seed, valid unique combinations, and five distinct result numbers. It records
the input SHA-256, best hit count, exact-5 count, and hit distribution. The report
is explicitly `EVALUATED_CONTROL_ONLY`; it does not create or alter a prospective
registration and cannot be used as evidence of predictive lift. Only use a completed,
officially verified result and preserve the original portfolio CSV.

## Exact uniform-null calibration

The post-draw evaluator also reports a finite-population null calibration for the
same portfolio size. The universe has 98,280 exact-5 combinations. For a fixed
five-number result, the number of universe combinations with exactly k hits is
`C(5,k) * C(23,5-k)`. Since portfolio lines are sampled without replacement,
the evaluator uses hypergeometric probabilities (not a binomial approximation)
to report expected hit counts and the null tail probability for observing a best
hit count at least as large as the one recorded. It also reports the null
probability of at least one exact-5 in a portfolio of that size.

These are descriptive null-calibration quantities for uniformly sampled controls.
A small tail probability from one observed portfolio is not by itself evidence of a
predictive model: repeated prospective testing, preregistration, multiple-testing
control, independent custody, and the protocol's evidence gates remain mandatory.
The output never upgrades the mode from control-only.

## Aggregate multiple completed control evaluations

Once each contest has its own completed evaluation JSON, summarize them without
editing the original reports:

```powershell
python -m src.pipeline.aggregate_uniform_controls --reports runs/eval_12390.json runs/eval_12391.json --out runs/uniform_controls_aggregate.json
```

The aggregator validates control-only status, the non-predictive flags, contest
uniqueness, portfolio SHA-256 format, hit-distribution totals, exact-5 count,
best-hit consistency, and compatible null-calibration metadata. It rejects duplicate
contest IDs. Reusing the same fixed portfolio across different independently drawn
contests is allowed and often desirable: each contest is a new draw, while the
portfolio hash makes the repeated fixed input explicit. The aggregate reports observed
versus expected 0–5 hit counts across the supplied contests. It is descriptive only:
it does not compute a predictive-edge p-value, does not append to the official
prospective ledger, and cannot upgrade any model's evidence status. Preserve each
original report and portfolio CSV.
