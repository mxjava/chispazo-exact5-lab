"""Offline cross-batch comparison of verified ORIGEN witness observations.

This module re-verifies every supplied batch before comparing signed checkpoint
roots. It can detect same-size conflicting roots and same-key witness
equivocation within the supplied batches. It does not implement network gossip,
persistent storage, authenticated observer identity, or global split-view
protection. Every result remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import base64
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from origen.checkpoint_witness_quorum_v1 import (
    MAX_REGISTRY_BYTES,
    MAX_STATEMENTS,
    MAX_WITNESS_BYTES,
    verify_checkpoint_witness_quorum,
)
from origen.independent_trust_adapter import ProvenanceStatus

MAX_OBSERVATION_BATCHES = 32
MAX_GOSSIP_TOTAL_BYTES = 8 * 1024 * 1024
BATCH_DOMAIN = b"ORIGEN-WITNESS-GOSSIP-BATCH-V1\x00"

GOSSIP_REMAINING_BLOCKERS = (
    "REGISTRY_ROOT_NOT_INDEPENDENTLY_PROVISIONED",
    "LOG_SIGNING_KEY_NOT_INDEPENDENTLY_PROVISIONED",
    "REGISTRY_SEQUENCE_FLOOR_NOT_EXTERNALLY_PERSISTED",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "OBSERVATION_BATCH_SOURCE_AND_COLLECTOR_IDENTITY_NOT_AUTHENTICATED",
    "OBSERVATIONS_NOT_PERSISTED_IN_INDEPENDENT_APPEND_ONLY_STORAGE",
    "NETWORK_GOSSIP_AND_GLOBAL_SPLIT_VIEW_DETECTION_NOT_ESTABLISHED",
    "WITNESS_OPERATOR_INDEPENDENCE_NOT_INSTITUTIONALLY_ESTABLISHED",
    "RFC3161_TIME_STAMP_NOT_VERIFIED",
    "PHYSICAL_CUSTODY_AND_ARTIFACT_TRUTH_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class WitnessObservationBatch:
    """Untrusted transport wrapper; every byte field is re-verified on use."""

    raw_registry_bytes: bytes
    raw_old_checkpoint_bytes: bytes
    raw_new_checkpoint_bytes: bytes
    raw_consistency_proof_bytes: bytes
    raw_witness_statement_bytes: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class WitnessGossipFinding:
    """A cryptographically supported same-size root conflict in supplied data."""

    log_id: str
    tree_size: int
    conflicting_root_sha256: tuple[str, ...]
    checkpoint_sha256: tuple[str, ...]
    witness_ids: tuple[str, ...]
    witness_key_sha256: tuple[str, ...]
    statement_sha256: tuple[str, ...]
    batch_indexes: tuple[int, ...]
    equivocating_witness_key_sha256: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WitnessGossipInspection:
    batch_count: int
    batch_sha256: tuple[str, ...]
    registry_sequences: tuple[int, ...]
    verified_witness_statement_count: int
    compared_checkpoint_observation_count: int
    comparable_tree_size_count: int
    distinct_witness_key_count: int
    split_view_detected: bool
    witness_equivocation_detected: bool
    comparison_status: str
    observation_scope: str
    persistence_status: str
    trust_anchor_source: str
    registry_sequence_source: str
    verification_clock_source: str
    provenance_status: ProvenanceStatus
    findings: tuple[WitnessGossipFinding, ...]
    remaining_blockers: tuple[str, ...]


def _batch_sha256(batch: WitnessObservationBatch) -> str:
    """Hash exact batch bytes with statement order normalized for deduplication."""
    parts = (
        batch.raw_registry_bytes,
        batch.raw_old_checkpoint_bytes,
        batch.raw_new_checkpoint_bytes,
        batch.raw_consistency_proof_bytes,
        *sorted(hashlib.sha256(item).digest() for item in batch.raw_witness_statement_bytes),
    )
    framed = bytearray(BATCH_DOMAIN)
    for part in parts:
        framed.extend(len(part).to_bytes(8, "big"))
        framed.extend(part)
    return hashlib.sha256(framed).hexdigest()


def inspect_witness_gossip(
    observation_batches: Sequence[WitnessObservationBatch],
    *,
    pinned_registry_root_public_key_bytes: bytes,
    expected_registry_root_key_id: str,
    expected_registry_id: str,
    minimum_registry_sequence: int,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_new_tree_size: int,
    verification_time: datetime,
) -> WitnessGossipInspection:
    """Re-verify and compare at least two non-identical witness observation batches.

    A split view is reported when valid signed observations contain different
    Merkle roots for the same log and tree size. Witness equivocation is reported
    when the same Ed25519 public-key fingerprint signs those conflicting roots.
    The function accepts no caller-constructed verification result objects.
    """
    if type(observation_batches) not in (tuple, list):
        raise TypeError("observation_batches must be an exact tuple or list")
    if not 2 <= len(observation_batches) <= MAX_OBSERVATION_BATCHES:
        raise ValueError(
            f"observation_batches must contain 2..{MAX_OBSERVATION_BATCHES} batches"
        )

    total_bytes = 0
    batch_hashes: list[str] = []
    seen_batch_hashes: set[str] = set()
    verified_sequences: set[int] = set()
    registry_digests_by_sequence: dict[int, str] = {}
    statement_hashes: set[str] = set()
    witness_key_fingerprints: set[str] = set()

    # (log_id, tree_size) -> root -> accumulated exact evidence references.
    views: dict[tuple[str, int], dict[str, dict[str, set]]] = defaultdict(dict)
    # (log_id, tree_size, public-key fingerprint) -> roots observed for that key.
    key_views: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    compared_observations = 0

    for batch_index, batch in enumerate(observation_batches):
        if type(batch) is not WitnessObservationBatch:
            raise TypeError(f"observation_batches[{batch_index}] must be an exact WitnessObservationBatch")
        byte_fields = (
            batch.raw_registry_bytes,
            batch.raw_old_checkpoint_bytes,
            batch.raw_new_checkpoint_bytes,
            batch.raw_consistency_proof_bytes,
        )
        if any(type(value) is not bytes for value in byte_fields):
            raise TypeError(f"observation_batches[{batch_index}] byte fields must be exact bytes")
        if type(batch.raw_witness_statement_bytes) is not tuple:
            raise TypeError(
                f"observation_batches[{batch_index}].raw_witness_statement_bytes must be an exact tuple"
            )
        if not 1 <= len(batch.raw_witness_statement_bytes) <= MAX_STATEMENTS:
            raise ValueError(
                f"observation_batches[{batch_index}] must contain 1..{MAX_STATEMENTS} witness statements"
            )
        if any(type(value) is not bytes for value in batch.raw_witness_statement_bytes):
            raise TypeError(
                f"observation_batches[{batch_index}] witness statements must be exact bytes"
            )
        if len(batch.raw_registry_bytes) > MAX_REGISTRY_BYTES:
            raise ValueError(f"observation_batches[{batch_index}] registry exceeds byte limit")
        if any(len(value) > MAX_WITNESS_BYTES for value in batch.raw_witness_statement_bytes):
            raise ValueError(f"observation_batches[{batch_index}] witness statement exceeds byte limit")

        total_bytes += sum(len(value) for value in byte_fields)
        total_bytes += sum(len(value) for value in batch.raw_witness_statement_bytes)
        if total_bytes > MAX_GOSSIP_TOTAL_BYTES:
            raise ValueError("combined observation batches exceed total byte limit")

        batch_digest = _batch_sha256(batch)
        if batch_digest in seen_batch_hashes:
            raise ValueError("duplicate observation batch adds no cross-batch comparison evidence")
        seen_batch_hashes.add(batch_digest)
        batch_hashes.append(batch_digest)

        # Do not trust a caller-supplied inspection object: verify the original
        # registry, checkpoint, consistency-proof, and statement bytes again.
        verified = verify_checkpoint_witness_quorum(
            batch.raw_registry_bytes,
            batch.raw_witness_statement_bytes,
            batch.raw_old_checkpoint_bytes,
            batch.raw_new_checkpoint_bytes,
            batch.raw_consistency_proof_bytes,
            pinned_registry_root_public_key_bytes=pinned_registry_root_public_key_bytes,
            expected_registry_root_key_id=expected_registry_root_key_id,
            expected_registry_id=expected_registry_id,
            minimum_registry_sequence=minimum_registry_sequence,
            pinned_log_public_key_bytes=pinned_log_public_key_bytes,
            expected_log_id=expected_log_id,
            expected_log_key_id=expected_log_key_id,
            minimum_new_tree_size=minimum_new_tree_size,
            verification_time=verification_time,
        )
        registry_sequence = verified.registry.registry_sequence
        registry_digest = verified.registry.registry_sha256
        previous_registry_digest = registry_digests_by_sequence.setdefault(
            registry_sequence,
            registry_digest,
        )
        if previous_registry_digest != registry_digest:
            raise ValueError(
                "same registry sequence has different signed digest"
            )
        verified_sequences.add(registry_sequence)

        # The quorum verifier has already strictly parsed and authenticated
        # these exact bytes. Decode only to associate each signed statement
        # with the public-key fingerprint from that verified registry.
        registry_document = json.loads(batch.raw_registry_bytes.decode("utf-8"))
        entries_by_id = {
            entry["witness_id"]: entry for entry in registry_document["witnesses"]
        }
        consistency = verified.checkpoint_consistency
        checkpoint_observations = (
            (
                consistency.old_tree_size,
                consistency.old_root_sha256,
                consistency.old_checkpoint_sha256,
            ),
            (
                consistency.new_tree_size,
                consistency.new_root_sha256,
                consistency.new_checkpoint_sha256,
            ),
        )

        for raw_statement in batch.raw_witness_statement_bytes:
            statement = json.loads(raw_statement.decode("utf-8"))
            witness_id = statement["witness_id"]
            entry = entries_by_id[witness_id]
            public_key_bytes = base64.b64decode(entry["public_key_b64"], validate=True)
            key_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
            statement_digest = hashlib.sha256(raw_statement).hexdigest()
            statement_hashes.add(statement_digest)
            witness_key_fingerprints.add(key_fingerprint)

            for tree_size, root_sha256, checkpoint_sha256 in checkpoint_observations:
                view_key = (consistency.log_id, tree_size)
                root_record = views[view_key].setdefault(
                    root_sha256,
                    {
                        "checkpoint_sha256": set(),
                        "witness_ids": set(),
                        "witness_key_sha256": set(),
                        "statement_sha256": set(),
                        "batch_indexes": set(),
                    },
                )
                root_record["checkpoint_sha256"].add(checkpoint_sha256)
                root_record["witness_ids"].add(witness_id)
                root_record["witness_key_sha256"].add(key_fingerprint)
                root_record["statement_sha256"].add(statement_digest)
                root_record["batch_indexes"].add(batch_index)
                key_views[(consistency.log_id, tree_size, key_fingerprint)].add(root_sha256)
                compared_observations += 1

    # A comparison is meaningful only under one exact signed registry snapshot.
    # Pooling statements authorized by different sequences can re-introduce a
    # witness key that a later registry has revoked. Registry rotation must be
    # handled as a separate comparison against externally persisted state.
    if len(verified_sequences) != 1:
        raise ValueError(
            "all witness batches must use one exact registry sequence"
        )

    findings: list[WitnessGossipFinding] = []
    for (log_id, tree_size), roots in sorted(views.items()):
        if len(roots) <= 1:
            continue
        equivocating_keys = tuple(sorted(
            key_fingerprint
            for (key_log_id, key_tree_size, key_fingerprint), key_roots in key_views.items()
            if key_log_id == log_id and key_tree_size == tree_size and len(key_roots) > 1
        ))
        all_records = tuple(roots[root] for root in sorted(roots))
        findings.append(
            WitnessGossipFinding(
                log_id=log_id,
                tree_size=tree_size,
                conflicting_root_sha256=tuple(sorted(roots)),
                checkpoint_sha256=tuple(sorted({
                    digest
                    for record in all_records
                    for digest in record["checkpoint_sha256"]
                })),
                witness_ids=tuple(sorted({
                    witness_id
                    for record in all_records
                    for witness_id in record["witness_ids"]
                })),
                witness_key_sha256=tuple(sorted({
                    fingerprint
                    for record in all_records
                    for fingerprint in record["witness_key_sha256"]
                })),
                statement_sha256=tuple(sorted({
                    digest
                    for record in all_records
                    for digest in record["statement_sha256"]
                })),
                batch_indexes=tuple(sorted({
                    index
                    for record in all_records
                    for index in record["batch_indexes"]
                })),
                equivocating_witness_key_sha256=equivocating_keys,
            )
        )

    comparable_tree_size_count = sum(
        1
        for roots in views.values()
        if len({
            batch_index
            for record in roots.values()
            for batch_index in record["batch_indexes"]
        }) >= 2
    )
    split_view = bool(findings)
    witness_equivocation = any(
        finding.equivocating_witness_key_sha256 for finding in findings
    )
    if split_view:
        comparison_status = "SPLIT_VIEW_DETECTED_IN_SUPPLIED_BATCHES"
    elif comparable_tree_size_count == 0:
        comparison_status = "INSUFFICIENT_OVERLAP_NO_SPLIT_VIEW_CLAIM"
    else:
        comparison_status = "NO_CONFLICT_FOUND_IN_SUPPLIED_BATCHES_NOT_GLOBAL_PROOF"
    return WitnessGossipInspection(
        batch_count=len(batch_hashes),
        batch_sha256=tuple(batch_hashes),
        registry_sequences=tuple(sorted(verified_sequences)),
        verified_witness_statement_count=len(statement_hashes),
        compared_checkpoint_observation_count=compared_observations,
        comparable_tree_size_count=comparable_tree_size_count,
        distinct_witness_key_count=len(witness_key_fingerprints),
        split_view_detected=split_view,
        witness_equivocation_detected=witness_equivocation,
        comparison_status=comparison_status,
        observation_scope="SUPPLIED_VERIFIED_BATCHES_ONLY",
        persistence_status="NOT_PERSISTED_BY_THIS_MODULE",
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        registry_sequence_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        findings=tuple(findings),
        remaining_blockers=GOSSIP_REMAINING_BLOCKERS,
    )
