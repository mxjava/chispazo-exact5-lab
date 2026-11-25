# ORIGEN v0.3 — witness gossip comparison v1

**Classification:** research-only offline comparison. No network gossip, persistent ledger, authenticated observer identity, institutional independence, or production provenance is established.

## Purpose

The checkpoint witness quorum verifier validates one batch of witness statements. It cannot detect a log that presents one signed Merkle root to one group and a different root to another group.

This increment adds a bounded comparison interface for two or more independently supplied observation batches. It re-verifies every original registry, checkpoint, consistency-proof, and witness-statement byte string before comparing the signed checkpoint roots.

Implementation: `src/origen/checkpoint_witness_gossip_v1.py`.

## Detection rules

For every successfully verified witness statement, the inspector records both the old and new checkpoint observations:

- log identifier;
- tree size;
- Merkle root;
- exact checkpoint SHA-256;
- witness identifier;
- SHA-256 fingerprint of the registry public key;
- exact witness-statement SHA-256;
- input batch index.

A **split-view finding** is emitted when the supplied, cryptographically verified observations contain more than one Merkle root for the same log ID and tree size. This detects conflicting roots even when the observations came from disjoint witness groups.

A **witness-equivocation finding** is emitted when the same Ed25519 public-key fingerprint is associated with more than one root for the same log ID and tree size.

The inspector does not infer malice. A conflict can indicate log equivocation, witness equivocation, a compromised key, incorrect log identity, or an upstream collection defect. It is an integrity incident requiring independent investigation.

## Fail-closed input contract

- Requires 2–32 exact `WitnessObservationBatch` values.
- Each batch carries original registry, old checkpoint, new checkpoint, consistency-proof, and witness-statement bytes.
- Every batch is re-verified with the same caller-supplied registry root, log key, expected IDs, sequence floor, tree-size floor, and verification time.
- Rejects duplicate batches, invalid signatures, malformed statements, noncanonical encodings, invalid proofs, and any batch that fails its quorum.
- Bounds each batch through the existing verifiers and caps aggregate input at 8 MiB.
- Does not accept caller-constructed quorum inspection objects or caller-supplied root summaries.

A duplicate batch is rejected because replaying the same exact evidence does not add a second observation.

## Interpretation

Possible comparison statuses:

- `SPLIT_VIEW_DETECTED_IN_SUPPLIED_BATCHES`: at least one same-size conflicting-root finding exists in the supplied verified data.
- `NO_CONFLICT_FOUND_IN_SUPPLIED_BATCHES_NOT_GLOBAL_PROOF`: no same-size root conflict was found in these inputs only.

The second status is deliberately not a statement that the log is globally consistent. The module does not know whether the supplied batches cover all clients, all witnesses, all time periods, or all checkpoint sizes.

Every output retains:

- `provenance_status = BLOCKED_PROVENANCE`;
- caller-supplied unauthenticated trust-anchor, sequence-floor, and clock labels;
- `persistence_status = NOT_PERSISTED_BY_THIS_MODULE`;
- `observation_scope = SUPPLIED_VERIFIED_BATCHES_ONLY`.

## What remains unimplemented

A production-grade gossip system still needs:

1. Independently authenticated collector/client identities and signed observation receipts.
2. Durable append-only storage in an administrative domain separate from the log operator.
3. Authenticated exchange of observations between clients and witnesses.
4. Persistent, rollback-resistant checkpoint and registry sequence state.
5. Detection and alerting for same-size root conflicts and incompatible histories across time.
6. A defined witness-intersection and collusion model, including key rotation and revocation.
7. Trusted time, such as full RFC 3161 token and TSA-chain verification.
8. Institutional identity and authority evidence for each witness operator.
9. Independent physical custody and original draw records.

Different witness IDs or public keys do not prove different organizations. Two supplied batches do not prove two independent collectors. A successful comparison is not a provenance decision.

## Synthetic test boundary

Tests use deterministic synthetic Ed25519 keys and synthetic Merkle trees. They cover:

- adjacent append-only checkpoints with no observed conflict;
- same-size conflicting roots signed by an overlapping witness group;
- same-size conflicting roots observed by disjoint witness groups;
- same-key witness equivocation;
- invalid statement signatures;
- duplicate batches;
- exact transport and statement-container types;
- the invariant that all outputs remain `BLOCKED_PROVENANCE`.

No synthetic key, registry, checkpoint, or witness statement is institutional evidence.

## Protections

This module is research-only. It does not write to `main`, modify V294, change model parameters, append to the canonical Chispazo history, or enable production. The canonical history and prospective edge gates remain unchanged.
