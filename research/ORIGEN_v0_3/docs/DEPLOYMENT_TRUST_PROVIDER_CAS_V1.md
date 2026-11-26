# ORIGEN v0.3 — deployment trust provider and atomic sequence boundary v1

**Classification:** executable interface contract / RESEARCH ONLY. No production provider, institutional trust anchor, or authenticated clock is implemented here.

## 1. Why this increment exists

The V3 verifier at PR #81 re-verifies exact policy and receipt bytes, but still receives the root pin, key ID, minimum sequence, and clock as individual call arguments. PR #69 and PR #56 already define the out-of-band bootstrap and anti-rollback requirements. This increment turns the required handoff into an executable application interface rather than repeating the provisioning design.

New module:

- `src/origen/deployment_trust_provider_v1.py`

New adversarial suite:

- `tests/test_deployment_trust_provider_v1.py`

The module deliberately ships no file-backed, SQLite, environment-variable, or in-memory production provider.

## 2. One provider snapshot, not request-level trust inputs

The high-level function accepts exact receipt bytes, exact signed policy-envelope bytes, and one provider dependency:

```python
inspect_receipt_with_deployment_trust_provider(
    original_receipt_bytes,
    signed_policy_envelope_bytes,
    provider=deployment_composition_root_provider,
)
```

The provider returns one immutable snapshot containing:

- root public-key bytes, root key ID, and root generation;
- fixed CLASSIC policy domain;
- minimum sequence, accepted sequence, exact accepted-envelope digest, last accepted clock-interval upper bound, and state generation;
- one normalized UTC time, its uncertainty, and a provisioned maximum uncertainty;
- identifiers for the clock source and state backend;
- the provisioning-record digest.

The application request cannot independently override those values. The snapshot is copied and strictly type-checked before verification. A boolean is not accepted as an integer sequence or generation.

The provider object is a trusted dependency supplied by the deployment composition root. Python Protocols and frozen dataclasses are not unforgeable capabilities; this module does not authenticate an arbitrary provider implementation.

## 3. Verification and state transition

The operation is ordered as follows:

1. Read exactly one provider snapshot for the fixed CLASSIC domain.
2. Reject malformed pins, identifiers, generations, sequence state, digest state, clock metadata, or provisioning-record digest.
3. Reject clock uncertainty above the provider's provisioned maximum.
4. Compute the closed uncertainty interval `[trusted_time - uncertainty, trusted_time + uncertainty]`.
5. Verify the exact canonical V3 policy envelope against the snapshot root pin, root key ID, CLASSIC domain, and the maximum of the provisioned floor and previously accepted sequence.
6. Reject equal-sequence/different-envelope-digest equivocation.
7. Verify the exact receipt bytes under the policy just verified.
8. Require the complete clock uncertainty interval to lie inside the signed policy validity interval and the receipt issuer-key validity interval. Require the receipt signing time to be no later than the earliest possible verification instant.
9. Re-run the exact-byte V3 policy and receipt verification at `verify_independent_provenance`. That gate must still return exactly `BLOCKED_PROVENANCE`.
10. Atomically compare-and-advance the provider state using the exact snapshot generation, root generation, policy sequence, envelope digest, accepted time, and clock uncertainty.
11. Return a diagnostic inspection with the exact byte hashes and before/after state generations. Its provenance status remains `BLOCKED_PROVENANCE`.

No state commit is attempted when policy signature, receipt signature, role authorization, time-window, or independent-boundary verification fails.

## 4. Required provider transaction semantics

The external implementation must provide a linearizable compare-and-advance transaction:

| Observed state vs candidate | Required outcome |
|---|---|
| Higher candidate sequence | Advance exactly one state generation |
| Same sequence + same exact envelope digest | Idempotent; generation unchanged |
| Same sequence + different digest | Reject as equivocation |
| Lower sequence | Reject as rollback |
| Snapshot generation changed before commit | Reject as conflict |
| Store unavailable, stale, restored, split-brain, or commit uncertain | Fail closed |

The provider must scope state by root generation and policy domain. A policy sequence from another domain must never satisfy the CLASSIC floor. Root rotation must be a separate, independently authorized transition and cannot reset the sequence.

For every higher-sequence acceptance, the provider must also enforce a trusted-time rollback floor atomically: candidate earliest time (accepted_at_utc minus clock uncertainty) must be greater than or equal to the previously stored accepted interval's upper bound. On successful advance it stores candidate latest time (accepted_at_utc plus clock uncertainty) together with the new sequence and exact envelope digest. The commit response must echo that exact upper bound. Same-sequence/same-digest idempotency returns the previously stored upper bound without changing it. A provider that restores or regresses this clock floor must fail closed.

The application checks the returned commit shape and exact policy digest, but only the provider's independently reviewed implementation can guarantee linearizability and durable anti-rollback.

## 5. Trusted-time uncertainty

The prior V3 verifier checked policy validity at one supplied instant. This provider interface carries the clock's stated uncertainty and requires the entire possible-time interval to fit within:

- policy issuance and activation boundaries;
- policy expiration;
- receipt issuer-key validity;
- receipt-signing-before-verification ordering.

A midpoint that is valid while either edge of the uncertainty interval crosses activation, expiry, or key validity is rejected.

This check is only as trustworthy as the provider's clock source and uncertainty claim. The code does not establish NTS, hardware clock attestation, RFC 3161, or institutional synchronization.

## 6. What is intentionally absent

No provider implementation is included. In particular, there is no:

- accepted institutional root or verified bootstrap ceremony;
- HSM/TPM/remote monotonic store;
- protection against privileged administrator rollback or restoration of provider storage;
- authenticated clock or independently measured uncertainty;
- verified OCSP/CRL client;
- root-rotation authority;
- institutional delegation for Chispazo records;
- original draw evidence or independent physical custody.

The Incode PSC material remains a public-metadata candidate only; certificate bytes, fingerprints, current revocation, live TSA response, and deployment authorization have not been verified. Do not configure its published OID or certificate names as trusted values from this repository.

## 7. Adversarial tests

All keys, receipts, envelopes, provider state, and time sources in this test module are synthetic. Tests cover:

- successful sequence advance while remaining blocked;
- exact same-sequence/digest idempotency;
- same-sequence/different-digest equivocation;
- rollback below accepted sequence;
- compare-and-swap generation race;
- trusted-clock interval rollback behind the last accepted upper bound;
- missing prior accepted-time state, clock-floor race and commit-response time-bound substitution;
- provider read and durable commit outages;
- receipt tampering before state advancement;
- clock uncertainty crossing activation, expiration, and receipt-signing order;
- uncertainty exceeding the provisioned maximum;
- boolean sequence values, wrong modality domain, noncanonical UTC and malformed provisioning digest;
- provider commit digest substitution.

These tests exercise the application contract and a synthetic reference provider only. They do not prove that any real external service meets the contract.

## 8. Non-promotion

V294 remains frozen. The canonical history file is not changed. PR #13 remains isolated and untouched. No write to `main`, merge, or production promotion is performed.

Every successful call returns `BLOCKED_PROVENANCE`. Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

No `EDGE_SUPPORTED` claim is possible without the full prospective Classic sample, preregistered positive lift, Holm threshold, anytime e-value, two pre-close seals, clean hashes, and authentic independent custody.
