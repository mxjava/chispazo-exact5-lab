# Detached Ed25519 verifier audit — key-expiry / untrusted issuance time

Date: 2026-11-24
Scope: research-only review of the detached verifier implementation present on the divergent ORIGEN V2 research branch. This finding is not a claim that the code is integrated into PR #13 or PR #26.

## Finding

The detached-envelope verifier checks that the envelope's self-declared `issued_at_utc` is no later than caller-supplied `verification_time_utc`, and that the key was valid at the declared issuance instant:

```python
if issued > verify_at:
    raise ValueError("signed envelope is from the future")
if not (not_before <= issued <= not_after):
    raise ValueError("signing key was not valid at envelope issuance")
```

It does not require an independently authenticated timestamp proving that the signature existed during that validity interval. The envelope's issuance time is inside the signed metadata, but a valid signature only proves that the key signed those bytes; it does not prove when the signature was created.

Consequently, after a key expires (or after a private key is compromised), a signer can create a new envelope using that key and backdate `issued_at_utc` to a time inside the key's validity interval. The verifier can accept it because the signature is valid and the claimed issuance time is in-range. The supplied verification time does not repair this: it is only an upper-bound check against a self-asserted signed field.

This is a temporal-authenticity gap, not an Ed25519 cryptographic break.

## Required remediation before any trust decision

1. Treat `issued_at_utc` as an untrusted claim unless bound to independently verified trusted-time evidence.
2. Verify original RFC 3161 token bytes (CMS signature, message imprint over the exact signature/envelope bytes, TSA EKU, certificate path to deployment-pinned TSA roots, policy, nonce where required, accuracy/ordering constraints, and revocation at the relevant time).
3. Define an explicit historical-key policy: either require trusted timestamp within key validity, or reject expired-key signatures at verification time. Do not silently infer historical validity from a self-declared timestamp.
4. Keep revocation semantics explicit (retroactive compromise cutoff versus ordinary revocation) and bind the applicable policy version to the externally pinned trust store.
5. Add adversarial tests: expired key + backdated self-asserted issuance must reject without a valid TSA token; same envelope with a valid trusted timestamp inside validity may pass only after full TSA-chain validation; timestamp substitution and wrong message imprint must reject.

## Integration status

The inspected implementation was found on the separate/divergent `research/origen-v2-integrated-20261123` line, not on the PR #13 head. It must not be represented as deployed or as the verifier used by PR #26. This audit records the finding for a later controlled port; no detached verifier was copied into the current PR #26 branch in this change.

## Current repository gate

PR #13 head remains `2646bcddf52ce629a52f580f7535096a67c7ead1`; its recorded isolated and root CI runs are successful (406 tests; 608 passed, 2 skipped, 128 subtests). PR #13 remains draft.

No original physical evidence, authenticated TSA service, institutional trust root, external ledger, or independent custody is available in this audit. V294 and the canonical history remain untouched. Production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**.
