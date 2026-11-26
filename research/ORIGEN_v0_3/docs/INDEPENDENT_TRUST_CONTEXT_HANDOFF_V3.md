# ORIGEN v0.3 — V3 independent-trust boundary re-verification

**Classification:** RESEARCH ONLY / FAIL CLOSED. This interface does not authenticate institutional provenance or enable eligibility.

## Reproducible boundary gap

The earlier V3 adapter accepted VerifiedTrustPolicyV3 and CryptographicallyVerifiedReceipt objects from its caller. It cross-checked their fields against the supplied receipt and policy-envelope digests, but it did not itself re-run the Ed25519 policy and receipt verifiers. Python result objects are not unforgeable capabilities: a caller with arbitrary code execution can construct or mutate objects through low-level mechanisms. The bridge normally created them correctly, but the adapter's own boundary did not independently establish that fact.

## Change in this revision

The adapter now accepts only:

- exact original receipt bytes;
- exact signed V3 policy-envelope bytes;
- a 32-byte caller-pinned deployment root public key;
- the expected root key ID;
- a caller-supplied minimum policy sequence;
- one exact, already-normalized UTC verification instant.

When a V3 context is present, the adapter itself:

1. verifies the exact policy-envelope bytes with verify_signed_trust_policy_v3, requiring the fixed CLASSIC provenance domain and the supplied sequence floor;
2. verifies the exact receipt bytes with verify_receipt_attestation under the policy just verified;
3. checks that the receipt and policy verifier results bind the exact input bytes;
4. checks policy/key validity intervals, issuer/key identity, revocation declaration and the unique root-signed role/artifact authorization;
5. returns only BLOCKED_PROVENANCE.

The adapter no longer accepts caller-created VerifiedTrustPolicyV3 or CryptographicallyVerifiedReceipt objects. The V3 bridge still performs its own verification to build its diagnostic result, then passes only bytes and explicit verifier inputs to the boundary for a second verification from source bytes.

## What this closes—and what it does not

This closes the concrete object-handoff gap: a forged result object cannot stand in for an Ed25519 verification at the adapter boundary. It also makes the exact byte-to-policy-to-receipt chain explicit at the final fail-closed gate.

It does not create independent institutional trust. The root public key, root key ID, minimum sequence and verification clock still come from the caller. Repeating cryptographic verification with the same caller-supplied values is not out-of-band provisioning, external anti-rollback, trusted time or legal identity verification. A caller able to choose a malicious root can still establish a self-consistent synthetic chain; the adapter will nevertheless remain blocked.

The adapter intentionally has no AUTHENTICATED status. A successful diagnostic verification is not an eligibility decision.

## Required deployment boundary

A future production-capable provider must independently and atomically load:

- the root pin and root key ID from a protected, reviewed deployment trust store;
- the monotonic policy-sequence floor from rollback-resistant durable state;
- authenticated verification time from a trusted time source;
- current key/TSA revocation and authorization state.

It must re-verify the exact policy and receipt bytes at the boundary, advance anti-rollback state atomically only after all checks pass, and fail closed if any read, signature, time, revocation, compare-and-swap or durable-write operation fails. Root rotation must require an independently authorized transition, not a caller-selected replacement key. This provider requires separate threat modeling, deployment controls and security review; synthetic fixtures must not masquerade as provisioning.

All test keys, receipts and policy envelopes in this branch are synthetic. No institutional root, monotonic store, trusted clock, physical record or independent custody is claimed. Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
