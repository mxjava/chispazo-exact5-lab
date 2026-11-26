"""Fail-closed composition of V1 signed policy and receipt attestation.

This is a research diagnostic only. It verifies raw policy bytes into a
VerifiedTrustPolicy, uses that policy to verify the exact receipt bytes, and
then asks the independent provenance boundary to re-verify those same raw
bytes. V1 has no signed policy-domain field and this composition has no durable
anti-rollback provider or authenticated clock. Every successful inspection
therefore remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from .trust_policy_envelope_v1 import (
    MAX_POLICY_BYTES,
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)


@dataclass(frozen=True, slots=True)
class SignedRootAttestationInspectionV1:
    """Diagnostic metadata; never an eligibility or authentication token."""

    policy_sequence: int
    root_key_id: str
    policy_envelope_sha256: str
    receipt_sha256: str
    receipt_issuer_id: str
    receipt_key_id: str
    receipt_attestation_payload_sha256: str
    policy_domain_binding: str
    provenance_status: ProvenanceStatus


def _normalize_verification_time(value: object) -> datetime:
    """Snapshot caller time once, then pass the same UTC instant to both verifiers."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("verification_time must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone offset is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError("verification_time timezone offset must be an exact timedelta")
    try:
        naive = value.replace(tzinfo=None)
        return (naive - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError("verification_time cannot be normalized to UTC") from exc


def inspect_signed_root_attestation_chain_v1(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> SignedRootAttestationInspectionV1:
    """Verify raw V1 policy/receipt bytes and preserve the provenance block.

    Only raw bytes are accepted. A caller cannot inject a preconstructed
    VerifiedTrustPolicy or receipt-verification result. The independent
    provenance boundary then re-verifies the exact original bytes itself.
    Root pin, key ID, minimum sequence and time remain caller-supplied research
    inputs.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError("original_receipt_bytes exceeds the trust receipt size limit")

    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")
    if not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must not be empty")
    if len(signed_policy_envelope_bytes) > MAX_POLICY_BYTES:
        raise ValueError("signed_policy_envelope_bytes exceeds the policy size limit")

    normalized_time = _normalize_verification_time(verification_time)
    verified_policy = verify_signed_trust_policy(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=normalized_time,
    )
    if type(verified_policy) is not VerifiedTrustPolicy:
        raise TypeError("policy verifier returned an unexpected result type")

    policy_digest = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()
    if verified_policy.envelope_sha256 != policy_digest:
        raise ValueError("verified policy does not bind the exact envelope bytes")

    verified_receipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_policy.policy,
        verification_time=normalized_time,
    )
    if type(verified_receipt) is not CryptographicallyVerifiedReceipt:
        raise TypeError("receipt verifier returned an unexpected result type")

    provenance_status = verify_independent_provenance(
        original_receipt_bytes,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=normalized_time,
    )
    if (
        type(provenance_status) is not ProvenanceStatus
        or provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
    ):
        raise RuntimeError(
            "independent provenance gate returned an unsupported non-blocked status"
        )

    return SignedRootAttestationInspectionV1(
        policy_sequence=verified_policy.policy_sequence,
        root_key_id=verified_policy.root_key_id,
        policy_envelope_sha256=policy_digest,
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        receipt_issuer_id=verified_receipt.verified_issuer_id,
        receipt_key_id=verified_receipt.verified_key_id,
        receipt_attestation_payload_sha256=verified_receipt.signed_payload_sha256,
        policy_domain_binding="ABSENT_IN_V1",
        provenance_status=provenance_status,
    )
