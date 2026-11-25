# ORIGEN V3 signed custody-receipt verifier — research only

## Purpose

The new custody_receipt_verifier_v3.py module adds a cryptographic interface for one detached custody record. It composes the existing V3 receipt-policy bridge with the existing Classic custody-record validator, then verifies a custodian Ed25519 signature under the same signed V3 key/role/artifact matrix.

The input is the original receipt bytes, the exact canonical custody-record bytes (including one LF terminator), the exact portfolio bytes, a detached 64-byte Ed25519 signature, and the signed V3 policy envelope. The verifier never accepts a caller-constructed VerifiedTrustPolicyV3 object.

## Binding contract

The verifier requires all of the following:

1. The original trust receipt verifies under the V3 policy and its root attester has the signed RECEIPT-ROOT-ATTESTER / TRUST-RECEIPT-ROOT-ATTESTATION authorization.
2. The custody record is bounded canonical UTF-8 JSON, has no duplicate keys or floats, has exact record schema and digest, and ends in exactly one LF.
3. Custody timestamps use canonical UTC RFC3339 with seconds and Z; permissive datetime.fromisoformat() spellings are rejected before the legacy custody validator is called.
4. verify_seal_record() verifies the record against the exact portfolio bytes, including the Classic 21:00 slot and pre-close chronology.
5. The record target and close, candidate digest, environment digest, generator ID and portfolio digest match the signed receipt's target/commitments/output-seal claims.
6. Exactly one receipt custodian claim matches the record custodian ID; its role is external-custodian, and its receipt_sha256 equals SHA-256 of the exact original custody-record bytes.
7. The custodian key ID is distinct from the pinned V3 policy root key ID, the receipt root-attester key ID, and every physical signer key ID. A delegated custodian key cannot reuse the root key identifier even if its public-key bytes differ.
8. The V3 policy authorizes (custodian_id, custodian_key_id, external-custodian, EXACT5-CUSTODY-RECORD). The key must be present, unrevoked and valid at the single normalized verification instant.
9. The detached signature verifies over the domain-separated canonical payload from canonical_custody_signature_payload(). That payload binds the exact custody-record digest, its internal record digest, the exact receipt digest, custodian identity/key ID, role, artifact type, target and portfolio digest.

## Signature payload

Domain: origen.custody-receipt-signature.v3.

The canonical ASCII JSON payload has exactly these fields:

- domain
- record_sha256
- record_internal_sha256
- receipt_sha256
- custodian_id
- custodian_key_id
- role
- artifact_type
- target_contest_id
- portfolio_sha256

The helper returns payload bytes only; it does not create a trusted signature or authenticate any identity.

## Deliberate limits

A successful signature check is only a cryptographic match relative to the caller-supplied V3 root, root key ID, sequence floor and clock. It does not prove:

- that the root belongs to Lotería Nacional, SEGOB, or any other institution;
- that the custodian is a real person/entity, was appointed, or is administratively independent;
- that the custody system, storage, clock, receipt origin or delivery channel is controlled independently;
- that the detached custody signature existed before the draw close; it has no RFC 3161 timestamp binding yet;
- that the sequence floor is held in an external monotonic store;
- RFC 3161 time, nested physical signer signatures, external ledger inclusion/consistency/witnesses, or physical-event truth;
- that all custodian claims or both output seals have been independently covered (this verifier inspects one matching custody record);
- any prospective predictive edge.

The result therefore remains exactly BLOCKED_PROVENANCE. The existing verify_independent_provenance() gate is still invoked by the receipt-policy bridge. No production capability is introduced.

## Test isolation

test_custody_receipt_verifier_v3.py uses generated Ed25519 keys and synthetic records only. It covers valid verification plus record-byte mutation, portfolio mutation, signature tampering, receipt-to-record digest mismatch, key-ID aliasing, unknown keys, unauthorized roles, policy-root/delegate key reuse, noncanonical timestamps, duplicate JSON keys, and a stateful caller timezone.

No synthetic key, certificate, custody record, timestamp or ledger fixture is an institutional artifact.

## Key-identifier namespace hardening

The V3 policy parser rejects any delegated issuer key identifier equal to the externally expected root key identifier, regardless of whether that key is used for receipt attestation, physical evidence, or custody. The custody verifier retains a role-specific guard as defense in depth. The policy root and delegated issuer keys occupy separate trust roles; reusing the same identifier is ambiguous even when the underlying public-key bytes differ. Synthetic signed-policy regressions cover both receipt-attester and custodian paths. This is structural key-ID separation only; it does not authenticate the root or custodian identity.
