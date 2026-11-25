"""Root-signed RFC 3161 TSA authorization bound to one trust-policy envelope.

This is a research-only authorization layer. Its Ed25519 root key, clock and
anti-rollback floor are supplied by the caller and remain unauthenticated until
an independent deployment authority provisions them out of band.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA_VERSION = "origen.timestamp-authority-policy.v1"
MAX_POLICY_BYTES = 131_072
MAX_AUTHORITIES = 64
MAX_POLICY_OIDS = 32
MAX_SEQUENCE = (1 << 63) - 1
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
_UTC = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\\.[0-9]{1,6})?Z\\Z"
)
_OID = re.compile(r"(?:0|1|2)(?:\\.(?:0|[1-9][0-9]*))+\\Z")


@dataclass(frozen=True, slots=True)
class TrustedTimestampAuthority:
    authority_id: str
    root_certificate_sha256: str
    policy_oids: tuple[str, ...]
    valid_from_utc: datetime
    valid_until_utc: datetime
    revoked: bool


@dataclass(frozen=True, slots=True)
class VerifiedTimestampAuthorityPolicy:
    root_key_id: str
    policy_sequence: int
    trust_policy_envelope_sha256: str
    envelope_sha256: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    authorities: tuple[TrustedTimestampAuthority, ...]


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("timestamp-authority policy contains a duplicate JSON key")
        result[key] = value
    return result


def _parse_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        raise ValueError("timestamp-authority policy integer exceeds signed 64-bit range")
    parsed = int(value)
    if not -(1 << 63) <= parsed <= MAX_SEQUENCE:
        raise ValueError("timestamp-authority policy integer exceeds signed 64-bit range")
    return parsed


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _UTC.fullmatch(value):
        raise ValueError(f"{field} must be a canonical UTC timestamp ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc


def _oid(value: object, field: str) -> str:
    if type(value) is not str or not _OID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical dotted-decimal OID")
    arcs = [int(item) for item in value.split(".")]
    if len(arcs) < 2 or arcs[0] not in (0, 1, 2):
        raise ValueError(f"{field} is not a valid object identifier")
    if arcs[0] < 2 and arcs[1] > 39:
        raise ValueError(f"{field} is not a valid object identifier")
    if any(item > (1 << 63) - 1 for item in arcs):
        raise ValueError(f"{field} contains an OID arc outside the supported bound")
    return value


def _canonical(document: dict) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _utc_now(value: object) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("verification_time must be a timezone-aware exact datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError("verification_time must have a valid timezone offset")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError("verification_time cannot be normalized to UTC") from exc


def verify_signed_timestamp_authority_policy(
    raw: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    expected_trust_policy_envelope_sha256: str,
    expected_policy_sequence: int,
    verification_time: datetime,
) -> VerifiedTimestampAuthorityPolicy:
    """Verify TSA authority bindings under the same root as the signed issuer policy.

    The envelope is cryptographically bound to the exact already-verified trust
    policy digest and sequence. It does not authenticate who provisioned the
    root key, the clock, or the external anti-rollback state.
    """
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_POLICY_BYTES:
        raise ValueError("timestamp-authority policy must be exact bytes within size limit")
    if type(pinned_root_public_key_bytes) is not bytes or len(pinned_root_public_key_bytes) != 32:
        raise ValueError("pinned root public key must be exactly 32 immutable bytes")
    if type(expected_root_key_id) is not str or not _ID.fullmatch(expected_root_key_id):
        raise ValueError("expected_root_key_id must be a canonical identifier")
    if type(expected_trust_policy_envelope_sha256) is not str or not _SHA256.fullmatch(
        expected_trust_policy_envelope_sha256
    ):
        raise ValueError("expected trust-policy envelope digest must be lowercase SHA-256")
    if type(expected_policy_sequence) is not int or not 1 <= expected_policy_sequence <= MAX_SEQUENCE:
        raise ValueError("expected_policy_sequence must be a positive signed 64-bit integer")
    now = _utc_now(verification_time)

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_int=_parse_integer,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("timestamp-authority policy must be valid UTF-8 JSON") from exc
    except ValueError as exc:
        if str(exc).startswith("timestamp-authority policy"):
            raise
        raise ValueError("timestamp-authority policy contains an invalid JSON value") from exc
    if type(document) is not dict:
        raise ValueError("timestamp-authority policy must be a JSON object")
    if raw != _canonical(document):
        raise ValueError("timestamp-authority policy must use canonical UTF-8 JSON bytes")

    required = {
        "schema_version", "root_key_id", "policy_sequence",
        "trust_policy_envelope_sha256", "issued_at_utc", "not_before_utc",
        "expires_at_utc", "authorities", "signature",
    }
    if set(document) != required:
        raise ValueError("timestamp-authority policy fields mismatch")
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported timestamp-authority policy schema")
    if document["root_key_id"] != expected_root_key_id:
        raise ValueError("timestamp-authority policy root key ID mismatch")
    if type(document["policy_sequence"]) is not int or document["policy_sequence"] != expected_policy_sequence:
        raise ValueError("timestamp-authority policy sequence does not match verified trust policy")
    if document["trust_policy_envelope_sha256"] != expected_trust_policy_envelope_sha256:
        raise ValueError("timestamp-authority policy is not bound to the verified trust-policy envelope")

    issued = _timestamp(document["issued_at_utc"], "issued_at_utc")
    not_before = _timestamp(document["not_before_utc"], "not_before_utc")
    expires = _timestamp(document["expires_at_utc"], "expires_at_utc")
    if not (issued <= not_before <= now < expires):
        raise ValueError("timestamp-authority policy is not currently valid")
    if not (issued <= not_before <= expires):
        raise ValueError("timestamp-authority policy validity chronology is inverted")

    raw_authorities = document["authorities"]
    if type(raw_authorities) is not list or not 1 <= len(raw_authorities) <= MAX_AUTHORITIES:
        raise ValueError(f"authorities must contain 1..{MAX_AUTHORITIES} entries")
    authorities = []
    seen_ids = set()
    seen_roots = set()
    for index, item in enumerate(raw_authorities):
        field = f"authorities[{index}]"
        if type(item) is not dict or set(item) != {
            "authority_id", "root_certificate_sha256", "policy_oids",
            "valid_from_utc", "valid_until_utc", "revoked",
        }:
            raise ValueError(f"{field} fields mismatch")
        authority_id = _identifier(item["authority_id"], f"{field}.authority_id")
        root_digest = item["root_certificate_sha256"]
        if type(root_digest) is not str or not _SHA256.fullmatch(root_digest):
            raise ValueError(f"{field}.root_certificate_sha256 must be lowercase SHA-256")
        if authority_id in seen_ids:
            raise ValueError("timestamp-authority policy contains duplicate authority IDs")
        if root_digest in seen_roots:
            raise ValueError("timestamp-authority policy reuses one root certificate across authorities")
        seen_ids.add(authority_id)
        seen_roots.add(root_digest)

        raw_oids = item["policy_oids"]
        if type(raw_oids) is not list or not 1 <= len(raw_oids) <= MAX_POLICY_OIDS:
            raise ValueError(f"{field}.policy_oids must contain 1..{MAX_POLICY_OIDS} OIDs")
        policy_oids = tuple(
            _oid(value, f"{field}.policy_oids[{oid_index}]")
            for oid_index, value in enumerate(raw_oids)
        )
        if len(set(policy_oids)) != len(policy_oids):
            raise ValueError(f"{field}.policy_oids must be unique")

        valid_from = _timestamp(item["valid_from_utc"], f"{field}.valid_from_utc")
        valid_until = _timestamp(item["valid_until_utc"], f"{field}.valid_until_utc")
        if not (not_before <= valid_from <= valid_until <= expires):
            raise ValueError(f"{field} validity interval must be inside the signed policy interval")
        if type(item["revoked"]) is not bool:
            raise ValueError(f"{field}.revoked must be an exact boolean")
        authorities.append(TrustedTimestampAuthority(
            authority_id=authority_id,
            root_certificate_sha256=root_digest,
            policy_oids=policy_oids,
            valid_from_utc=valid_from,
            valid_until_utc=valid_until,
            revoked=item["revoked"],
        ))

    signature_doc = document["signature"]
    if type(signature_doc) is not dict or set(signature_doc) != {"algorithm", "signature_b64"}:
        raise ValueError("timestamp-authority policy signature fields mismatch")
    if signature_doc["algorithm"] != "ed25519":
        raise ValueError("timestamp-authority policy supports Ed25519 only")
    signature_b64 = signature_doc["signature_b64"]
    if type(signature_b64) is not str:
        raise ValueError("timestamp-authority policy signature must be base64 text")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("timestamp-authority policy signature is invalid base64") from exc
    if base64.b64encode(signature).decode("ascii") != signature_b64 or len(signature) != 64:
        raise ValueError("timestamp-authority policy signature must be canonical 64-byte base64")

    unsigned = dict(document)
    unsigned.pop("signature")
    try:
        Ed25519PublicKey.from_public_bytes(pinned_root_public_key_bytes).verify(
            signature, _canonical(unsigned)
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("timestamp-authority policy root signature verification failed") from exc

    return VerifiedTimestampAuthorityPolicy(
        root_key_id=expected_root_key_id,
        policy_sequence=expected_policy_sequence,
        trust_policy_envelope_sha256=expected_trust_policy_envelope_sha256,
        envelope_sha256=hashlib.sha256(raw).hexdigest(),
        issued_at_utc=issued,
        expires_at_utc=expires,
        authorities=tuple(authorities),
    )
