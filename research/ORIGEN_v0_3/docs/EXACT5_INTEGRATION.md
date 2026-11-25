# ORIGEN x Exact5 integration boundary

The adapter creates a read-only research packet from canonical Chispazo history. It checks required columns, five unique values in 1..28, unique contiguous contest IDs and by default the exact expected SHA-256 of the canonical CSV. Records are sorted chronologically in memory only.

It generates ten research frames and descriptive frequency, sum, parity and adjacent-draw overlap diagnostics. Output is labelled RESEARCH_ONLY_NO_EDGE.

It does not modify or re-export the canonical CSV, read or modify V294 parameters, generate combinations, claim predictive advantage, calculate inferential p-values from retrospective patterns, or certify external custody.

Run from repository root:

    $env:PYTHONPATH = '.\research\ORIGEN_v0_3\src'
    python -m origen.exact5_adapter --history .\data\history\Chispazo_through_12249.csv --out .\research\ORIGEN_runs\baseline_20261118

For a noncanonical sensitivity dataset, explicitly pass --allow-noncanonical-hash. Never point output into data/history or a V294 directory.
