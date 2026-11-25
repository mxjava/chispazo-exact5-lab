# ORIGEN — canonical signed trust-policy bytes

**Date:** 2026-11-25  
**Base:** PR #43 head `002b1c1bc6717d2199919af722cfe8617ceab488`  
**Classification:** RESEARCH ONLY. This change does not provision a trust anchor or enable provenance.

## Audit finding

The v1 policy verifier parsed JSON with duplicate-key rejection and verified the Ed25519 signature over a canonicalized unsigned object. However, it did not require the received envelope bytes themselves to be canonical. Consequently, leading/trailing whitespace, reordered object members, or equivalent escaped-ASCII spellings could represent the same signed policy claims while producing different SHA-256 values for `VerifiedTrustPolicy.envelope_sha256`.

That ambiguity matters because downstream receipts, audit records, and future ledger entries bind the exact envelope digest. Two byte strings could verify as the same logical policy but carry different envelope hashes.

## Minimal correction

Immediately after strict JSON decoding and top-level object validation, the verifier now requires:

```python
raw == _canonical(document)
```

The check covers the complete envelope, including the signature object. It therefore enforces the existing canonical JSON profile for both signed claims and detached signature encoding. The Ed25519 algorithm, schema, trust policy, root provisioning, and sequence-floor semantics are unchanged.

## Adversarial tests

A new synthetic-only test module checks:
- canonical envelope bytes continue to verify;
- leading whitespace, trailing newline, and prefixed newline are rejected;
- reordered JSON object members are rejected;
- an equivalent escaped-ASCII member name is rejected even though JSON decoding yields the same semantic key.

The signature and generated keys are test fixtures only. No institutional root is included.

## Security boundary retained

- Root public key and key ID remain caller/deployment supplied.
- Minimum policy sequence remains caller supplied and is not persisted in an external monotonic store.
- Verification time remains caller supplied and unauthenticated.
- Policy revocation freshness is not established.
- `verify_independent_provenance` remains fail-closed; every successful diagnostic remains `BLOCKED_PROVENANCE`.
- No RFC 3161 token, external ledger, authenticated collector, custody record, or physical-event truth is established.

## Validation

The exact-head isolated ORIGEN workflow and repository CI must both pass before this increment is considered validated. No local test execution is claimed.

## Protected state

This branch is a draft child of PR #43. It does not write to `main`, merge or promote any PR, change V294, or modify `data/history/Chispazo_through_12249.csv`. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
