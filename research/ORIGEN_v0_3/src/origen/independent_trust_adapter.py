"""Fail-closed boundary for independently authenticated ORIGEN provenance.

The root-policy and receipt-attestation primitives are composed here only from
one deployment-owned bootstrap snapshot. This verifies the receipt's root
attestation only; it does not verify nested signers, original artifact bytes,
RFC 3161 tokens, ledger inclusion, custody, physical evidence, or two output
seals. Therefore the public adapter remains BLOCKED_PROVENANCE even when this
first cryptographic layer succeeds.

No genuine deployment bootstrap is provisioned in this repository.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from .deployment_trust_bootstrap import (
    _ProvisionedTrustBootstrap,
    _load_provisioned_trust_bootstrap,
)
from .trust_policy_envelope_v1 import VerifiedTrustPolicy, verify_signed_trust_policy
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)


class ProvenanceStatus(str, Enum):
    """Only status this not-yet-provisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def _snapshot_bootstrap_verification_time(value: object) -> datetime:
    """Normalize one potentially hostile tzinfo callback exactly once.

    Both policy and receipt verification must evaluate the same instant. Passing
    the original datetime to both verifiers would call a stateful tzinfo twice
    and could make the two checks observe different instants.
    """
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("bootstrap verification_time must be an exact aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("bootstrap verification_time timezone is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError("bootstrap verification_time must have a valid UTC offset")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError("bootstrap verification_time cannot be normalized") from exc


def _verify_root_attestation_layer(
    original_receipt_bytes: bytes,
    bootstrap: _ProvisionedTrustBootstrap,
) -> tuple[VerifiedTrustPolicy, CryptographicallyVerifiedReceipt]:
    """Compose signed policy verification and receipt root-attestation verification.

    The bootstrap must come from the private deployment loader, not from a
    caller-controlled argument. This helper is intentionally private and its
    result is only a root-attestation verification, never full provenance.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(bootstrap) is not _ProvisionedTrustBootstrap:
        raise TypeError("bootstrap must be an exact deployment bootstrap snapshot")

    verification_time = _snapshot_bootstrap_verification_time(
        bootstrap.verification_time
    )
    verified_policy = verify_signed_trust_policy(
        bootstrap.policy_envelope_bytes,
        pinned_root_public_key_bytes=bootstrap.pinned_root_public_key_bytes,
        expected_root_key_id=bootstrap.expected_root_key_id,
        minimum_policy_sequence=bootstrap.minimum_policy_sequence,
        verification_time=verification_time,
    )
    verified_receipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_policy.policy,
        verification_time=verification_time,
    )
    return verified_policy, verified_receipt


def verify_independent_provenance(original_receipt_bytes: bytes) -> ProvenanceStatus:
    """Fail closed until the complete independent evidence stack is provisioned.

    The private bootstrap loader currently returns None. If a future reviewed
    deployment provisions it, this adapter will verify the signed policy and
    root receipt attestation in one control flow, but will STILL return
    BLOCKED_PROVENANCE until nested signatures, original source bytes,
    RFC 3161 trusted time, independent ledger/custody, and both pre-close seals
    are verified by separately reviewed providers.

    The function accepts no caller-supplied keys, policy objects, clocks,
    callbacks, reference sets, or authenticated-status flags.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )

    try:
        bootstrap = _load_provisioned_trust_bootstrap()
        if bootstrap is None:
            return ProvenanceStatus.BLOCKED_PROVENANCE
        _verify_root_attestation_layer(original_receipt_bytes, bootstrap)
    except Exception:
        # Bootstrap-store outages, invalid/expired/rolled-back policies,
        # malformed receipts and signature failures all fail closed at this
        # non-authorizing public boundary.
        return ProvenanceStatus.BLOCKED_PROVENANCE

    # A valid root attestation is only one layer of the complete trust chain.
    return ProvenanceStatus.BLOCKED_PROVENANCE
