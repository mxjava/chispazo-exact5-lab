"""Research-only composition of V2 timestamp-bundle inclusion and RFC 6962 continuity.

The exact same new checkpoint bytes must pass both verifiers. The prior
checkpoint is bound to the provider's accepted watermark (size, root and raw
checkpoint digest). This remains a diagnostic verifier: roots, floor and clock
are caller inputs, and no independent witness quorum is authenticated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .independent_trust_adapter import ProvenanceStatus
from .transparency_checkpoint_consistency_v1 import (
    CheckpointConsistencyInspection,
    verify_checkpoint_consistency,
)
from .transparency_ledger_bundle_verifier_v2 import (
    TransparencyLedgerBundleInspectionV2,
    verify_transparency_ledger_bundle_inclusion_v2,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_TREE_SIZE = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class TransparencyLedgerBundleTransitionInspectionV2:
    inclusion: TransparencyLedgerBundleInspectionV2
    checkpoint_consistency: CheckpointConsistencyInspection
    accepted_old_tree_size: int
    accepted_old_root_sha256: str
    accepted_old_checkpoint_sha256: str
    provenance_status: ProvenanceStatus
    append_only_continuity_status: str
    remaining_blockers: tuple[str, ...]


def _require_digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def verify_transparency_ledger_bundle_transition_v2(
    raw_manifest_bytes: bytes,
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_old_checkpoint_bytes: bytes,
    raw_signed_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    raw_timestamp_bundle_bytes: bytes,
    timestamp_token_der: bytes,
    signed_policy_envelope_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    *,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_tree_size: int,
    expected_old_tree_size: int,
    expected_old_root_sha256: str,
    expected_old_checkpoint_sha256: str,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_tsa_policy_oid: str,
    expected_nonce: int,
    verification_time: datetime,
) -> TransparencyLedgerBundleTransitionInspectionV2:
    """Verify V2 inclusion plus append-only continuity from the exact accepted head.

    This composes the V2 sidecar/token/leaf/new-checkpoint inclusion verifier
    with the existing signed-checkpoint consistency verifier. The same
    raw_signed_checkpoint_bytes object is passed to both. The caller's old
    watermark is checked against the exact old checkpoint bytes and claims.
    Equal-size/idempotent checkpoints are not accepted as an evidence advance.

    Successful output remains BLOCKED_PROVENANCE. This function does not
    authenticate caller-supplied keys, TSA provisioning, clock, anti-rollback
    storage, independent witnesses, custody or institutional provenance.
    """
    if type(raw_old_checkpoint_bytes) is not bytes or not raw_old_checkpoint_bytes:
        raise ValueError("raw_old_checkpoint_bytes must be non-empty exact bytes")
    if type(raw_consistency_proof_bytes) is not bytes or not raw_consistency_proof_bytes:
        raise ValueError("raw_consistency_proof_bytes must be non-empty exact bytes")
    if (
        type(expected_old_tree_size) is not int
        or not 1 <= expected_old_tree_size <= _MAX_TREE_SIZE
    ):
        raise ValueError("expected_old_tree_size must be an exact positive signed-64-bit integer")
    expected_old_root_sha256 = _require_digest(
        expected_old_root_sha256, "expected_old_root_sha256"
    )
    expected_old_checkpoint_sha256 = _require_digest(
        expected_old_checkpoint_sha256, "expected_old_checkpoint_sha256"
    )

    inclusion = verify_transparency_ledger_bundle_inclusion_v2(
        raw_manifest_bytes,
        raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes,
        raw_signed_checkpoint_bytes,
        raw_timestamp_bundle_bytes,
        timestamp_token_der,
        signed_policy_envelope_bytes,
        artifact_bytes_by_sha256,
        signature_bytes_by_sha256,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_log_key_id=expected_log_key_id,
        minimum_tree_size=minimum_tree_size,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        expected_tsa_policy_oid=expected_tsa_policy_oid,
        expected_nonce=expected_nonce,
        verification_time=verification_time,
    )
    continuity = verify_checkpoint_consistency(
        raw_old_checkpoint_bytes,
        raw_signed_checkpoint_bytes,
        raw_consistency_proof_bytes,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_key_id=expected_log_key_id,
        minimum_new_tree_size=minimum_tree_size,
        verification_time=verification_time,
    )

    if continuity.old_checkpoint_sha256 != expected_old_checkpoint_sha256:
        raise ValueError("old checkpoint digest does not match the provider's accepted watermark")
    if continuity.old_tree_size != expected_old_tree_size:
        raise ValueError("old checkpoint tree size does not match the provider's accepted watermark")
    if continuity.old_root_sha256 != expected_old_root_sha256:
        raise ValueError("old checkpoint root does not match the provider's accepted watermark")
    if continuity.new_checkpoint_sha256 != inclusion.checkpoint_sha256:
        raise ValueError("V2 inclusion and consistency checks did not consume the same exact new checkpoint bytes")
    if continuity.new_tree_size != inclusion.tree_size:
        raise ValueError("V2 inclusion and consistency checks disagree on the new checkpoint tree size")
    if continuity.new_tree_size <= continuity.old_tree_size:
        raise ValueError("V2 evidence advance requires the new checkpoint tree size to strictly advance")

    blockers = tuple(dict.fromkeys(
        (*inclusion.remaining_blockers, *continuity.remaining_blockers)
    ))
    return TransparencyLedgerBundleTransitionInspectionV2(
        inclusion=inclusion,
        checkpoint_consistency=continuity,
        accepted_old_tree_size=continuity.old_tree_size,
        accepted_old_root_sha256=continuity.old_root_sha256,
        accepted_old_checkpoint_sha256=continuity.old_checkpoint_sha256,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        append_only_continuity_status="CONSISTENCY_VERIFIED_WITNESS_QUORUM_UNVERIFIED",
        remaining_blockers=blockers,
    )
