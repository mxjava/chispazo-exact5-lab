# Exact5 Run123 — official result and physical-timing audit

**Captured:** 2026-11-20 00:57:32 America/Mexico_City  
**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`  
**Scope:** read-only official-source review, temporal feasibility audit, and isolated documentation only.

## 1. Preservation

- V294 remains FROZEN; no parameter, challenger, or candidate changes.
- No write to `main`, no merge, no promotion.
- Canonical history remains untouched. Blob observed on both `main` and the Run121 research branch: `2f5ff5bfbd779fe505736398e417b7211955958e`.
- Expected canonical SHA-256 remains `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`; this run verified Git blob identity, not a fresh SHA-256 over downloaded CSV bytes.
- `main` head observed by GitHub compare: `424eee9dd906f8235541e97ae61026441083bbfe`.
- No historical PMF/rank/score rebuild; no OOS target scored.

## 2. Official Chispazo results and next scheduled draw

The official daily mask for 19-Nov-2026 is linked from the live Mascarillas index. Its PDF text identifies:

| Contest | Date | Modality | Numbers |
|---|---|---|---|
| 12383 | 19-Nov-2026 | De las Tres | 01 03 08 27 28 |
| 12384 | 19-Nov-2026 | Clásico | 01 02 09 21 25 |

The Clásico result page reports 1 first-tier winner, 216 second-tier, 5,675 third-tier and 44,074 fourth-tier winners (49,966 total).

Sources:
- Results page: https://comercializadores.loterianacional.gob.mx/Chispazo/Resultados
- Live mask index: https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- Daily mask PDF: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-19.pdf?v=19112026215833
- Official schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Commercializer home schedule: https://comercializadores.loterianacional.gob.mx/

At capture, the official commercializer home listed **contest 12385, 20-Nov-2026, 15:00**. The official Chispazo schedule defines 15:00 as De las Tres and 21:00 as Clásico. Contest 12385 had not yet occurred at capture. The 20-Nov Clásico contest ID was not established; do not infer it by parity or sequence.

### Endpoint freshness discrepancies

- The opened live Mascarillas page listed 19-Nov as its latest date; one search-index snippet still showed 18-Nov.
- The dedicated commercializer Chispazo results page and the 19-Nov daily mask agree on 12384. The separate Lotería Nacional Home/Resultados extraction still showed the 12384 number field blank. Treat the dedicated result page plus daily mask as the corroborated result; preserve the stale home-page discrepancy rather than silently filling it.
- The daily PDF was readable through official web extraction, but a raw-byte download attempt failed. Original PDF SHA-256 is **NOT_CAPTURED**; no independent forensic custody is claimed.

## 3. Critical finding: V317's same-draw pre-close timing requirement conflicts with the published operating sequence

The current public procedure is **SGVO-PRO-05, Procedimiento Sorteos Electrónicos, revision 39**, published 20-Mar-2026:
https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

Its activity sequence is explicit:

1. The process section is headed **Cierre de Venta**; activity 4.1 verifies that the SICAL sale state is `Cerrado`.
2. The next section is **Pesaje y Colocación de las Esferas**; activity 5.1 then weighs spheres one by one in numerical order.
3. Activities 5.4–5.5 sign/review the weighing strip and attach it to the Act; 5.6 places the spheres into the feeders.
4. Annex 1 says the electronic signature for the participation file is generated immediately after automatic sales closure.

The procedure's policy 9 also gives 15:00 for De las Tres and 21:00 for nocturnal sales closure. The published order therefore places the same-contest weighing after sales closure, not before it.

### Consequence for the existing V317 specification

The frozen V317 preregistration asks for the mass vector and physical-number mapping for contest t to be authenticated before contest t's sales close. The existing intake validator enforces:
- `set_assigned_at < draw_close_at`
- `measurement_at < draw_close_at`
- `mapping_valid_from < draw_close_at`

Under the published process, the ordinary same-draw weighing strip cannot satisfy the same-draw pre-close feature rule. A record timestamped before the draw but after sales close is **not** a pre-close predictor. The after-close participation-file signature/custody step is likewise not evidence that the file existed before sales close.

**Classification:** `MODEL_IMPLEMENTATION_DEFECT` for the current V317 temporal contract/eligibility assumption, plus `BLOCKED_PROVENANCE` because no primary records have been received. This is a protocol-feasibility defect, not evidence of misconduct or a physical bias.

No V317 code, beta, challenger, or preregistration was changed in this run. Do not weaken the pre-close gate to admit post-close measurements.

A future, separately versioned hypothesis could only use prior-draw masses for a later contest if primary records prove that the same physical spheres, printed-number mapping, case and relevant equipment persisted and were known before the later contest's close. Every replacement, remap, reweigh and equipment change would need a timestamped event chain. That would be a new preregistered question, not a retrospective repair of V317.

## 4. Additional document-control inconsistency

In SGVO-PRO-05 revision 39, activity 5.2 and the quality-plan weighing check refer to “Política número 8” for weight parameters. The actual weight limits are in policy 6; policy 8 concerns the electronic signature and custody of the participation file. This is an internal cross-reference inconsistency. It does not prove that weighing was performed incorrectly. The request draft should ask Lotería Nacional to clarify the intended reference and identify any corrected/current version.

## 5. SGVO-MAN-02 project document: corroborative only, not treated as governing

The Normateca project list includes `sgvo_man_02p.pdf`, titled *Manual de Apoyo para la Operación de Sorteos y Equipos Electrónicos*. The PDF itself is marked `TIPO: RESERVADO`, revision 09, dated June 2011, and is listed as a 23-Feb to 04-Mar-2026 project item. It describes individual sphere weights, printed date/time and statistics, and says weighing is preferably after sales close. Because it is a project-list document marked reserved, this run does **not** treat it as the currently operative approved manual. Request the currently authorized version/status and use SGVO-PRO-05 revision 39 as the public governing procedure.

Project list: https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0  
Project PDF: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/PROYECTO/sgvo_man_02p.pdf

## 6. Intake request and evidence still missing

The existing v3 request is already in the Run121 research branch:
- Path: `research/ORIGEN_v0_3/docs/SOLICITUD_TRANSPARENCIA_TRAZABILIDAD_FISICA_V3_20261119.md`
- Blob: `048205947927ed3b1287007ff44692e6e72288dc`
- Status: draft only; not submitted.

A v4 draft is added alongside this report. It preserves the non-presumption of bias and adds:
- exact timestamps for automatic sales closure, every sphere measurement (if individually timestamped), strip print/signature, feeder loading and draw start;
- explicit confirmation whether any sphere/set assignment or mass record is genuinely available before sales close;
- the currently authorized SGVO-MAN-02 version/status;
- clarification of the policy-8/policy-6 cross-reference;
- the CS-11, Act, weighing strip, calibration, set/machine, mapping, replacement/reweigh, archive, CS-12 and CS-18 record chain.

Still absent: authentic per-draw 28-sphere masses, physical-sphere-to-number mapping, scale calibration evidence, pre-close assignment evidence, independent beta calibration, raw official PDF bytes and independent custody. No V317 empirical test or real OOS score was run.

## 7. Final classification

- V317 same-draw pre-close timing contract: `MODEL_IMPLEMENTATION_DEFECT`.
- Physical mechanism evidence: `BLOCKED_PROVENANCE`.
- Predictive edge: `NO_EDGE_EVIDENCE`.
- Production: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

Run53–56 and all previously closed runs remain closed. Run99 remains unchanged. V294 and the canonical history remain protected.
