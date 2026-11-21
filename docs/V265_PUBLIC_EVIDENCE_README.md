# V265 Public Physical Evidence Audit

This folder and its companion script contain a **documentary procedure-timeline audit**, not draw-level physical observations.

## Inputs

- `data/physical-metadata/V265_PUBLIC_PROCEDURE_TIMELINE_20261121.json` — manually transcribed activity order and public-document availability status from the current public SGVO-PRO-05 Rev. 39, the Chispazo regulation, and the 2018–2024 government-management report.
- No synthetic draw records, sphere weights, RFID reads, machine IDs, or extraction timestamps are generated.

## Reproduce

```bash
python scripts/audit_v265_public_evidence.py \
  --input data/physical-metadata/V265_PUBLIC_PROCEDURE_TIMELINE_20261121.json \
  --output reports/V265_PUBLIC_EVIDENCE_AUDIT_20261121.json

pytest -q tests/test_v265_public_evidence_audit.py
```

The expected status is `BLOCKED_PUBLIC_DRAW_LEVEL_PHYSICAL_DATA`. The audit distinguishes the pre-close inspection/planned-case confirmation from post-close weighing, final case selection, loading, draw video, CS-11, and incident records. Policy 30 requires recording from sphere weighing through the draw and an edited draw-only copy as an Acta attachment; no original per-draw recording was located publicly.

## Interpretation boundary

This evidence establishes documented operational controls and the timing of their records. It does **not** establish a physical bias or predictive edge. The V265 regime evaluator only uses machine and sphere-set labels; its output must not be treated as proof of bias. Promotion still requires the project's exact-set prequential OOS, multiplicity, and anytime e-value gates, and physical-mechanism claims require per-draw weights, verified IDs, extraction order, and timestamps.
