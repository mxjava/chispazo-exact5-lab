# SGVO-PRO-05 Rev. 39 — ORIGEN evidence matrix

**Observation:** 2026-11-23 08:53:45 America/Mexico_City  
**Classification:** official public procedure and status review; not draw-specific physical evidence  
**Branch:** `research/origen-trust-adapter-spec-20261121`

## 1. Current official procedure located

The Lotería Nacional Normateca publishes **SGVO-PRO-05, Procedimiento Sorteos Electrónicos**, in the `SUSTANTIVAS/VIGENTES` path. The PDF identifies:

- Public internal norm, 38 pages
- Revision **39**, footer **DN-07 Version 09**
- Publication date **20-Mar-2026**
- Issuing area: Subdirección General de Ventas y Operaciones

Source: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

The official Chispazo product page separately maps **De las Tres to 15:00** and **Clásico to 21:00**:
https://www.loterianacional.gob.mx/Chispazo/Chispazo

SGVO-PRO-05 policy 9 specifies automatic sales closure at 15:00 for De las Tres and 21:00 for nocturnal draws. This aligns the current official schedule with the V2 Clásico close-slot check; it does not make the actual extraction timestamp equal to the sales-close timestamp.

## 2. Physical controls and exact mass tolerances

SGVO-PRO-05 policy 6 specifies two sphere types:

| Sphere type | Minimum | Maximum | Maximum set spread |
|---|---:|---:|---:|
| Smartballs | 4.25 g | 5.25 g | 0.30 g |
| Ping Pong | 2.30 g | 3.00 g | 0.15 g |

The constants in `src/origen/physical_intake_v2.py` match these values exactly. This confirms the current V2 mass limits against the public revision-39 procedure; it is not proof that any particular draw's spheres were weighed or met those limits.

## 3. Mandatory Chispazo record bundle

The procedure's Acta attachment matrix lists these Chispazo records:

1. **Sumario de sorteo (cierre de venta)**
2. **Números Ganadores de los Sorteos CS-11**
3. **Sumario de sorteo** (post-result)
4. **Tira de pesaje**

The Tira de Pesaje is defined as signed by four roles:
- responsible sphere-weighing person;
- representative of the Dirección de Operación de Concursos, Juegos y Sorteos;
- representative of the Dirección General;
- SEGOB inspector.

The Acta must record the place, date and time, names/roles/signatures of Lotería Nacional representatives, and the SEGOB inspector's name, signature and commission number; incidents must also be recorded when present.

The procedure also specifies an electronic signature for participation/cancellation files, generated after automatic sales close, copied to controlled media, checked against the printed signature form, signed by responsible representatives, and deposited by the SEGOB inspector in the security box for Órgano Interno de Control custody.

These are **records to request and verify**, not records shown to have been produced for the 23-Nov draw.

## 4. Modality and result status — 23-Nov-2026

The official product page states:
- **De las Tres:** 15:00
- **Clásico:** 21:00

The opened official home index displays a 23-Nov 15:00 card numbered **12391**, but the card does not print the product name. Its match to De las Tres is therefore a schedule-slot match using the official product page, not an explicit product label on the card. No 23-Nov 21:00 Clásico card or Clásico contest ID is inferred.

The official results endpoint still publishes:
- **12390, 22-Nov, Clásico:** 01 06 09 19 23
- **12389, 22-Nov, De las Tres:** 01 15 17 22 25

The official mask index's latest entry is **RESULTADOS 2026-11-22**. The opened 22-Nov PDF labels both modalities. No 23-Nov result or mask was visible in this observation.

## 5. Contract gap for the future independent adapter

The current V2 CSV is a per-sphere structural intake and has no dedicated typed slot for each of the four Acta attachments, the participation/cancellation signature media, the inspector commission evidence, or the safe-deposit/OIC custody record.

The V1 trust-receipt parser currently accepts a generic artifact array with a minimum of one item; it does not enforce a mandatory Chispazo artifact set. This is **not an authentication bypass today**: the returned type is `UnverifiedTrustReceipt`, and `verify_independent_provenance` remains hard-wired to `BLOCKED_PROVENANCE`. It is a required design gate before any future adapter can issue an authenticated status.

Next safe implementation boundary is a versioned artifact manifest that binds each required artifact type to original bytes, exact byte length and digest, signer/role, time proof, custody record and contest/modality. The manifest must be verified against trust roots provisioned outside the submitted evidence. Do not add caller-controlled booleans, reference sets or keys.

## 6. Source-byte and provenance limitations

The official 22-Nov result mask and SGVO-PRO-05 PDF were opened and text-extracted in the browser. Attempts to capture the original PDF bytes in this working environment were unsuccessful. Their original source SHA-256 values remain **NOT_CAPTURED**; no hash of extracted text or rendered content is substituted.

No draw-specific 23-Nov physical evidence was obtained:
- signed Acta and CS-11;
- sales-close and post-result summaries;
- original Tira de Pesaje with all 28 readings;
- scale identity and calibration;
- equipment/urn records;
- signed participation/cancellation files and proof of secure deposit;
- independent custody and trusted-time/ledger proof;
- two independent pre-close Exact5 seals.

## 7. ORIGEN disposition

- Keep the 15:00 draw separate from the 21:00 Clásico target.
- Do not infer a 23-Nov Clásico contest ID from the 12391 card.
- Keep V294 frozen and the canonical history untouched.
- No prospective score or OOS eligibility is added.
- Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Official sources

- https://www.loterianacional.gob.mx/home/index
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Chispazo/Chispazo
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-22.pdf?v=22112026221841
- https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
