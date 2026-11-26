# V265 modality isolation correction

The physical-regime scanner must not infer draw modality from contest order, row order, or the fact that two draws share a date.

## Required input contract

Run the scanner only against a source CSV with an explicit modality field:

```bash
python -m src.v265.CHISPAZO_V265_PHYSICAL_REGIME_SCANNER \
  --history path/to/history.csv \
  --modality-column MODALIDAD \
  --early-value "DE LAS TRES" \
  --classic-value "CLASICO"
```

The labels above are examples; supply the exact values present in the source. The scanner rejects a missing modality column, null/blank modality values, duplicate contest IDs, unexpected modality labels, and ambiguous same-day duplicate rows.

All persistence, periodic and motif analyses are run on explicitly labelled Clásico rows only. Same-day carryover is computed only for dates containing exactly one explicitly labelled early draw and one explicitly labelled Clásico draw. Pair direction is determined by the labels, never by contest number or CSV row order.

The repository's canonical historical CSV currently has no modality column. It therefore cannot be used for this V265 scanner until a separately sourced, auditable modality field is added. Do not infer it or silently produce a mixed-modality result. This correction does not modify the canonical history, V294, model parameters, or production gates.
