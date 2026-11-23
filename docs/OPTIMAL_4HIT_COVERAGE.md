# 30-line combinatorial 4-hit coverage portfolio (research-only)

Generate a deterministic portfolio with 30 distinct 5-of-28 lines:

\`\`\`powershell
python -m src.pipeline.generate_optimal_4hit_portfolio --seed 20261123 --out runs/optimal_4hit_coverage_20261123.csv
\`\`\`

This algorithm exhaustively considers the 98,280 possible winning 5-sets and greedily
maximizes the number of outcomes covered by at least one ticket with four or five hits.
Ties minimize number-frequency imbalance and are resolved by a versioned SHA-256
counter stream. It does not use historical frequencies, V294, or a predictive model.

## Exact combinatorial bound for 30 lines

One 5-number ticket covers at most 116 distinct winning sets with at least four hits:
its five 4-number subsets each have 24 possible one-number extensions, with the
ticket's own exact 5-set counted five times and therefore reduced by four duplicates.
For 30 tickets, the union cannot exceed 30 × 116 = 3,480 winning sets.

For seed \`20261123\`, the generator attains the bound:
- 30 distinct tickets;
- marginal new coverage of 116 outcomes for every ticket;
- 3,480 of 98,280 winning sets covered (3.5409%);
- 3,450 outcomes yield exactly four hits and 30 yield five hits;
- number usage is balanced: 18 numbers appear five times and 10 appear six times.

This is a combinatorial coverage optimum for the stated 30-ticket objective, not a
predictive edge. The probability of an exact 5/5 result remains 30/98,280 (0.0305%)
for any 30 distinct tickets. No portfolio can improve that probability under a
uniform 5-of-28 draw.

The artifact mode is \`COMBINATORIAL_4HIT_COVERAGE_NOT_PREDICTIVE\`; the predictive
freeze path must reject it. Do not relabel it, register it as V294, or treat it as
a prospective predictive result.
