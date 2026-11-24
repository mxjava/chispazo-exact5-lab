# ORIGEN CLI strict JSON boundary audit — 2026-11-24

## Reproducible defect

The CLI used Python's default `json.load` / `json.loads` for protocol, Holm, evaluation, null-benchmark and manifest inputs, and for JSONL frame registries. The default decoder silently accepts duplicate object keys (last value wins) and accepts the non-standard constants `NaN`, `Infinity` and `-Infinity`.

This creates ambiguous input semantics at a user-facing research boundary. In particular, a duplicated gate or protocol field can be silently overwritten before validation; a duplicated hypothesis identifier can silently replace an earlier p-value. The typed library validators cannot recover the discarded duplicate.

## Change

- Added one strict JSON decoder shared by single-document and JSONL CLI ingestion.
- Reject duplicate keys at every nesting level.
- Reject non-finite JSON constants.
- Convert malformed/ambiguous document input into stable `ValueError` outcomes; JSONL errors retain the physical line number.
- Added six adversarial tests, including nested duplicate gates, duplicate protocol fields, all three non-finite constants, and JSONL duplicate-key handling.

This is input determinism and parser hardening only. It does not authenticate the file author, establish preregistration time, validate external custody, or authorize EDGE_SUPPORTED.

## Validation

CI is triggered on the research branch after the commit. Results will be reported only against the exact resulting HEAD.
