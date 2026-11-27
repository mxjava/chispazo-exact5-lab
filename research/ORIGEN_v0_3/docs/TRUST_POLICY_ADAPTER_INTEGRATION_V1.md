# ORIGEN v0.3 — signed-policy adapter integration and deployment boundary

Status: **RESEARCH-ONLY COMPOSITION / FAIL-CLOSED**. This document describes the
composition of the signed trust-policy envelope and root receipt-attestation
verifier. It does not provision an institutional trust root or authenticate
physical evidence.

## Composition implemented

The integration order is:

1. A deployment composition root calls `verify_signed_trust_policy` with the
   exact policy-envelope bytes, a separately pinned 32-byte Ed25519 root public
   key, the expected root key ID, an externally maintained minimum policy
   sequence, and an explicit verification time.
2. The function validates the envelope signature, strict schema, key identities,
   validity interval, and supplied sequence floor. It returns
   `VerifiedTrustPolicy`; its public constructor is disabled so ordinary
   application code cannot accidentally manufacture this result.
3. `verify_independent_provenance` may receive that exact result together with
   the receipt-verification time. It calls `verify_receipt_attestation` using
   the policy's issuer keys and rechecks the policy's issue/not-before/expiry
   window at the receipt-verification instant.
4. The adapter still returns only `BLOCKED_PROVENANCE`, even after a valid root
   receipt signature. A bad signature or invalid policy window raises and cannot
   fall through to a success status.

The adapter never accepts a caller-supplied verifier callback, trust-root map,
boolean, or reference set. Omitting the policy keeps the prior byte-only
fail-closed behavior.

## What the composition does not authenticate

The current function arguments are still supplied by the caller/deployment.
The code does not prove that the root key, key ID, minimum sequence, or clock
were provisioned authentically. The disabled result constructor is an
accidental-misuse guard, not a process-isolation boundary: arbitrary Python code
executing in the same interpreter can bypass ordinary object construction.

The root receipt verifier authenticates only the root Ed25519 signature over
the canonical receipt claims. It does not verify:

- original institutional artifact bytes against an independently controlled
  artifact store;
- nested signer signatures, certificate chains, signer identity or role;
- RFC 3161 timestamp-token signatures, TSA certificate path, policy OID,
  nonce/imprint binding, or revocation at the relevant time;
- ledger inclusion, checkpoint consistency, independent ledger ownership, or
  monotonic head progression;
- custody receipt signatures, custodian identity, or independent custody;
- machine/ball-set identity, the 28 physical-ball mapping, weighing strips,
  CS-11, CS-02, calibration evidence, or source video.

Therefore neither a verified policy nor a verified root receipt signature is
an authenticated provenance decision. Production remains
`BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Required out-of-band deployment provisioning

Before any production-capable verifier can be considered, a separately reviewed
deployment system must provide all of the following:

### 1. Root trust anchor

- Generate and retain the Ed25519 root private key offline or in a controlled
  HSM; never place private key material in this repository or the policy
  envelope.
- Distribute the 32-byte public key and root key ID through a separate
  authenticated channel, with two-person approval and a recorded fingerprint.
- Pin the exact public key and key ID in access-controlled deployment
  configuration or an immutable release artifact. Do not read either from the
  envelope, receipt, or a caller-controlled request.
- Define key rollover and emergency revocation, including the period in which
  old and new roots are both accepted and how a compromised root is removed.

### 2. Anti-rollback state

- Persist the minimum accepted policy sequence outside the downloaded policy
  and outside mutable application-local files.
- Use a rollback-resistant store such as a managed HSM/TPM-backed state service
  or independently controlled append-only ledger, with authenticated reads and
  atomic compare-and-swap updates.
- Verify the envelope signature and all policy constraints before attempting
  to advance the floor. Advance it atomically only after successful validation;
  never lower it during normal recovery or restore.
- Define backup/restore, disaster recovery, concurrent verifier, and
  administrator-override procedures. An override must itself be independently
  authorized and audited.
- The current API merely enforces the supplied minimum sequence. It does not
  persist or authenticate that floor.

### 3. Trusted time

- Do not treat a Python `datetime` argument or host wall clock as trusted time.
- Verify RFC 3161 tokens against an independently configured TSA trust list:
  signature, certificate path, EKU/policy, nonce where used, message imprint,
  generation time, and revocation status.
- Bind the exact timestamp token bytes and their SHA-256 digest to the policy
  envelope and receipt event. Preserve the original token bytes.
- Define a fail-closed response for TSA outage, stale revocation data, clock
  rollback, and conflicting timestamps.

### 4. Nested signatures, ledger, and custody

- Verify every signer and custodian signature over its exact original artifact
  bytes; bind signer identity, role, key ID, algorithm, certificate path, and
  revocation evidence.
- Verify the ledger inclusion proof and checkpoint consistency from an
  independently operated ledger, not a self-declared ledger ID or digest.
- Verify custody receipts and independent organizational identities; keep
  evidence of transfer, receipt, storage, access, and retention.
- Preserve two independently generated output seals and their separate
  pre-close trusted-time proofs. A self-declared timestamp is insufficient.

### 5. Physical evidence and modality

For Chispazo, keep the modalities separate: **De las Tres is 15:00** and
**Clásico is 21:00**. The current receipt schema and this research path accept
CLASSIC only. Physical evidence must be linked to the exact contest, machine,
ball set, 28 physical IDs, and measurement snapshot. Public result pages and
mask PDFs identify published results; they do not substitute for signed Acta,
CS-11, weighing strip, calibration records, original bytes, or independent
custody.

## API shape under research

```python
verified_policy = verify_signed_trust_policy(
    policy_envelope_bytes,
    pinned_root_public_key_bytes=deployment_pinned_root,
    expected_root_key_id=deployment_root_key_id,
    minimum_policy_sequence=externally_persisted_sequence_floor,
    verification_time=deployment_clock,
)

status = verify_independent_provenance(
    original_receipt_bytes,
    verified_trust_policy=verified_policy,
    verification_time=deployment_clock,
)
assert status is ProvenanceStatus.BLOCKED_PROVENANCE
```

This is an integration test seam, not a production deployment recipe: the
example inputs are only trustworthy after the out-of-band controls above are
implemented and independently audited. The supplied clock is not currently an
RFC 3161 verification result.

## Release gates

No change in this branch authorizes merge, promotion, canonical-history writes,
or a model update. V294 remains frozen and
`data/history/Chispazo_through_12249.csv` remains protected.

Before any provenance status could change, independent review must cover the
root provisioning, rollback-resistant sequence store, RFC 3161 verifier,
nested signatures, ledger proofs, custody, original-byte intake, and physical
evidence chain. Separately, EDGE_SUPPORTED still requires at least 100
untouched prospective CLASSIC draws, preregistered positive lift, Holm
p<0.05, anytime e-value >=20, two independently sealed pre-close outputs,
clean hashes, and authentic independent custody.
