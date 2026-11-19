# V323 — Context-conditioned hierarchical partition result (2026-11-19)

Status: COMPLETED — NEGATIVE PREQUENTIAL LOG-SCORE — NO PREDICTIVE EDGE — RESEARCH ONLY.

## Provenance and execution

- Preregistration: `research/ORIGEN_v0_3/PREREGISTRATION_V323_CONTEXT_PARTITION.md`.
- Implementation: `src/origen/v323_context_partition.py`.
- Tests: `tests/test_v323_context_partition.py`.
- Executed commit: `8a8c30de1aacda4b7ebf2aa4b367c806da207f6f`.
- Dedicated GitHub Actions run: [44585896389](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44585896389) — success.
- Artifact: `exact5-v323-context-partition`, ID `14560344260`.
- Artifact ZIP SHA-256: `337998a74a464f474534bf0c497b6a10b8dc9593243c720d2a5d74041a0918e7`.
- Per-target CSV SHA-256: `af6fd17c934c56a4ce7a6eba9d282605bae744f67dda4cf2c545eaa74648a815`.
- Canonical source SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.

## Frozen model

- 98,280 unordered five-number combinations.
- Three independent copies of the fixed V322 hierarchical partition model; alpha=200 and equal three-tree mixture unchanged.
- Each target's context is the mean overlap between consecutive pairs in its preceding 20 structurally assigned Classic draws.
- LOW_REPEAT: mean < 0.75; TYPICAL_REPEAT: 0.75–1.05 inclusive; HIGH_REPEAT: >1.05.
- First 800 Classic targets are warmup; models are primed only with prior-context labels.
- Each of the 6,923 later targets is scored before it updates only its own regime model.
- Empty regime uses the exact uniform PMF.
- No threshold search, parameter sweep, or V294 modification.

## Overall results

- Classic history: 7,723 draws, contests 1363–12248.
- Scored targets: 6,923, contests 2163–12248.
- Mean log-lift vs exact uniform: **-0.0053313444 nats**.
- Median log-lift: **-0.0043784869 nats**.
- Cumulative log-lift: **-36.90889705 nats**.
- Positive log-lift fraction: **47.9272%**.
- Exact rank-1 winning combinations: **0 of 6,923**.

| Tie-aware ranking | V323 expected inclusions | Uniform expected inclusions |
|---|---:|---:|
| Top 1 | 0 | 0.0704 |
| Top 5 | 0 | 0.3522 |
| Top 10 | 0 | 0.7044 |
| Top 30 | 1.5 | 2.1132 |
| Top 100 | 8 | 7.0442 |

## Regime results

| Regime | Targets | Mean log-lift | Cumulative log-lift |
|---|---:|---:|---:|
| LOW_REPEAT | 1,533 | -0.00491158 | -7.52945 |
| TYPICAL_REPEAT | 3,738 | -0.00488380 | -18.25564 |
| HIGH_REPEAT | 1,652 | -0.00673354 | -11.12380 |

All three regimes have negative mean log-lift. No regime provides evidence of a predictive subgroup. Do not select a regime or adjust boundaries after observing these results.

## Comparison with V322

V322 mean log-lift was -0.0054277528; V323 was -0.0053313444, a small numerical difference of +0.0000964085 nats per target. This is not a demonstrated improvement: both are negative, V323 had zero expected top-5/top-10 inclusions and fewer top-30 inclusions than uniform expectation, and no target was ranked first. The small mean difference is descriptive only and has no independent significance test.

## Decision

`NO_EDGE_EVIDENCE`. V323 is closed as a completed negative result. The tested recent-overlap regime does not rescue the static hierarchical partition. Do not retune the thresholds or choose the best subgroup on this same history. Do not use V323 for betting combinations.

This replay is retrospective prequential reconstruction, not an authenticated historical pre-close forecast. Structural modality labels remain pending row-level official verification. Prospective edge certification still requires >=100 untouched consecutive Classic draws, two independently sealed pre-close outputs, complete provenance, positive preregistered lift, Holm p<0.05 and Exact5 anytime e-value >=20.

## Non-interference

- V294 remains frozen.
- Canonical history remains byte-for-byte unchanged.
- No writes to `main`, no merge and no model promotion.
- V323 remains isolated research only.
