# Causal history

`Chispazo_through_12249.csv` is the frozen causal baseline used for the target-12250 reconstruction.

Rules:

- The history used for target `T` must end at exactly `T-1`.
- Never insert the target result before freezing the target prediction.
- New results are appended only after external verification with `src/data/append_verified_result.py`.
- Verification source and timestamp are recorded in `provenance.csv`.
