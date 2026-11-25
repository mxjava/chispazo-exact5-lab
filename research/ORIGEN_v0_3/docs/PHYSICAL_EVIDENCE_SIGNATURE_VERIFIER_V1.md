# ORIGEN v0.3 — nested physical-evidence signature verifier v1

**Classification:** RESEARCH ONLY. This verifier cannot authenticate provenance or enable production.

## Scope of this increment

The physical-evidence manifest parser already checks declarations and cross-references, but its signature entries contain only a SHA-256 digest of the detached signature. This increment adds a verifier that consumes:

- the exact canonical manifest bytes;
- the exact original bytes for every declared physical artifact;
- the exact detached signature bytes for every declared signature;
- the original signed trust-policy envelope;
- a separately supplied root public key, expected root key ID, minimum policy sequence, and verification time.

The verifier rechecks the policy envelope from its original bytes. It does not accept a caller-constructed VerifiedTrustPolicy object.

## What is actually verified

1. The manifest passes the existing strict structural parser.
2. The artifact-byte map contains exactly the manifest artifact digests.
3. Every supplied artifact has the declared byte length and SHA-256.
4. The signature-byte map contains exactly the declared signature digests.
5. Every supplied signature has the declared SHA-256.
6. The signed policy envelope verifies against the supplied Ed25519 root and sequence floor.
7. Each nested signature is Ed25519 and its subject/key pair is present, unrevoked, and within the policy validity interval at the supplied verification time.
8. Every nested signature verifies over the common canonical manifest-claims payload.

The signature payload uses the domain string origen.physical-evidence-signature.v1 and contains the complete manifest claim set. The signature_sha256 fields are omitted from the signed payload to avoid a circular dependency; the detached signature bytes are independently bound by those SHA-256 claims.

## What is deliberately not verified

- The deployment root key, expected key ID, sequence floor, or verification clock are independently provisioned. All are caller-supplied and unauthenticated.
- Policy v1 has no signer-role authorization mapping. The signer identity/key is cryptographically matched, but the role string remains a signer-supplied claim. The result is UNVERIFIED_CLAIM_ONLY.
- The policy's revocation list is only as fresh as the caller-supplied policy envelope and clock.
- No RFC 3161 token, TSA certificate path, nonce, imprint, or trusted-time authority is verified.
- No external transparency-log inclusion proof or independently anchored ledger-head continuity is verified.
- No custody-receipt signature, custodian identity, transfer event, storage immutability, or independent custody is verified.
- No physical event is proven merely because a document's bytes and signature verify.
- The module is not wired into verify_independent_provenance. That adapter remains fail-closed and the returned status remains BLOCKED_PROVENANCE.

## Adversarial fixture separation

The tests generate fresh synthetic Ed25519 keys in-process. Synthetic keys and signatures are used only to exercise parsing, byte binding, key lookup, revocation checks, and signature verification. They are not Lotería Nacional, SEGOB, OIC, TSA, custodian, or institutional identities and must never be reused outside tests.

The adversarial suite covers exact artifact bytes, signature digest mismatch, a re-hashed but invalid signature, role-claim substitution, missing policy key, revoked key, wrong root, and extra artifact-map entries.

## Next external interfaces

This increment deliberately stops before claiming end-to-end verification. The next separately reviewed interfaces must consume original external proof bytes and validate:

1. role authorization from an independently provisioned identity/role policy;
2. actual RFC 3161 tokens and TSA certificate/revocation chains;
3. transparency-log inclusion paths and signed, independently anchored log checkpoints;
4. signed custody receipts, custodian identities, transfer continuity, and independent retention;
5. original physical artifacts and the procedure-specific cross-document facts.

Each interface must remain fail-closed when its trust source, bytes, clock, revocation state, or external anchor is absent or ambiguous.

## Validation boundary

A passing unit test or CI workflow demonstrates only that this research implementation behaves as tested against synthetic fixtures. It does not demonstrate institutional provenance, a real draw's physical records, prospective custody, or predictive edge.
