# ORIGEN v0.3 — provider physical-composition V1 audit (2026-11-28)

## Finding

The V1 physical/deployment composition called the public
`inspect_receipt_with_deployment_trust_provider` facade with `provider` and
`provider_snapshot` keyword arguments. The public facade intentionally accepts
neither argument, so an unmocked successful physical-verification path raised
`TypeError` instead of completing the provider-backed diagnostic composition.
The prior orchestration test masked this defect by replacing that facade with a
permissive test double.

A second binding gap existed on this V1 path: the provider-returned
`PhysicalTrustContextV1` was used for physical verification without requiring
its generation and canonical digest to match the deployment snapshot. The V2
external-evidence helper had a context binding check, but this older V1
composition did not.

## Correction

- The orchestration now calls the internal snapshot-bound composition helper,
  passing the exact already-validated snapshot and physical context. It does
  not perform a second snapshot read.
- Before invoking the physical verifier, it requires the physical context
  generation and canonical SHA-256 to match the same provider snapshot.
- It separately requires the context policy-root public key, key ID and
  minimum policy sequence to equal the snapshot's deployment root and floor.
- Any missing or mismatched binding raises `TrustStateRejected` before
  physical verification or provider CAS.
- The tests patch the snapshot-bound helper rather than the public facade, and
  include digest and root-pin substitution cases.

## Validation boundary

All fixtures are synthetic. The private helper is a Python API-discipline
boundary, not an unforgeable capability. The repository bootstrap still returns
no deployment provider. A successful test therefore proves only that the
research composition enforces its declared bindings; it does not authenticate
institutional provisioning, provider identity, CAS implementation, TSA roots,
witnesses, physical records or custody.

Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`. V294 and the canonical
history are unchanged.
