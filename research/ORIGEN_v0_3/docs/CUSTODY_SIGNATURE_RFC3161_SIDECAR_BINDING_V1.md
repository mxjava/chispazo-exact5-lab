# ORIGEN V3 — non-circular detached custody-signature timestamp binding (V1)

Status: RESEARCH ONLY. All tests use synthetic keys, certificates, receipts, custody records and TSA tokens. This contract does not authenticate an institution, a custodian, a TSA, a clock, or physical evidence.

## Why the existing record timestamp is insufficient

The V3 custodian signature is over a domain-separated payload containing both the exact custody-record digest and the exact root-receipt digest. The receipt, in turn, can carry trusted-time proof digests. If a token over the detached signature were inserted into that same receipt, the dependency would be circular:

1. The receipt digest is an input to the custodian signature.
2. The timestamp token digest is an input to the receipt.
3. The token imprint is the custodian signature bytes.

No ordering can construct all three while preserving those exact bindings.

## V1 solution: detached RFC 3161 sidecar

Do not change the V3 receipt schema or signature payload. Instead:

1. Canonicalize and freeze the custody record bytes.
2. Construct and root-sign the receipt. Its custodian claim binds the exact custody-record digest and the root attestation binds the complete receipt.
3. Produce the V3 detached custodian signature. Its signed payload binds the exact receipt digest, custody-record digest, custodian identity/key ID, target and portfolio.
4. Obtain an RFC 3161 token whose message imprint is SHA-256 over the exact 64 signature bytes.
5. Preserve the token as a detached sidecar. Do not insert its digest into the receipt it timestamps.
6. Verify the V3 receipt/policy/custody chain first; then verify the token imprint over the same exact signature bytes. Require the entire RFC 3161 accuracy interval to be at or after the record's claimed receipt time and strictly before the declared CLASSIC 21:00 close.

The token is transitively bound to the receipt and record: the verified signature is bound to both exact digests, and the timestamp token is bound to the exact verified signature bytes. This avoids the cycle without weakening the existing V3 signature.

## Fail-closed result

A passing synthetic test means only that the exact signature bytes are cryptographically timestamped relative to a caller-supplied TSA root and caller-supplied verification clock. The result remains `BLOCKED_PROVENANCE`.

Outstanding blockers include external TSA-root provisioning, certificate revocation, authenticated TSA policy authorization, authenticated clock, independently witnessed ledger anchoring of the detached sidecar, legal identity and delegation of the custodian, independent custody, authentic physical records, and prospective edge criteria.

This V1 adapter deliberately does not claim that a sidecar is institutional evidence. It does not write to the canonical history, change V294, enable production, or promote any PR.
