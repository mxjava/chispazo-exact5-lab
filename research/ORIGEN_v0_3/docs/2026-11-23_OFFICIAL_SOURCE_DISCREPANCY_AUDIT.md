# Official Chispazo source discrepancy audit — 2026-11-23

## Purpose

Superseding clarification for the 2026-11-23 public-results refresh. This note records a live-source discrepancy and corrects any implication that a 2026-11-23 official mask PDF was available in the mask index.

## Observations from official public endpoints

- The dedicated official Chispazo results page currently publishes contest **12392**, dated 23/11/2026, with winning combination **06 11 16 23 28**. Its recent-results list also shows contest **12391 = 03 07 19 20 24**.
- The commercializer Chispazo results page currently publishes contest **12391 = 03 07 19 20 24**. This endpoint is stale relative to the dedicated page for contest 12392.
- The official Home/Resultados page snapshot returned by the current search still shows contest 12392 as blank, while the dedicated Chispazo results page publishes its combination. This is an endpoint freshness discrepancy, not evidence that the draw did not occur.
- The official home index places contest 12391 in the 15:00 slot and contest 12392 in the 21:00 slot. The official Chispazo schedule maps 15:00 to **De las Tres** and 21:00 to **Clásico**.
- The official Mascarillas index currently lists **RESULTADOS 2026-11-22** as its latest visible date. It does **not** currently list RESULTADOS 2026-11-23. Therefore, the earlier statement that the 2026-11-23 mask index/PDF was available is not supported by the current index response and is superseded by this audit.

## Source URLs

- Dedicated results: https://www.loterianacional.gob.mx/Chispazo/Resultados
- Commercializer results: https://comercializadores.loterianacional.gob.mx/Chispazo/Resultados
- Home results: https://www.loterianacional.gob.mx/Home/Resultados
- Official home index: https://www.loterianacional.gob.mx/home/index
- Chispazo schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Mask index: https://www.loterianacional.gob.mx/Mascarillas/Mascarillas

## Provenance and eligibility limits

This is a status-only public-source audit. Original HTML response bytes and any 2026-11-23 mask PDF bytes were not captured; no source-byte SHA-256 is claimed. No signed draw act, signed participation file, CS-11, 28-sphere weighing strip, scale calibration, machine-to-contest linkage, RFID trace, trusted timestamp, independent custody receipt, or two independent pre-close output seals were obtained.

Public result publication is not physical provenance and is not a pre-close prediction. Neither contest is made snapshot/OOS/score eligible by this note. The canonical history and V294 remain untouched. Production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**.

## Follow-up source recheck — 2026-11-23 23:55 America/Mexico_City

This is a later observation and supersedes the preceding statement that the mask index's latest visible date was 2026-11-22. On this recheck, the official Mascarillas index displayed **RESULTADOS 2026-11-23** and its link opened the official one-page PDF:

https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-23.pdf?v=23112026215757

The PDF text extraction contains both Chispazo contests and combinations:
- 12391: 03 07 19 20 24
- 12392: 06 11 16 23 28

The PDF extraction does not itself label the two Chispazo modalities. The official Chispazo product schedule states De las Tres at 15:00 and Clásico at 21:00; the official home index places 12391 in the 15:00 slot. The 12392 / 21:00 / Clásico assignment is therefore schedule-cross-referenced, not inferred from the PDF text alone.

The earlier 22-Nov-only observation is retained as a time-bounded snapshot; it must not be treated as the current index state after this recheck. The official results page, home index and PDF are public outcome records, not authenticated physical provenance.

The original PDF bytes were not captured into the repository or the working container, so no PDF SHA-256 is claimed. The PDF viewer's extracted text is not a byte-preserving capture. Original HTML bytes and a trusted capture timestamp were also not obtained.

SGVO-PRO-05 Rev. 39 remains the applicable public electronic-draw procedure reviewed here: policy 6 requires weighing for each draw; policy 9 specifies 15:00 for De las Tres and 21:00 for nocturnal draws; policy 11 identifies the Acta and Chispazo attachments including the sales-close summary, CS-11 winning numbers, post-draw summary and weighing strip. This procedural source does not establish that any of those draw-specific records were received for contest 12392.

No signed Acta, signed participation/cancellation file, CS-11 original, 28-sphere weighing strip, scale calibration certificate, machine-to-contest link, sphere-ID mapping, RFID trace, independent custody receipt, trusted timestamp or two independent pre-close output seals were obtained. Physical provenance and prospective eligibility remain **BLOCKED**.
