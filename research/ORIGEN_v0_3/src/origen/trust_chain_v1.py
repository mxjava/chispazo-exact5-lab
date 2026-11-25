"""Compose a signed trust-policy envelope with a root-attested receipt.

This verifies two cryptographic links only:
  deployment-supplied Ed25519 root -> signed policy envelope
  policy-listed issuer key -> receipt root attestation

It does not provision the root, persist anti-rollback state, authenticate the
clock, verify nested signer signatures, fetch original artifact bytes, validate
RFC 3161 tokens, prove ledger inclusion, or establish custody. A successful
result is not an independent-provenance or eligibility decision.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from origen.trust_policy_envelope_v1 import (
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from origen.trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)


def _snapshot_verification_time_utc(value: object) -> datetime:
    """Normalize one caller-supplied instant while invoking tzinfo only once."""
    if type(value) is not datetime:
        raise ValueError("verification_time must be an exact datetime")
    if value.tzinfo is None:
        raise ValueError("verification_time must be timezone-aware")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone offset is invalid") from exc
    if offset is None or type(offset) is not timedelta:
        raise ValueError("verification_time must have an exact timedelta UTC offset")
    try:
        naive = value.replace(tzinfo=None)
        return (naive - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError("verification_time cannot be normalized to UTC") from exc


@dataclass(frozen=True, slots=True, init=False)
class VerifiedReceiptTrustChain:
    """Scoped result for the policy-envelope -> receipt-attestation chain.

    This is not an unforgeable capability and does not imply authenticated
    physical provenance. Downstream eligibility must not rely on this type or
    on an isinstance check; the independent adapter remains separately blocked.
    """

    verified_policy: VerifiedTrustPolicy
    verified_receipt: CryptographicallyVerifiedReceipt
    policy_envelope_sha256: str
    receipt_bytes_sha256: str
    verified_at_utc: datetime

    def __init__(self, *args, **kwargs) -> None:
        raise TypeError(
            "verification results are created only by verify_receipt_trust_chain"
        )


def _build_verified_chain(
    *,
    verified_policy: VerifiedTrustPolicy,
    verified_receipt: CryptographicallyVerifiedReceipt,
    policy_envelope_sha256: str,
    receipt_bytes_sha256: str,
    verified_at_utc: datetime,
) -> VerifiedReceiptTrustChain:
    result = object.__new__(VerifiedReceiptTrustChain)
    object.__setattr__(result, "verified_policy", verified_policy)
    object.__setattr__(result, "verified_receipt", verified_receipt)
    object.__setattr__(result, "policy_envelope_sha256", policy_envelope_sha256)
    object.__setattr__(result, "receipt_bytes_sha256", receipt_bytes_sha256)
    object.__setattr__(result, "verified_at_utc", verified_at_utc)
    return result


def verify_receipt_trust_chain(
    raw_policy_envelope: bytes,
    raw_receipt: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> VerifiedReceiptTrustChain:
    """Verify a signed policy envelope, then verify a receipt with that policy.

    The root key, key ID, minimum sequence, and source clock are explicit
    deployment inputs. This function cannot establish that those inputs were
    provisioned independently or persisted against rollback.

    The same normalized UTC instant is passed to both verifiers. This avoids a
    stateful caller-supplied tzinfo returning different offsets across the two
    verification steps. Normalization does not make the clock trusted.
    """
    if type(raw_policy_envelope) is not bytes:
        raise TypeError("raw_policy_envelope must be exact bytes")
    if type(raw_receipt) is not bytes:
        raise TypeError("raw_receipt must be exact bytes")

    verified_at = _snapshot_verification_time_utc(verification_time)

    verified_policy = verify_signed_trust_policy(
        raw_policy_envelope,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    verified_receipt = verify_receipt_attestation(
        raw_receipt,
        verified_policy.policy,
        verification_time=verified_at,
    )

    policy_digest = hashlib.sha256(raw_policy_envelope).hexdigest()
    receipt_digest = hashlib.sha256(raw_receipt).hexdigest()
    if verified_policy.envelope_sha256 != policy_digest:
        raise RuntimeError("verified policy digest does not bind the supplied envelope bytes")
    if verified_receipt.receipt.raw_sha256 != receipt_digest:
        raise RuntimeError("verified receipt digest does not bind the supplied receipt bytes")

    return _build_verified_chain(
        verified_policy=verified_policy,
        verified_receipt=verified_receipt,
        policy_envelope_sha256=policy_digest,
        receipt_bytes_sha256=receipt_digest,
        verified_at_utc=verified_at,
    )
