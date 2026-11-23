"""Detached Ed25519 envelope verification against an out-of-band pinned trust store.

The caller MUST obtain pinned_trust_store_sha256 and verification_time_utc
from deployment-controlled configuration/services, never from submitted
evidence. This verifies signature, key validity, revocation and role policy;
it does not establish who provisioned the pin or prove physical custody.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone

from .crypto_primitives import verify_ed25519_signature_bytes

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ENVELOPE_FIELDS = {"schema", "key_id", "role", "issued_at_utc", "payload_b64", "signature_b64"}
_STORE_FIELDS = {"schema", "keys"}
_KEY_FIELDS = {"key_id", "public_key_b64", "roles", "not_before_utc", "not_after_utc", "revoked"}
_MAX_ENVELOPE_BYTES = 1048576
_MAX_TRUST_STORE_BYTES = 1048576
_MAX_PAYLOAD_BYTES = 524288
_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_object(raw: bytes, label: str) -> dict:
    if type(raw) is not bytes:
        raise TypeError(f"{label} must be exact bytes")
    try:
        obj = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_unique_object, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if type(obj) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if raw != canonical:
        raise ValueError(f"{label} must use canonical JSON encoding")
    return obj


def _utc(value: object, label: str) -> datetime:
    if type(value) is not str or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{label} must be canonical RFC3339 UTC with at most 6 fractional digits")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{label} must be UTC")
    return parsed


def verify_detached_ed25519_envelope(
    envelope_bytes: bytes,
    trust_store_bytes: bytes,
    pinned_trust_store_sha256: str,
    required_role: str,
    verification_time_utc: str,
) -> bytes:
    """Verify envelope and return exact signed payload bytes; fail closed."""
    if type(envelope_bytes) is not bytes or len(envelope_bytes) > _MAX_ENVELOPE_BYTES:
        raise ValueError("signed envelope exceeds 1 MiB limit")
    if type(trust_store_bytes) is not bytes or len(trust_store_bytes) > _MAX_TRUST_STORE_BYTES:
        raise ValueError("trust store exceeds 1 MiB limit")
    if type(pinned_trust_store_sha256) is not str or not _SHA256_RE.fullmatch(pinned_trust_store_sha256):
        raise ValueError("pinned_trust_store_sha256 must be lowercase SHA-256 hex")
    if type(required_role) is not str or not required_role:
        raise ValueError("required_role must be a non-empty string")
    actual_pin = hashlib.sha256(trust_store_bytes).hexdigest()
    if actual_pin != pinned_trust_store_sha256:
        raise ValueError("trust store SHA-256 does not match deployment pin")

    store = _canonical_object(trust_store_bytes, "trust store")
    if set(store) != _STORE_FIELDS or store["schema"] != "origen.trust-store.v1":
        raise ValueError("trust store schema or fields are invalid")
    if type(store["keys"]) is not list or not store["keys"] or len(store["keys"]) > 4096:
        raise ValueError("trust store keys must be a non-empty bounded array")
    key_map = {}
    for row in store["keys"]:
        if type(row) is not dict or set(row) != _KEY_FIELDS:
            raise ValueError("trust store key entry fields are invalid")
        kid = row["key_id"]
        if type(kid) is not str or not _KEY_ID_RE.fullmatch(kid) or kid in key_map:
            raise ValueError("trust store key_id is invalid or duplicated")
        if type(row["roles"]) is not list or not row["roles"] or any(type(r) is not str or not r for r in row["roles"]):
            raise ValueError("trust store roles are invalid")
        if len(set(row["roles"])) != len(row["roles"]):
            raise ValueError("trust store roles contain duplicates")
        if type(row["revoked"]) is not bool:
            raise ValueError("trust store revoked must be boolean")
        key_map[kid] = row

    env = _canonical_object(envelope_bytes, "signed envelope")
    if set(env) != _ENVELOPE_FIELDS or env["schema"] != "origen.detached-ed25519-envelope.v1":
        raise ValueError("signed envelope schema or fields are invalid")
    if type(env["key_id"]) is not str or type(env["role"]) is not str or env["role"] != required_role:
        raise ValueError("signed envelope role or key_id is invalid")
    row = key_map.get(env["key_id"])
    if row is None or row["revoked"] or required_role not in row["roles"]:
        raise ValueError("signing key is unknown, revoked, or unauthorized for role")
    issued = _utc(env["issued_at_utc"], "issued_at_utc")
    verify_at = _utc(verification_time_utc, "verification_time_utc")
    if issued > verify_at:
        raise ValueError("signed envelope is from the future")
    if not (_utc(row["not_before_utc"], "not_before_utc") <= issued <= _utc(row["not_after_utc"], "not_after_utc")):
        raise ValueError("signing key was not valid at envelope issuance")
    try:
        payload = base64.b64decode(env["payload_b64"], validate=True)
        signature = base64.b64decode(env["signature_b64"], validate=True)
        public_key = base64.b64decode(row["public_key_b64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("signed envelope or trust store contains invalid base64") from exc
    if len(payload) > _MAX_PAYLOAD_BYTES:
        raise ValueError("signed payload exceeds 512 KiB limit")
    if base64.b64encode(payload).decode("ascii") != env["payload_b64"] or base64.b64encode(signature).decode("ascii") != env["signature_b64"] or base64.b64encode(public_key).decode("ascii") != row["public_key_b64"]:
        raise ValueError("base64 encoding is not canonical")
    if not verify_ed25519_signature_bytes(public_key, payload, signature):
        raise ValueError("Ed25519 signature verification failed")
    return payload
