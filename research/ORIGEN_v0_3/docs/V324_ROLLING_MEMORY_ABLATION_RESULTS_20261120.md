# V324 — Rolling-memory ablation results (2026-11-20)

## Scope and reproducibility

- Engine: `research/ORIGEN_v0_3/src/origen/v324_rolling_memory.py`
- Test suite: `research/ORIGEN_v0_3/tests/test_v324_rolling_memory.py`
- Workflow: `.github/workflows/v324-rolling-memory.yml`
- Validated source head: `98408e84f40f073a17e0f1b982d2f23d2e438c59`
- Replay run: [44841454934](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44841454934) — success
- Artifact ID: `14680448490`
- Artifact ZIP SHA-256: `76937e5881b7f32dc137a8546996374743c159b0744eca470983763d9b372ab9`
- Canonical history SHA-256 verified by workflow: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`
- Source rows: 10,887; structurally assigned Classic draws: 7,723; warmup: 800; common scored targets: 6,923 (contests 2163–12248).
- Universe: 98,280 combinations; fixed alpha: 200; same V322 partition trees and target sequence for every horizon.

The rolling FIFO preflights counters, removes the exact oldest draw, and maintains an exact count of observed combinations so an unseen set cannot be removed merely because it shares feature prefixes. The initial isolated test run exposed that latter edge case; it was fixed before the validated head. Isolated ORIGEN validation on the fixed head: **263 tests passed**.

## Results

All three rolling horizons produced negative mean log-lift against uniform. V322 expanding memory is shown as the existing comparison baseline; its scores were not reconstructed in this experiment.

| Model / memory | Mean log-lift | Median log-lift | Cumulative log-lift | Positive fraction | Expected top-100 inclusions | Exact rank-1 |
|---|---:|---:|---:|---:|---:|---:|
| V322 expanding | -0.005428 | -0.004788 | -37.5763 | 0.4752 | 7.0 | 0 |
| V324 rolling 400 | -0.006330 | -0.005718 | -43.8207 | 0.4759 | 6.0 | 0 |
| V324 rolling 800 | -0.007004 | -0.005722 | -48.4916 | 0.4749 | 7.0 | 0 |
| V324 rolling 1600 | -0.007065 | -0.004442 | -48.9121 | 0.4781 | 7.3 | 0 |

Uniform expected top-100 inclusions across 6,923 targets: **7.0442**. No model produced an exact rank-1 target.

Expected top-k inclusion totals (ties apportioned fractionally):

| Model | Top-1 | Top-5 | Top-10 | Top-30 | Top-100 |
|---|---:|---:|---:|---:|---:|
| Uniform expectation | 0.0704 | 0.3522 | 0.7044 | 2.1132 | 7.0442 |
| V322 expanding | 0.0 | 1.0 | 1.0 | 3.0 | 7.0 |
| V324 rolling 400 | 0.0 | 0.0 | 0.0 | 0.0 | 6.0 |
| V324 rolling 800 | 0.0 | 0.0 | 0.0 | 1.2 | 7.0 |
| V324 rolling 1600 | 0.0 | 0.0 | 0.1429 | 3.0 | 7.3 |

## Dependence-aware uncertainty

Circular moving-block bootstrap, 20,000 replicates, PCG64 seed 20261120, block lengths 7/14/28. The same chronological target rows were paired for each window against V322 expanding scores.

### 95% block-bootstrap intervals for mean log-lift

| Model | Block 7 | Block 14 | Block 28 |
|---|---:|---:|---:|
| V322 expanding | [-0.007558, -0.003322] | [-0.007546, -0.003299] | [-0.007540, -0.003305] |
| V324 rolling 400 | [-0.008727, -0.003951] | [-0.008769, -0.003943] | [-0.008651, -0.003963] |
| V324 rolling 800 | [-0.009347, -0.004620] | [-0.009342, -0.004690] | [-0.009285, -0.004725] |
| V324 rolling 1600 | [-0.009210, -0.004919] | [-0.009251, -0.004927] | [-0.009263, -0.004872] |

All intervals are below zero: the tested models underperform the uniform reference on average in this historical prequential replay.

### Paired difference: rolling minus V322 expanding

| Window | Mean difference | Block 7 95% CI | Block 14 95% CI | Block 28 95% CI |
|---|---:|---:|---:|---:|
| 400 | -0.000902 | [-0.003614, 0.001823] | [-0.003586, 0.001802] | [-0.003555, 0.001712] |
| 800 | -0.001577 | [-0.003947, 0.000760] | [-0.003902, 0.000739] | [-0.003882, 0.000682] |
| 1600 | -0.001637 | [-0.003450, 0.000143] | [-0.003428, 0.000169] | [-0.003446, 0.000134] |

No paired interval excludes zero. No rolling horizon demonstrates a reliable improvement over expanding memory.

## Decision

**Reject the rolling-memory hypothesis in its current form.** Window 400 is the least negative rolling variant, but remains worse than V322 expanding on the point estimate, its paired intervals cross zero, and its top-100 inclusion total is below uniform expectation. The 800/1600 windows are more negative. This is not a basis for choosing a production model or claiming a 5/5 capability.

This experiment is exploratory and retrospective: the candidate horizons were chosen after inspecting earlier V322/V323 diagnostics. These block intervals are descriptive and do not repair post-hoc selection or prove prospective performance. No multiplicity-adjusted confirmatory claim is made.

## Next falsifiable step

Do not continue tuning the window length on this same target sequence. The next useful experiment must freeze a candidate-generation protocol and emit, for every target, the full pre-target ranked portfolio (e.g. top 30 or 100 combinations) so that actual portfolio hit counts **3/5, 4/5 and 5/5** can be measured. Compare against uniform portfolios with identical line counts, use a chronologically untouched prospective stream, predeclare the full hypothesis family, and apply dependence-aware sequential evidence gates. Without a pre-close snapshot and independent custody, retrospective outputs remain research-only.

## Non-interference

V294 remains frozen. The canonical CSV was only read and its SHA-256 verified; no canonical append or mutation occurred. No write to `main`, no model promotion, and no production enablement. Classification remains `RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE` / `RESEARCH_ONLY_NO_EDGE`.
