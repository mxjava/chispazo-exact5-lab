# ORIGEN v0.3 — checkpoint witness quorum v1

**Status:** research-only verifier and synthetic fixtures. A successful result is not authenticated provenance, institutional governance, global gossip, or production eligibility.

## Scope

This interface verifies a root-signed witness registry and a quorum of distinct Ed25519 witness statements over the exact same:

- registry bytes and registry sequence;
- old and new signed checkpoint bytes;
- RFC 6962 consistency-proof bytes;
- log ID, checkpoint roots, and tree sizes.

The implementation is in src/origen/checkpoint_witness_quorum_v1.py. Tests use deterministic synthetic Ed25519 keys and synthetic Merkle checkpoints only.

## Verification order

1. Parse bounded canonical UTF-8 JSON. Reject duplicate keys, floats, non-standard constants, noncanonical encodings, and oversized/deep documents.
2. Verify the registry signature against the caller-supplied registry root key and exact root key ID.
3. Enforce registry ID, log ID, sequence floor, validity window, active membership, distinct witness IDs/key IDs/public keys, revocation flags, and quorum feasibility.
4. Verify both exact checkpoint byte strings and their RFC 6962 consistency proof through verify_checkpoint_consistency.
5. For each statement, bind the exact registry/checkpoint/proof digests, roots, sizes, registry sequence, witness ID, and key ID.
6. Enforce that statement issuance falls inside both the signed registry validity window and the witness key validity window, does not predate the checkpoint, is not in the future, is fresh, and respects the configured cross-witness clock-skew bound.
7. Verify the statement's domain-separated Ed25519 signature using the exact key entry in the signed registry.
8. Reject duplicate witness identities, duplicate signing-key identities, duplicate statement bytes, invalid extra statements, or a batch below the registry quorum threshold.

A quorum means only that the configured number of distinct registry identities signed the same exact checkpoint pair and consistency proof. It does **not** prove that the operators are independent organizations.

## Important temporal invariant

A witness statement cannot be accepted merely because its key was valid and its timestamp is recent. It must also have been issued at or after the registry's not_before_utc, and strictly before the registry's expires_at_utc. This prevents a statement from claiming authorization under a registry that had not yet become effective.

The verifier still receives verification_time from the caller. Therefore these timestamp checks are relative to an unauthenticated clock until a separately validated time source is integrated.

## Out-of-band provisioning contract (not implemented)

A production deployment must not read the following values from an evidence manifest, CLI argument, environment variable controlled by the evidence producer, or witness response:

- registry root public key and root key ID;
- expected registry ID and log ID;
- minimum accepted registry sequence;
- minimum accepted log tree size/checkpoint sequence;
- trusted verification time and revocation freshness policy;
- witness quorum threshold and operator-independence policy.

A future deployment adapter must obtain these from a separately controlled trust domain, such as a reviewed immutable deployment image/configuration plus an authenticated update channel. The root fingerprint should be approved through an independently authenticated institutional channel and recorded in a controlled change process. A key copied from a public webpage, repository, or the same log operator is not an independent trust anchor.

The accepted registry sequence and log tree-size floor must be stored in rollback-resistant state outside this repository and outside the evidence producer's control. Updates must be monotonic and atomic; a restore from backup must not silently lower the floor. Failure to read, authenticate, or advance this state must fail closed.

Trusted time must come from a separately verified source (for example, a fully validated RFC 3161 token and TSA certificate/revocation chain, with policy-specific constraints). A timestamp string, local system clock, Git commit date, HTTP Date header, or signed witness issued_at_utc field is not trusted time by itself.

No official institutional witness registry or root key has been identified or authenticated by this research branch. Do not populate a production trust store with synthetic keys.

## Split-view and independence limits

This verifier evaluates one batch of statements. It does not persist observations, compare batches, gossip with other clients, or detect that a log has shown different roots to disjoint witness groups. It also cannot establish that distinct witness IDs belong to distinct legal entities, operators, administrative domains, or infrastructure providers.

A future gossip/equivocation service must:
- retain signed statements and checkpoint bytes in independently controlled append-only storage;
- compare overlapping witness observations across clients and time;
- detect same-size conflicting roots and incompatible checkpoint histories;
- define witness failure/collusion assumptions and quorum intersection;
- expose auditable alerts and a fail-closed response;
- use independently governed witness operators and a published identity/rotation/revocation process.

Do not describe the current quorum result as global split-view protection.

## Status and safety

Even after a valid synthetic quorum, provenance_status remains BLOCKED_PROVENANCE. The blockers explicitly retain caller-supplied root, registry sequence, and clock; cross-batch gossip; institutional operator independence; RFC 3161; physical custody; and prospective edge requirements.

No official Chispazo record, mask, CS-11, weighing strip, act, recording, signed participation file, or independent custody receipt is supplied by these fixtures.

The module does not modify main, V294, or data/history/Chispazo_through_12249.csv. It does not enable production or alter model parameters.
