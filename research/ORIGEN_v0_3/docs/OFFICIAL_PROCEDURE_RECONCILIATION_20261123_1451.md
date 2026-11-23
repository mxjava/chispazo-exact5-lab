# Official procedure reconciliation — Chispazo electronic draws — 23-Nov-2026 14:51 America/Mexico_City

## Scope and source authority

This note reconciles ORIGEN's physical-intake assumptions against the official Lotería Nacional Normateca as observed on 23-Nov-2026. It is a public procedural-source review, not a draw-specific evidence receipt.

The Normateca's **Normas Sustantivas Vigentes** table identifies:
- **SGVO-PRO-05 — Procedimiento Sorteos Electrónicos**, last updated 20-Mar-2026; the linked 38-page PDF identifies revision 39 and DN-07 Version 09.
- **SGVO-PRO-34 — Procedimiento para la verificación de peso y diámetro de las bolas de madera de números y premios, distribución del boleo, armado y revisión de ábacos**, last updated 20-Mar-2026; the linked 16-page PDF identifies revision 01.

Official sources:
- Normateca vigente: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-05 Rev. 39: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SGVO-PRO-34 Rev. 01: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_34.pdf
- Chispazo schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo

## Directly relevant electronic-draw requirements (SGVO-PRO-05 Rev. 39)

The following are the requirements visible in the official PDF:

1. **Per-draw weighing** — policy 6 says sphere weighing is performed for each draw. It identifies:
   - Smartballs: 4.25–5.25 g per sphere; max difference between lightest and heaviest 0.30 g.
   - Ping Pong: 2.30–3.00 g per sphere; max difference 0.15 g.
   - If any condition fails, another sphere case is selected and weighed again.
2. **Responsible observers** — policy 7 names the SEGOB inspector, the Dirección General representative and the Subdirección General de Ventas y Operaciones representative for verifying sales close, weighing, loading spheres into the machine, the draw and entry of winning numbers into SICAL. The IT/Telecommunications representative also verifies sales close, draw and SICAL entry.
3. **Pre-draw participation-file seal/custody** — policy 8 says the electronic signature of the participation file is written to a storage device before the draw; IT delivers it to the SEGOB inspector, who deposits it in a safe accessible only to the Órgano Interno de Control.
4. **Sales-close slots** — policy 9 specifies daily automatic close at 15:00 for De las Tres and 21:00 for nocturnal draws; changes require authorization and notice. The official Chispazo product page maps De las Tres to 15:00 and Clásico to 21:00.
5. **Draw act and attachments** — policy 11 requires an acta with place, date, event time, names/roles/signatures of commissioned Lotería personnel and the SEGOB inspector's name, signature and commission-office number. The Chispazo attachment matrix lists the Sumario de sorteo (cierre de venta), CS-11 winning numbers, Sumario de sorteo and Tira de Pesaje.
6. **Calibration** — policy 25 says scales used for electronic-draw sphere weighing are calibrated at least annually under the responsible subgerencia's calendar; the interval may change if the number of draws requiring weighing increases.

These provisions are useful to define the evidence request and adapter contract. They do **not** establish that any specific contest's records exist, were signed, were retained, or are authentic.

## Critical applicability exclusion: SGVO-PRO-34

SGVO-PRO-34 is **not** the governing weight specification for Chispazo. Its own scope (section II, PDF page 3) says it applies exclusively to balls and abaci used in **Sorteos Tradicionales** and excludes the electronic-draw process. It concerns wooden maple balls, including 3.0 g nominal weight with ±0.8 g tolerance, and traditional abaci.

Therefore:
- Do not import SGVO-PRO-34's wooden-ball material, dimensions, 3.0 g nominal weight, ±0.8 g tolerance, sampling, or abacus controls into Chispazo.
- The Chispazo electronic sphere bands in ORIGEN V2 correspond instead to SGVO-PRO-05 policy 6.
- A code path that treats traditional wooden-ball limits as Chispazo limits would be a modality/specification defect.

## ORIGEN alignment and remaining gap

The current V2 structural constants are:
- SMARTBALLS: 4.25–5.25 g, max within-set spread 0.30 g.
- PING PONG: 2.30–3.00 g, max within-set spread 0.15 g.

The values match SGVO-PRO-05 policy 6. V2 also requires a 28-sphere set, sphere/set/machine identity, scale identity, calibration interval and certificate digest, pre-close evidence availability, and a CLASSIC target. These are structural gates only. The code does not independently authenticate the procedure version, the institution, the scale certificate, source bytes, signature cryptography, clock, custody or the fact that the observed set was actually used.

For a real Classic target, the evidence request must obtain the original per-draw Tira de Pesaje and its full 28 measurements, sphere type and set ID, machine ID/model, scale ID and calibration evidence, the signed Acta and its attachment links, CS-11, Sumario/cierre de venta, signed participation/cancellation file and its pre-draw safe-custody chain, and independent trusted-time/custody/ledger proofs. Any required record not supplied stays missing; no synthetic or reconstructed values are permitted.

## Public status at 14:51 local on 23-Nov-2026

- Official Chispazo results page still showed contest 12390 (22-Nov): 01 06 09 19 23; contest 12389: 01 15 17 22 25; and 23-Nov as the next draw date, with no 23-Nov result.
- Official home index showed a 23-Nov 15:00 generic card numbered 12391, titled “Ilumina tu suerte”; the rendered card did not explicitly identify product/modality. Do not bind it to the Chispazo De las Tres register solely from that card.
- The official Chispazo product page identifies De las Tres at 15:00 and Clásico at 21:00. No 23-Nov Classic contest ID was visible in the inspected result/home sources.
- Official mask index latest visible date was 22-Nov. The 22-Nov mask identifies 12389 as De las Tres (01 15 17 22 25) and 12390 as Clásico (01 06 09 19 23).
- No draw-specific primary physical records for a 23-Nov Chispazo draw were obtained in this observation. The 23-Nov 15:00 and 21:00 slots were still in the future at observation time.

## Source-byte integrity

The official pages and PDF text were reviewed through the browser-rendered/indexed source. Direct retrieval of original PDF bytes was not successful in this run. Consequently, original-byte SHA-256 values for SGVO-PRO-05, SGVO-PRO-34 and the 22-Nov mask are **NOT_CAPTURED**. Do not substitute a browser-rendered text digest or guessed hash.

## Decision

**BLOCKED_PROVENANCE / RESEARCH_ONLY_NO_EDGE**. The procedure defines what should be requested; it is not the records themselves. No prospective score, eligibility upgrade, prediction, V294 change, canonical-history append, main write, merge or promotion is authorized by this review.
