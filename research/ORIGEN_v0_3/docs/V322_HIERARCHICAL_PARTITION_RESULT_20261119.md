# V322 — Hierarchical partition-and-divide result (2026-11-19)

Status: COMPLETED — NEGATIVE PREQUENTIAL LOG-SCORE — NO PREDICTIVE EDGE — RESEARCH ONLY.

## Provenance and execution

- Preregistration: `research/ORIGEN_v0_3/PREREGISTRATION_V322_HIERARCHICAL_PARTITION.md`.
- Implementation: `src/origen/v322_hierarchical_partition.py`.
- Tests: `tests/test_v322_hierarchical_partition.py`.
- Executed commit: `d629ebabefc144da037ec8d67270c4ed68cfc6d2`.
- Dedicated GitHub Actions run: [44581344357](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44581344357) — success.
- ORIGEN isolated test workflow: run `44581344235` — success.
- Artifact: `exact5-v322-hierarchical-partition`, ID `14558553834`.
- Artifact ZIP SHA-256: `7009da322a20c1426eabc97d5a5f48e768483a35abafe5150e61e117c055b2d6`.
- Per-target CSV SHA-256: `8f816e8c1635c8fcdf13e070e30972faba3a90890a8b4637050da91a324bf26a`.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.

## Frozen model

- Full outcome universe: 98,280 unordered five-number combinations.
- Three disjoint hierarchical partition trees; equal fixed mixture.
- Each tree assigns posterior predictive probability to a leaf, then divides that mass uniformly among combinations in the leaf.
- Exact-uniform cell mass is the Dirichlet prior base; fixed alpha = 200.
- First 800 structurally assigned Classic draws are warmup.
- Each of the 6,923 later Classic targets is scored before it is added to the training history.
- No parameter sweep, target-informed cut point, or V294 change.

The three trees have 1,573, 2,346 and 1,932 non-empty leaves, respectively. They cover the complete 98,280-combination universe. The implementation vectorizes leaf scoring and checks normalized PMFs.

## Results

- Classic history: 7,723 draws, contests 1363–12248.
- Scored targets: 6,923, contests 2163–12248.
- Mean log-lift vs exact uniform: **-0.0054277528 nats**.
- Median log-lift: **-0.0047881124 nats**.
- Cumulative log-lift: **-37.57633286 nats**.
- Positive log-lift fraction: **47.5228%**.
- Winning combination ranked exactly first: **0 of 6,923**.

| Tie-aware ranking | V322 expected inclusions | Uniform expected inclusions |
|---|---:|---:|
| Top 1 | 0 | 0.0704 |
| Top 5 | 1 | 0.3522 |
| Top 10 | 1 | 0.7044 |
| Top 30 | 3 | 2.1132 |
| Top 100 | 7 | 7.0442 |

The top-30 count is slightly above its uniform expectation, but the top-100 count is essentially identical, the mean log-score is negative, and the model never ranked a winning set first. The small top-30 difference is not evidence of an edge and was not the primary scoring criterion.

## Decision

`NO_EDGE_EVIDENCE`. V322 is closed as a completed negative result. Do not retune alpha, reorder the trees, change bins, or select a best-performing subgroup on these same 6,923 targets. Do not use V322 to generate betting combinations.

This tests joint interactions among fixed result-shape partitions, beyond the individual shape families tested in V318. It does not test physical sphere identity or measured mass. The next genuinely different path is the already preregistered V317 physical Plackett–Luce mechanism, but it remains blocked until authentic per-sphere masses, sphere-ID ↔ printed-number mapping, calibration, machine/set identity and pre-close custody are available.

## Non-interference

- V294 remains frozen.
- Canonical history remains byte-for-byte unchanged.
- No writes to `main`, no merge and no model promotion.
- Modality remains structurally assigned and pending row-level official verification.
