# V312 — fixed static mixture retrospective result

Status: COMPLETED — NEGATIVE LOG-SCORE — RESEARCH ONLY — NO EDGE.

## Provenance
- Implementation: `src/origen/v312_static_mixture.py`.
- Canonical replay workflow: https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446737614 (success).
- Executed source history SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Classic-only sample: 7,723 draws, contests 1363–12248.
- Warm-up: 800 Classic draws; 6,923 subsequent Classic targets scored.
- Artifact: `exact5-v312-retrospective-integrity`, ID `14494415176`.

## Frozen candidate
- 27 non-uniform V264 experts: frequency windows 50/200/800, EWMA half-lives 16/32/64, hotgap/duegap/transition, beta values 0.15/0.30/0.60.
- Fixed distribution: 50% uniform plus 50% arithmetic mean of the 27 expert distributions.
- Exact unordered 5-of-28 likelihood; features use only prior Classic rows; transition context row is excluded from its own training targets.

## Result
- Mean log-lift versus uniform: -0.0262296890 nats per target.
- Cumulative log-lift: -181.5881372 nats.
- Positive log-lift fraction: 36.0682%.
- Minimum probability floor: 5.0875e-06.
- Prospective gates satisfied: false.

## Interpretation
The fixed 50/50 static mixture underperformed the uniform 5-of-28 baseline on the 6,923 retrospective Classic targets. The mixture's uniform floor guarantees nonzero probability support but does not make it predictive. This is a negative retrospective score, not a prospective e-value or a multiplicity-adjusted test.

Do not retune the expert family against this same stream or promote it. V294 remains frozen; no model promotion is authorized.