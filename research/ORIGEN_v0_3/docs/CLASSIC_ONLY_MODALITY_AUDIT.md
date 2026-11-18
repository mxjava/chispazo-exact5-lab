# Research lead: isolate Chispazo Clásico from De las Tres

**Status:** high-priority unresolved data-definition issue; hypothesis only, not evidence of predictive edge.

## Why this matters

The official Lotería Nacional Chispazo page states that two separate draws are held daily:
- Chispazo de las Tres (15:00)
- Chispazo Clásico (21:00)

The canonical file `data/history/Chispazo_through_12249.csv` contains consecutive contest IDs and two records per date in its recent section, but it has no explicit draw-type column. For example, contests 12247 and 12248 are both dated 2026-09-12, and 12249 is dated 2026-09-13. Recent independently published result listings identify 12379 (2026-11-17) as De las Tres and 12380 as Clásico. This is consistent with odd/even contest parity separating draw types in the recent data, but parity must be verified across the entire historical period before it is used as a classifier.

Official source: https://loterianacional.gob.mx/Chispazo/Chispazo
Official result examples: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-15.pdf?v=15112026221353

## Why existing evaluations may not answer the Classic-only question

The V264 reports cover contests 1363–12249 as one chronological stream. V265's physical regime scanner also loads the full CSV without a game-type filter; its `same_day_pairs` helper pairs two draws by date and models the earlier one as context for the later one. The scanner therefore needs an explicit modality audit before its temporal/same-day outputs can be interpreted as Classic-only evidence.

Mixing both daily modalities can:
1. Make the immediately preceding row a De las Tres result when the target is Clásico (and vice versa).
2. Change weekday/lag/gap features from "previous Classic draw" to "previous draw of either modality".
3. Double the apparent sample size while halving the number of observations from the target modality.
4. Distort same-day pair tests if they are interpreted as same-process transitions without a predeclared mechanism.

This does **not** prove the pooled V264 null result would become positive after filtering. It means the pooled result is not a direct test of the correctly isolated Classic-only temporal hypothesis.

## Required experiment (research branch only)

1. Preserve the canonical CSV byte-for-byte. Do not add a game-type column to it.
2. Build a derived, fully reproducible view with columns: contest, date, draw_type, five numbers, source/derivation rule, and audit status.
3. Do not assume contest parity globally. Verify mapping against official Lotería Nacional result records across multiple eras and detect any numbering reset, skipped draw, schedule change, or exception. Quarantine uncertain rows.
4. Once mapping is independently verified, construct:
   - Classic-only series;
   - De las Tres-only control series;
   - pooled series retained solely as a comparison.
5. Re-run only the relevant temporal families on each stream using chronological prequential scoring, identical warm-up policy, identical candidate family, and separate multiplicity accounting. The target for Classic must use the previous **Classic** result, never merely the previous contest ID.
6. Compare each series to its own uniform 5-of-28 null. Report sample counts, missing/ambiguous contests, log-score lift, e-values, calibration, and portfolio hit distribution.
7. Use an untouched prospective Classic-only sequence for confirmation. No retuning after inspecting its outcomes.

## Falsifiable predictions

- If interleaving is materially harmful, Classic-only lagged features should improve out-of-sample log score versus both the pooled-stream version and uniform baseline, not merely retrospective fit.
- If not, Classic-only performance should remain at or below the uniform null; the modality split then closes this lead without claiming a predictive edge.
- A signal that appears only in one modality but fails multiplicity correction or untouched prospective validation is not accepted.

## Guardrails

- V294 remains frozen and unchanged. Any Classic-only variant is a separately named research challenger.
- Canonical history remains unchanged and its known Git blob is `2f5ff5bfbd779fe505736398e417b7211955958e`.
- No writes to `main`, no model promotion, no prediction claim.
- Do not reuse the same-day pairing as evidence until draw types and time ordering are independently verified.
- Classification at this stage: `BLOCKED_PROVENANCE` for modality-specific conclusions; no evidence of predictive edge has been established.

## Existing code paths requiring audit

- `src/v264/CHISPAZO_V264_EXACTSET_ANYTIME.py`
- `src/v264/CHISPAZO_V264_EVIDENCE_FIREWALL.py`
- `src/v265/CHISPAZO_V265_PHYSICAL_REGIME_SCANNER.py`
- `research/ORIGEN_v0_3/src/origen/exact5_adapter.py`

The ORIGEN adapter must not silently infer draw type from parity. It should accept only a verified, versioned mapping artifact with provenance and explicit ambiguous-row handling.

## Verified reconstruction and first diagnostic (2026-11-18)

The canonical file was parsed without modification: 10,887 unique contiguous contests (1363–12249), zero invalid draws, and the canonical Git blob remained `2f5ff5bfbd779fe505736398e417b7211955958e`.

The date structure is exact under the transition rule:
- 4,560 single-draw dates before the transition, contests 1363–5922.
- Transition begins at contest 5923 on 2017-09-25.
- 3,163 complete post-transition dates, each containing an odd/even consecutive pair.
- The final source date is partial: contest 12249 only, because the canonical file ends there.
- No date-structure anomalies under this mapping.
- Derived counts: 7,723 Classic rows and 3,164 De las Tres rows.

This mapping is supported by the institutional accountability report stating that the second daily Chispazo draw was introduced on 2017-09-25, and an official 2017-11-02 result sheet explicitly labels 5999 De las Tres and 6000 Clásico. It is still marked as structurally derived rather than independently verified row-by-row against primary records for every contest.

### First controlled comparison: fixed marginal-frequency model

A fixed expanding-window smoothed marginal-frequency diagnostic was scored on the same 6,923 Classic targets after an 800-Classic-draw warm-up, with alpha=200 and uniform 5-of-28 log probability as baseline.

| Training stream | Mean log-lift | Cumulative log-lift | Positive target fraction |
|---|---:|---:|---:|
| Classic-only prior draws | -0.00416720 | -28.84953 | 47.83% |
| Pooled prior draws, scored on same Classic targets | -0.00383395 | -26.54241 | 47.20% |

The paired mean difference (Classic-only minus pooled) was -0.00033325 nats per target. **This does not show a benefit from filtering for this fixed marginal model; both versions underperformed uniform.** It is exploratory retrospective scoring, not an e-value, p-value, multiplicity-adjusted finding, or prospective validation.

Reproducible implementation: `research/ORIGEN_v0_3/src/origen/exact5_modalities.py`.
Recorded result: `reports/CLASSIC_MODALITY_PREQUENTIAL_DIAGNOSTIC_20261118.json`.
Tests: `research/ORIGEN_v0_3/tests/test_exact5_modalities.py`.

### Next experiment

Re-run the V264 temporal transition family on the Classic-only series with the lag defined as the previous Classic contest, and compare it against the pooled-stream version on identical Classic target dates. Keep all original model parameters fixed; no retuning after seeing the Classic-only result. The untouched prospective sequence remains sealed.

### Second controlled comparison: corrected V264 transition expert

The same 6,923 Classic targets were also scored with the fixed V264 transition expert (`beta=0.15), warm-up 800). The historical loop uses the leakage correction `range(start, t-1)`, excluding the current context draw from historical successor counts.

| Training stream | Mean log-lift | Cumulative log-lift | Positive target fraction |
|---|---:|---:|---:|
| Classic-only sequence | -0.04903262 | -339.45282 | 44.65% |
| Pooled sequence, same Classic targets | -0.04384260 | -303.52229 | 44.46% |

Paired mean difference (Classic-only minus pooled): -0.00519002 nats per target. Both variants are strongly negative; Classic-only is worse. This is a single fixed expert, not the full V264 Bayesian mixture, and it is not multiplicity-adjusted or prospective. It does, however, falsify the simple claim that isolating Classic alone rescues this transition expert.

The canonical audit and all 47 isolated ORIGEN tests passed in GitHub Actions. The canonical audit produced and uploaded a reproducible CSV modality map and JSON report as the `exact5-classic-modality-audit` workflow artifact.
