"""Fail-closed boundary for the not-yet-provisioned independent trust adapter.

No institutional trust roots, controlled artifact store, trusted-time service,
or independent ledger have been provisioned and independently reviewed for
this repository. The adapter therefore has only BLOCKED_PROVENANCE.

For V1 diagnostics it can independently re-verify exact signed policy and
receipt bytes. Those inputs still use caller-supplied root pins, sequence floors
and time; successful re-verification never changes the blocked status.

Do not replace this gate with caller-supplied booleans, callbacks, key maps,
reference sets, or verifier-result objects.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum

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


class ProvenanceStatus(str, Enum):
    """Only status this unprovisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def verify_independent_provenance(
    original_receipt_bytes: bytes,
    *,
    signed_policy_envelope_bytes: bytes | None = None,
    pinned_root_public_key_bytes: bytes | None = None,
    expected_root_key_id: str | None = None,
    minimum_policy_sequence: int | None = None,
    verification_time: datetime | None = None,
) -> ProvenanceStatus:
    """Fail closed, optionally re-verifying the complete V1 signed-byte chain.

    Legacy one-argument calls remain blocked. If any V1 context value is
    supplied, all five are mandatory and the adapter independently verifies
    the raw signed policy bytes and original receipt bytes. It accepts no
    caller-created VerifiedTrustPolicy or CryptographicallyVerifiedReceipt.

    The root pin, key ID, sequence floor and UTC time are still caller supplied.
    V1 also lacks a signed policy-domain field and this module has no durable
    anti-rollback provider. Therefore even successful re-verification returns
    only BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )

    context_values = (
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes,
        expected_root_key_id,
        minimum_policy_sequence,
        verification_time,
    )
    if any(value is not None for value in context_values):
        if any(value is None for value in context_values):
            raise ValueError(
                "V1 provenance re-verification requires exact policy bytes, root pin, "
                "root key ID, sequence floor, and verification time together"
            )
        if type(signed_policy_envelope_bytes) is not bytes:
            raise TypeError("signed_policy_envelope_bytes must be exact bytes")
        if not 1 <= len(signed_policy_envelope_bytes) <= MAX_POLICY_BYTES:
            raise ValueError(
                f"signed_policy_envelope_bytes must contain 1..{MAX_POLICY_BYTES} bytes"
            )
        if type(pinned_root_public_key_bytes) is not bytes:
            raise TypeError("pinned_root_public_key_bytes must be exact bytes")
        if type(expected_root_key_id) is not str:
            raise TypeError("expected_root_key_id must be exact text")
        if type(minimum_policy_sequence) is not int:
            raise TypeError("minimum_policy_sequence must be an exact integer")
        if (
            type(verification_time) is not datetime
            or verification_time.tzinfo is not timezone.utc
        ):
            raise ValueError(
                "verification_time must be one exact normalized UTC datetime at the provenance boundary"
            )

        verified_policy = verify_signed_trust_policy(
            signed_policy_envelope_bytes,
            pinned_root_public_key_bytes=pinned_root_public_key_bytes,
            expected_root_key_id=expected_root_key_id,
            minimum_policy_sequence=minimum_policy_sequence,
            verification_time=verification_time,
        )
        if type(verified_policy) is not VerifiedTrustPolicy:
            raise TypeError("policy verifier returned an unexpected result type at provenance boundary")
        policy_digest = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()
        if verified_policy.envelope_sha256 != policy_digest:
            raise ValueError("verified policy does not bind the exact signed policy bytes at provenance boundary")

        verified_receipt = verify_receipt_attestation(
            original_receipt_bytes,
            verified_policy.policy,
            verification_time=verification_time,
        )
        if type(verified_receipt) is not CryptographicallyVerifiedReceipt:
            raise TypeError("receipt verifier returned an unexpected result type at provenance boundary")
        if (
            verified_receipt.receipt.raw_sha256
            != hashlib.sha256(original_receipt_bytes).hexdigest()
        ):
            raise ValueError("verified receipt does not bind the exact original bytes at provenance boundary")

    return ProvenanceStatus.BLOCKED_PROVENANCE
