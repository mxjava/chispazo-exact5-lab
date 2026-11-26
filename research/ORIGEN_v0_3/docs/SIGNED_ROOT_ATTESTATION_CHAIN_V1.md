# ORIGEN v0.3 — V1 signed root-attestation chain composition

**Classification:** research diagnostic only. No production trust decision or provenance eligibility is produced.

## Implemented composition

`inspect_signed_root_attestation_chain_v1(...)` accepts original receipt bytes and signed V1 policy-envelope bytes, plus caller-supplied root pin, root key ID, minimum sequence and verification time. It:

1. snapshots the supplied time-zone offset once and passes one normalized UTC instant to both verifiers;
2. verifies the exact signed policy bytes with `verify_signed_trust_policy`, producing an internally obtained `VerifiedTrustPolicy`;
3. checks that the policy result binds the exact envelope bytes;
4. passes only the verified policy's immutable `TrustPolicy` snapshot to `verify_receipt_attestation`;
5. checks the exact scoped receipt-verification result;
6. invokes `verify_independent_provenance` on the original receipt bytes and requires the exact `BLOCKED_PROVENANCE` result.

The composition accepts raw bytes, not a caller-constructed `VerifiedTrustPolicy` or `CryptographicallyVerifiedReceipt`. A successful diagnostic returns hashes and signer identifiers, not a capability or eligibility token. A failed policy or receipt signature never reaches the independent provenance gate.

## Deliberate V1 limitations

This is not a production integration:

- V1 signed policy envelopes do **not** include `policy_domain`; the returned inspection records `ABSENT_IN_V1`.
- Root pin, expected key ID, minimum sequence and verification time remain caller-supplied.
- The minimum sequence is not persisted and there is no durable CAS/anti-rollback backend.
- The supplied time is not authenticated and carries no uncertainty interval.
- No OCSP/CRL freshness, root rollover authority, institutional signer delegation, TSA chain, ledger inclusion or independent custody is established.
- `verify_independent_provenance` remains a kill switch that returns only `BLOCKED_PROVENANCE`.

Do not use this V1 composition as a substitute for the domain-bound V3/provider research path. A deployment implementation still requires out-of-band root provisioning, separately protected monotonic state, authenticated time and independent evidence services, each independently reviewed. The provider interface in the V3 research branch is itself only a contract; no real backend is provisioned.

## Adversarial fixtures

All keys, policy envelopes, receipts and clocks in `tests/test_signed_root_attestation_chain_v1.py` are synthetic. Tests cover valid cryptographic composition while blocked, receipt tampering before the independent gate, wrong root pin, caller-supplied result-object rejection, exact raw-byte re-verification at the independent gate, partial-context downgrade rejection, unexpected independent-gate status, mutable buffers and a stateful timezone callback.

No institutional or Chispazo draw evidence is created by these tests.
