# Official Chispazo endpoint discrepancy — 2026-11-24

## Classification
Status-only reconciliation. Observation time was not captured, so this note records the displayed page state without claiming an exact retrieval timestamp. No result is admitted to the canonical historical CSV.

## What the official pages currently display
- The aggregate [Home/Resultados view](https://www.loterianacional.gob.mx/Home/Resultados?cluster=2&view=cG5sUmVzdWxTdXBlcmlvcg%3D%3D) displays contest **12393** dated 24-Nov-2026 with **01 07 08 09 12**. It also displays contest **12394** without winning numbers.
- The official [home index](https://www.loterianacional.gob.mx/home/index/) lists contest **12394** for 24-Nov at **21:00**.
- The official [Chispazo schedule](https://www.loterianacional.gob.mx/Chispazo/Chispazo) defines **De las Tres at 15:00** and **Clásico at 21:00**. Therefore 12393 is schedule-consistent with De las Tres, but this modality assignment remains an inference from the schedule and contest sequence, not a timestamp printed on the aggregate result card.
- The dedicated [Chispazo results page](https://www.loterianacional.gob.mx/Chispazo/Resultados) still shows **12392**, dated 23-Nov-2026, with **06 11 16 23 28** as its latest result.
- The [official mask index](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas) still lists **RESULTADOS 2026-11-23** as its newest document. No 24-Nov PDF was visible in the index.

## Interpretation and controls
This is a publication-lag/discrepancy across official public views, not a basis to overwrite the dedicated result page or assert physical provenance. Contest 12393 may be recorded only as an aggregate-portal observation, schedule-consistent with De las Tres. Contest 12394 remains the scheduled 21:00 Classic draw with no numbers visible in the observed pages.

No original 24-Nov mask PDF bytes or SHA-256 were captured. No Acta, CS-11, signed participation file, weighing strip, physical sphere measurements, calibration certificate, independent custody receipt, trusted timestamp, external ledger proof, or two sealed pre-close outputs were obtained.

## Research disposition
- Do not append either draw to the canonical historical CSV from this status-only observation.
- Do not score a prospective prediction from these pages.
- Do not infer a predictive edge.
- Preserve V294 unchanged.
- Production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**.

Machine-readable companion: `data/official-overlays/2026-11-24_official_portal_discrepancy_status_only.json`.
