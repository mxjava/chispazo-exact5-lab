"""Fail-closed boundary for the not-yet-provisioned independent trust adapter.

No institutional trust roots, controlled artifact store, trusted-time service,
or independent ledger have been provisioned and independently reviewed for
this repository. Until those dependencies exist, every request returns the
single non-authenticating BLOCKED_PROVENANCE enum value.

Do not replace this gate with caller-supplied booleans, callbacks, key maps, or
reference sets. A future implementation must be separately reviewed and bind
original artifact bytes to independently controlled trust roots.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from .trust_policy_envelope_v1 import verify_receipt_attestation_with_signed_policy
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES


class ProvenanceStatus(str, Enum):
    """Only status this unprovisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def _validate_original_receipt_bytes(original_receipt_bytes: bytes) -> None:
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )


def verify_independent_provenance(original_receipt_bytes: bytes) -> ProvenanceStatus:
    """Fail closed until independent trust infrastructure is deployed.

    The input limit is shared with the strict receipt parser. This function does
    not parse claims, trust digests, inspect caller-provided references, or
    invoke caller-controlled verifiers. Its return type has no AUTHENTICATED
    member, so this module cannot issue an authenticated status.
    """
    _validate_original_receipt_bytes(original_receipt_bytes)
    return ProvenanceStatus.BLOCKED_PROVENANCE


def verify_independent_provenance_with_signed_policy(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> ProvenanceStatus:
    """Research-only composition of signed policy + receipt root attestation.

    This verifies the policy envelope and receipt's Ed25519 root attestation
    using caller-supplied pins, sequence floor and clock, then STILL returns
    BLOCKED_PROVENANCE. Those inputs are not an independently provisioned trust
    anchor or anti-rollback service. No nested participant signatures, RFC 3161
    tokens, ledger inclusion, custody, physical records, or pre-close seals are
    verified here. The production boundary remains fail-closed.
    """
    _validate_original_receipt_bytes(original_receipt_bytes)
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")
    verify_receipt_attestation_with_signed_policy(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    return ProvenanceStatus.BLOCKED_PROVENANCE
