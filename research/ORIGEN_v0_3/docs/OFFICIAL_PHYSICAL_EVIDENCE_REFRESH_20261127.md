# Official physical-evidence refresh — 2026-11-27

## New official publication reviewed

Lotería Nacional's official one-page result mask for Thursday 26-Nov-2026 is published at:

- [Official daily mask PDF](https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-26.pdf?v=26112026215226)
- [Official Chispazo product page and schedule](https://loterianacional.gob.mx/Chispazo/Chispazo)

Visual inspection of page 1 confirms two distinct Chispazo blocks with modality logos:

| Contest | Modality printed on mask | Winning numbers | Time established by product page |
|---|---|---|---|
| 12397 | Chispazo De las Tres | 05 20 23 26 28 | 15:00 |
| 12398 | Chispazo Clásico | 01 03 17 26 28 | 21:00 |

This is stronger than schedule-only inference: the PDF itself labels each draw's modality. The product page independently defines De las Tres as 15:00 and Clásico as 21:00. The official results page separately reports contest 12398 as 26-Nov-2026 with 01 03 17 26 28 and six first-prize winners.

## Byte provenance limitation

The PDF was retrieved and visually inspected through the official public web publication, but the available binary download path failed. Therefore:
- Original PDF bytes are **NOT_CAPTURED**.
- SHA-256 is **NOT_CAPTURED**.
- The URL's `v=26112026215226` parameter is a publication/cache version marker, not a cryptographic digest.
- No original PDF is stored in this repository by this overlay.

The structured status-only record is in `data/official-overlays/2026-11-26_official_mask_status_only.json`. It is not an original signed result artifact.

## New authoritative procedure baseline

Lotería Nacional publicly exposes `SGVO-PRO-05 — Procedimiento Sorteos Electrónicos`, Revision 39, 38 pages, published 20-Mar-2026:

- [Official procedure PDF](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)

Relevant requirements visible in the published procedure:

1. **Per-draw weighing:** each sphere is weighed one by one and in numeric order in the presence of the SEGOB inspector and Lotería Nacional representatives. The weighing strip is the named record.
2. **Weight limits:** Ping Pong 2.30–3.00 g with maximum spread 0.15 g; Smartballs 4.25–5.25 g with maximum spread 0.30 g. A nonconforming set is replaced and reweighed.
3. **Weighing-strip signatures and attachment:** the responsible operator signs the strip; the SGVO representative, SEGOB inspector and Dirección General representative review/rubric it; the strip is delivered to be annexed to the corresponding Acta.
4. **CS-11 winning-number record:** the numbers are checked against the displayed spheres, read aloud before the representatives and SEGOB inspector, signed, and issued in four copies. The original goes to the SGVO representative for the Acta; copies go to SEGOB and IT.
5. **Acta contents:** place, date, time, names/roles/signatures of commissioned Lotería Nacional officials, and inspector name/signature/commission number; the winner report is attached. For Chispazo, the procedure's annex matrix also lists the sale-close summary, CS-11, draw summary and weighing strip as Acta attachments.
6. **Electronic participation-file custody:** the participation-file electronic signature is recorded to storage before the draw, delivered to the SEGOB inspector and deposited in a safe whose access is assigned to the Órgano Interno de Control.
7. **Scale calibration:** the procedure says scales used for sphere weighing must be calibrated at least annually.

### Procedure cross-reference anomaly

The document's policy 6 contains the sphere-weighing specifications, while activity 5.2 refers to “Política número 8” when checking the weighing strip. Policy 8, in the same document, concerns the electronic signature of the participation file. This is an internal cross-reference inconsistency in the published procedure. Do not silently normalize it in code; retain the quoted requirements and seek institutional clarification before treating the cross-reference as resolved.

## What this does not establish

The public mask confirms published draw results and explicit modality labels. It does not establish that we possess the signed Acta, actual weighing strip, CS-11, CS-02 inspection record, current scale calibration certificate, signed participation file, original video, or independent custody for either draw. No physical sphere-to-number mapping artifact was acquired.

The next evidence target is not another copy of the public result page: it is a draw-specific, signed Acta with its named attachments, plus original participation-file/signature evidence and the underlying per-draw weighing and inspection records. Acquisition must preserve original bytes, signer identity/authority, timestamps and independent custody.

## Safety

Status-only research overlay. No canonical history append, no predictor/model changes, V294 unchanged, no main write or merge. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.


## Same-day official publication check — 2026-11-27 09:56:45 America/Mexico_City

A fresh check of the official results page, home index, Chispazo product page, and
mask index found no 27-Nov result mask or published result at capture:

- The dedicated results page still showed contest **12398**, dated 26-Nov-2026,
  with **01 03 17 26 28**; it displayed 27-Nov as the next draw date.
- The official home index listed contest **12399** for 27-Nov at **15:00**.
- The official Chispazo product page continues to map **15:00 to De las Tres**
  and **21:00 to Clásico**. The 21:00 contest ID was not established by this
  capture and is deliberately left unassigned.
- The official mask index listed 26-Nov as its newest visible result mask; no
  27-Nov mask was visible.

Status-only overlay:
`data/official-overlays/2026-11-27_0956_official_status_only.json`.

This is a publication-state observation, not new physical evidence. No original
27-Nov PDF bytes or SHA-256 were captured. No signed Acta, CS-11, weighing
strip, CS-02, calibration certificate, signed participation file, original
video, RFC 3161 token, external ledger proof, or independent custody record was
obtained. Do not infer the 21:00 contest ID from sequence order.

