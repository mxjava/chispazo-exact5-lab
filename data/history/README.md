# Causal history

`Chispazo_through_12249.csv` is the frozen causal baseline used for the target-12250 reconstruction. Its bytes must remain unchanged unless a separately authorized, verified data migration is approved.

## Causal and provenance rules

- The history used for target `T` must end at exactly `T-1`.
- Never insert the target result before freezing the target prediction.
- Chispazo Regulation Article 8 defines the official winning results as those recorded in the signed Article 15 Acta. Website and results-mask publications are expressly informational only.
- A public result URL and a five-number combination are not sufficient evidence for a canonical append.
- The original Acta bytes, contest identity/modality, required signatures and authority, supporting records, and independent custody must be verified before a result is eligible for canonical history.
- `src/data/append_verified_result.py` is intentionally **fail-closed and disabled** until an independently reviewed official-Acta verifier is implemented and integrated. It currently makes no file changes.
- `provenance.csv` is referenced as the intended provenance ledger but is **not currently tracked in this repository**. Do not claim that source/timestamp provenance has been recorded for existing rows.

The frozen historical CSV remains an experimental baseline, not a substitute for primary Acta provenance. Do not infer that every historical row has been independently reconciled to a signed Acta.
