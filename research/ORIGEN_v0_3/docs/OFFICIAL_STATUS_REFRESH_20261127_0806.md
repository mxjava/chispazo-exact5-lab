# Official Chispazo status refresh — 2026-11-27 08:06:26 America/Mexico_City

## Classification

Status-only capture of current Lotería Nacional pages and the 26-Nov-2026 results mask. The mask is an official publication artefact, but it is not the signed Acta and does not establish physical provenance. No canonical history update or prospective score is authorized.

## 1. New official mask observation

The official [Mascarillas index](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas) now lists **RESULTADOS 2026-11-26**. Its linked one-page PDF is:

https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-26.pdf?v=26112026215226

Visual review of page 1 directly identifies both Chispazo modalities:

| Modality printed on mask | Contest | Winning numbers |
|---|---:|---|
| Chispazo De las Tres | 12397 | 05 20 23 26 28 |
| Chispazo Clásico | 12398 | 01 03 17 26 28 |

This resolves the prior 26-Nov modality ambiguity: **12398 is directly labelled Clásico on the mask**, not merely inferred from the 21:00 schedule. The product page independently states De las Tres at 15:00 and Clásico at 21:00: https://www.loterianacional.gob.mx/Chispazo/Chispazo

The dedicated results page on `www.loterianacional.gob.mx` now displays 12398 as its latest result and shows 12397 immediately before it:
https://www.loterianacional.gob.mx/Chispazo/Resultados

The legacy alias `lotenal.gob.mx` still displays 12397 as latest:
https://lotenal.gob.mx/Chispazo/Resultados

That alias lag is preserved as a source observation; it is not used to override the primary host or the directly labelled official mask.

## 2. Next draw schedule observed

The official home index captured at 08:06 local on 27-Nov shows Chispazo contest **12399** at **15:00**, consistent with De las Tres. The same capture did not identify a 21:00 Chispazo Clásico contest ID. Do not infer or manufacture that ID from sequence arithmetic.

Source: https://www.loterianacional.gob.mx/home/index

## 3. Legal and evidentiary status

The official [Reglamento del Concurso Chispazo](https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf) states in Article 8 that the winning results recorded in the Article 15 Acta are official; website and results-mask publications are informational only. Article 15 requires the Acta to be prepared after the ceremony with the SEGOB-designated inspector and designated officials, who intervene and sign it.

Therefore the 26-Nov mask is valuable discovery/publication evidence and resolves the modality labels, but it is **not** a substitute for:
- signed Acta and its attachments;
- closing and draw summaries, CS-11 and the complete weighing strip;
- 28 sphere measurements, scale identity/calibration and equipment/sphere-set mapping;
- participation-file signature, OIC deposit/custody records and relevant recordings;
- independently verified custody, trusted timestamps and external ledger/witness proofs.

## 4. Byte-capture limitation

The PDF was inspected through the official web-rendered page and its visible labels. The original PDF bytes could not be downloaded into the execution environment in this cycle. Accordingly:
- `original_pdf_bytes_captured = false`;
- `original_pdf_sha256 = NOT_CAPTURED`.

No digest is invented. The screenshot/rendered view is not represented as the original PDF byte stream.

## 5. ORIGEN disposition

- Status overlay: `data/official-overlays/2026-11-27_0806_official_status_only.json`.
- No signed Acta or complete physical evidence package was obtained.
- No pre-close snapshot or two sealed pre-close outputs were established by this status capture.
- No prospective score was computed.
- The canonical historical CSV was not modified.
- V294 remains frozen.
- `main` was not modified.
- Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

The mask publication must not be appended as an authenticated draw result. Continue seeking the signed Acta and underlying evidence from the responsible institutional custodian.
