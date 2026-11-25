# ORIGEN — trust-anchor provisioning and independent-provenance contract v1

**Classification:** design contract / research-only. This document does not provision trust, create an institutional identity, or enable production.

## 1. Audit result of the current V3 integration

The current receipt-policy integration is fail-closed in the following narrow sense:

1. `verify_signed_trust_policy_v3` verifies canonical policy-envelope bytes and the root signature relative to caller-supplied root public-key bytes, root key ID, policy domain, minimum sequence and verification time. It returns a `VerifiedTrustPolicyV3` object containing the signed role matrix.
2. `verify_receipt_attestation_with_policy_v3` passes the verified policy payload to `verify_receipt_attestation`, checks the exact receipt issuer/key/role/artifact authorization against the signed role matrix, and calls `verify_independent_provenance` with the original receipt bytes.
3. The integration accepts only the exact `ProvenanceStatus.BLOCKED_PROVENANCE` result. A future or injected non-blocked status raises `RuntimeError`; the independent gate has no authenticated status to issue.
4. The V3 custody verifier preserves that exact blocked state. A valid root signature or signed role authorization is not promoted into independent provenance.

This separation is intentional. `VerifiedTrustPolicyV3` proves that a policy envelope verifies against the pins and clock supplied to the verifier. It does not prove that those pins, the clock, or the issuer identity were provisioned by Lotería Nacional, SEGOB, or another institution. The independent-provenance gate does not currently consume `VerifiedTrustPolicyV3`, and it must not do so merely to clear the blocked status.

## 2. Current caller-controlled inputs — explicit blockers

The current public API still receives these values from the caller:

- pinned root public-key bytes;
- expected root key ID;
- expected policy domain;
- minimum accepted policy sequence;
- verification time.

Therefore the current verifier can establish only a cryptographic match **relative to those inputs**. It cannot establish authentic deployment provisioning, durable anti-rollback state, or an authenticated clock. Passing the same values through another wrapper does not change their trust origin.

Do not describe the root as externally provisioned or institutional merely because it is passed in a parameter named `pinned_root_public_key_bytes`.

## 3. Required out-of-band bootstrap ceremony

A production-capable deployment would require a separate bootstrap ceremony, not a command-line flag, environment variable, repository constant, or caller-supplied JSON object.

### 3.1 Trust-anchor enrollment

1. Generate or import the policy-root signing key under an approved institutional key-management process; retain the private key in an HSM or equivalent controlled signing boundary.
2. Obtain the root public key and key ID through a channel independent of the application repository and the operator who deploys the application.
3. Verify the public-key fingerprint in a two-person ceremony against an institutionally signed provisioning record. Record the issuing authority, key custody, key purpose, domain, activation time, expiration/rotation policy and emergency revocation path.
4. Bind the root key to the exact policy domain `CLASSIC_PHYSICAL_POLICY_DOMAIN`. A root pinned for one domain must not silently authorize another.
5. Store the verified public pin in deployment-controlled, integrity-protected configuration. Runtime callers may select a deployment profile, but may not replace the pin or its key ID.

The bootstrap record itself must be retained with original bytes, signature chain, acquisition channel, approvers and SHA-256. A hash computed by the application is an integrity identifier, not proof that the institution issued the record.

### 3.2 Anti-rollback state

The minimum policy sequence must come from durable state established by the bootstrap ceremony, not a caller-provided integer.

Required state is scoped by policy domain and root key ID and contains at least:

- highest accepted policy sequence;
- SHA-256 of the exact accepted canonical envelope bytes;
- acceptance time from the trusted clock;
- root-key generation/rotation identifier;
- source provisioning-record digest;
- audit reference for the state transition.

The update operation must be atomic and monotonic (compare-and-set or equivalent). A lower sequence is rejected; an equal sequence with different envelope bytes is rejected; an equal sequence with the same envelope digest is idempotent. State must survive process restart, host replacement and deployment rollback.

Suitable implementation classes could be a hardware monotonic counter or an authenticated append-only state service with witnessed checkpoints. A normal local file, environment variable, database row without rollback protection, or repository commit alone is insufficient.

Root rotation must use a separately reviewed transition signed by the old root and the new root (or a documented recovery ceremony with equivalent independent approval). Never reset the sequence to zero during rotation. A compromised or revoked root must not be silently re-enrolled under the same key ID.

### 3.3 Authenticated verification time

The current `verification_time` parameter is caller-controlled. A production adapter must obtain time from a deployment-controlled trusted clock interface whose source and synchronization state are authenticated and monitored. NTS-protected time or a hardware-backed clock with externally anchored audit records are possible design inputs, not claims that such infrastructure currently exists.

The verifier must receive one immutable UTC instant per operation. It must reject unavailable, stale, unsynchronized or rollback-detected clock state. RFC 3161 token time is a separate evidence source and does not authenticate the application verification clock.

## 4. Future API boundary

The current low-level function should remain available for isolated cryptographic tests and research fixtures. Production-facing code must not call it with arbitrary runtime values.

A future high-level boundary should accept an opaque deployment context created only by a verified bootstrap component, for example:

```python
class ProvisionedTrustContext:
    # Created only by the deployment bootstrap boundary.
    # Contains a verified root pin, domain, monotonic state handle,
    # authenticated clock handle, and provisioning-record digest.
    ...

def verify_receipt_with_provisioned_policy(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    trust_context: ProvisionedTrustContext,
) -> VerifiedReceiptPolicyResult:
    ...
```

The context is a capability handle, not a serializable bundle of root bytes and sequence values. It must not expose a public constructor that lets arbitrary callers manufacture a trusted context. The implementation must validate the bootstrap provenance and live state handle at use time.

The policy verifier must atomically compare and persist the envelope sequence/digest under the context's monotonic store. The verified policy result should retain the root generation, domain, sequence, envelope digest and provisioning-record reference so downstream audit can reconstruct why it was accepted.

## 5. Independent provenance is a separate trust domain

`verify_independent_provenance` must remain fail-closed until an independent evidence backend is actually provisioned. It must not return an authenticated result merely because the root-signed policy or receipt attestation verifies.

A future backend requires separately provisioned trust anchors and evidence contracts for:

1. nested institutional signatures over the original physical and operational records;
2. RFC 3161 tokens over exact original record/signature bytes, with authenticated TSA root, policy, revocation and bounded time;
3. append-only ledger inclusion and consistency proofs, with independent witnesses and anti-equivocation controls;
4. custody receipts that bind exact evidence digests, custodians, transfer events and the receipt/ledger graph;
5. original Acta, Tira de Pesaje, CS-11, Sumario, calibration and signed participation/cancellation artifacts for the exact draw.

Each evidence object must be checked over its original bytes. OCR, reserialization, filenames, public result pages and repository-generated synthetic fixtures are not substitutes for the original evidence. Every fixture must remain labelled synthetic and must never be counted as institutional provenance.

The backend must return a structured verification result with source identities, trust-anchor generation, exact byte digests, verification times, policy/sequence state, revocation status, ledger proof and custody path. Until every required evidence class is satisfied by independent authentic sources, the public status remains `BLOCKED_PROVENANCE`.

## 6. Required adversarial tests before any provisioning implementation

- caller attempts to replace root bytes or key ID after bootstrap;
- caller supplies a lower sequence or same sequence with a different envelope digest;
- concurrent policy acceptance attempts cannot race the monotonic store;
- store rollback, deletion, restore-from-old-backup and unavailable-store conditions fail closed;
- root rotation without a valid transition, reused key ID, revoked root or wrong policy domain is rejected;
- untrusted, stale, unsynchronized or rollback-detected clock is rejected;
- policy signature succeeds but receipt role/artifact authorization fails;
- receipt and policy verify but independent provenance returns any non-blocked status: integration rejects;
- synthetic TSA/ledger/custody fixtures cannot be represented as institutional evidence;
- exact original receipt and evidence bytes are preserved through every verifier boundary.

## 7. Current status and non-goals

No out-of-band trust-anchor provisioning, monotonic store, authenticated clock, institutional key ceremony, TSA designation, ledger witness service or independent custody service has been implemented or verified by this document.

This is an interface and deployment contract only. It does not alter V294, historical data, predictive parameters or production status. The required production classification remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`.

No `EDGE_SUPPORTED` declaration is possible without the full prospective draw, preregistration, multiplicity, anytime-evidence, sealed pre-close output and authentic independent-custody requirements.
