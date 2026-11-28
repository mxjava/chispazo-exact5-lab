# ORIGEN — signed-policy/receipt composition with independent fail-closed gate

## Status

Research-only diagnostic composition. This increment is stacked on PR #126 and does not modify PR #13, #40 or #41.

## Composition

`verify_policy_bound_independent_provenance` accepts only the original receipt bytes and original signed policy-envelope bytes.

1. The existing `verify_policy_bound_receipt_attestation` verifies the policy envelope using a separately supplied Ed25519 root pin, key ID, minimum sequence and verification clock.
2. That verifier derives `VerifiedTrustPolicy` from the exact signed envelope bytes and passes its `TrustPolicy` to `verify_receipt_attestation`; no caller-created `VerifiedTrustPolicy` or verified-receipt object is accepted.
3. Only after the policy and receipt root-attestation checks succeed does the composition call `verify_independent_provenance` with the exact same immutable receipt-bytes object.
4. The independent adapter must return the exact enum value `BLOCKED_PROVENANCE`. An unexpected type or any other value raises a contract error; it is never converted into success.

The returned `PolicyBoundIndependentProvenanceResult` is an audit/diagnostic value, not an unforgeable Python capability and not an eligibility decision. It records the verified policy/receipt identifiers and the still-blocked independent status.

## What this does not establish

The root public key, expected root key ID, minimum policy sequence and verification clock remain caller/deployment inputs. The code does not authenticate their provisioning. In particular:

- no institutional trust anchor or key ID has been provisioned out of band;
- no durable, independent, atomic anti-rollback store is connected;
- no trusted deployment clock is authenticated;
- no root/issuer revocation or rollover service is connected;
- no nested participant or custodian signatures are authenticated by this wrapper;
- no original physical artifact bytes, RFC 3161 token, TSA chain/revocation, ledger inclusion/consistency, witness quorum or custody record is verified by this wrapper;
- no physical draw result or pre-close condition is established.

The independent adapter remains intentionally unprovisioned and always returns `BLOCKED_PROVENANCE`. This increment must not change that gate.

## Required out-of-band provisioning

Before any future deployment can rely on a signed policy:

1. Generate/import the offline root under documented multi-person control.
2. Verify its 32-byte public-key fingerprint and key ID through an independent channel; pin them in access-controlled deployment configuration, separate from the policy distribution channel.
3. Store the accepted policy sequence in a separately administered durable store with authenticated reads and atomic compare-and-swap. Recovery/restore must never lower the floor; require an independently audited recovery ceremony.
4. Obtain verification time from an independently monitored deployment clock. Event-time claims require actual RFC 3161 token verification, TSA certificate path validation, revocation checks, nonce/imprint binding and accuracy-interval checks.
5. Define root rotation, issuer revocation, emergency disablement, key expiry and audit retention before enrolling institutional keys.
6. Independently acquire original evidence bytes and preserve acquisition hashes, custody identity, transfer events and witness records.

These are requirements, not implemented provisioning. Do not treat a caller-supplied root, sequence or clock as authenticated merely because signature verification succeeds.

## Modality boundary

The inherited receipt schema is CLASSIC-only and enforces the 21:00 America/Mexico_City close slot. De las Tres at 15:00 is a separate modality and must not be relabelled as Classic or passed through this Classic receipt chain.

## Tests

All fixtures use freshly generated in-memory Ed25519 keys and synthetic receipt/policy bytes. Tests cover successful ordered composition that remains blocked, policy/receipt/root tampering before the independent gate, unexpected gate outcomes, propagated backend exceptions, rejection of preconstructed verified-policy objects, and the absence of any authenticated enum member.

## Non-promotion

No main write, merge, canonical-history append, V294 change, predictor/threshold change or production promotion. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
