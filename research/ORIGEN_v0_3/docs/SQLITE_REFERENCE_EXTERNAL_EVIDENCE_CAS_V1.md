# SQLite reference CAS for ORIGEN external-evidence watermarks

Status: **research-only reference and conformance fixture**. This is not a production provider, not an independent trust service, and not evidence of institutional custody.

## What is implemented

`SQLiteReferenceExternalEvidenceCASV1` provides a local filesystem-backed reference for the external-evidence watermark portion of the provider contract:

- Explicit one-time genesis insertion; a second genesis attempt is rejected.
- SQLite WAL mode and `synchronous=FULL`.
- `BEGIN IMMEDIATE` serialization and a conditional generation/digest update.
- Exact canonical watermark bytes and SHA-256 digest verification on every read.
- Atomic generation increment with checkpoint and registry watermark update.
- Fail-closed handling for missing genesis, stale generation, stale digest, corrupt bytes, and SQL transaction failure.
- Reopen and concurrent-writer tests.

The implementation reuses the exact application-side `ExternalEvidenceWatermarkV1` and `ExternalEvidenceAdvanceV1` validation. It deliberately does **not** implement `DeploymentTrustProvider`; it cannot be passed to the full evidence-composition entry point.

## Validation boundary

The included fixtures are synthetic. `provision_genesis` accepts a caller-supplied record digest but does not authenticate the signer, the institution, the source instrument, or the ceremony. The module does not verify policy signatures, receipt attestations, physical signatures, RFC 3161 tokens, witness signatures, or ledger inclusion/consistency proofs inside an independently isolated service. Those checks remain the responsibility of a future reviewed provider.

## Explicit non-guarantees

A SQLite database and its WAL can be copied, restored, replaced, or rolled back by an operator who controls the storage and backups. This module has no external monotonic anchor and cannot detect restoration of an older, internally consistent database snapshot. WAL plus FULL synchronous mode improves local crash durability; it does not establish independent custody, tamper resistance against privileged storage administrators, or institutional trust.

It also does not atomically combine the complete policy sequence, trusted-time watermark, clock sample, nonce consumption, physical trust context, and external-evidence watermark in one production transaction. The production contract still requires all of those fields to share one linearizable transaction and one independently anchored generation.

## Required production successor

A production backend must be separately administered and must:

1. Provision the root, TSA/log/registry keys, policy floor, and signed genesis through a dual-control out-of-band ceremony.
2. Re-verify exact policy, receipt, physical-signature, RFC 3161, ledger, registry, and witness bytes against authoritative provisioned material.
3. Compare and advance policy sequence, trusted-time upper bound, nonce consumption, ledger checkpoint, and registry digest atomically.
4. Anchor monotonic state outside the database's own backup/restore domain, or provide an independently witnessed recovery protocol that detects rollback and split-brain.
5. Produce externally retained signed transaction receipts and an independently audited access/recovery trail.
6. Pass process-crash, power-loss, concurrent-writer, stale-read, equivocation, backup-restore, failover, and split-brain exercises.

Until that exists, the SQLite reference is only an executable local conformance aid. Every successful ORIGEN result remains `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
