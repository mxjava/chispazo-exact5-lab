# ORIGEN v0.3 — transparency ledger entry v2 for timestamped nested-signature bundles

**Classification:** RESEARCH ONLY / FAIL CLOSED. This is a diagnostic ledger-verification interface. It does not establish institutional provenance or enable production.

## Purpose

The detached sidecar in `NESTED_SIGNATURE_BUNDLE_TIMESTAMP_V1.md` proves, relative to caller-supplied TSA pins, that the exact normalized manifest claims, signed policy bytes, original artifact bytes and nested signature bytes existed by the RFC 3161 accuracy upper bound. Before this increment, the sidecar was not committed by the transparency ledger.

Entry schema v2 adds two mandatory fields to the existing ledger leaf:

- `timestamp_bundle_sha256`: SHA-256 of the exact canonical sidecar bytes.
- `timestamp_token_sha256`: SHA-256 of the exact RFC 3161 token DER bytes.

The complete exact field set is:

- `schema_version` = `origen.transparency-ledger-entry.v2`
- `ledger_id`
- `entry_id`
- `manifest_commitment_sha256`
- `artifact_sha256s` (sorted, unique, exact manifest artifact digest set)
- `timestamp_bundle_sha256`
- `timestamp_token_sha256`

V1 leaves are not accepted by the V2 verifier. The V1 verifier and schema remain unchanged for compatibility.

## Cycle-free construction order

1. Build and sign the CLASSIC manifest, using a placeholder for `ledger_anchor.inclusion_proof_sha256`.
2. Build the canonical timestamp sidecar. As specified in V1, it omits only that inclusion-proof digest; all other manifest claims, exact policy bytes, all artifact bytes and all detached signature bytes remain bound.
3. Obtain the RFC 3161 token over the exact sidecar bytes.
4. Create the canonical V2 ledger entry committing to the normalized manifest commitment, exact artifact digest set, sidecar SHA-256 and token DER SHA-256.
5. Append that exact entry to the transparency log and obtain a signed checkpoint and inclusion proof.
6. Put the exact inclusion-proof digest into the manifest. This field is excluded from the sidecar and normalized manifest commitment, so the sidecar and its timestamp remain stable.
7. Verify the exact final manifest, V2 entry, proof, checkpoint, sidecar, token, policy and original evidence bytes together.

This creates an acyclic commitment chain:

`manifest claims -> timestamp sidecar -> RFC 3161 token`
`manifest commitment + sidecar digest + token digest -> V2 ledger leaf`
`V2 ledger leaf -> inclusion proof -> final manifest proof digest`

## Verification behavior

`verify_transparency_ledger_bundle_inclusion_v2`:

1. snapshots artifact/signature byte mappings once and uses only those snapshots for sidecar reconstruction and nested verification;
2. rebuilds the canonical sidecar and requires byte-for-byte equality with the supplied sidecar;
3. verifies the RFC 3161 token, nonce, TSA root fingerprint, policy OID, accuracy interval and strict pre-close bound through the V1 verifier;
4. parses a canonical V2 ledger leaf with an exact field set and checks both timestamp digests against the exact bytes;
5. binds the normalized manifest commitment and sorted artifact digest set;
6. verifies the exact signed checkpoint, checkpoint identity, time, tree-size floor, inclusion-proof digest and RFC 6962 inclusion path over the exact V2 leaf bytes.

The output explicitly reports sidecar/token commitment and inclusion. It remains `BLOCKED_PROVENANCE`.

## Adversarial coverage

Synthetic tests cover:
- successful exact bundle/token commitment and inclusion;
- substituted sidecar digest in the V2 leaf;
- substituted token DER digest in the V2 leaf;
- sidecar byte mutation;
- rejection of V1 leaf schema at the V2 boundary;
- exact manifest-to-proof digest binding; and
- mutation of an inclusion path even after rebinding the proof digest.

All fixture keys, TSA certificates, manifests, policies, signatures, tokens and log checkpoints are synthetic.

## Remaining blockers

- The TSA root, OID, nonce policy, revocation state and verification clock are caller supplied, not independently provisioned.
- The log key, monotonic tree-size floor and checkpoint clock are caller supplied.
- This verifier does not replace consistency-proof and independent-witness verification.
- The new V2 leaf is not yet wired into `ExternalEvidenceAdvanceV1` or the deployment provider CAS. The CAS must receive and independently re-verify the exact V2 leaf, proof, checkpoint, timestamp sidecar and token bytes in the same transaction.
- Key authorization at the actual signature-creation instant remains unproven without an unpredictable signer challenge bound into the signed payload.
- Institutional signer identity, official physical source, custody and the prospective statistical criteria remain unverified.

No production status is changed. No canonical history, V294 artifact, main branch, or existing PR is modified or promoted.
