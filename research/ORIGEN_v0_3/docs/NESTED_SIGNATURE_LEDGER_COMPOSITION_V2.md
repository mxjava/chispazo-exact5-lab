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

1. Construct the canonical physical manifest with all artifact declarations and a syntactically valid placeholder inclusion-proof digest.
2. Compute the V3 non-circular nested-signature payload and sign it with each declared physical signer.
3. Populate exact signature digests and construct the root-signed V3 policy authorizing the physical signers, receipt attester and custodian for their exact roles/artifact types.
4. Compute the ledger manifest commitment with only the inclusion-proof digest omitted; this commitment includes the populated nested-signature digests.
5. Build the ledger entry, signed checkpoint and exact inclusion proof; replace the placeholder with the proof's exact SHA-256.
6. At verification, re-verify the exact physical artifact bytes and nested signatures using the final manifest bytes. The V3 signature payload deliberately normalizes only the proof digest and signature digests.
7. Independently verify the exact ledger entry, inclusion proof, signed checkpoint, append-only consistency and witness observations.
8. Cross-bind the physical-signature result to the exact custody policy/manifest and require the exact custody record in the verified artifact map.
9. Return diagnostics only. Every result remains `BLOCKED_PROVENANCE`.

## Adversarial coverage

Synthetic tests exercise:
- successful nested-signature + custody + RFC 3161 + ledger + witness composition while still blocked;
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
