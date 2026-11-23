# Physical provenance delta — 2026-11-23

## Scope and classification

Continuation of the existing Chispazo Clásico physical-evidence line. No closed frequency, pair, triple or transition work was repeated. No draw-specific physical records were obtained. Classification: MECHANISM EVIDENCE ONLY; no physical-bias or predictive-advantage claim.

## New findings

1. **SGVO-PRO-05 revision 39 cross-reference defect.** Policy 6 contains sphere weight limits (Smartballs 4.25–5.25 g, max-min spread 0.30 g; Ping Pong 2.30–3.00 g, spread 0.15 g). Policy 8 concerns the electronic signature of the participation file. Activity 5.2 and the Quality Plan weighing row cite Policy 8 while repeating Policy 6 weight limits. This is a confirmed documentary defect, not evidence staff applied an incorrect tolerance. Obtain the controlled strip and current controlled copy.

2. **Tira de Pesaje signatory role discrepancy.** Activity 5.4 names the SGVO representative; the glossary definition names the representative of the Dirección de Operación de Concursos, Juegos y Sorteos. Obtain the controlled form and current delegation/commission record.

3. **CS-11 field claim narrowed.** The public Quality Plan lists date, draw number, case number, sphere-vs-number comparison and participant names. It does not list a time field in that table, and the blank controlled CS-11 template is not embedded in SGVO-PRO-05. Activity 13 completes CS-11 after sphere capture. Defensible statement: the public plan does not specify a CS-11 time field; the actual template has not been obtained. Do not claim the actual form definitely has or lacks time.

4. **SGVO-MAN-02 is a reserved project lead only.** SGVO-PRO-05 refers to the Manual de Apoyo for inspection and weighing details. The located SGVO-MAN-02 PDF is in the PROYECTO path, its cover says RESERVADO, issue date June 2011, revision 09, and it is absent from the current Vigentes list. It describes draft CS-02 fields (date, draw numbers, inspection time, signatures; up to 30 minutes pre-draw) and a draft weighing strip (individual values, start/end printed times, summary statistics, signatures, feeder loading in weighing order). These are leads for the records request, not current operative facts.

5. **Regulation/procedure order needs written interpretation.** Chispazo Regulation Article 9 says 28 spheres are introduced into an urn before sales close, then sales close/signature occur, then five spheres are extracted. SGVO-PRO-05 describes SICAL close, then weighing, possible case replacement (returning to close activity), strip signatures and feeder loading. This may reflect different meanings of urn, preliminary placement and final feeder loading. It is an unresolved sequence ambiguity, not proof of breach. Link the final case to the final SICAL close.

6. **Electronic signature is post-close/pre-draw, not a physical feature.** It authenticates the participation/cancellation file. SGVO-PRO-05 places receipt/custody after close and weighing/loading, before the draw. It does not measure sphere mass, sphere identity, machine condition or extraction order and cannot be a pre-close feature for the same draw.

7. **Maintenance has a dated boundary.** Policy 24 requires an annual preventive/corrective maintenance calendar; Policy 25 requires annual scale calibration. Lotería's 2018–2024 management report identifies contract 058-2024 for 21 draw machines, controls and consoles, including Chispazo, concluded by June 2024. This is historical, not draw-level condition evidence. No asset work orders, machine serial assignment, scale certificates or current post-June-2024 records were obtained. The 2026 tender IA-06-HJY-006HJY001-N-222-2026 is for building electrical equipment (generators, UPS, substations/transformers etc.), not draw machines, and is excluded.

8. **RFID existence is not event-level traceability.** The management report states 14 machines (10 Jupiter, 2 Mercury 5, 2 Mercury 8) and spheres have RFID recognition. It states 10 sets for each of seven products (70 by arithmetic) but reports 60; unresolved. No raw reader events, RFID-to-sphere-number map, machine serial-to-contest assignment, reader/antenna ID or synchronized per-draw log was obtained.

9. **Strict modality boundary.** The official product page classifies Chispazo as electronic and lists De las Tres at 15:00 and Clásico at 21:00. SGVO-PRO-34 explicitly applies exclusively to traditional wooden balls and abaci. Its wood-ball tolerances, boleo and abacus forms are not Chispazo sphere procedures.

## Prospective timing

| Variable | Document | Timing | Same-draw pre-close eligibility |
|---|---|---|---|
| CS-02 / machine condition | CS-02 referenced by PRO-05; current blank form unavailable | Before each draw; exact lead time not specified in PRO-05 | Candidate only with controlled form, machine ID and timestamp before final close |
| Machine identity / maintenance | Inventory, RFID, calendar, work orders | Unknown per draw | Candidate only with asset-to-contest mapping and pre-close timestamp |
| Scale calibration | Certificate/calendar | May predate close | Candidate only with scale ID and valid certificate before close |
| Initial case | Activity 3.1 | Pre-close | Not safe if later rejected/replaced |
| Final case | Tira and activity 5.3 | Can change after failed weighing; return to final SICAL close | Candidate only if linked to final close |
| Same-draw weights | Tira de Pesaje | Post-close | No |
| Prior-draw weights | Prior Tira | Post prior close | Potentially for a later draw with authenticated availability and continuous sphere/set mapping |
| Participation signature | Electronic file/CD | Post-close, pre-draw | No; participation integrity only |
| CS-11 / Acta | Result capture | Post-extraction | No |
| Video | Master from weighing through draw | During/post event | No for same-draw prediction |
| CS-09 incident | Acta/bitácora | During/post event | No unless a separate pre-close record exists |

## Reproducibility and integrity

- Source excerpt snapshot: research/ORIGEN_v0_3/data/official-overlays/2026-11-23_sgvo_pro05_source_contract.json
- Audit code: research/ORIGEN_v0_3/src/origen/sgvo_source_audit.py
- Tests: research/ORIGEN_v0_3/tests/test_sgvo_source_audit.py
- Result: research/ORIGEN_v0_3/reports/SGVO_PRO05_SOURCE_CONTRACT_AUDIT_20261123.json
- Local tests: 10 passed.
- Snapshot SHA-256: a850802bc8e814158170575a23b8d19c25b523acf7110a2cedf89d96073f557f
- Script SHA-256: 1be64d99d2d4a68d13f0dba34c39afed40cc3cd9105a2fa04148dfc522536215
- Tests SHA-256: 640a036c76a7e7e84446de926e0cb2b1fb1fecce6e25a06de2f2d67a10667a85
- Result JSON SHA-256: b3b7158e537a9f411c80be22b57a1a7312e2ce7c967bf8d9f2259dfba4bd0a94

The script validates a frozen transcript of official excerpts; it does not parse/authenticate the original PDF bytes. No SHA-256 is claimed for the official PDFs because their binary bytes were not materialized in this run.

## Blocking request

Request controlled current CS-02/CS-11 forms and revisions; signed CS-02 and SICAL close summaries; original 28-row Tiras de Pesaje; RFID tag-to-number map and raw reader logs; machine serial-to-contest assignments; asset-specific maintenance orders; scale calibration certificates; continuous video masters with timecodes and custody hashes; original Actas and annexes; CS-09/CS-18 entries; original signed participation/cancellation files and custody logs; and written clarification of the Article 9/PRO-05 sequence and both internal reference/role discrepancies.

## Guardrails

No main writes, merge or promotion. No V294 changes. No edits to data/history/Chispazo_through_12249.csv. No frequency, pair, triple or transition analysis. OOS, multiplicity and anytime e-value gates remain unsatisfied.
