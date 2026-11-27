# ORIGEN trust-anchor provisioning and anti-rollback requirements

Status: **design requirements only**. No institutional root, KMS/HSM, trusted
clock, or durable anti-rollback service is provisioned by this repository.

## 1. Root trust anchor

The Ed25519 root public key and its key identifier must be provisioned outside
the application and outside the policy-envelope delivery channel. A deployment
must retain a reviewed record containing the key ID, raw public-key bytes,
SHA-256 fingerprint, owner, approval evidence, activation time, and revocation
or replacement history.

A production ceremony should require dual control by distinct security roles,
independent fingerprint confirmation over an authenticated channel, and
immutable/auditable deployment configuration. The application must not accept
a root pin from a receipt, policy envelope, request payload, environment value
writable by the application identity, or user-controlled file. Root rotation
must be explicit, versioned, and recoverable without silently trusting a
replacement key supplied alongside the new envelope.

## 2. Monotonic policy sequence

The accepted policy sequence needs an independently controlled durable state
store with a provisioned genesis value. The store must support an atomic
compare-and-advance operation scoped to the policy authority and root-key
identity. A verifier must reject:
- a missing or uninitialized genesis watermark;
- a sequence lower than the durable accepted value;
- reuse of a sequence with different exact policy bytes;
- a concurrent advance based on a stale prior watermark;
- reset, rollback, or restoration from an untrusted backup.

Signature verification and watermark compare-and-advance must be serialized
under one provider transaction or an equivalently isolated verification
service. A caller-provided integer floor is useful for tests but is not an
anti-rollback implementation.

## 3. Trusted time

A caller-provided datetime is not trusted time. Production policy validity,
receipt signing time, revocation state, and pre-close ordering require a
trusted-time source with authenticated response bytes and independently pinned
authority keys. RFC 3161 tokens must be verified for message imprint, TSA
signature chain, policy OID, nonce where used, accuracy, ordering, and
revocation status. Local wall-clock time may be diagnostic only.

## 4. Nested evidence and custody

The provider must independently verify exact original bytes for every artifact,
detached signature, signer identity and role, custody record, portfolio, both
pre-close output seals, timestamp token, manifest, transparency-ledger entry,
inclusion proof, checkpoint consistency proof, and independent witness
statement. It must bind every digest to the bytes it actually reads and make
verification plus monotonic state advancement atomic.

A valid root signature on the receipt or policy does not validate any of these
nested claims. Structural parsing and synthetic fixtures remain research-only.

## 5. Acceptance criteria before any provenance promotion

A production-capable implementation requires:
1. independently provisioned and reviewed root pins;
2. durable anti-rollback genesis and atomic monotonic updates;
3. independently authenticated trusted time;
4. real provider-side nested-signature and evidence-byte verification;
5. independently authenticated custody and ledger/witness services;
6. security review and adversarial integration tests against the deployed
   provider, including key rotation, revocation, stale snapshots, concurrent
   updates, restart, backup restore, and service compromise.

Until all criteria are independently evidenced, the only eligible outcome is
`BLOCKED_PROVENANCE`, and production remains
`BLOCKED / RESEARCH_ONLY_NO_EDGE`.
