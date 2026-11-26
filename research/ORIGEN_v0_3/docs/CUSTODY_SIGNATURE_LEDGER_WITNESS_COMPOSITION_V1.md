# ORIGEN v0.3 — custody signature, RFC 3161, ledger and witness composition v1

**Classification:** RESEARCH ONLY. Every successful result remains `BLOCKED_PROVENANCE`. This interface composes cryptographic diagnostics; it does not authenticate institutional identity, physical draw truth, or production eligibility.

## Purpose

The V3 custody verifier already validates the exact root-signed receipt, signed policy, custody-record bytes, portfolio bytes and detached Ed25519 custodian signature. The RFC 3161 sidecar verifier timestamps the exact 64-byte detached signature without modifying the receipt that the signature references.

Separate research increments already verify:

- exact physical-manifest and Merkle-ledger inclusion;
- RFC 6962 checkpoint append-only consistency;
- a root-signed witness registry and quorum of distinct witness keys;
- offline comparison of independently supplied observation batches for same-size conflicting roots.

This increment composes those interfaces and closes the byte-binding gap between them.

## Non-circular signature timestamp binding

The physical manifest has an existing `trusted_time_proofs` collection. The composition requires one additional entry with:

- `event_id = custody-signature-sha256:<SHA-256 of exact detached signature bytes>`;
- `authority_id = tsa-root-sha256:<SHA-256 of the supplied TSA root certificate>`;
- `proof_sha256 = SHA-256 of the exact RFC 3161 token DER bytes`;
- `event_at_utc = the exact RFC 3161 genTime`.

This signature-time proof is a separate time event. It is **not** reused as the custody receipt event, whose time proof must match the custodian's `received_at_utc`. That distinction preserves the manifest parser's event semantics and avoids putting the timestamp-token digest into the already-signed receipt.

The manifest must also bind:

- the `SEGOB-OIC-CUSTODY-RECORD` artifact digest and exact byte length to the V3 custody record;
- its custody event's subject, role, receipt digest and received time to the V3 custody chain;
- the target contest, CLASSIC modality and 21:00 close to the exact custody record.

The V3 and RFC 3161 verifiers still validate the exact source bytes independently. Manifest claims are not treated as signatures or authenticated records.

## Composition order

1. Normalize the caller-supplied verification time once to UTC.
2. Verify V3 signed policy, root receipt attestation, custody record, portfolio and detached custodian signature.
3. Verify the RFC 3161 token over the exact detached signature bytes and require its complete accuracy interval to be after receipt and strictly before Classic 21:00.
4. Parse the exact canonical physical manifest and cross-bind the custody record, receipt digest, detached signature event, token digest, TSA-root fingerprint and genTime.
5. Verify manifest-bound ledger inclusion and append-only checkpoint consistency using the exact same new checkpoint bytes.
6. Re-verify every witness observation batch, including its signed registry, checkpoint pair, consistency proof and quorum statements.
7. Require the exact ledger checkpoint digest to appear as an old or new checkpoint in at least one witness batch.
8. Return the bounded gossip comparison status. A supplied-batch split view is surfaced, never hidden or promoted.

## Result semantics

The result distinguishes:

- `NO_CONFLICT_FOUND_IN_SUPPLIED_BATCHES_NOT_GLOBAL_PROOF`;
- `SPLIT_VIEW_DETECTED_IN_SUPPLIED_BATCHES`;
- `INSUFFICIENT_OVERLAP_NO_SPLIT_VIEW_CLAIM`.

No-conflict means only that the supplied verified batches had comparable tree sizes and no conflict was found in those batches. It is not a global proof, network gossip, durable persistence, or proof of independent collection.

Every result is `BLOCKED_PROVENANCE`. No result enum or capability authorizes production.

## Adversarial tests

Synthetic-only tests cover:

- successful exact-byte composition while remaining blocked;
- altered manifest timestamp-token digest;
- absence of the exact ledger checkpoint from witness batches;
- a valid same-size fork reported as a split view;
- one-time normalization of a stateful caller timezone.

All receipts, policies, custody records, signatures, TSA certificates/tokens, manifests, ledger entries/checkpoints, witness registries and statements are generated test fixtures. No institutional key or real Chispazo physical evidence is embedded.

## Remaining trust boundary

The caller still supplies the V3 policy root, TSA root, log key, witness-registry root, policy/registry/tree-size floors and verification clock. The module does not provision or persist those values outside the caller. It does not check TSA revocation, authenticate TSA policy authorization, establish legal identity or organizational independence of custodians/witnesses, persist observation batches, implement network gossip, or verify original institutional Acta/CS-11/Sumario/Tira de Pesaje bytes.

Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

V294 and the canonical history are not modified. No main write, merge or promotion is part of this increment.
