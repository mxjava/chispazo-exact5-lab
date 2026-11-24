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
