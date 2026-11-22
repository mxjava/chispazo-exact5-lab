"""Root-level Ed25519 receipt attestation verification.

This module verifies only the detached root attestation over the canonical receipt
claims. It does NOT authenticate nested signer claims, physical artifacts, TSA
proofs, ledger inclusion, custody, or the truth of any claim in the receipt.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from origen.trust_receipt_v1 import UnverifiedTrustReceipt, parse_unverified_receipt


@dataclass(frozen=True, slots=True)
class TrustedIssuerKey:
    issuer_id: str
    key_id: str
    public_key_bytes: bytes
    valid_from_utc: datetime
    valid_until_utc: datetime
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class TrustPolicy:
    policy_version: str
    issuer_keys: tuple[TrustedIssuerKey, ...]


@dataclass(frozen=True, slots=True)
class CryptographicallyVerifiedReceipt:
    """Proof that the root receipt attestation verified under one supplied key.

    This type deliberately makes no claim that embedded physical evidence,
    signer/custodian assertions, trusted time, or ledger proofs were verified.
    """

    receipt: UnverifiedTrustReceipt
    verified_issuer_id: str
    verified_key_id: str
    verified_at_utc: datetime
    signed_payload_sha256: str


def canonical_attestation_payload(raw: bytes) -> bytes:
    """Canonical JSON of all receipt claims except the self-referential attestation."""
    parsed = parse_unverified_receipt(raw)
    del parsed  # Parsing first enforces the strict schema and duplicate-key rules.
    document = json.loads(raw.decode("utf-8"))
    document.pop("receipt_attestation")
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def verify_receipt_attestation(
    raw: bytes,
    policy: TrustPolicy,
    *,
    verification_time: datetime,
) -> CryptographicallyVerifiedReceipt:
    """Verify the receipt's root Ed25519 signature against externally supplied trust.

    The caller must provision policy keys independently of the receipt. The
    verification time is explicit so callers cannot mistake an untrusted local
    clock for a trusted timestamp.
    """
    receipt = parse_unverified_receipt(raw)
    if receipt.declared_status != "AUTHENTICATED":
        raise ValueError("receipt declaration is REJECTED, not eligible for verification")
    if receipt.policy_version != policy.policy_version:
        raise ValueError("receipt policy_version does not match externally supplied policy")
    if verification_time.tzinfo is None or verification_time.utcoffset() is None:
        raise ValueError("verification_time must be timezone-aware")
    verified_at = verification_time.astimezone(timezone.utc)

    matches = [
        item for item in policy.issuer_keys
        if item.issuer_id == receipt.attestation.issuer_id
        and item.key_id == receipt.attestation.key_id
    ]
    if len(matches) != 1:
        raise ValueError("receipt issuer/key is unknown or ambiguous in trust policy")
    key_record = matches[0]
    if key_record.revoked:
        raise ValueError("receipt issuer key is revoked")
    if key_record.valid_from_utc.tzinfo is None or key_record.valid_until_utc.tzinfo is None:
        raise ValueError("trust-policy key validity bounds must be timezone-aware")
    if not (
        key_record.valid_from_utc <= verified_at <= key_record.valid_until_utc
    ):
        raise ValueError("receipt issuer key is outside its policy validity interval")
    if receipt.attestation.algorithm != "ed25519":
        raise ValueError("root verifier currently supports Ed25519 only")
    if len(key_record.public_key_bytes) != 32:
        raise ValueError("Ed25519 trust-policy public key must be exactly 32 bytes")

    signature = base64.b64decode(receipt.attestation.signature_b64, validate=True)
    payload = canonical_attestation_payload(raw)
    try:
        Ed25519PublicKey.from_public_bytes(key_record.public_key_bytes).verify(
            signature, payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("receipt root attestation signature verification failed") from exc

    import hashlib

    return CryptographicallyVerifiedReceipt(
        receipt=receipt,
        verified_issuer_id=key_record.issuer_id,
        verified_key_id=key_record.key_id,
        verified_at_utc=verified_at,
        signed_payload_sha256=hashlib.sha256(payload).hexdigest(),
    )
