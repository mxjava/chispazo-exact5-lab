# ORIGEN v1 — signed policy to receipt-attestation composition

## Status and scope

Research-only integration of two existing primitives:

1. `verify_signed_trust_policy` authenticates a policy envelope against a separately supplied Ed25519 root key, root key ID, minimum sequence and verification clock.
2. `verify_receipt_attestation` authenticates the receipt's root Ed25519 signature against the issuer policy produced in step 1.

`verify_policy_bound_receipt_attestation` accepts the original receipt bytes and original signed policy-envelope bytes, performs both checks in one call, and returns `ROOT_ATTESTATION_ONLY`. It deliberately does not accept a caller-created `VerifiedTrustPolicy` object; the policy is derived inside the function from the signed envelope bytes.

## Security boundary

The following remain caller/deployment inputs and are NOT authenticated by this code:

- pinned 32-byte root public key;
- expected root key ID;
- minimum accepted policy sequence;
- verification clock.

A successful composition proves only that the supplied policy envelope verifies against the supplied root pin, meets the supplied sequence floor and time window, and that the receipt root attestation verifies under the issuer key in that policy. The receipt's `AUTHENTICATED` declaration is still just an untrusted claim.

The result does NOT verify nested participant signatures, original physical artifact bytes, signer/custodian identities, RFC 3161 tokens, external ledger inclusion/head anchoring, custody, calibration, or the physical truth of any claim. It is not an authenticated-provenance decision or an unforgeable Python capability.

## Why the independent adapter remains blocked

`verify_independent_provenance(original_receipt_bytes)` is intentionally unchanged and continues to return only `BLOCKED_PROVENANCE`. It does not invoke this composition, accept trust roots, or accept callbacks. A valid root-attestation chain is a prerequisite component, not sufficient evidence to release the independent provenance gate.

## Required out-of-band provisioning design

Before any deployment can rely on this chain, a separately controlled deployment boundary must provide:

1. **Root pin ceremony:** create or import the offline Ed25519 root under documented multi-person control; verify the 32-byte public-key fingerprint through an independent channel; pin both the exact key bytes and key ID in access-controlled deployment configuration. Do not download the pin from the same service that distributes the envelope.
2. **Anti-rollback state:** persist the highest accepted policy sequence in storage outside the envelope and outside the application workspace. Reads and updates must be authenticated, access-controlled, durable, and atomic (compare-and-swap). Reject a sequence below the stored floor. After a policy is successfully verified, commit the new floor before accepting any dependent operation. Backup/restore must not lower the floor; recovery requires a separately audited operator procedure.
3. **Clock:** obtain verification time from an independently monitored time source. For event-time evidence, validate actual RFC 3161 tokens and their TSA chains/revocation/nonce/imprint; do not treat this local clock as a timestamp authority.
4. **Key lifecycle:** define root rotation, overlap, issuer-key revocation propagation, emergency disablement, expiry handling, and audit records before enrollment of institutional keys.
5. **Independent custody:** acquire original artifacts from the institutional source, preserve exact bytes, record hashes at acquisition, and maintain independently witnessed custody and immutable audit records.

These are deployment requirements, not implemented provisioning. No institutional key, service, clock, ledger, or custodian has been acquired or authenticated in this PR.

## Modality boundary

The current V1 receipt parser accepts only `CLASSIC` and enforces the 21:00 America/Mexico_City close slot. `DE LAS TRES` at 15:00 is a different modality and must not be relabeled or passed through the Classic trust-receipt schema. The public result page or a schedule-derived inference is not a substitute for an official modality-labelled primary record.

## Synthetic tests

`test_trust_policy_receipt_chain_v1.py` generates fresh Ed25519 keys in memory. These fixtures are synthetic, test-only, and have no institutional authority. They test composition, signature tampering, wrong root, sequence rollback, policy-version mismatch, and the invariant that the independent adapter remains blocked.

## Non-promotion protections

No main writes, merges, predictor changes, V294 changes, canonical-history edits, or production promotion. This work remains research-only and must not be used to claim `EDGE_SUPPORTED`.
