"""Root-level Ed25519 receipt attestation verification.

This module verifies only the detached root attestation over the canonical receipt
claims. It does NOT authenticate nested signer claims, physical artifacts, TSA
proofs, ledger inclusion, custody, or the truth of any claim in the receipt.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from origen.trust_receipt_v1 import UnverifiedTrustReceipt, parse_unverified_receipt


MAX_POLICY_ISSUER_KEYS = 256
_POLICY_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")


def _policy_identifier(value: object, field: str) -> str:
    if type(value) is not str or not _POLICY_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical policy identifier")
    return value


def _policy_utc_datetime(value: object, field: str) -> datetime:
    if type(value) is not datetime:
        raise ValueError(f"{field} must be an exact datetime")
    if value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field} timezone offset is invalid") from exc
    if offset is None:
        raise ValueError(f"{field} must be timezone-aware")
    if type(offset) is not timedelta:
        raise ValueError(f"{field} timezone offset is invalid")
    # Snapshot the offset exactly once. Calling astimezone() after utcoffset()
    # would invoke an untrusted tzinfo callback a second time; a stateful
    # implementation could return a different offset and move the instant.
    try:
        naive = value.replace(tzinfo=None)
        return (naive - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError(f"{field} cannot be normalized to UTC") from exc


def _snapshot_trust_policy(policy: object):
    """Validate and snapshot mutable/untrusted policy containers before use."""
    if type(policy) is not TrustPolicy:
        raise ValueError("policy must be an exact TrustPolicy instance")
    version = _policy_identifier(policy.policy_version, "policy_version")
    if type(policy.issuer_keys) is not tuple:
        raise ValueError("policy issuer_keys must be an exact tuple")
    if not 1 <= len(policy.issuer_keys) <= MAX_POLICY_ISSUER_KEYS:
        raise ValueError(
            f"policy issuer_keys must contain 1..{MAX_POLICY_ISSUER_KEYS} entries"
        )

    entries = []
    seen_pairs = set()
    seen_public_keys = set()
    for index, item in enumerate(policy.issuer_keys):
        if type(item) is not TrustedIssuerKey:
            raise ValueError(f"policy issuer_keys[{index}] must be an exact TrustedIssuerKey")
        issuer_id = _policy_identifier(item.issuer_id, f"issuer_keys[{index}].issuer_id")
        key_id = _policy_identifier(item.key_id, f"issuer_keys[{index}].key_id")
        if type(item.public_key_bytes) is not bytes or len(item.public_key_bytes) != 32:
            raise ValueError(
                f"issuer_keys[{index}].public_key_bytes must be exactly 32 immutable bytes"
            )
        if type(item.revoked) is not bool:
            raise ValueError(f"issuer_keys[{index}].revoked must be an exact boolean")
        valid_from = _policy_utc_datetime(
            item.valid_from_utc, f"issuer_keys[{index}].valid_from_utc"
        )
        valid_until = _policy_utc_datetime(
            item.valid_until_utc, f"issuer_keys[{index}].valid_until_utc"
        )
        if valid_from > valid_until:
            raise ValueError(f"issuer_keys[{index}] validity interval is inverted")
        pair = (issuer_id, key_id)
        if pair in seen_pairs:
            raise ValueError("policy contains duplicate issuer/key identifiers")
        seen_pairs.add(pair)
        if item.public_key_bytes in seen_public_keys:
            raise ValueError("policy reuses one public key across issuer identities")
        seen_public_keys.add(item.public_key_bytes)
        entries.append(
            (issuer_id, key_id, item.public_key_bytes, valid_from, valid_until, item.revoked)
        )
    return version, tuple(entries)


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


@dataclass(frozen=True, slots=True, init=False)
class CryptographicallyVerifiedReceipt:
    """Result value for root-attestation verification, not an unforgeable capability.

    This type deliberately makes no claim that embedded physical evidence,
    signer/custodian assertions, trusted time, or ledger proofs were verified.
    Its public initializer is disabled to prevent accidental fabrication; Python
    code with arbitrary execution in this process can still bypass that guard,
    so downstream security decisions must use trusted control flow, not merely
    an isinstance check on an externally supplied object.
    """

    receipt: UnverifiedTrustReceipt
    verified_issuer_id: str
    verified_key_id: str
    verified_at_utc: datetime
    signed_payload_sha256: str

    def __init__(self, *args, **kwargs) -> None:
        raise TypeError(
            "verification results are created only by verify_receipt_attestation"
        )


def _build_verified_receipt(
    receipt: UnverifiedTrustReceipt,
    verified_issuer_id: str,
    verified_key_id: str,
    verified_at_utc: datetime,
    signed_payload_sha256: str,
) -> CryptographicallyVerifiedReceipt:
    """Internal constructor used only after the Ed25519 verification succeeds."""
    result = object.__new__(CryptographicallyVerifiedReceipt)
    object.__setattr__(result, "receipt", receipt)
    object.__setattr__(result, "verified_issuer_id", verified_issuer_id)
    object.__setattr__(result, "verified_key_id", verified_key_id)
    object.__setattr__(result, "verified_at_utc", verified_at_utc)
    object.__setattr__(result, "signed_payload_sha256", signed_payload_sha256)
    return result


def canonical_attestation_payload(raw: bytes) -> bytes:
    """Canonical JSON of all receipt claims and attestation metadata except signature bytes."""
    if type(raw) is not bytes:
        raise TypeError("trust receipt input must be exact bytes")
    parsed = parse_unverified_receipt(raw)
    del parsed  # Parsing first enforces the strict schema and duplicate-key rules.
    document = json.loads(raw.decode("utf-8"))
    document["receipt_attestation"].pop("signature_b64")
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def verify_receipt_attestation(
    raw: bytes,
    policy: TrustPolicy,
    *,
    verification_time: datetime,
) -> CryptographicallyVerifiedReceipt:
    """Verify the receipt's root Ed25519 signature against an external policy.

    The policy is snapshotted and strictly type-checked before matching. The
    verification time is explicit but remains caller-supplied, not trusted time.
    """
    if type(raw) is not bytes:
        raise TypeError("trust receipt input must be exact bytes")
    policy_version, issuer_keys = _snapshot_trust_policy(policy)
    receipt = parse_unverified_receipt(raw)
    if receipt.declared_status != "AUTHENTICATED":
        raise ValueError("receipt declaration is REJECTED, not eligible for verification")
    if receipt.policy_version != policy_version:
        raise ValueError("receipt policy_version does not match externally supplied policy")
    verified_at = _policy_utc_datetime(verification_time, "verification_time")

    matches = [
        item for item in issuer_keys
        if item[0] == receipt.attestation.issuer_id
        and item[1] == receipt.attestation.key_id
    ]
    if len(matches) != 1:
        raise ValueError("receipt issuer/key is unknown or ambiguous in trust policy")
    issuer_id, key_id, public_key_bytes, valid_from, valid_until, revoked = matches[0]
    if revoked:
        raise ValueError("receipt issuer key is revoked")
    if not (valid_from <= verified_at <= valid_until):
        raise ValueError("receipt issuer key is outside its policy validity interval")
    signed_at = datetime.fromisoformat(
        receipt.attestation.signed_at_utc.replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if not (valid_from <= signed_at <= valid_until):
        raise ValueError("receipt attestation signing time is outside key validity interval")
    if signed_at > verified_at:
        raise ValueError("receipt attestation signing time is after verification time")
    if receipt.attestation.algorithm != "ed25519":
        raise ValueError("root verifier currently supports Ed25519 only")

    signature = base64.b64decode(receipt.attestation.signature_b64, validate=True)
    payload = canonical_attestation_payload(raw)
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("receipt root attestation signature verification failed") from exc

    return _build_verified_receipt(
        receipt=receipt,
        verified_issuer_id=issuer_id,
        verified_key_id=key_id,
        verified_at_utc=verified_at,
        signed_payload_sha256=hashlib.sha256(payload).hexdigest(),
    )
