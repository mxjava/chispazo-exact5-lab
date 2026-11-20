# Run127 — official endpoint freshness discrepancy

**Capture:** 2026-11-20 03:16:37 America/Mexico_City  
**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Directly observed

- The dedicated Chispazo results page publishes 12384, dated 19-Nov-2026, Clásico, `01 02 09 21 25`, and only says the next draw date is 20/11. It does not identify 12385 on that page.
- The official Mascarillas index still lists 19-Nov-2026 as its newest date; no 20-Nov mask is listed.
- The official Chispazo information page confirms De las Tres at 15:00 and Clásico at 21:00, but not the 20-Nov Clásico contest ID.
- A search-index snippet for the official commercializer homepage reports 12385 at 15:00 on 20-Nov. However, opening the commercializer homepage directly returns stale content dated 12-Oct-2026 and does not corroborate that schedule entry.
- The separate Home/Resultados extraction still leaves 12384's number field blank, while the dedicated Chispazo page publishes the combination.

## Classification

Treat **12385 / 20-Nov / 15:00 / De las Tres as provisional**, supported by an official search-index snippet but not corroborated by the direct current commercializer page or a daily mask. Do not use it as an authenticated target or append it to canonical history. The 20-Nov Clásico contest ID remains unknown.

No 20-Nov result or mask was available at capture. No raw PDF bytes, source hash, independent custody, pre-close snapshot, or OOS score was obtained. V294 remains frozen; canonical blob identity is unchanged; no main write, merge, promotion, tuning, or scoring occurred.

Sources: [dedicated Chispazo results](https://www.loterianacional.gob.mx/Chispazo/Resultados), [official mask index](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas), [official Chispazo schedule](https://www.loterianacional.gob.mx/Chispazo/Chispazo), [commercializer homepage](https://comercializadores.loterianacional.gob.mx/).
