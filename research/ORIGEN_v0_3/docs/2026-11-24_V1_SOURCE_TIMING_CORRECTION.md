# ORIGEN V1 source-draw timing correction — 24-Nov-2026

Status: implemented in the PR #26 research branch; awaiting exact-head CI.

## Reproducible defect

The V1 `physical_intake.py` validator required `measurement_at < draw_close_at` and accepted either `CLASSIC` or `TRES` without binding the modality to its official close slot. Its CLI exposed this validator as `validate-physical`. The fixture marked a CLASSIC draw closing at 19:00 local and treated a 17:10 measurement as structurally usable.

That is incompatible with the current official electronic-draw procedure. SGVO-PRO-05 Rev. 39 policy 9 sets 15:00 for De las Tres and 21:00 for nocturnal sales close. The activity flow verifies the sales state closed in activity 4.1, then begins weighing in activity 5.1, signs/delivers the weighing strip in activities 5.4–5.5, and loads spheres in 5.6 before extraction. The official Chispazo product schedule identifies 15:00 as De las Tres and 21:00 as Clásico.

## Minimal correction

- Bind V1 `TRES` records to exactly 15:00 and `CLASSIC` records to exactly 21:00 in `America/Mexico_City`.
- Validate source event order as assignment/mapping before close, sales close before extraction, and weighing at/after close but no later than source extraction.
- Stop presenting V1 `usable_contests` as target pre-close eligibility. V1 has no target, evidence-availability, custody-receipt or source-to-target continuity fields; those remain V2 responsibilities.
- Bound V1 materialization to 28,000 rows, require exact built-in row dictionaries and text cells, reject extra/missing row keys, reject duplicate/extra CSV headers, and reject string/mapping subclass coercion at the intake boundary.
- Add adversarial regressions for the CLASSIC/15:00 mismatch, valid TRES/15:00, pre-close and post-extraction measurement, spoofed timestamp subclasses, spoofed row subclasses and unbounded iterables.

This is a source-intake correctness/resource hardening change. It does not authenticate timestamps, signatures, hashes, custody, sphere identity or physical continuity. It does not create target eligibility, predictive edge or a same-draw pre-close mass feature.

## Official references

- SGVO-PRO-05 Rev. 39, policies 6, 9, 11 and activity flow 4.1–5.6: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Official Chispazo schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- V2 temporal contract: `PHYSICAL_EVIDENCE_TEMPORAL_CONTRACT_V2_20261119.md`
- V317 timing audit: `V317_OFFICIAL_TIMING_COMPATIBILITY_AUDIT_20261123.md`

Production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**. V294 and canonical history are unchanged.
