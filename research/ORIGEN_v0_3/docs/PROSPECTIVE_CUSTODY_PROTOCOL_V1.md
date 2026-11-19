# Exact5 — prospective prediction custody protocol v1

Status: protocol specification; not yet operationally certified
Scope: Chispazo Clásico only
Branch: `research/origen-v0.3-engine-20261118`
Purpose: establish auditable, pre-close, untouched prospective evidence. This protocol does not claim an edge and does not authorize model promotion.

## 1. Non-negotiable separation

- V294 remains frozen and is not silently retuned.
- The canonical history remains read-only and byte-for-byte fixed at SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Classic is the only target stream. De las Tres rows are excluded from feature construction, warm-up, scoring and target selection.
- Every candidate, probability transformation, ticket-generation rule, scoring rule, hypothesis family, stopping rule and multiplicity correction must be frozen before the prospective evaluation window begins.
- No candidate is called predictive because it has attractive retrospective metrics or a favorable single draw.
- No replacement, patch, configuration change or parameter search is allowed after the first prospective commitment. A changed candidate starts a new prospective epoch with a new preregistration and fresh untouched targets.

## 2. Actors and separation of duties

Minimum roles:
1. **Generator** — runs the frozen code and creates the prediction payload before sales close.
2. **Independent custodian** — receives the payload and verifies timestamp, hash and immutability; must not be the person selecting/tuning the model.
3. **Result auditor** — after official result publication, independently retrieves the official Classic result and reconciles contest ID, date, modality and five-number set.

One person may operate the software, but the generator must not self-certify independent custody. If genuinely independent custody is unavailable, mark the output `CUSTODY_NOT_INDEPENDENT` and do not count it toward the evidence gate.

## 3. Per-contest pre-close sequence

For every eligible Classic contest:

1. Determine the next Classic contest ID and local draw date from an authoritative schedule. Record the source and retrieval time. Do not infer Classic from an unverified odd/even rule when an official contest label is available.
2. Freeze the input snapshot. Record the canonical-history SHA-256, the maximum included contest ID, row count, modality filter version and all auxiliary input hashes. The target contest and any later row must be absent.
3. Run only the preregistered candidate commit and configuration. Record Git commit SHA, dependency lock hash, runtime version, command, random seed (if any), and machine/container identity.
4. Generate a complete prediction payload. If the candidate emits a probability distribution, retain the full normalized distribution over all 98,280 five-number sets or a lossless representation from which every probability can be reconstructed. If the experiment evaluates a fixed set of lines, retain the exact ordered lines, uniqueness checks and the preregistered selection algorithm. Never replace a failed output with hand-picked lines.
5. Serialize canonical UTF-8 JSON with sorted keys, fixed numeric formatting, no NaN/Infinity, and a documented schema version. Include contest ID, Classic modality, local scheduled close time, generation timestamp in UTC, input cutoff, source hashes, code/config hashes, output payload, and status.
6. Compute SHA-256 over the exact serialized bytes. Encrypt the payload for the custodian if predictions must remain confidential until close; separately commit the plaintext hash and ciphertext hash.
7. Deliver the payload and manifest to the independent custodian before the published sales close. The custodian records receipt time from an independent trusted clock, verifies hashes, signs/attests the manifest, and stores the original bytes in append-only or version-locked storage.
8. Publish a minimal commitment record before close containing contest ID, model/version, input cutoff, payload SHA-256, ciphertext SHA-256 if applicable, trusted timestamp token/reference, and custodian attestation. Do not publish the prediction contents if doing so would disclose a live ticket.
9. After close, do not regenerate or modify the commitment. Any late, missing, malformed or post-close output is retained as a failure record, not silently repaired.

## 4. Required manifest fields

- `schema_version`
- `contest_id`, `draw_date_local`, `modality=CLASSIC`
- `scheduled_close_local`, `scheduled_draw_local`, timezone identifier
- `generated_at_utc`, `custodian_received_at_utc`, trusted timestamp reference
- `candidate_id`, `candidate_version`, `git_commit_sha`, `config_sha256`, `dependency_lock_sha256`
- `input_history_sha256`, `input_max_contest_id`, `input_row_count`, `modality_filter_version`
- `payload_sha256`, optional `ciphertext_sha256`
- `generator_identity`, `custodian_identity`, `signature_or_attestation_reference`
- `generation_status`, `custody_status`, `failure_code` (nullable)
- `prediction_payload` or immutable payload object reference

All timestamps must state their timezone and source. A self-entered timestamp or Git commit timestamp alone is not an independent trusted timestamp.

## 5. After-draw reconciliation

1. Result auditor retrieves the official Lotería Nacional result for the exact contest and saves the source document unchanged with retrieval timestamp and SHA-256.
2. Verify the official contest number, date, modality and five distinct values in 1..28. If any field is ambiguous, quarantine the target; do not score it.
3. Custodian releases/decrypts the pre-close payload. Verify its bytes against the committed SHA-256 and verify the trusted timestamp predates the official sales close.
4. Append the official result, source hash, payload hash, reconciliation outcome and score to an append-only ledger. Never rewrite previous rows.
5. Compute only the preregistered score. For full distributions use the preregistered log score/log-lift against the exact uniform baseline. For line sets report exact-hit coverage and the corresponding combinatorial baseline; do not substitute retrospective ranking metrics.
6. Record every eligible target, including misses, failures, skipped draws and custody exceptions. No selective deletion of inconvenient contests.

## 6. Failure and recovery rules

- Missing pre-close timestamp, missing custodian attestation, hash mismatch, post-close generation, ambiguous modality, future-data leakage or untracked code/config changes => quarantine the target and classify the specific failure.
- A failed run cannot be replaced by a second output for the same contest unless the preregistration explicitly defines deterministic retry behavior before the epoch starts. Preserve both the failure and any retry evidence.
- Clock drift, outage, schedule change or official draw postponement must be recorded with source evidence. The target remains excluded unless the preregistered rule explicitly handles that condition.
- Do not backfill predictions for past contests.
- Do not reset the prospective sample clock after seeing outcomes.

## 7. Evidence gates and reporting

An edge claim requires all of the following, independently verified:
- at least 100 chronological, untouched Classic OOS targets;
- positive preregistered prequential lift over uniform;
- Holm-adjusted p < 0.05 over the complete frozen hypothesis family;
- Exact5 anytime e-value >= 20 under a valid, preregistered betting/e-process construction;
- at least two sealed pre-close prospective outputs with independent custody (and the complete target ledger, not merely two favorable draws);
- clean source, code, payload, timestamp and custody hashes.

Until every gate is met, classification remains `NO_EDGE_EVIDENCE` or the appropriate failure/blocker classification. A green CI run validates implementation, not predictive performance. Historical falsification results V313–V315 do not become predictive evidence by being repeated.

## 8. Operational readiness checklist

Before starting the prospective clock, verify:
- [ ] Candidate and all parameters frozen; preregistration committed and independently reviewed.
- [ ] Generator and independent custodian identified and tested.
- [ ] Trusted timestamping and append-only storage tested end-to-end.
- [ ] Canonical serialization, hashing, signing/attestation and encryption/decryption tested.
- [ ] Official Classic contest identification and close-time source documented.
- [ ] Failure/retry rules tested, including late output and hash mismatch.
- [ ] Scoring implementation tested against hand-computed synthetic cases.
- [ ] No target outcomes are present in the input snapshot.
- [ ] Full sample ledger and independent audit procedure ready.

**Current status:** specification only. No independent custodian, trusted timestamp service, sealed prospective output or 100-draw untouched prospective ledger is certified by this document. Do not describe the prospective experiment as started until the checklist is evidenced.
