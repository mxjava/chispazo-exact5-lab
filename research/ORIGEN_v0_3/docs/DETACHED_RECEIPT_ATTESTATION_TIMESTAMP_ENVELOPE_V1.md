# ORIGEN — detached receipt-attestation RFC 3161 proof envelope v1

**Classification:** synthetic-interface research only. Successful verification remains BLOCKED_PROVENANCE; production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.

## Defect and non-circular construction

The V1 receipt contains receipt_attestation.timestamp_proof_sha256 and a matching trusted_time_proofs[] entry inside the payload signed by the receipt issuer. If that digest is intended to identify an RFC 3161 token whose message imprint covers the issuer's signature bytes, the dependency is circular:

- the issuer signature covers the token digest;
- the token digest depends on the token;
- the token's signed imprint depends on the issuer signature.

This module does not omit, rewrite, or weaken any signed V1 field. It introduces a detached transport envelope that is not part of the issuer-signed receipt.

The detached envelope carries:
- receipt_sha256: SHA-256 of the exact original canonical receipt bytes;
- signature_sha256: SHA-256 of the exact Ed25519 signature bytes decoded from receipt_attestation.signature_b64;
- token_sha256: SHA-256 of the exact DER RFC 3161 token bytes;
- authority_id: identifier resolved through the root-signed TSA authorization policy;
- expected_nonce: positive request nonce matched against the TSA-signed token;
- token_der_b64: canonical Base64 of the exact DER token.

Its exact schema version is origen.receipt-attestation-timestamp-proof.v1. The raw envelope must be bounded canonical ASCII JSON, with unique keys, exact field set, canonical Base64, bounded token bytes and a positive signed-64-bit nonce.

## Verification sequence

inspect_signed_root_attestation_chain_with_detached_receipt_timestamp():

1. Parses and validates the detached envelope from its original bytes.
2. Calls the existing policy → receipt → independent-provenance → two output-seal integration. The existing independent adapter must still return BLOCKED_PROVENANCE.
3. Recomputes the exact receipt SHA-256 and compares it with the envelope.
4. Extracts the issuer signature bytes from the strictly parsed receipt, recomputes their SHA-256 and compares it with the envelope.
5. Re-verifies the root-signed TSA policy against the exact trust-policy envelope digest and sequence already verified by the root chain.
6. Resolves the envelope authority ID; rejects missing, revoked, out-of-validity, wrong-root or disallowed-policy-OID authorities.
7. Verifies the exact DER RFC 3161 token against the exact issuer signature bytes, including the TSA CMS signature, message imprint, signer chain, nonce and pinned root fingerprint.
8. Requires genTime == receipt_attestation.signed_at_utc, requires RFC 3161 accuracy, and requires genTime + accuracy < CLASSIC draw close.
9. Returns diagnostic evidence only. The top-level result remains BLOCKED_PROVENANCE.

The receipt's embedded V1 timestamp_proof_sha256 is retained and reported as legacy_embedded_proof_reference_sha256, but it is not used as the token binding. The new detached proof is bound by the exact receipt digest and by the TSA token's message imprint over the issuer signature. The embedded V1 pointer remains a signed declaration, not an independently authenticated reference.

## Why the envelope itself is not signed

The sidecar is an untrusted transport wrapper, not a new trust authority. The verifier does not trust its digest or declarations: it recomputes the receipt and signature digests from original bytes, recomputes the token digest, and cryptographically verifies the TSA token against those exact signature bytes. Replacing a wrapper field cannot change the verified receipt signature or TSA imprint.

This does not establish who collected, transmitted, stored or presented the sidecar. It also does not authenticate the nonce request's origin. Those are separate custody and acquisition controls and remain explicit blockers.

## Deliberate limits

- Deployment root key, key ID, anti-rollback floor and verification clock remain caller-supplied.
- TSA root certificate and policy are only trusted relative to that caller-pinned root; institutional designation and provisioning are not established.
- TSA revocation freshness (CRL/OCSP), complete RFC 5280 validation and legal authorization remain incomplete.
- The V1 embedded timestamp proof reference remains unauthenticated as a pointer; the detached token is independently verified instead.
- Nested physical signer and custodian signatures, identities and role authorization are not verified by this module.
- External ledger inclusion/head anchoring, independent witnesses, original physical records, signed CS-11/weighing strip, 28 sphere measurements, calibration, machine/set assignment and custody are not authenticated.
- No real institutional TSA token, certificate, root key, receipt, physical evidence or custody record is included. Tests use ephemeral synthetic keys, certificates and CMS tokens.

## Diagnostic consistency invariant

After the detached receipt-attestation token verifies, the returned top-level
inspection, its nested root/output-seal inspection, and the nested root-chain
inspection expose the same remaining-blocker tuple. The blocker
RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED is removed only from
those projections after exact token/imprint verification; the independent
provenance status remains BLOCKED_PROVENANCE and the detached-envelope,
nonce-origin, institutional provisioning, custody, and physical-evidence
blockers remain explicit.

## Synthetic adversarial tests

The new tests cover exact receipt/signature/token digest binding, message-imprint binding, nonce mismatch, unlisted authority, unauthorized OID, genTime mismatch, absent accuracy, noncanonical JSON, duplicate JSON keys, unknown fields and invalid nonce type. The fixtures are generated in tests and are not institutional evidence.

## Guardrails

- PR #13 remains OPEN/DRAFT and isolated.
- This work is stacked as a research-only child of PR #51; no merge or promotion.
- No writes to main.
- V294 and data/history/Chispazo_through_12249.csv remain unchanged.
- The independent-provenance adapter is unchanged and can return only BLOCKED_PROVENANCE.
- Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
