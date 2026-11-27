"""Research-only composition of signed receipt verification and exact artifact bytes.

A successful result proves only that the receipt's root signature verifies against
the supplied policy and that supplied immutable bytes match the receipt's signed
SHA-256/length claims. It does NOT authenticate the source, signer identities,
trusted time, ledger, custody, or physical evidence.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from datetime import datetime

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from .trust_policy_envelope_v1 import VerifiedTrustPolicy
from .trust_receipt_v1 import parse_unverified_receipt


ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED = (
    "RECEIPT_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED"
)
SIGNATURE_AND_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED = (
    "RECEIPT_SIGNATURE_AND_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED"
)


@dataclass(frozen=True, slots=True)
class ReceiptArtifactByteMatch:
    artifact_type: str
    sha256: str
    byte_length: int
    contest_id: str


@dataclass(frozen=True, slots=True)
class ReceiptArtifactBytesCheck:
    receipt_sha256: str
    artifact_matches: tuple[ReceiptArtifactByteMatch, ...]
    status: str = ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED


@dataclass(frozen=True, slots=True)
class IndependentReceiptArtifactCheck:
    provenance_status: ProvenanceStatus
    receipt_sha256: str
    artifact_matches: tuple[ReceiptArtifactByteMatch, ...]
    status: str = SIGNATURE_AND_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED


def _snapshot_artifact_bytes(
    artifacts_by_sha256: dict[str, bytes],
) -> dict[str, bytes]:
    """Snapshot an exact built-in dict before checking untrusted byte inputs."""
    if type(artifacts_by_sha256) is not dict:
        raise TypeError("artifact_bytes_by_sha256 must be an exact dict")
    try:
        items = tuple(artifacts_by_sha256.items())
    except RuntimeError as exc:
        raise ValueError("artifact byte mapping changed while being snapshotted") from exc
    if len(items) != len(artifacts_by_sha256):
        raise ValueError("artifact byte mapping changed while being snapshotted")

    snapshot: dict[str, bytes] = {}
    for key, value in items:
        if type(key) is not str:
            raise TypeError("artifact digest keys must be exact built-in strings")
        if type(value) is not bytes:
            raise TypeError("artifact values must be exact immutable bytes")
        snapshot[key] = value
    return snapshot


def verify_receipt_artifact_bytes(
    original_receipt_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
) -> ReceiptArtifactBytesCheck:
    """Match every exact supplied artifact byte string to unverified receipt claims.

    This function checks only SHA-256 and byte length. It does not verify the
    receipt's root signature; use verify_independent_provenance_with_artifacts
    when a VerifiedTrustPolicy is available.
    """
    receipt = parse_unverified_receipt(original_receipt_bytes)
    supplied = _snapshot_artifact_bytes(artifact_bytes_by_sha256)

    expected_lengths: dict[str, int] = {}
    for artifact in receipt.artifacts:
        prior_length = expected_lengths.get(artifact.sha256)
        if prior_length is not None and prior_length != artifact.byte_length:
            raise ValueError(
                "one receipt SHA-256 digest has conflicting declared byte lengths"
            )
        expected_lengths[artifact.sha256] = artifact.byte_length

    expected_digests = set(expected_lengths)
    supplied_digests = set(supplied)
    if supplied_digests != expected_digests:
        missing = sorted(expected_digests - supplied_digests)
        extra = sorted(supplied_digests - expected_digests)
        raise ValueError(
            f"receipt artifact byte set mismatch; missing={missing}, unexpected={extra}"
        )

    actual_digests: dict[str, str] = {}
    for digest, expected_length in expected_lengths.items():
        payload = supplied[digest]
        actual_length = len(payload)
        if actual_length != expected_length:
            raise ValueError(
                f"artifact {digest} byte length mismatch: "
                f"declared={expected_length}, actual={actual_length}"
            )
        actual_digest = hashlib.sha256(payload).hexdigest()
        if actual_digest != digest:
            raise ValueError(
                f"artifact SHA-256 mismatch: declared={digest}, actual={actual_digest}"
            )
        actual_digests[digest] = actual_digest

    matches = tuple(
        ReceiptArtifactByteMatch(
            artifact_type=artifact.artifact_type,
            sha256=artifact.sha256,
            byte_length=artifact.byte_length,
            contest_id=artifact.contest_id,
        )
        for artifact in receipt.artifacts
    )
    return ReceiptArtifactBytesCheck(
        receipt_sha256=receipt.raw_sha256,
        artifact_matches=matches,
    )


def verify_independent_provenance_with_artifacts(
    original_receipt_bytes: bytes,
    *,
    verified_trust_policy: VerifiedTrustPolicy,
    verification_time: datetime,
    artifact_bytes_by_sha256: dict[str, bytes],
) -> IndependentReceiptArtifactCheck:
    """Verify the policy/receipt root-signature layer and bind all original bytes.

    The returned provenance status remains BLOCKED_PROVENANCE. A successful
    result is not an authenticated provenance decision and does not validate
    nested signatures, RFC 3161 tokens, ledger inclusion, institutional roles,
    source acquisition, or independent custody.
    """
    status = verify_independent_provenance(
        original_receipt_bytes,
        verified_trust_policy=verified_trust_policy,
        verification_time=verification_time,
    )
    if status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("independent provenance adapter returned an unknown status")

    byte_check = verify_receipt_artifact_bytes(
        original_receipt_bytes,
        artifact_bytes_by_sha256,
    )
    return IndependentReceiptArtifactCheck(
        provenance_status=status,
        receipt_sha256=byte_check.receipt_sha256,
        artifact_matches=byte_check.artifact_matches,
    )
