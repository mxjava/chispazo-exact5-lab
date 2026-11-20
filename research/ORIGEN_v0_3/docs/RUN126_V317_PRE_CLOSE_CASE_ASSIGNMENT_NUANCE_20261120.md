# Run126 — V317 temporal nuance: pre-close case confirmation vs post-close weighing

**Capture:** 2026-11-20 03:09:10 America/Mexico_City  
**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`  
**Scope:** read-only procedure analysis; no code, challenger, V294, or canonical-history changes.

## Fresh official-results status

At capture, the dedicated Chispazo results page still ended at 12384 (19-Nov-2026, Clásico, `01 02 09 21 25`); the official mask index still ended at 19-Nov. The commercializer scheduled 12385 for 20-Nov at 15:00 (De las Tres). Clásico remains scheduled at 21:00, but its 20-Nov contest ID is not established. The home-results extraction still showed a blank number field for 12384 while the dedicated page published the numbers. No 20-Nov result or mask was available yet.

## New distinction in SGVO-PRO-05 revision 39

The published activity order contains a nuance that must be preserved:

1. **Activity 3.1, before the “Cierre de Venta” section:** confirms with the SEGOB inspector and General Directorate representative that the draw number and sphere case to be used correspond to the draw.
2. **Activity 4.1:** verifies the SICAL automatic sales closure and contest/date/time.
3. **Activity 5.1, after closure:** begins weighing each sphere individually in numerical order.
4. **Activity 5.3:** if the weight is incorrect, the case is changed and the process returns to 4.1.
5. **Activities 5.6–6.1:** spheres are placed in the feeders and representatives verify that the deposited spheres correspond to the draw.

Therefore, the same-draw mass vector remains post-close and cannot satisfy V317's same-draw pre-close feature rule. However, a planned sphere-case confirmation is a pre-close process step. The public procedure does not establish that a timestamped record of that confirmation, the physical sphere IDs, or the sphere-to-number mapping are available before close.

A further complication is explicit: activity 5.3 allows the case to change after closure. Thus the planned pre-close case may not be the final case used. Any feature based on the final case would be post-close information and prohibited.

## Research-only possibility: lagged measurements for the same case

A future, separately preregistered design might use the last authenticated mass vector for a physical case, but only if all of the following are proven before evaluating outcomes:

- the target contest's planned case ID was confirmed before sales close;
- the previous mass vector belongs to that exact physical case;
- all 28 stable physical sphere IDs and their printed-number mapping persist;
- no remapping, replacement, maintenance, or case change intervenes;
- the post-close final-case record matches the planned case;
- every case switch and ineligible contest is retained in a predeclared ledger;
- beta is independently calibrated without using Chispazo outcomes.

Because the case can be replaced after close, do not silently condition on the final case or retrospectively remove changed-case draws. This is a research hypothesis, not a repair or modification of V317.

## Evidence still missing

No activity-3.1 pre-close case-confirmation records, original per-draw weighing strips, physical-sphere identity register, sphere-to-number mapping, case-change ledger, CS-11 records with authenticated timestamps, or raw policy-30 recordings with independent custody have been received. The official PDF was read through web extraction; raw PDF bytes and source SHA-256 were not captured.

## Classification

- Same-draw V317 mass timing contract: `MODEL_IMPLEMENTATION_DEFECT`.
- Lagged same-case hypothesis: `BLOCKED_PROVENANCE`.
- Predictive edge: `NO_EDGE_EVIDENCE`.
- Production: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

V294 remains frozen. Canonical history is unchanged. No scoring, tuning, or challenger changes were performed.
