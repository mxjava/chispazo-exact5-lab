# ORIGEN search-ledger strict JSON audit — 2026-11-24

## Defect reproduced

The local hash-chain ledger used Python's permissive JSON defaults. json.loads
accepted duplicate object keys and non-standard NaN/Infinity constants;
json.dumps emitted non-finite floats unless allow_nan=False. The audit
reconstructed a Python object and hashed its canonical re-serialization, so a
non-standard ledger line could be accepted as PASS when its hashes were
computed using the same permissive representation. Raw duplicate-key
representations were also silently collapsed to the final value.

A second append-boundary issue was identified: a valid final record without a
line-feed terminator could pass the old audit, after which an append would
concatenate the next JSON record onto the same physical line.

## Correction

- Canonical serialization now permits only exact built-in JSON types, finite
  floats, text object keys and valid UTF-8 strings; allow_nan=False is explicit.
- Ledger parsing rejects duplicate keys and non-standard JSON constants.
- Each record must have the exact envelope fields, valid lowercase SHA-256
  fields, a valid event shape and byte-for-byte canonical JSON serialization.
- Ledger files with CR characters or an unterminated final record are blocked.
- Appends reject dict subclasses and nested values outside the deterministic
  JSON type set. Existing duplicate-event checks now use the strict parser.
- Six adversarial regressions cover NaN/Infinity, dict subclasses, duplicate
  keys, a hash-consistent non-finite record, noncanonical serialization and
  a missing final line feed.

## Security boundary that remains

The hash chain is still local and self-contained. It cannot prove completeness,
prevent whole-file replacement, establish a trusted clock, authenticate event
authors, or prove that omitted events never occurred. audit_ledger PASS is
integrity of the retained canonical chain only, not independent custody or
prospective eligibility. The independent trust adapter remains fail-closed.

No model parameters, V294, canonical history, main, or production gates were
changed.
