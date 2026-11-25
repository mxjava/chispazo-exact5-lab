# Official Chispazo and Normateca status — 2026-11-25 14:55 America/Mexico_City

**Classification:** STATUS-ONLY / NO DRAW-SPECIFIC PHYSICAL EVIDENCE  
**Scope:** De las Tres (15:00) and Clásico (21:00), kept separate

## Current-day schedule and result status

The official Chispazo product page explicitly maps:
- Chispazo de las Tres — **15:00**.
- Chispazo Clásico — **21:00**.

At the 14:55 observation, the 15:00 event had not yet occurred. The official home index showed a card titled “Ilumina tu suerte” at 15:00 with contest **12395**, but the extracted card did not explicitly identify the product as Chispazo. It is therefore recorded as **schedule-inferred De las Tres only**, not result- or mask-confirmed.

The home index also displayed a separate 21:00 card numbered **4296**, without an explicit product label. It is not assigned to Chispazo. The 25-Nov Clásico contest ID remains unknown.

The dedicated Chispazo results page still showed contest 12394 (24-Nov-2026), **01 09 12 16 24**, as latest. The mask index still showed 24-Nov as the newest daily mask. Its visual labels confirm:
- 12393 — De las Tres — 01 07 08 09 12.
- 12394 — Clásico — 01 09 12 16 24.

The 24-Nov mask PDF was visually reviewed, but original PDF bytes were not captured; SHA-256 remains **NOT_CAPTURED**.

## Official procedure identity correction

The current **Normas Sustantivas Vigentes** index lists **PROCEDIMIENTO SORTEOS ELECTRÓNICOS**, emitted 01/10/2003 and last updated 20/03/2026, linking to `sgvo_pro_05.pdf`. That exact PDF is under `SUSTANTIVAS/VIGENTES`, identifies itself as **SGVO-PRO-05 revision 39**, and states publication date **20 MAR 2026**.

Do not conflate it with separate historical project files:
- `sgvo_pro_05p.pdf` — PROCEDIMIENTO SORTEOS ELECTRÓNICOS, consultation 23/02/2026–04/03/2026.
- `svo_p_05.pdf` — SORTEOS, consultation 19/09/2025–25/09/2025.

Revision 39 specifies:
- Smartballs: 4.25–5.25 g, maximum spread 0.30 g.
- Ping Pong: 2.30–3.00 g, maximum spread 0.15 g.
- Weighing is performed for each draw.
- The participation-file electronic signature is stored before the draw; the DTIT representative hands the device to the SEGOB inspector, who deposits it in the security box assigned for OIC access.
- The Chispazo Acta support matrix includes CLSBR140, CLIER195, CLSKR170, CLSAR110, Sumario, CS-11 and Tira de Pesaje.

The public procedure still does not disclose a public verification key, certificate chain, signature algorithm/parameters, canonical signed-byte format, revocation information or public verification vector. The procedure's “Firma Electrónica” cannot be treated as an Ed25519 signature or a public PKI trust anchor.

Original PDF bytes for revision 39 were not captured in the working container; SHA-256 remains **NOT_CAPTURED**.

## Evidence and integrity limits

No draw-specific physical records were obtained:
- signed Acta and annexes;
- CS-11;
- Sumario/cierre de venta;
- original Tira de Pesaje with all 28 readings;
- scale calibration certificate and traceability;
- machine, set and sphere identifiers;
- signed participation/cancellation archive and original signature sidecar;
- institutional verification material for the electronic signature;
- RFC 3161 token, external ledger inclusion/consistency proof, or independent custody receipt;
- two sealed pre-close outputs.

Public schedule, public result and public mask are not proof of independent physical provenance or a pre-close prospective snapshot.

## ORIGEN disposition

- Record 12395 as **schedule-inferred De las Tres only**; do not treat it as a result.
- Do not assign 4296 to Chispazo or assert a 25-Nov Classic contest ID.
- Do not append this status overlay to the canonical history, score a prospective target, or alter a model.
- V294 remains frozen; production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**.

## Official sources

- [Dedicated Chispazo results](https://www.loterianacional.gob.mx/Chispazo/Resultados)
- [Official results mask index](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas)
- [Official home index](https://www.loterianacional.gob.mx/home/index)
- [Chispazo product schedule](https://www.loterianacional.gob.mx/Chispazo/Chispazo)
- [Normas Sustantivas Vigentes](https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2)
- [Historical Proyectos Normativos](https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0)
- [Current SGVO-PRO-05 revision 39 PDF](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)
