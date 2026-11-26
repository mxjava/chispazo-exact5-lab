# Official Chispazo source status refresh — 2026-11-26

**Review time:** 14:56:51 America/Mexico_City  
**Classification:** public web status only. No draw-specific physical evidence obtained.

## Modality separation and contest-ID correction

The official Chispazo product page states two daily slots: **De las Tres at 15:00** and **Clásico at 21:00** local time. This establishes the product schedule and modality mapping, not a contest ID for every slot.

The official results endpoint still displayed contest **12396**, dated 25-Nov-2026, with **05 07 21 24 28**, and contest 12395 dated 25-Nov with **01 13 19 23 28**. It showed 26-Nov as the next draw date but no 26-Nov result at review.

The official commercializer home page explicitly listed **Chispazo contest 12397 at 15:00 on 26-Nov**. Combined with the official product page's slot mapping, this is schedule-only evidence for **De las Tres**. No result was yet published at review.

**Correction to an earlier status overlay:** the same commercializer home page has a separate item at 21:00 labelled **“Sorteo | 3093”**. It is not labelled Chispazo and must not be assigned to Chispazo contest 12398. The product page confirms that Chispazo Clásico is scheduled daily at 21:00, but the reviewed home-page snapshot does **not** publish a Chispazo contest ID for that slot. Therefore:
- Contest 12397: schedule-only De las Tres 15:00; no result confirmed.
- Clásico 21:00 on 26-Nov: schedule-only; contest ID not independently confirmed in the reviewed index.
- Contest 12398: **not confirmed by the reviewed sources**; do not use it as a target identifier.

The result page's historical rows omit time/modality. A draw must not be classified from contest-number order alone.

## Procedure-derived physical record requirements

Lotería Nacional's public procedure **SGVO-PRO-05, revision 39**, was published on 20-Mar-2026. Its current public PDF path identifies the procedure as “Procedimiento Sorteos Electrónicos”. Relevant requirements include:

- Each draw's spheres are weighed individually and in numerical order in the presence of the SEGOB inspector and Lotería Nacional representatives.
- Smartballs: 4.25–5.25 g, with maximum set spread 0.30 g. Ping-pong spheres: 2.30–3.00 g, maximum set spread 0.15 g.
- Scales must be calibrated at least annually.
- The weighing strip is signed by the weighing representative and initialled by Lotería Nacional/SEGOB representatives, then attached to the act.
- The act must identify place, date, time, commissioned Lotería Nacional officials by name/role/signature, and the SEGOB inspector with commission order; incidents must be recorded.
- The recording covers the weighing through the electronic draw and is included with the act as documentary evidence.
- The SICAL sales-close summary and post-result summary are attached/reconciled as described by the procedure.

The PDF also describes the roles of the SEGOB inspector and Lotería Nacional representatives in verifying sales close, weighing, sphere placement, draw conduct and result entry. These are procedure requirements, not proof of compliance in a specific draw.

**No draw-specific physical evidence was obtained** for the 26-Nov De las Tres or the 21:00 Clásico slot: no original signed act, pre-close SICAL summary, CS-11, signed weighing strip, calibration certificate, original recording, signed participation/cancellation files, or independent custody/time/ledger proofs. The PDF bytes could not be captured locally, so no SHA-256 is claimed.

## Source ledger

- Chispazo product and daily schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Official result endpoint: https://www.loterianacional.gob.mx/Chispazo/Resultados
- Official commercializer home page: https://comercializadores.loterianacional.gob.mx/home/
- Procedure SGVO-PRO-05 Rev.39: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SEGOB Inspection and Surveillance: https://www.juegosysorteos.gob.mx/es/Juegos_y_Sorteos/inspecciones_lotenal_pronosticos

Machine-readable status is stored in `data/official-overlays/2026-11-26_public_web_status_only.json`. It contains no invented source-byte digest and makes no claim of physical authentication.

## Non-promotion invariants

V294 remains frozen. The canonical historical CSV is not changed; its main-branch Git blob remains `2f5ff5bfbd779fe505736398e417b7211955958e`. This refresh does not append draws, establish physical provenance, alter any model, or change `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
