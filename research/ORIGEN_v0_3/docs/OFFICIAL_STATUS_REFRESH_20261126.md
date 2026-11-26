# Official Chispazo source status refresh — 2026-11-26

**Review time:** 14:56:51 America/Mexico_City  
**Classification:** official public schedule/result records only. No draw-specific physical evidence obtained.

## Modality separation and contest-ID correction

The official Chispazo product page states two daily slots: **De las Tres at 15:00** and **Clásico at 21:00** local time.

A newly reviewed official Lotería Nacional result-mask PDF for **25-Nov-2026** explicitly labels:
- Contest **12395** as **Chispazo De las Tres**, numbers **01 13 19 23 28**.
- Contest **12396** as **Chispazo Clásico**, numbers **05 07 21 24 28**.

This resolves the modality of the two 25-Nov contests from the official PDF itself, rather than guessing from contest order or the results table.

For 26-Nov:
- The official commercializer home page shows a card titled **“Ilumina tu suerte”** with **26-Nov-2026, 15:00, Sorteo 12397**. The card text does not explicitly print the product name. Combined with the official product page's slot mapping, this is a **15:00 slot-level association** with De las Tres, not draw-specific modality proof. No result was published at the 14:56 review.
- The Chispazo product page confirms that **Clásico is scheduled daily at 21:00**, but the reviewed commercializer home-page snapshot does not identify a Chispazo contest ID for that slot.
- The separate 21:00 home-page card is labelled **“Sorteo | 3093”**. It is not labelled Chispazo and must not be assigned to Chispazo.
- No 26-Nov Classic contest ID is inferred from contest-number sequence or a nonofficial aggregator.

The official Chispazo results endpoint still displayed contest **12396**, dated 25-Nov-2026, as its latest result and showed 26-Nov as the next draw date. The 26-Nov results were not yet published at review.

## Procedure-derived physical record requirements

Lotería Nacional's public procedure **SGVO-PRO-05, revision 39**, was published on 20-Mar-2026. Its public PDF identifies the procedure as “Procedimiento Sorteos Electrónicos”. Relevant requirements include:

- Each draw's spheres are weighed individually and in numerical order in the presence of the SEGOB inspector and Lotería Nacional representatives.
- Smartballs: 4.25–5.25 g, with maximum set spread 0.30 g. Ping-pong spheres: 2.30–3.00 g, maximum set spread 0.15 g.
- Scales must be calibrated at least annually.
- The weighing strip is signed by the weighing representative and initialled by Lotería Nacional/SEGOB representatives, then attached to the act.
- The act must identify place, date, time, commissioned Lotería Nacional officials by name/role/signature, and the SEGOB inspector with commission order; incidents must be recorded.
- The recording covers the weighing through the electronic draw and is included with the act as documentary evidence.
- The SICAL sales-close summary and post-result summary are attached/reconciled as described by the procedure.
- The MJF is recorded to DVD every day after the 21:00 automatic sales close and deposited with its printed electronic-signature form. It is a daily-scope record, not a contest-only artifact; for a 15:00 De las Tres packet it can only be linked later, after 21:00, and must not be represented as available at the draw time.

These are published procedure requirements, not proof that a particular draw complied. No original signed act, pre-close SICAL summary, CS-11, signed weighing strip, calibration certificate, original recording, signed participation/cancellation files, or independent custody/time/ledger proofs were obtained for 26-Nov.

## Source ledger

- Chispazo product and daily schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Official result endpoint: https://www.loterianacional.gob.mx/Chispazo/Resultados
- Official results-publication timing FAQ: https://www.loterianacional.gob.mx/Nosotros/PreguntasFrecuentes
- Official commercializer home page: https://comercializadores.loterianacional.gob.mx/home/
- Official 25-Nov-2026 result-mask PDF: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-25.pdf?v=25112026221906
- Procedure SGVO-PRO-05 Rev.39: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SEGOB Inspection and Surveillance: https://www.juegosysorteos.gob.mx/es/Juegos_y_Sorteos/inspecciones_lotenal_pronosticos

The 25-Nov mask and SGVO-PRO-05 PDF were inspected through the public web text extraction. Their original bytes were not captured locally; no SHA-256 is claimed for either PDF. Machine-readable status is stored in `data/official-overlays/2026-11-26_public_web_status_only.json`.

## Non-promotion invariants

V294 remains frozen. The canonical historical CSV is not changed; its main-branch Git blob remains `2f5ff5bfbd779fe505736398e417b7211955958e`. This refresh does not append draws, establish physical provenance, alter any model, or change `BLOCKED / RESEARCH_ONLY_NO_EDGE`.


## Follow-up status snapshot — 2026-11-26 15:04 America/Mexico_City

- The official product page continues to map Chispazo De las Tres to 15:00 and Chispazo Clásico to 21:00.
- The official home index lists contest 12397 at 15:00. At 15:04, the dedicated official results page still showed 12396 (25-Nov-2026) as latest; 12397 had not yet appeared as a published result.
- The home index's separate 21:00 card is Sorteo 3093, not a Chispazo contest. The daily Classic 21:00 slot is confirmed by the product schedule, but its 26-Nov contest ID remains unconfirmed by the reviewed official index.
- New status-only snapshot: `data/official-overlays/2026-11-26_1504_public_status_only.json` (commit `d7063016622f1cb7079c3f1e029bf4d793f5ae37`). No original PDF bytes or draw-specific physical artifacts were obtained; no SHA-256 is claimed.
- This record is not a draw result, not a physical-evidence receipt, and is not eligible for the canonical history or prospective scoring.


## Follow-up status snapshot — 2026-11-26 15:54 America/Mexico_City

- The official commercializer home page shows a card titled **“Ilumina tu suerte”** with **26-Nov-2026, 15:00, Sorteo 12397**. The card text does not explicitly print the product name. Combined with the official Chispazo schedule, this is a **15:00 slot-level association** with De las Tres, not a draw-specific modality confirmation. Do not promote it to a confirmed Chispazo result solely from the card.
- The dedicated Chispazo results endpoint still showed contest **12396** (25-Nov-2026) as latest and did not yet publish contest 12397 at the 15:54 observation.
- Lotería Nacional's FAQ says afternoon results are normally updated between **16:30 and 17:00**. The absence of a published result at 15:54 is therefore not evidence of a failed draw and must not be filled with a guessed combination.
- The 21:00 **Clásico** draw for 26-Nov remains a separate future event. The home page separately shows **Sorteo 3093 at 21:00** without a Chispazo product label; it is not assigned to Chispazo and no Classic contest ID is inferred from it.
- No draw-specific primary physical records for contest 12397 were obtained: no signed Acta/CS-11, original weighing strip, SICAL close/post-draw summaries, pre-draw participation-signature media, video original, or SEGOB/OIC custody record. The public mask/result publication is a derived official result, not a substitute for those primary records.
- Source bytes for the 25-Nov official result-mask PDF and SGVO-PRO-05 remain **NOT_CAPTURED** in the working environment; no binary SHA-256 is asserted.
- No history append, physical eligibility upgrade, model change, V294 change, main write, merge or promotion occurred.
- Machine-readable snapshot: `research/ORIGEN_v0_3/data/official-overlays/2026-11-26_1554_public_status_only.json` (commit `7d32f24d13746702cf8f77f7669b85cae07d7c85`). It records source URLs, modality confidence, publication timing, missing primary records, and null binary hashes where original bytes were not captured.
