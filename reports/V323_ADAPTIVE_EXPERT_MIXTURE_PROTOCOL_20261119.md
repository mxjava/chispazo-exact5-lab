# V323 adaptive expert mixture — preregistered research protocol

Date: 2026-11-19

## Motivation

The V264 static Bayesian expert mixture progressively assigned essentially all posterior mass to the uniform expert after the historical experts repeatedly underperformed. At contest 12250, the recorded uniform posterior was 1.0 and the cumulative mixture log-lift was -3.3322045102 (mixture likelihood ratio approximately 0.0357142857). This is a meaningful diagnostic: the current alternatives did not beat uniform in the evaluated sequence.

The V323 experiment asks a narrower question: can a *causal, adaptive* mixture respond to regime changes without using future outcomes? It does not presume that such a mixture will improve performance.

## Frozen comparison set

The new evaluator compares the existing static full-history Bayesian mixture with a fixed grid of rolling expert mixtures:

- Windows: 100, 250, and 500 previously scored contests.
- Temperatures: 0.25, 0.5, and 1.0.
- Prior: equal weight across experts, including the uniform expert if supplied.
- Target weights: computed only from score rows strictly before the target.
- Outcome metric: log of the mixture probability relative to the uniform probability for the realized exact 5-subset.
- Uncertainty: moving-block bootstrap, block length 30, 3,000 resamples, fixed seed.

No parameter will be selected or promoted from this retrospective comparison. The entire grid is reported, including candidates that lose.

## Mathematical rule

Let (L_{t,j} = log(p_{t,j}(y_t)/p_0(y_t))) be expert (j)'s realized log-likelihood ratio at target (t). For a rolling window (W) and temperature (eta), weights are

[
w_{t,j} =
rac{pi_jexpleft(etasum_{s=max(1,t-W)}^{t-1}L_{s,j}ight)}
{sum_kpi_kexpleft(etasum_{s=max(1,t-W)}^{t-1}L_{s,k}ight)}.
]

The target mixture log-lift is

[
L_t^{mix} = logleft(sum_j w_{t,j}exp(L_{t,j})ight).
]

For every target, (w_t) depends on past rows only. Any convex mixture of valid expert predictive distributions remains a valid predictive distribution when its weights are predictable. Rolling/tempered weights are an adaptive forecast rule, not the original fixed Bayesian posterior and not a claim of e-process validity.

## New data contract

V264 now exports `v264_expert_log_likelihoods.csv` with one row per contest and expert:

- `CONCURSO`
- `expert`
- `log_lift`

The V323 loader rejects duplicate contest/expert pairs, missing cells, and non-finite scores. This preserves the per-expert evidence needed to compare adaptive policies instead of retaining only the aggregate mixture score.

## Reproduction

After running V264 on a historical file ending at target - 1:

```bash
python -m src.v264.CHISPAZO_V264_EXACTSET_ANYTIME --history data/history/Chispazo_through_12249.csv --out-dir /tmp/v264_replay
python -m src.v323.adaptive_expert_mixture --scores /tmp/v264_replay/v264_expert_log_likelihoods.csv --out /tmp/v323_grid.json
```

## Decision gates

1. All V323 grid candidates must be evaluated on the same targets and same expert set.
2. Compare every candidate to uniform and static V264, not merely to the weakest candidate.
3. Report chronological subperiods and calibration diagnostics; do not select a lucky weekday.
4. A positive retrospective result is only a hypothesis. Freeze the candidate before a separate future prospective holdout.
5. No 5/5 success, predictive edge, or production readiness is claimed absent that prospective evidence.

## Guardrails

V294 remains frozen. Canonical history remains byte-for-byte unchanged. The experiment stays on the research branch; no writes to `main`, merge, or promotion.
