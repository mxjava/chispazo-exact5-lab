# ORIGEN physical-evidence manifest V2 — modality separation

**Status:** research-only structural parser; no authentication or production promotion  
**Implementation:** `physical_evidence_manifest_v2.py`  
**Compatibility:** V1 remains unchanged and CLASSIC-only

## Why V2

The official Chispazo product page identifies two distinct daily products: **De las Tres at 15:00** and **Clásico at 21:00**. SGVO-PRO-05 Rev. 39 policy 9 assigns the automatic sales-close times at 15:00 for De las Tres and 21:00 for nocturnal draws. The close time is not the actual extraction timestamp; V2 records both separately.

The V1 schema is intentionally not reinterpreted. V2 adds an explicit modality field and enforces the corresponding Mexico City sales-close slot.

## Modality-specific requirements

| Modality | Mexico City sales close | Required special handling |
|---|---:|---|
| `DE_LAS_TRES` | 15:00 | Daytime participation/cancellation signature reconciliation; no nightly MJF records |
| `CLASSIC` | 21:00 | Nightly participation/cancellation handling and MJF transaction file plus printed signature form |

The distinction follows the official procedure's policy 16 and its activity notes: the MJF/CD-II process is specified for nocturnal draws; daytime draws use the separate signature-comparison loop. The V2 parser therefore requires the MJF pair only for CLASSIC and rejects it for DE_LAS_TRES. It keeps the common Chispazo Acta attachments, CS-11, weighing strip, equipment, recording, custody and time-proof declarations for both.

V2 also records `draw_event_at_utc` separately from `sales_close_at_utc` and rejects an event time earlier than the automatic sales close or on a different Mexico City date. These are structural consistency checks only; timestamps remain untrusted strings until independently verified.

## Source mapping

- Product schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Normateca current list and last-update metadata: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-05 Rev. 39, DN-07 Version 09: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Official 25-Nov-2026 result mask: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-25.pdf?v=25112026221906

The 25-Nov mask explicitly labels contest 12395 as De las Tres (01 13 19 23 28) and contest 12396 as Clásico (05 07 21 24 28). This is a modality mapping example, not a claim that the source PDF's original bytes were captured locally. No SHA-256 is asserted for the PDF because direct binary retrieval failed.

## Security boundary

`parse_unverified_physical_manifest_v2` returns `UnverifiedPhysicalEvidenceManifestV2`. It validates canonical JSON, schema shape, modality/slot binding, required artifact coverage, signature references, declared custody/time-proof consistency and the ledger-anchor shape. It does not read original artifacts, recompute their hashes, verify detached signatures, authenticate identities/roles, validate RFC 3161 tokens, prove ledger inclusion/consistency, or establish independent custody.

Synthetic test fixtures use generated labels and hashes only. They are not Lotería Nacional records. The public independent-provenance adapter remains `BLOCKED_PROVENANCE`; V294 remains frozen; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
