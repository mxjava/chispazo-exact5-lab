# ORIGEN search-path integrity snapshot audit — 2026-11-24

## Reproducible defects

The search-path auditor previously called `audit_ledger(path)` and then reopened
the path with `read_text()` to interpret events. Two failures followed:

1. If the ledger was malformed JSON or invalid UTF-8, `audit_ledger` correctly
   returned BLOCKED, but `audit_search_path` continued parsing and raised
   `JSONDecodeError` or `UnicodeDecodeError` instead of returning a blocked
   audit result.
2. A file could be replaced after the integrity check and before the second
   read. The auditor could then report the integrity state of one byte sequence
   while evaluating event semantics from another.

## Correction

- Added `audit_ledger_bytes(raw)`, which audits one exact built-in byte string.
- `audit_ledger(path)` now reads bytes once and delegates to that helper.
- `audit_search_path(path)` reads one snapshot, audits that same snapshot, and
  stops before semantic parsing whenever integrity is not PASS.
- Malformed JSON and invalid UTF-8 now produce a structured BLOCKED result.
- Three adversarial regressions cover malformed JSON, invalid UTF-8, and
  replacement of the on-disk path after the snapshot has already been audited.

## Scope and remaining limits

This closes a local parser crash and a path-level TOCTOU mismatch. It does not
authenticate the ledger writer, clock, completeness, external anchoring, TSA,
signatures, physical custody, or draw provenance. A valid local hash chain can
still be replaced in its entirety. The independent trust adapter remains
fail-closed and production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
