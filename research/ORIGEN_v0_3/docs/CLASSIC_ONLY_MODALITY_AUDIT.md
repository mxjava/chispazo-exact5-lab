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
