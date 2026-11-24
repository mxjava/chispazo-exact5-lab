# ORIGEN CLI anytime-e-value forwarding audit — 2026-11-24

## Defect

The library evaluator accepts `exact5_max_log_e_value`, but the `origen evaluate` CLI did not forward the corresponding JSON field. Consequently, CLI-driven evaluations always omitted the supplied value and could not faithfully report the declared threshold input.

## Minimal correction

- Forward optional `exact5_max_log_e_value` from the strict-decoded evaluation document.
- Add an explicit `exact5_e_value_provenance` output marker: `CALLER_DECLARED_UNVERIFIED` or `NOT_PROVIDED`.
- Clarify in the evaluator interpretation that a caller-supplied e-value is not independently verified and must be recomputed from sealed pre-close artifacts.
- Add CLI integration tests for forwarding and omission.

This fixes CLI/library parity only. It does not authenticate or recompute the e-value, validate the betting strategy, or permit EDGE_SUPPORTED. Caller-provided values remain untrusted claims.
