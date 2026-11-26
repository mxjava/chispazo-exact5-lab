# Official Chispazo source status refresh — 2026-11-26

**Classification: public web status only. No draw-specific physical evidence obtained.**

## Modality separation

Lotería Nacional's official Chispazo product page states two daily slots: **De las Tres at 15:00** and **Clásico at 21:00** local time. The page is explicit about the modality/time mapping. Do not infer a draw's modality from contest-number order alone.

The official results page still displayed contest **12396**, dated 25-Nov-2026, with **05 07 21 24 28**, and contest 12395 dated 25-Nov with **01 13 19 23 28**. It displayed 26-Nov as the next draw date but did not show a 26-Nov result at review. The official commercializer home index listed contest **12398** at 21:00 on 26-Nov; the official home search-index snippet listed contest **12397** at 15:00. These are schedule records only, not winning-result evidence.

Consequently:
- Contest 12397: schedule-only De las Tres 15:00; no result confirmed in the results endpoint at review.
- Contest 12398: schedule-only Clásico 21:00; no result confirmed in the results endpoint at review.

The result page's historical rows do not state time/modality. Keep the time/modality inference separate from the result record until a draw-specific official mask/result record confirms it.

## Procedure-derived physical record requirements

The Lotería Nacional public procedure **SGVO-PRO-05, revision 39**, published 20-Mar-2026, identifies a concrete evidence chain:

- Each draw's spheres are weighed individually and in numerical order in the presence of the SEGOB inspector and Lotería Nacional representatives.
- Smartballs: 4.25–5.25 g, with maximum set spread 0.30 g. Ping-pong spheres: 2.30–3.00 g, maximum set spread 0.15 g.
- Scales must be calibrated at least annually.
- The weighing strip is signed by the weighing representative and initialled by Lotería Nacional/SEGOB representatives, then attached to the act.
- The act must identify place, date, time, commissioned Lotería Nacional officials by name/role/signature, and the SEGOB inspector with commission order; incidents must be recorded.
- The recording covers the weighing through the electronic draw and is included with the act as documentary evidence.
- The SICAL sales-close summary is generated after automatic close and before winning-number entry; it includes draw identity, date, close time and sales state/figures and receives the required initials.
- The post-result SICAL summary includes winning numbers, winner divisions and prize totals and is reconciled against the winner-selection system.

SEGOB's Dirección General de Juegos y Sorteos describes its Inspection and Surveillance area as responsible for attesting legality and transparency of draws conducted by institutions including Lotería Nacional. This establishes the published oversight role, not the identity or signature of the inspector for a particular draw.

**Important distinction:** these are procedure requirements and institutional role statements. They do not prove that the 26-Nov draws complied. This review did not obtain original draw acts, pre-close SICAL summaries, CS-11 records, signed weighing strips, calibration certificates, original recordings, signed participation/cancellation files, or independent custody/time/ledger proofs. The SGVO-PRO-05 PDF bytes were not captured locally, so no SHA-256 is claimed for that PDF.

## Source ledger

- Product and schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Official result endpoint: https://www.loterianacional.gob.mx/Chispazo/Resultados
- Official commercializer schedule index: https://comercializadores.loterianacional.gob.mx/
- Procedure SGVO-PRO-05 Rev.39: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SEGOB Inspection and Surveillance: https://www.juegosysorteos.gob.mx/es/Juegos_y_Sorteos/inspecciones_lotenal_pronosticos

Machine-readable status is stored in `data/official-overlays/2026-11-26_public_web_status_only.json`. It contains no invented source-byte digest and makes no claim of physical authentication.

## Non-promotion invariants

V294 remains frozen. The canonical historical CSV is not changed; its main-branch Git blob remains `2f5ff5bfbd779fe505736398e417b7211955958e`. This refresh does not append draws, establish physical provenance, alter any model, or change `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
