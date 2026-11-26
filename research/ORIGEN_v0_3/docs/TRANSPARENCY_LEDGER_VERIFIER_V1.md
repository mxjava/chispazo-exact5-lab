# ORIGEN v0.3 — signed transparency-ledger inclusion verifier v1

**Classification:** RESEARCH ONLY. A valid inclusion result does not authenticate provenance or enable production.

## Scope

This increment adds a narrow RFC 6962-style Merkle inclusion verifier. It consumes:

- the exact canonical physical-evidence manifest bytes;
- the exact canonical ledger-entry bytes;
- the exact canonical inclusion-proof envelope bytes;
- the exact canonical signed-checkpoint bytes;
- a caller-supplied Ed25519 log public key, expected log ID/key ID, minimum tree-size floor, and verification clock.

The verifier binds the ledger entry to the manifest's ledger ID, entry ID, normalized manifest commitment, and complete sorted artifact-digest set. It verifies the checkpoint signature and proves that the exact ledger-entry bytes are included in the checkpoint's Merkle root.

## Breaking the manifest/proof circular dependency

The physical manifest contains the inclusion-proof SHA-256. The inclusion proof contains the exact signed-checkpoint digest, while the ledger entry is included in the checkpoint. Hashing the full manifest into that ledger entry would create a cycle:

1. the manifest hash depends on the proof digest;
2. the proof digest depends on the checkpoint;
3. the checkpoint root depends on the ledger entry;
4. the ledger entry would depend on the full manifest hash.

The v1 ledger-entry schema therefore uses manifest_commitment_sha256, computed by parsing the already-canonical manifest, removing only ledger_anchor.inclusion_proof_sha256, re-encoding the remaining object with sorted keys and compact separators, and hashing those bytes with SHA-256. Every other manifest claim remains committed, including the ledger ID, entry ID, previous/current head claims, target, all artifacts, signatures, custody declarations, and time-proof declarations.

The full raw manifest SHA-256 is still reported separately. The full manifest commits to the exact proof bytes through inclusion_proof_sha256; the proof commits to the exact checkpoint bytes; the checkpoint commits to the Merkle root; and the Merkle path proves inclusion of the exact ledger-entry bytes. This is a deliberately specified normalized commitment, not the raw-file hash.

## Exact schemas

### Ledger entry

Canonical JSON with exactly these fields:

- schema_version = origen.transparency-ledger-entry.v1
- ledger_id
- entry_id
- manifest_commitment_sha256
- artifact_sha256s — sorted, unique list containing every manifest artifact digest

### Inclusion-proof envelope

Canonical JSON with exactly these fields:

- schema_version = origen.transparency-ledger-inclusion-proof.v1
- ledger_id
- entry_id
- log_id
- leaf_index
- checkpoint_sha256 — SHA-256 of the exact checkpoint bytes
- audit_path_b64 — canonical base64 encoding of 32-byte RFC 6962 audit-path nodes

The SHA-256 of the exact proof-envelope bytes must equal the manifest's ledger_anchor.inclusion_proof_sha256.

### Signed checkpoint

Canonical JSON with exactly these fields:

- schema_version = origen.transparency-ledger-checkpoint.v1
- log_id
- key_id
- tree_size
- root_hash
- issued_at_utc
- signature_b64

The Ed25519 signature covers a domain-separated canonical JSON encoding of all checkpoint fields except signature_b64. Leaf hashing uses SHA256(0x00 || exact_entry_bytes) and internal-node hashing uses SHA256(0x01 || left_hash || right_hash).

## What is verified

1. The physical manifest passes the existing strict parser.
2. The ledger entry exactly matches the manifest's ledger ID, entry ID, normalized commitment, and all artifact digests.
3. The checkpoint uses the expected log ID and key ID and satisfies the caller-supplied minimum tree-size floor.
4. The checkpoint signature verifies against the caller-supplied Ed25519 public key.
5. The proof bytes match the exact proof digest declared by the manifest.
6. The proof binds the exact checkpoint bytes, ledger ID, entry ID, and log ID.
7. The Merkle audit path verifies the exact ledger-entry bytes at the declared leaf index.

## What is not verified

- The log public key is not provisioned from an authenticated institution or independently pinned deployment channel.
- The minimum tree-size floor is caller-supplied and not stored in an independent monotonic service.
- The checkpoint time is checked only against a caller-supplied clock; no RFC 3161 token or trusted clock is verified.
- No consistency proof between checkpoints is checked. A signed root plus inclusion proof does not prove append-only continuity across time or prevent split views.
- No independent witness/gossip protocol or log governance is verified.
- The manifest's declared head_sha256/previous_head_sha256 remain claims; this increment does not reinterpret them as the Merkle root or verify a separate hash-chain continuity protocol.
- Custody receipts, custodian identity, physical event truth, and institutional signer roles remain unverified.
- No production eligibility or predictive edge is established.

The result always carries BLOCKED_PROVENANCE, UNVERIFIED_NO_CONSISTENCY_PROOF, and explicit caller-supplied trust-source labels.

## Synthetic test separation

Tests use a deterministic Ed25519 key generated solely for fixtures and a locally constructed Merkle tree. No Lotería Nacional, SEGOB, OIC, TSA, custodian, or external transparency-log key is embedded or claimed. Test success is not evidence that a real log exists or has accepted any Chispazo record.

## Next required interface

Before any provenance promotion, a separately reviewed increment must verify checkpoint consistency proofs across successive tree sizes and independently witnessed checkpoints, backed by a root and monotonic floor provisioned outside the caller. RFC 3161 tokens and custody receipts remain separate proof interfaces.
