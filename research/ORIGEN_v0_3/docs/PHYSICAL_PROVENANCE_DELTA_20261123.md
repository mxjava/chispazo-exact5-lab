# Physical provenance delta — 2026-11-23

## Scope

Continuation of the existing Chispazo Clásico physical/operational evidence line. No closed frequency, pair, triple or transition work was repeated. No draw-specific physical records were obtained. Classification: **mechanism/documentary evidence only**; no physical-bias or predictive-advantage claim.

## New findings

1. **SGVO-PRO-05 rev. 39 cross-reference defect.** Policy 6 contains sphere weight limits: Smartballs 4.25–5.25 g with max-min spread 0.30 g; Ping Pong 2.30–3.00 g with spread 0.15 g. Policy 8 concerns the electronic signature of the participation file. Activity 5.2 and the Quality Plan weighing row cite Policy 8 while repeating Policy 6 weight limits. This is a documentary cross-reference defect, not proof that staff applied the wrong tolerance.

2. **Tira de Pesaje signatory role discrepancy.** Activity 5.4 names the representative of the Subdirección General de Ventas y Operaciones; the glossary definition names the representative of the Dirección de Operación de Concursos, Juegos y Sorteos. The controlled form and current delegation/commission record are needed to resolve the role.

3. **CS-11 hour field confirmed, with a checklist omission.** The Quality Plan checklist lists date, draw number, case number, sphere-vs-number comparison and participant names, but does not repeat a time field. The glossary definition explicitly specifies date, draw name, draw number, **hour of the draw**, selected case, results and the preparer/verifier/certifier and Director General representative signatures. The blank controlled CS-11 form and completed records remain unavailable. Activity 13 completes CS-11 after sphere capture, so it is retrospective for the same draw.

4. **SGVO-MAN-02 is a reserved project lead, not current approved authority.** The located manual is in the PROYECTO path, marked RESERVADO, issue date June 2011, revision 09, and is absent from the current Vigentes list. Its draft describes CS-02 date/draw/time/signature fields, a 30-minute pre-draw inspection window, and a weighing strip with individual values, start/end times, summary statistics and signatures. These are retrieval leads only, not current operative facts.

5. **Regulation/procedure sequence needs written interpretation.** Chispazo Regulation Article 9 describes introducing 28 spheres into an urn before sales close, then closing sales/signature, then extracting five. SGVO-PRO-05 describes SICAL close, then weighing, possible case replacement (returning to the close activity), strip signatures and feeder loading. Different meanings of urn, preliminary placement and final feeder loading may explain the sequence. Treat it as an ambiguity, not proof of a breach; link the final case to the final SICAL close.

6. **Electronic signature is post-close/pre-draw, not a physical covariate.** It authenticates the participation/cancellation file and is handled after close and weighing/loading, before the draw. It does not measure sphere mass, identity, machine condition or extraction order.

7. **Maintenance evidence has a dated boundary.** Policy 24 requires an annual preventive/corrective maintenance calendar; Policy 25 requires at least annual scale calibration. Lotería's 2018–2024 management report identifies contract 058-2024 for 21 draw machines, controls and consoles, including Chispazo, concluded by June 2024. No asset-level work orders, serial-to-contest assignments, scale certificates or post-June-2024 maintenance records were obtained. The 2026 tender IA-06-HJY-006HJY001-N-222-2026 concerns building electrical equipment (generators, UPS, substations/transformers), not draw machines, and is excluded.

8. **RFID existence is not draw-level traceability.** The management report says 14 machines (10 Jupiter, 2 Mercury 5, 2 Mercury 8) and spheres have RFID recognition. It reports 60 sets although 10 sets × 7 named products equals 70; unresolved. No RFID-to-sphere-number map, raw reader events, machine serial-to-contest assignment, reader/antenna ID or synchronized per-draw log was obtained.

9. **Strict modality boundary.** The official product page classifies Chispazo as electronic and lists De las Tres at 15:00 and Clásico at 21:00. SGVO-PRO-34 is exclusively for traditional wooden balls and abaci. Its wood-ball tolerances, boleo and abacus procedures are not Chispazo sphere procedures.

## Prospective timing

| Variable | Record | Timing | Same-draw pre-close use |
|---|---|---|---|
| Machine condition / CS-02 | CS-02 referenced by PRO-05; current blank form unavailable | Before each draw; exact lead time not specified in PRO-05 | Candidate only with controlled form, machine ID and timestamp before final close |
| Machine identity / maintenance | Inventory, RFID, annual calendar, work orders | Unknown per draw | Candidate only with asset-to-contest mapping and pre-close timestamp |
| Scale calibration | Certificate/calendar | May predate close | Candidate only with scale ID and valid certificate before close |
| Initial case | Activity 3.1 | Pre-close | Not safe if later rejected/replaced |
| Final case | Tira and activity 5.3 | Can change after failed weighing; return to final SICAL close | Candidate only if linked to final close |
| Same-draw sphere weights | Tira de Pesaje | Post-close | No |
| Prior-draw weights | Prior Tira | Post prior close | Potentially for a later draw with authenticated availability and continuous sphere/set mapping |
| Participation signature | Electronic file/CD | Post-close, pre-draw | No; participation-file integrity only |
| CS-11 / Acta | Result capture | Post-extraction | No |
| Video | Master from weighing through draw | During/post event | No for same-draw prediction |
| CS-09 incident | Acta/bitácora | During/post event | No unless a separate pre-close record exists |

## Reproducibility

- Source excerpt snapshot: [JSON](../data/official-overlays/2026-11-23_sgvo_pro05_source_contract.json)
- Audit code: [sgvo_source_audit.py](../src/origen/sgvo_source_audit.py)
- Tests: [test_sgvo_source_audit.py](../tests/test_sgvo_source_audit.py)
- Machine result: [JSON](../reports/SGVO_PRO05_SOURCE_CONTRACT_AUDIT_20261123.json)
- Local tests: **10 passed**.
- Snapshot SHA-256: 6f91b0bd52156635403459d30e6acaa32e00ed012954b2bff4956304d21c380b
- Script SHA-256: 1f096f453e6efcc5f5563e4402bc7bf6390f2113a6b362126f5eef4d47b45b10
- Tests SHA-256: 6545b424c379600e59f9f6a42af58ec70f4cd486f29d24fe5aff23fc9570fb31
- Result JSON SHA-256: 174c7f2faff58dde858553054b07a30a15276bcdead33a70574f016da9853bee

The script checks a frozen transcript of official excerpts; it does not parse or authenticate the original PDF bytes. No SHA-256 is claimed for the official PDFs because their binary bytes were not materialized.

## Blocking evidence request

Obtain the controlled current CS-02 and CS-11 forms/revisions; signed CS-02 and SICAL close summaries; original 28-row Tiras de Pesaje; RFID tag-to-number map and raw reader logs; machine serial-to-contest assignment; asset-level maintenance orders; scale calibration certificates; continuous video masters with metadata/timecodes and custody hashes; original Actas and annexes; CS-09/CS-18 entries; signed participation/cancellation files and custody logs; and written clarification of the Article 9/PRO-05 sequence and the two internal Policy 8/Policy 6 and Tira signatory-role discrepancies.

## Guardrails

No writes to main, merge or promotion. No V294 changes. No edits to data/history/Chispazo_through_12249.csv. No frequency, pair, triple or transition analysis. OOS, multiplicity and anytime e-value gates remain unsatisfied.
