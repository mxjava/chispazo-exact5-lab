# Exact5 detached-attestation contract v1

Each attestation is canonical UTF-8 JSON with exactly these fields:

- schema_version: `exact5.detached_attestation.ed25519.v1`
- attestation_type: `schedule_source`, `target_manifest`, `ledger_head`, `pmf_custody`, `timestamp_token`, or `official_result`
- subject_sha256: SHA-256 of exact subject bytes
- key_id: identity in the out-of-band trust policy
- issued_at_utc: RFC3339 UTC ending in Z
- claims: exact role-specific claims
- signature_ed25519_b64: Ed25519 signature over canonical JSON excluding only the signature field

The caller supplies raw 32-byte Ed25519 public keys and six non-overlapping role allowlists. The verifier rejects reused key IDs and reused public-key material across roles. It fingerprints the exact trust policy. Key ownership, revocation, certificate status and independence are external governance requirements.

## Role bindings

- schedule_source: captured official schedule bytes and target/date/modality/timezone/21:00 close/source URI/retrieval time.
- target_manifest: complete expected Classic target-manifest bytes, count, modality and timezone, attested before first close.
- ledger_head: complete ledger bytes, target-manifest hash, record count and final record hash, attested after last close.
- pmf_custody: pre-seal commitment plus PMF/history/spec/lock/environment/source-commit hashes, custodian identity, timestamp-token hash and receipt time.
- timestamp_token: timestamp-token bytes and the pre-seal commitment imprint at PMF generation time.
- official_result: raw official result-source bytes plus parsed contest/date/modality/combination/source URI/capture time.

## Pre-seal commitment

The pre-seal commitment includes PMF hash, full history snapshot hash/metadata, candidate specification, dependency lock, environment, source commit, target ID/date/Classic modality/close/timezone, schedule source hash/retrieval, generator identity and generation time. The timestamp-token and custodian-attestation hashes are excluded to avoid circular hashing; the custody attestation separately binds the timestamp-token hash and receipt time.

## Operational rule

Never store private keys in the repository, test fixtures, ZIP or same custody channel as evidence. Do not treat a locally generated key as independent. Use separate controlled owners/systems for schedule, target-manifest, ledger, PMF custody, timestamp and result roles. Preserve raw bytes; never replace them with a copied hash string.
