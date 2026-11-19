# Exact5 — Prospective custody specification v1

Status: DESIGN / NOT YET OPERATIONAL
Scope: Chispazo Clásico only
Research branch: `research/origen-v0.3-engine-20261118`

## 1. Purpose and non-claim

This specification defines an independently auditable pre-close process for preserving predictions against backdating, selective omission, replacement, or silent alteration. It does not establish predictive edge or authorize a wager. A valid custody record proves what was committed and when, not that the prediction is informative.

## 2. Roles

- **Generator:** runs the frozen candidate and exports the exact portfolio.
- **Independent custodian/witness:** receives the export, verifies target and timestamp, recomputes hashes, and retains a separate copy.
- **Evaluator:** scores the sealed portfolio only after the official result is independently verified.

A prospective evidence claim requires a custodian who is not the generator and whose receipt can be independently inspected.

## 3. Freeze before the first scored target

Hash and freeze: candidate ID/specification; source commit; dependency and environment manifest; canonical history SHA-256 and final included contest; target definition and Classic modality; expected official draw-close timestamp/time zone; portfolio schema; primary score; secondary metrics; multiplicity family; one-sided test and Holm procedure; stopping rule; minimum sample size; Exact5 anytime-valid e-process and threshold (20); and failure/restart rules.

No target may be added to the evaluation set after its result is known.

## 4. Per-target sealing sequence

1. Confirm the next eligible Classic contest and verify that its draw has not closed.
2. Record the history cutoff, strictly earlier than the target, and the history hash.
3. Run the frozen candidate once; do not manually edit output.
4. Validate the preregistered portfolio size (default 30 distinct lines), each line containing five distinct integers in 1..28; reject duplicate lines, malformed rows, wrong target IDs, or non-Classic targets.
5. Export canonical UTF-8 bytes with LF line endings. Do not round-trip through a spreadsheet.
6. Compute SHA-256 for portfolio, candidate specification, source commit identifier, and environment manifest.
7. Record UTC generation time, local time zone, synchronized clock source, and raw timestamp evidence.
8. Transfer portfolio and manifest to the independent custodian before draw close. Custodian independently recomputes hashes and records receipt time, target ID, and hash.
9. Generator and custodian retain byte-identical copies in separate locations.
10. Mark SEALED only after all prior steps pass.

A timestamp alone is insufficient: receipt, hash match, target identity, and evidence of receipt before draw close are mandatory.

## 5. Per-target record schema

Each append-only JSON record contains: schema_version; candidate_id; target_contest_id; modality; history_max_contest_id; history_sha256; source_commit; environment_manifest_sha256; portfolio_sha256; portfolio_line_count; generator_id; generated_at_utc; generator_clock_source; custodian_id; received_at_utc; custodian_clock_source; custodian_recomputed_sha256; official_draw_close_at_utc and source; seal_status; previous_record_sha256; record_sha256.

Calculate record_sha256 over canonical serialization excluding record_sha256 itself. previous_record_sha256 forms a tamper-evident chain. Retain raw portfolio and receipt alongside the record.

## 6. Append-only and corrections

- Never overwrite a sealed registration or receipt.
- Corrections append a new record referencing the invalidated record and explaining why.
- A replacement after draw close is invalid for that target and cannot enter prospective scoring.
- Failed or late seals are recorded as FAILED / LATE, never silently omitted.
- Preserve malformed and abandoned attempts in an audit log.
- Never reset the prospective sample counter after observing outcomes.

## 7. Result verification and scoring

After publication, capture the result from an authoritative source with URL, retrieval timestamp, and raw evidence. Independently verify contest ID, modality, date, and five distinct numbers. Score only the exact bytes whose hash was sealed before close. Append result evidence hash and per-target scores to a separate evaluation ledger. Corrections to result transcription are append-only events; never edit the sealed prediction. Report eligible, failed, late, missing, and corrected targets.

## 8. Evidence gates for any edge statement

Every gate must pass:

- At least 100 chronological, untouched, prospectively sealed Classic targets.
- Independent receipt before each corresponding draw close.
- Positive preregistered prequential mean log-lift versus uniform.
- Preregistered one-sided primary test passes Holm-adjusted p < 0.05.
- Exact5 anytime-valid e-value >= 20 under the frozen process.
- Two independently witnessed pre-close outputs exist before the first target is counted.
- Canonical history, code, candidate, portfolio, result, and ledger hashes verify.
- Independent review finds no leakage, post-hoc exclusions, candidate switching, or unregistered stopping.

If any gate fails, classification remains RESEARCH_ONLY / NO EDGE. Thresholds cannot be weakened after outcomes are seen.

## 9. Dry-run acceptance checklist

Run two non-scored dry runs and verify:

- [ ] Generator and custodian independently calculate identical SHA-256 values.
- [ ] A changed byte fails hash verification.
- [ ] Duplicate lines, repeated numbers, out-of-range numbers, and wrong target IDs are rejected.
- [ ] A timestamp after draw close is rejected.
- [ ] Missing custodian receipt prevents SEALED status.
- [ ] A second registration cannot overwrite the first for the same target.
- [ ] Corrections append events and preserve originals.
- [ ] Ledger chaining detects deletion, reordering, and mutation.
- [ ] Recovery after interruption preserves all prior sealed bytes.

Dry-run success validates custody only; it is not prospective predictive evidence.

## 10. Current blockers

This design is not operational until an independent custodian and separate retention location are designated; trusted clock and official draw-close reference are fixed; candidate package and environment manifest are frozen; two witnessed dry runs pass; primary statistical plan and executable e-process are frozen; and official Classic result source and correction policy are independently verified.

Until then, no prospective target is sealed and no prospective sample count may be claimed.


## 11. Implementation hardening addendum

The executable verifier requires an exact v1 field set, including candidate_spec_sha256; rejects identical generator/custodian identifiers; requires receipt strictly after generation and both before close; and verifies the complete ordered hash chain. A separately retained expected final ledger-head hash can detect tail truncation. The head anchor must itself be stored outside the ledger (for example, with an independent custodian or signed timestamp service).

SHA-256 chaining is tamper-evident only relative to a trusted external anchor. It is not a digital signature, trusted timestamp, proof of identity, or immutable storage. The current code verifies supplied assertions; it cannot authenticate the clock source, custodian identity, or official close-time source. No real registration is SEALED until independent external custody and timestamp evidence exist.
