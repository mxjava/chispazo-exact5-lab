# ORIGEN v0.3 — RFC 6962 checkpoint consistency verifier v1

**Classification:** RESEARCH ONLY. A valid consistency proof does not authenticate the log operator, establish independent witness agreement, or enable production.

## Purpose

The inclusion verifier in the parent research increment proves that one exact ledger-entry byte string is included in one signed checkpoint. Inclusion alone does not show that a later checkpoint extends an earlier checkpoint. A log operator could sign two different roots at different times, including split views, without violating a single-checkpoint inclusion proof.

This increment adds a narrow verifier for append-only consistency between two exact, Ed25519-signed checkpoint byte strings.

## Inputs

- exact old signed-checkpoint bytes;
- exact new signed-checkpoint bytes;
- exact canonical consistency-proof envelope bytes;
- caller-supplied Ed25519 public key, expected log ID, expected key ID;
- caller-supplied minimum new tree-size floor;
- caller-supplied verification clock.

Both checkpoints must use the same log ID and key ID. Key rotation and cross-key transition proofs are deliberately out of scope.

## Consistency-proof envelope

Canonical UTF-8 JSON with exactly these fields:

- `schema_version = origen.transparency-ledger-consistency-proof.v1`
- `log_id`
- `old_checkpoint_sha256` — SHA-256 of exact old checkpoint bytes
- `new_checkpoint_sha256` — SHA-256 of exact new checkpoint bytes
- `old_tree_size`
- `new_tree_size`
- `consistency_path_b64` — canonical base64 array of 32-byte RFC 6962 proof nodes

Duplicate JSON keys, non-canonical JSON, floating-point numbers, non-standard constants, non-canonical base64, unexpected fields, oversized inputs, and non-32-byte proof nodes are rejected.

## Verification

1. Parse and validate both exact checkpoint byte strings.
2. Verify both checkpoint signatures using the same caller-supplied Ed25519 key and expected log/key identifiers.
3. Require positive signed-64-bit tree sizes, nondecreasing checkpoint times, and a new tree size at or above the caller-supplied floor.
4. Bind the proof to the exact old and new checkpoint SHA-256 digests and their declared tree sizes.
5. Verify the RFC 6962 consistency path using domain-separated Merkle node hashing: `SHA256(0x01 || left || right)`.
6. For equal tree sizes, accept only an empty proof and identical roots. For a smaller old tree, reject rollback, incomplete paths, extra nodes, or roots that do not establish append-only continuity.

The verifier is tested over every old/new tree-size pair from 1 through 32, plus adversarial checkpoint, proof, encoding, and time cases.

## What this proves

A successful result proves, relative to the supplied public key and supplied clock, that:
- both exact checkpoint byte strings have valid signatures under the same supplied key;
- the consistency envelope references those exact checkpoint bytes;
- the supplied RFC 6962 proof cryptographically establishes that the old Merkle tree is a prefix of the new Merkle tree.

The result reports `CONSISTENCY_VERIFIED_WITNESS_QUORUM_UNVERIFIED` and always returns `BLOCKED_PROVENANCE`.

## What this does not prove

- The log public key is not institutionally provisioned or independently pinned.
- The minimum tree-size floor is not persisted in an external monotonic service.
- The verification clock is not authenticated by RFC 3161 or another trusted-time service.
- No independent witness quorum, witness identity registry, gossip protocol, or split-view detection is verified.
- The log operator's governance, availability, or honesty is not established.
- Custodian identities, signed custody receipts, physical artifact truth, or institutional signer roles are not established.
- No Chispazo draw is authenticated and no predictive edge is established.

A consistency proof is not a witness. An operator-controlled key can sign two mutually consistent checkpoints; it can also equivocate to separate clients unless independent witnesses exchange and compare signed roots. Therefore this increment does not remove the independent-witness blocker.

## Synthetic fixture separation

All keys, leaves, checkpoints, and proofs in tests are deterministic synthetic fixtures. No Lotería Nacional, SEGOB, OIC, TSA, or external log key is embedded or claimed. Passing tests are software validation only and are not evidence that a real institutional log accepted any record.

## Next external boundary

The next meaningful integration requires a separately provisioned witness-key registry and a quorum policy delivered outside the caller, plus signed witness statements over exact checkpoint digests and cross-witness gossip or equivalent split-view detection. The trust anchor, monotonic checkpoint floor, and time source must be independently provisioned. RFC 3161 tokens and physical custody receipts remain separate evidence interfaces.
