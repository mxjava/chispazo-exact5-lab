"""Signed, versioned ORIGEN trust-policy envelope.

The root public key and minimum accepted sequence MUST be provisioned by an
independent deployment trust boundary (for example, reviewed immutable config).
Passing an attacker-controlled key or minimum sequence defeats the trust model.
This module authenticates policy bytes relative to that supplied anchor; it does
not establish who provisioned the anchor or provide trusted time.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from origen.trust_verifier_v1 import TrustPolicy, TrustedIssuerKey

SCHEMA_VERSION = "origen.trust-policy-envelope.v1"
MAX_POLICY_BYTES = 131_072
MAX_POLICY_KEYS = 256
MAX_POLICY_JSON_DEPTH = 32
MAX_POLICY_SEQUENCE = (1 << 63) - 1
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_UTC = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z\Z"
)


@dataclass(frozen=True, slots=True, init=False)
class VerifiedTrustPolicy:
    """Policy verified against an externally supplied root anchor.

    This result is an application-level provenance marker, not an unforgeable
    capability against arbitrary code executing in this Python process.
    """
    policy: TrustPolicy
    policy_sequence: int
    root_key_id: str
    envelope_sha256: str
    issued_at_utc: datetime
    not_before_utc: datetime
    expires_at_utc: datetime

    def __init__(self, *args, **kwargs) -> None:
        raise TypeError(
            "verified policies are created only by verify_signed_trust_policy"
        )


def _build_verified_trust_policy(
    *,
    policy: TrustPolicy,
    policy_sequence: int,
    root_key_id: str,
    envelope_sha256: str,
    issued_at_utc: datetime,
    not_before_utc: datetime,
    expires_at_utc: datetime,
) -> VerifiedTrustPolicy:
    """Construct the result only after envelope signature and claims validate."""
    result = object.__new__(VerifiedTrustPolicy)
    object.__setattr__(result, "policy", policy)
    object.__setattr__(result, "policy_sequence", policy_sequence)
    object.__setattr__(result, "root_key_id", root_key_id)
    object.__setattr__(result, "envelope_sha256", envelope_sha256)
    object.__setattr__(result, "issued_at_utc", issued_at_utc)
    object.__setattr__(result, "not_before_utc", not_before_utc)
    object.__setattr__(result, "expires_at_utc", expires_at_utc)
    return result


def _validate_json_depth(raw: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_POLICY_JSON_DEPTH:
                raise ValueError("policy envelope exceeds maximum JSON nesting depth")
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


def _parse_bounded_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        raise ValueError("policy JSON integer exceeds signed 64-bit range")
    parsed = int(value)
    if not -(1 << 63) <= parsed <= MAX_POLICY_SEQUENCE:
        raise ValueError("policy JSON integer exceeds signed 64-bit range")
    return parsed

def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _identifier(value, field):
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _timestamp(value, field):
    if type(value) is not str or not _UTC.fullmatch(value):
        raise ValueError(f"{field} must be a canonical UTC timestamp ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc


def _b64(value, field, expected_length):
    if type(value) is not str:
        raise ValueError(f"{field} must be base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field} is not valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field} must use canonical base64 encoding")
    if len(decoded) != expected_length:
        raise ValueError(f"{field} must decode to exactly {expected_length} bytes")
    return decoded


def _canonical(document):
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def verify_signed_trust_policy(
    raw: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> VerifiedTrustPolicy:
    """Authenticate a policy envelope using a separately pinned Ed25519 root.

    The pinned key, expected key ID, and minimum sequence are security-critical
    deployment inputs. They must not come from the envelope or user-controlled
    data. verification_time is caller-supplied and is NOT trusted time.
    """
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_POLICY_BYTES:
        raise ValueError("policy envelope must be exact bytes within size limit")
    if type(pinned_root_public_key_bytes) is not bytes or len(pinned_root_public_key_bytes) != 32:
        raise ValueError("pinned root public key must be exactly 32 immutable bytes")
    root_key_id = _identifier(expected_root_key_id, "expected_root_key_id")
    if type(minimum_policy_sequence) is not int or not 1 <= minimum_policy_sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError(
            "minimum_policy_sequence must be an exact positive signed 64-bit integer"
        )
    if type(verification_time) is not datetime or verification_time.tzinfo is None:
        raise ValueError("verification_time must be a timezone-aware exact datetime")
    try:
        offset = verification_time.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone is invalid") from exc
    if offset is None:
        raise ValueError("verification_time must be timezone-aware")
    now = (verification_time.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)

    _validate_json_depth(raw)
    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_int=_parse_bounded_integer,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("policy envelope must be valid UTF-8 JSON") from exc
    if type(document) is not dict:
        raise ValueError("policy envelope must be a JSON object")
    # Bind the signed claims to one exact raw representation. Otherwise the
    # same valid signature can be replayed with alternate whitespace/key order
    # while producing a different envelope_sha256 in the verified result.
    if raw != _canonical(document):
        raise ValueError("policy envelope must use canonical JSON encoding")
    fields = {
        "schema_version", "policy_version", "policy_sequence", "issuer_id",
        "root_key_id", "issued_at_utc", "not_before_utc", "expires_at_utc",
        "issuer_keys", "signature",
    }
    if set(document) != fields:
        raise ValueError("policy envelope fields mismatch")
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported trust-policy envelope schema")
    policy_version = _identifier(document["policy_version"], "policy_version")
    _identifier(document["issuer_id"], "issuer_id")
    if document["root_key_id"] != root_key_id:
        raise ValueError("policy root_key_id does not match pinned deployment key")
    sequence = document["policy_sequence"]
    if type(sequence) is not int or not 1 <= sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("policy_sequence must be a positive signed 64-bit integer")
    if sequence < minimum_policy_sequence:
        raise ValueError("policy sequence is below the externally pinned minimum")

    issued = _timestamp(document["issued_at_utc"], "issued_at_utc")
    not_before = _timestamp(document["not_before_utc"], "not_before_utc")
    expires = _timestamp(document["expires_at_utc"], "expires_at_utc")
    if not (issued <= now and not_before <= now < expires):
        raise ValueError("policy envelope is not currently valid at verification time")
    if not (issued <= not_before <= expires):
        raise ValueError("policy envelope validity chronology is inverted")

    entries = document["issuer_keys"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_POLICY_KEYS:
        raise ValueError(f"issuer_keys must contain 1..{MAX_POLICY_KEYS} entries")
    trusted_keys = []
    seen_pairs = set()
    seen_bytes = set()
    for index, item in enumerate(entries):
        if type(item) is not dict or set(item) != {
            "issuer_id", "key_id", "public_key_b64", "valid_from_utc",
            "valid_until_utc", "revoked",
        }:
            raise ValueError(f"issuer_keys[{index}] fields mismatch")
        key_issuer = _identifier(item["issuer_id"], f"issuer_keys[{index}].issuer_id")
        key_id = _identifier(item["key_id"], f"issuer_keys[{index}].key_id")
        public_bytes = _b64(item["public_key_b64"], f"issuer_keys[{index}].public_key_b64", 32)
        valid_from = _timestamp(item["valid_from_utc"], f"issuer_keys[{index}].valid_from_utc")
        valid_until = _timestamp(item["valid_until_utc"], f"issuer_keys[{index}].valid_until_utc")
        if valid_from > valid_until:
            raise ValueError(f"issuer_keys[{index}] validity interval is inverted")
        if type(item["revoked"]) is not bool:
            raise ValueError(f"issuer_keys[{index}].revoked must be an exact boolean")
        pair = (key_issuer, key_id)
        if pair in seen_pairs:
            raise ValueError("duplicate issuer/key identifiers in signed policy")
        if public_bytes in seen_bytes:
            raise ValueError("public key reused across signed policy identities")
        seen_pairs.add(pair)
        seen_bytes.add(public_bytes)
        trusted_keys.append(TrustedIssuerKey(
            issuer_id=key_issuer,
            key_id=key_id,
            public_key_bytes=public_bytes,
            valid_from_utc=valid_from,
            valid_until_utc=valid_until,
            revoked=item["revoked"],
        ))

    signature_doc = document["signature"]
    if type(signature_doc) is not dict or set(signature_doc) != {"algorithm", "signature_b64"}:
        raise ValueError("signature object fields mismatch")
    if signature_doc["algorithm"] != "ed25519":
        raise ValueError("trust-policy envelope supports Ed25519 only")
    signature = _b64(signature_doc["signature_b64"], "signature.signature_b64", 64)

    unsigned = dict(document)
    unsigned.pop("signature")
    payload = _canonical(unsigned)
    try:
        Ed25519PublicKey.from_public_bytes(pinned_root_public_key_bytes).verify(
            signature, payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("trust-policy root signature verification failed") from exc

    return _build_verified_trust_policy(
        policy=TrustPolicy(policy_version=policy_version, issuer_keys=tuple(trusted_keys)),
        policy_sequence=sequence,
        root_key_id=root_key_id,
        envelope_sha256=hashlib.sha256(raw).hexdigest(),
        issued_at_utc=issued,
        not_before_utc=not_before,
        expires_at_utc=expires,
    )
