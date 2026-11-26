# ORIGEN v0.3 — nested signatures with ledger inclusion, V3 composition v2

**Classification:** RESEARCH ONLY. Every successful inspection remains `BLOCKED_PROVENANCE`. This document defines a non-circular byte-binding contract; it does not authenticate an institution, source system, physical draw, custodian, TSA, log operator or witness.

## Integration gap closed

The custody/RFC 3161/ledger/witness composition previously parsed the physical manifest structurally and cross-bound the custody-record artifact, but did not invoke the existing V3 nested physical-evidence signature verifier. The composition now requires the exact artifact and detached-signature byte maps and re-verifies every declared artifact and nested Ed25519 signature using the same signed V3 policy envelope as the root receipt and custodian.

The resulting inspection is cross-bound to the same exact manifest digest, policy-envelope digest, CLASSIC policy domain and policy sequence reported by the custody chain. The exact custody-record bytes must also occur under their manifest digest in the artifact map.

## Why a second V3 signature-payload domain is necessary

The previous payload covered `ledger_anchor.inclusion_proof_sha256`. The ledger entry commitment includes nested signature digests. Therefore:

1. A nested signature digest depends on the signed manifest payload.
2. The ledger entry includes that signature digest.
3. The inclusion proof depends on the ledger entry and signed checkpoint.
4. The manifest includes the inclusion-proof digest.
5. If the nested signature covers that proof digest, the signature digest depends on the proof digest from step 3.

That is a dependency cycle, not merely an inconvenient build order.

V3 nested physical signatures now use the explicit domain:

`origen.physical-evidence-signature.v2`

The payload omits:
- each `signatures[].signature_sha256` value, as before;
- only `ledger_anchor.inclusion_proof_sha256`, to break the cycle.

It continues to sign the remaining manifest claims, including modality, contest, artifact digests and lengths, signer identities/roles/key IDs, custody declarations, ledger ID, entry ID, previous-head digest and declared head digest. The V2 signature payload and its behavior are unchanged.

The omitted proof digest is not trusted by omission: the ledger verifier independently checks the exact proof bytes against the manifest's proof digest, the exact entry/manifest commitment, the signed checkpoint and the consistency chain. Witness verification independently checks the supplied signed checkpoint observations. The composition never treats a valid nested signature as proof that the external ledger is institutionally operated.

## Required build and verification order

1. Construct the root-signed V3 policy with a deliberate lead interval between `issued_at_utc` and `not_before_utc`; authorize the physical signers, receipt attester and custodian for their exact roles/artifact types.
2. Obtain a detached RFC 3161 token whose message imprint covers the exact signed policy-envelope bytes. Require the complete accuracy interval to be at or after `issued_at_utc` and strictly before `not_before_utc`.
3. Insert one manifest `trusted_time_proofs` event for `trust-policy-envelope-sha256:<envelope digest>`, binding the exact TSA-root fingerprint, `genTime`, and token SHA-256. This event is a detached sidecar claim, not a self-authenticating TSA identity.
4. Construct the canonical physical manifest with all artifact declarations, custody-time proof, policy-envelope-time proof and a syntactically valid placeholder inclusion-proof digest.
5. Compute the V3 non-circular nested-signature payload and sign it with each declared physical signer. The signatures therefore commit to the policy-envelope timestamp event and exact token digest.
6. Compute the ledger manifest commitment with only the inclusion-proof digest omitted; this commitment includes the policy-time event, nested-signature digests and all other manifest claims.
7. Build the ledger entry, signed checkpoint and exact inclusion proof; replace the placeholder with the proof's exact SHA-256.
8. At verification, re-verify the exact policy envelope, its RFC 3161 message imprint and pre-effective accuracy interval, then re-verify exact physical artifact bytes and nested signatures using the final manifest bytes.
9. Independently verify the exact ledger entry, inclusion proof, signed checkpoint, append-only consistency and witness observations. Because only the inclusion-proof digest is normalized out, the policy-time event/token digest is transitively committed by the ledger leaf.
10. Cross-bind the physical-signature result to the exact custody policy/manifest and require the exact custody record in the verified artifact map.
11. Return diagnostics only. Every result remains `BLOCKED_PROVENANCE`.

## V3 policy-envelope existence timestamp (new composition increment)

The composition now requires a second detached RFC 3161 token, distinct from the token over the custodian's detached signature. This second token's message imprint is SHA-256 over the exact `signed_policy_envelope_bytes`; reconstructed JSON or a policy object is never timestamped in its place.

The verifier checks:

- the exact V3 envelope signature/domain/key/sequence using the same caller-supplied root pin as the custody chain;
- the RFC 3161 token, TSA chain, nonce and exact envelope message imprint using a separately supplied TSA root pin;
- non-negative, present accuracy and the full interval `genTime ± accuracy`;
- the full interval starts no earlier than the signed `issued_at_utc` and ends strictly before signed `not_before_utc`, proving existence before activation relative to the supplied TSA root;
- exactly one manifest event whose event ID is `trust-policy-envelope-sha256:<SHA-256(envelope)>`, whose authority ID identifies the exact TSA-root fingerprint, whose event time equals RFC 3161 `genTime`, and whose proof digest equals the exact token bytes;
- the event is distinct from custody receipt events.

That event is included in the nested physical-signature payload and in the ledger manifest commitment. The ledger normalizes only `ledger_anchor.inclusion_proof_sha256`; it does not omit `trusted_time_proofs`. The exact token bytes are therefore committed by the manifest digest and the ledger leaf, while the RFC 3161 token independently proves the imprint over the exact policy envelope relative to the caller's TSA root.

The additional result field `policy_envelope_timestamp_proof_in_manifest_commitment_verified` describes this byte-binding chain only. It does not mean the log is institutionally operated, the TSA root is authentic, or the TSA clock/revocation state is independently trusted.

Synthetic adversarial tests cover wrong-envelope imprint, nonce mismatch, absent accuracy, and a timestamp interval at/after policy activation. The fixture's policy is deliberately issued before its activation time to make the chronology test meaningful.

## Adversarial coverage

Synthetic tests exercise:
- successful nested-signature + custody + RFC 3161 + policy-envelope timestamp + ledger + witness composition while still blocked;
- exact V3 policy-envelope timestamp imprint and pre-effective accuracy interval;
- policy timestamp nonce, accuracy, and post-activation rejection;
- a modified trusted-time proof claim, which invalidates nested signatures;
- a modified inclusion-proof digest, which is not part of the nested-signature payload but is rejected by the ledger verifier;
- altered original artifact bytes;
- altered detached-signature bytes;
- missing or extra artifact/signature map entries;
- missing ledger checkpoint from verified witness batches;
- same-size split-view observations;
- lazy/mutable witness-batch rejection and resource bounds;
- single normalization of the caller-supplied verification clock.

All private keys, root pins, certificates, timestamp tokens, receipts, custody records, manifests, artifacts, ledger records, checkpoints and witness statements are synthetic test fixtures.

## Remaining blockers

- V3 root anchor, TSA root, log key and witness-registry root are still caller supplied, not independently provisioned.
- Policy/registry/tree-size anti-rollback floors are not persisted in an external monotonic store.
- The verification clock is not authenticated.
- TSA revocation and institutional TSA policy authorization are not independently established.
- Log and witness operators, collectors and custodians have no authenticated institutional identity or demonstrated administrative/legal independence.
- Witness observations are not durably persisted or globally gossiped.
- Original Acta, CS-11, Sumario, Tira de Pesaje, calibration records and signed participation/cancellation files have not been acquired with authentic custody.
- Prospective statistical edge requirements remain unmet.

Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

No main write, merge, promotion, canonical-history append or V294 change is part of this increment.
