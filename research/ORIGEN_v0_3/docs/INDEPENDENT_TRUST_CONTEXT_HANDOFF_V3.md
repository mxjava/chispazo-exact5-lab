# ORIGEN v0.3 — V3 independent-trust context handoff

**Classification:** RESEARCH ONLY / FAIL CLOSED. This interface does not authenticate institutional provenance or enable eligibility.

## Problem addressed

The V3 receipt bridge verified a signed policy envelope and the root-attested receipt, then called `verify_independent_provenance(original_receipt_bytes)` without passing the exact policy envelope or the verifier outputs. The adapter could only return `BLOCKED_PROVENANCE`, but it could not detect accidental cross-wiring between one receipt's bytes, another policy's bytes, and different verifier results.

## Handoff contract

The V3 bridge now passes all of the following together:

- exact original receipt bytes;
- exact signed V3 policy-envelope bytes;
- the `VerifiedTrustPolicyV3` returned after verifying those policy bytes against the caller's root pin, key ID, domain, sequence floor and clock;
- the `CryptographicallyVerifiedReceipt` returned after verifying the receipt's Ed25519 attestation under that policy.

The adapter checks:

1. receipt digest equals the parsed verifier result's `raw_sha256`;
2. policy-envelope digest equals the verified policy's `envelope_sha256`;
3. receipt policy version equals the policy version;
4. receipt issuer/key IDs equal the verified receipt issuer/key IDs;
5. exactly one policy issuer key matches that identity and is not revoked;
6. policy and issuer-key validity intervals cover both the receipt signing time and verification time;
7. exactly one signed authorization binds the receipt issuer/key to `RECEIPT-ROOT-ATTESTER` and `TRUST-RECEIPT-ROOT-ATTESTATION`;
8. the policy domain is the fixed CLASSIC physical-provenance domain.

Incomplete contexts, mismatched bytes, mismatched identities, and missing role/artifact authorization are rejected before the backend gate.

## Security limits

This is an **in-process consistency handoff**, not an unforgeable capability. Python code with arbitrary execution can fabricate objects or bypass private constructors. The adapter does not trust these objects as independent evidence, does not accept caller booleans or callbacks, and does not produce an authenticated status.

Even a fully consistent V3 handoff returns only `BLOCKED_PROVENANCE`. The enum intentionally has no `AUTHENTICATED` member.

Still caller supplied and not independently provisioned:

- deployment root public key and root key ID;
- minimum policy sequence;
- verification clock;
- TSA root and revocation state;
- log key, witness-registry root and anti-rollback floors.

The repository has no deployed independent trust backend, authenticated institutional identity, external monotonic state, or original physical evidence custody.

## Required next implementation boundary

A future provider must independently load the root pin and monotonic sequence from protected deployment state, obtain authenticated time, re-verify exact policy and receipt bytes at the boundary, check revocation and institutional role authorization, and bind policy-envelope existence time to an independently witnessed timestamp/ledger record. Failure to read or advance any trusted state must fail closed. That provider requires separate security review and must not be simulated by test fixtures.

All test keys and envelopes in this branch are synthetic. Production remains **`BLOCKED / RESEARCH_ONLY_NO_EDGE`**.
