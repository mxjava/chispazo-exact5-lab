# SGVO-PRO-05 Rev. 39 — ORIGEN evidence matrix

**Observation:** 2026-11-23 09:56:49 America/Mexico_City  
**Classification:** official public procedure and status review; not draw-specific physical evidence  
**Branch:** research/origen-trust-adapter-spec-20261121

## 1. Current official procedure

The Lotería Nacional Normateca exposes SGVO-PRO-05, Procedimiento Sorteos Electrónicos, under its SUSTANTIVAS/VIGENTES path. The PDF identifies revision 39 and DN-07 Version 09. The cover also retains the original emission field OCTUBRE 2003; this matrix does not infer a separate revision-publication date from the PDF.

Official PDF:
https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

The official Chispazo product page maps De las Tres to 15:00 and Clásico to 21:00:
https://www.loterianacional.gob.mx/Chispazo/Chispazo

Policy 9 of SGVO-PRO-05 sets automatic sales close at 15:00 for De las Tres and 21:00 for nocturnal draws. The product page supplies the Chispazo product-name mapping. The close slot is not the actual extraction timestamp.

## 2. Physical controls and metrology

Policy 6 specifies:

| Sphere type | Minimum | Maximum | Maximum set spread |
|---|---:|---:|---:|
| Smartballs | 4.25 g | 5.25 g | 0.30 g |
| Ping Pong | 2.30 g | 3.00 g | 0.15 g |

The constants in physical_intake_v2.py match these values. This is a policy-to-code comparison, not evidence that a particular draw's spheres were weighed or passed.

Policy 25 requires calibration of the scales used to weigh the spheres at least once per year. Policy 24 separately covers preventive/corrective maintenance of draw equipment. The manifest therefore distinguishes a scale calibration certificate from equipment/urn identity records.

Activity 5.1 says the spheres are weighed one by one and in numerical order in the presence of the SEGOB inspector and the representatives of the Dirección General and Subdirección General de Ventas y Operaciones.

## 3. Chispazo Acta attachments and exact weighing-strip roles

Policy 11's attachment matrix lists these four records for Chispazo:

1. SUMARIO DE SORTEO (CIERRE DE VENTA)
2. NÚMEROS GANADORES DE LOS SORTEOS CS-11
3. SUMARIO DE SORTEO
4. TIRA DE PESAJE

The Acta itself must include place, date and event time; names, roles and signatures of the public servants commissioned under policy 2; the SEGOB inspector's name, signature and commission number; and incidents when present.

**Role correction:** the prior matrix mislabeled the SGVO reviewer as the Dirección de Operación de Concursos, Juegos y Sorteos. Activity 5.4 instead says the person responsible for weighing signs the Tira de Pesaje, which is then reviewed/rubricated by:
- representative of the Subdirección General de Ventas y Operaciones;
- SEGOB inspector;
- representative of the Dirección General.

Together with the weighing-responsible signer, those are the four activity-5.4 roles enforced by the new structural manifest schema. The Acta signer roles are separately derived from policy 2 plus the SEGOB inspector; they are not conflated with the weighing-strip roles.

## 4. Participation/cancellation files, custody and room access

Policy 8 states that the electronic signature of the participation file is recorded to a storage device before the draw, delivered by the IT representative to the designated SEGOB inspector, and deposited in the security box accessible only to the Órgano Interno de Control.

Policy 16's activity note says its validation sequence is performed only for nocturnal draws. This is relevant to the 21:00 Clásico target and must not be generalized to the 15:00 De las Tres workflow without checking the applicable steps.

Policy 19 requires people participating in an electronic draw to register in CS-12, the room-attendance form. The ORIGEN manifest includes the CS-12 record as a supporting access-control artifact.

## 5. Versioned physical-evidence manifest

The new physical-evidence manifest v1 requires one original-byte entry for each of:
- the draw Acta;
- the four Chispazo Acta attachments listed above;
- participation/cancellation signature media;
- scale calibration certificate;
- equipment/urn record;
- sphere-to-number mapping register;
- CS-12 room-access register;
- SEGOB/OIC custody record.

Only the four attachment names above are stated as Chispazo Acta attachments by policy 11. The remaining entries are ORIGEN supporting-evidence requirements for reconstructing equipment, mapping, access and custody; they are not represented as verbatim SGVO attachment names.

The schema also requires:
- exact target contest ID, local draw date and 21:00 Mexico City close;
- source ID, immutable source-object ID, media type, original-byte SHA-256 and byte length for every artifact;
- explicit signature claims for the Acta, weighing strip and participation/cancellation signature media;
- exactly four distinct weighing-strip signers with the activity-5.4 roles;
- a custody event for every artifact;
- each custody event's time-proof reference to resolve to the same declared UTC event time;
- an advancing ledger-head claim.

The parser returns UnverifiedPhysicalEvidenceManifest. It does not open or hash source bytes, validate detached signature bytes, prove signer identities/roles, validate trusted timestamp tokens, verify ledger inclusion, or authenticate custody. A digest, timestamp string, signer label, URL or internally consistent ledger claim remains an untrusted declaration.

The independent adapter remains hard-wired to BLOCKED_PROVENANCE. This manifest cannot issue AUTHENTICATED and is not wired into temporal eligibility.

## 6. Official status — 23-Nov-2026, 09:56 local

Official pages checked:
- Results: https://www.loterianacional.gob.mx/Chispazo/Resultados
- Product schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Home index: https://www.loterianacional.gob.mx/home/index
- Mask index: https://www.loterianacional.gob.mx/Mascarillas/Mascarillas

The results endpoint still shows:
- 12390, 22-Nov, Clásico: 01 06 09 19 23
- 12389, 22-Nov, De las Tres: 01 15 17 22 25

The home index shows a 23-Nov 15:00 card numbered 12391, but the card rendering does not explicitly print the product name. Its association with De las Tres is a schedule-slot match only. No 23-Nov 21:00 Clásico card or Clásico contest ID is inferred.

The mask index's latest visible entry remains RESULTADOS 2026-11-22. No 23-Nov result or mask was visible at observation time.

## 7. Source-byte and physical-evidence limitations

The official SGVO-PRO-05 PDF was opened and text-extracted in the browser. The original PDF bytes could not be downloaded into this run's working environment; the attempted download failed. Its original SHA-256 therefore remains NOT_CAPTURED. No hash of extracted text or rendered PDF content is substituted.

No draw-specific primary physical records for 23-Nov were obtained:
- signed draw Acta and CS-11;
- sales-close and post-draw summaries;
- original weighing strip with 28 readings and four activity-5.4 roles;
- scale identity and valid calibration certificate;
- equipment/urn and sphere-to-number mapping records;
- CS-12 room-access record;
- participation/cancellation signature media;
- SEGOB/OIC security-box deposit and independent custody record;
- trusted timestamp and external ledger inclusion proofs;
- two independent pre-close Exact5 output seals.

## 8. ORIGEN disposition

- Keep the 15:00 De las Tres slot separate from the 21:00 Clásico target.
- Do not infer a 23-Nov Clásico contest ID from the 12391 card.
- Keep V294 frozen and the canonical history byte-for-byte untouched.
- Do not grant snapshot, prospective OOS or score eligibility from this public status review.
- Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.

## Official sources

- https://www.loterianacional.gob.mx/home/index
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Chispazo/Chispazo
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
