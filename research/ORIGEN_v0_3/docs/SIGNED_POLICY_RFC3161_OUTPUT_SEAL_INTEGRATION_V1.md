# ORIGEN — signed policy, receipt and RFC 3161 output-seal integration v1

**Classification:** research-only diagnostic. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Implemented composition

This branch is based on the exact PR #49 head and composes:

1. canonical signed trust-policy envelope verification against a separately supplied Ed25519 root;
2. root receipt-attestation verification using the resulting `VerifiedTrustPolicy.policy`;
3. the existing independent-provenance adapter, which must still return exactly `BLOCKED_PROVENANCE`;
4. RFC 3161 verification for the two output-seal signature byte strings.

For each output seal, the integration requires all of the following:

- the exact DER token's SHA-256 equals both the signed receipt's `trusted_time_proofs[].proof_sha256` and the seal's `timestamp_proof_sha256`;
- the proof's event ID and authority ID match the caller's requested evidence item and pinned authority label;
- the SHA-256 of the exact supplied signature bytes equals the seal's signed `signature_sha256`;
- the RFC 3161 message imprint is recomputed over those exact signature bytes;
- the token's `genTime` equals the signed event time and the seal's declared creation time;
- the token includes a positive nonce matching the separately supplied request nonce;
- the RFC 3161 accuracy field is present and its upper time bound is strictly before the receipt's declared Classic close.

The two tokens are matched by signed proof digest/event identity, not by array order. Missing, duplicate, extra, mismatched, stale, future, or ambiguous evidence fails closed.

## Deliberate limitation: receipt-attestation timestamp remains unresolved

The V1 receipt schema places `receipt_attestation.timestamp_proof_sha256` and its matching `trusted_time_proofs` entry inside the receipt payload covered by the root Ed25519 signature. If the timestamp token were required to imprint the root signature bytes, then:

- the root signature depends on the token digest because that digest is in the signed payload;
- the token digest depends on the token bytes;
- the token's message imprint depends on the root signature bytes.

That is a self-referential construction. This branch does not weaken the receipt signature, omit fields from the signed payload, or pretend the token is verified. It leaves `RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED` as an explicit blocker. A future schema version should use a detached outer proof envelope or a two-stage signed object with an independently specified non-circular commitment.

## Trust boundary still not established

All of the following remain caller-supplied or incomplete:

- policy root public key, root key ID, minimum sequence and verification clock;
- TSA root certificate/fingerprint, authority ID and expected request nonces;
- TSA legal/institutional designation and authorized policy OIDs;
- CRL/OCSP and revocation freshness;
- complete RFC 5280 path validation (the standalone verifier explicitly implements a bounded subset);
- nested signer and custodian signatures, identities and role authorization;
- actual original physical records, physical sphere identity/number mapping, 28 individual masses, calibration, machine/set assignment and incident history;
- independently controlled immutable acquisition, custody receipts, ledger-head anchoring and split-view-resistant witnesses;
- two independently sealed prospective Classic outputs and all statistical edge gates.

The returned result is a diagnostic only. It does not authenticate a TSA institution, establish real-world time, establish that a draw record is true, or change the independent adapter's status. Synthetic keys, certificates, CMS tokens and signature bytes exist only in tests.

## Out-of-band provisioning contract

The policy-root and anti-rollback runbook remains in [SIGNED_POLICY_ROOT_CHAIN_REVIEW_20261124.md](SIGNED_POLICY_ROOT_CHAIN_REVIEW_20261124.md). Before any future use, an independent deployment authority must provision and attest the policy root, TSA root, legal role bindings, revocation channel, monotonic sequence store, trusted clock and key-rotation/recovery procedures through independently authenticated channels. Values supplied by the receipt submitter or the same operator who supplies the evidence are not independent trust anchors.

## Validation and guardrails

- Parent: PR #49 exact head `c0c98d0843aaa53c7d8ec078ccf0a3b14a916e29`.
- RFC 3161 primitive is copied from the separately tested PR #50 research branch; its synthetic tests are retained.
- New integration tests exercise exact token/proof/signature bindings, order independence, authority mismatch, missing evidence, bad imprint, missing accuracy, and a pre-close interval crossing the close.
- No main writes, merge, promotion, V294 changes, canonical-history changes, model retuning, or prospective ledger writes.
- PR #13 remains separate, OPEN/DRAFT and untouched.
- All successful paths remain `BLOCKED_PROVENANCE`.
