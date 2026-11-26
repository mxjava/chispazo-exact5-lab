# V3 — 30-line 3+ coverage portfolio (2026-11-26)

## Result

The V3 portfolio covers **67,377 of 98,280** possible five-number draws with at least three hits (68.5562%). It preserves the prior portfolio's 4+ coverage: **3,480 of 98,280** (3.5409%), including 30 exact 5/5 outcomes.

| Metric | V1 | V2 | V3 |
|---|---:|---:|---:|
| 3+ covered outcomes | 59,859 | 66,849 | **67,377** |
| 3+ coverage | 60.9067% | 68.0159% | **68.5562%** |
| 4+ covered outcomes | 3,480 | 3,480 | **3,480** |
| Exact 5/5 outcomes | 30 | 30 | **30** |

V3 adds 528 covered outcomes over V2 (+0.5373 percentage points) and 7,518 over V1 (+7.6495 points).

## Search method

A seeded stochastic local search started from V2. Neighbourhood moves replace one or two numbers within one line. A move is rejected if any pair of lines would intersect in more than two numbers. The objective is the exact cardinality of the union of all five-number draws that achieve at least three hits against at least one portfolio line. The final candidate was evaluated over all \(\binom{28}{5}=98,280\) possible draws.

The search is heuristic; this result is not claimed globally optimal. The final verifier independently enumerates the entire outcome space and checks the pairwise-intersection invariant.

## Historical observation (not prospective evidence)

Against contest 12396 (05-07-21-24-28), V3's best line is line 22 (07-14-19-24-28), with 3/5. This is a post-hoc observation, not a prospective test, and it must not be interpreted as evidence of predictive edge.

## Guardrails

- Coverage optimization only; not a probability model or predictive claim.
- Keep V1 and V2 immutable as baselines.
- Freeze V3 before any future draw; do not replace lines after observing outcomes.
- No change to V294, canonical historical data, or production eligibility.
- Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.

## Reproduction

From repository root:

```bash
python src/research/verify_3plus_portfolio_v3.py
```

The verifier is standard-library-only and should report PASS with 67,377 3+ outcomes, 3,480 4+ outcomes, and maximum pairwise line intersection 2.
