# Official Chispazo daily-pair structure audit — 2026-11-23

**Status:** STRUCTURAL PATTERN OBSERVED; MODALITY NOT ASSERTED  
**Scope:** Research-only description of the preserved official CSV snapshot.  
**Source:** `https://loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv`  
**Retrieved:** 2026-11-22T18:32:06.451954Z  
**Source SHA-256:** `e5d042b0779cc4d271636612a9a35ce8b372b82ca72a380687c914ff2f3adb0b`  
**Source size:** 377,707 bytes  
**Source header:** `CONCURSO,R1,R2,R3,R4,R5,FECHA`

## Method

The exact retained CSV bytes were parsed without reserializing the source. Rows were grouped by calendar date after parsing `FECHA` as `DD/MM/YYYY`. For dates on or after 2017-09-25, the audit checked whether each observed date had exactly two contest IDs, whether those IDs were consecutive, and whether the first was odd and the second even. It separately checked whether the union of observed post-transition IDs was contiguous.

This is a structural analysis only. The CSV does not include a modality column. No row is relabelled as De las Tres or Clásico by this report.

## Results

- Total source rows: 12,388.
- Distinct dates in the full source: 9,145.
- Single-row dates in the full source: 5,902.
- Two-row dates in the full source: 3,243.
- Dates on/after 2017-09-25: 3,233.
- Post-transition dates with exactly two rows: 3,233 / 3,233.
- Post-transition dates with consecutive odd/even IDs: 3,233 / 3,233.
- Post-transition ID range: 5923–12388.
- Post-transition IDs contiguous: yes; 6,466 IDs, no gaps.
- Post-transition date anomalies: 0.
- The five earlier two-row dates (1999–2002) are outside the post-transition rule and are not silently reclassified.

The published Lotería Nacional schedule lists De las Tres at 15:00 and Clásico at 21:00. Official daily results/masks identify both named modalities and provide anchors for independent review. These facts make an odd/even modality mapping a plausible *candidate*, but this structural report itself does not prove the mapping for every historical row.

## Required next validation

1. Collect official daily result masks across the transition boundary and representative/full coverage thereafter.
2. Match both contest IDs and both result combinations per date to the corresponding explicitly named modality on the official mask.
3. Record source URL, original bytes/digest, draw date, contest ID, named modality, winning numbers, and row locator for every match.
4. Quantify missing masks, changed/corrected masks, exceptions, and any date with a nonstandard schedule; do not interpolate.
5. Have an independent reviewer reproduce the complete mapping from original sources and sign the derived table.
6. Only then consider publishing a Classic-only ordinal manifest with preserved global IDs and row locators. Authenticate the manifest separately; a structural parity rule is not a trust root.

## Guardrails

- Do not call the parity pattern an explicit official modality field.
- Do not treat a candidate mapping as a signed or authenticated Classic-only manifest.
- Do not feed this report into model training, retrospective ranking, or prospective scoring.
- Do not modify `data/history/Chispazo_through_12249.csv`, V294, or `main`.
- Canonical reconciliation remains `BLOCKED_CANONICAL_CONFLICTS` due to ten discrepancies. This report does not resolve them.
- Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Official references

- Historical data index: https://loterianacional.gob.mx/DatosAbiertos/NumerosGanadores
- Official CSV: https://loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv
- Chispazo schedule: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- Official results and recent masks: https://www.loterianacional.gob.mx/Chispazo/Resultados
