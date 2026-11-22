"""Research-only Ed25519 attestation verifier for ORIGEN.

Pinned public keys must be provisioned out-of-band by an independent operator.
A valid signature proves possession of a pinned key, not real-world identity,
trusted time, revocation status, or independent custody. Timestamp authorities
must be independently audited; this module does not implement RFC 3161.
"""
from __future__ import annotations

import base64
import binascii
import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Mapping

_HEX64 = re.compile(r"[0-9a-f]{64}")
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,128}")
_FIELDS = {
    "schema_version", "key_id", "role", "subject_sha256",
    "issued_at_utc", "expires_at_utc", "nonce",
}


def canonical_payload(envelope: Mapping[str, Any]) -> bytes:
    """Return canonical signed bytes, excluding the detached signature."""
    if type(envelope) is not dict or any(type(key) is not str for key in envelope):
        raise ValueError("attestation envelope must be an exact dict with built-in string keys")
    payload = {key: value for key, value in envelope.items() if key != "signature_b64"}
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build JSON objects without silently collapsing duplicate member names."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise ValueError("attestation JSON object keys must be exact strings")
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def parse_attestation_json(raw: bytes) -> dict[str, Any]:
    """Parse one canonical UTF-8 attestation object, rejecting duplicate keys."""
    if type(raw) is not bytes:
        raise ValueError("attestation JSON must be exact built-in bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid attestation JSON: {exc}") from exc
    if type(value) is not dict:
        raise ValueError("attestation JSON must be an exact built-in object")
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("attestation JSON cannot be canonically encoded") from exc
    if raw != canonical:
        raise ValueError(
            "attestation JSON must use canonical UTF-8 JSON encoding without whitespace or trailing LF"
        )
    return value


def _utc(value: Any, field: str) -> datetime:
    if type(value) is not str or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)",
        value,
    ):
        raise ValueError(
            f"{field}: exact built-in canonical extended ISO-8601 UTC text required"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field}: explicit UTC offset required")
    return parsed.astimezone(timezone.utc)


def _decode_canonical_base64(value: Any, field: str) -> bytes:
    """Decode strict padded base64 and reject alternate encodings of the same bytes."""
    if type(value) is not str:
        raise ValueError(f"{field} must be exact built-in base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"{field} is not valid strict base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field} must use canonical padded base64")
    return decoded


def verify_attestation(
    envelope: Mapping[str, Any],
    *,
    trust_roots: Mapping[str, Mapping[str, Any]],
    expected_role: str,
    expected_subject_sha256: str,
    verification_time_utc: str,
) -> dict[str, Any]:
    """Verify a detached Ed25519 signature against explicitly pinned role roots.

    verification_time_utc must come from a separately trusted clock source.
    Caller-supplied roots are only as trustworthy as their provisioning channel.
    """
    try:
        if type(envelope) is not dict or set(envelope) != _FIELDS | {"signature_b64"}:
            raise ValueError("attestation must be an exact dict matching the exact schema")
        if any(type(envelope[field]) is not str for field in _FIELDS | {"signature_b64"}):
            raise ValueError("all attestation fields must be exact built-in strings")
        if type(trust_roots) is not dict:
            raise ValueError("trust_roots must be a mapping controlled outside the evidence bundle")
        if any(type(root_key) is not str for root_key in trust_roots):
            raise ValueError("trust-root identifiers must be exact built-in strings")
        if type(expected_role) is not str or not expected_role:
            raise ValueError("expected_role must be a non-empty string")
        if type(expected_subject_sha256) is not str or not _HEX64.fullmatch(expected_subject_sha256):
            raise ValueError("expected_subject_sha256 must be 64 lowercase hexadecimal characters")
        if envelope["schema_version"] != "exact5.attestation.ed25519.v1":
            raise ValueError("unsupported attestation schema")
        key_id, role = envelope["key_id"], envelope["role"]
        if type(key_id) is not str or not key_id or type(role) is not str or not role:
            raise ValueError("key_id and role must be non-empty strings")
        if role != expected_role:
            raise ValueError("attestation role mismatch")
        subject = envelope["subject_sha256"]
        if type(subject) is not str or not _HEX64.fullmatch(subject):
            raise ValueError("subject_sha256 must be 64 lowercase hexadecimal characters")
        if subject != expected_subject_sha256 or not _HEX64.fullmatch(expected_subject_sha256):
            raise ValueError("attestation subject hash mismatch")
        nonce = envelope["nonce"]
        if type(nonce) is not str or not _NONCE.fullmatch(nonce):
            raise ValueError(
                "nonce must be 16-128 ASCII URL-safe characters (letters, digits, '_' or '-')"
            )

        root = trust_roots.get(key_id)
        if type(root) is not dict:
            raise ValueError("key_id is not present in pinned trust roots")
        if any(type(field) is not str for field in root):
            raise ValueError("trust-root field names must be exact built-in strings")
        allowed_root_fields = {"public_key_b64", "roles", "enabled", "revoked"}
        if set(root) != allowed_root_fields:
            raise ValueError(
                "pinned trust root must explicitly define public_key_b64, roles, enabled, and revoked"
            )
        if type(root["enabled"]) is not bool or type(root["revoked"]) is not bool:
            raise ValueError("pinned trust root enabled/revoked flags must be exact booleans")
        roles = root.get("roles")
        if (type(roles) is not list
                or any(type(item) is not str or not item for item in roles)):
            raise ValueError("pinned trust root roles must be an explicit string list")
        if role not in roles:
            raise ValueError("pinned key is not authorized for requested role")
        if root["revoked"] is True or root["enabled"] is not True:
            raise ValueError("pinned key is revoked or disabled by trust policy")

        try:
            public_bytes = _decode_canonical_base64(root["public_key_b64"], "public_key_b64")
            signature = _decode_canonical_base64(envelope["signature_b64"], "signature_b64")
        except (KeyError, ValueError, binascii.Error) as exc:
            raise ValueError("invalid or non-canonical base64 key or signature") from exc
        if len(public_bytes) != 32 or len(signature) != 64:
            raise ValueError("invalid Ed25519 public key or signature length")

        issued = _utc(envelope["issued_at_utc"], "issued_at_utc")
        expires = _utc(envelope["expires_at_utc"], "expires_at_utc")
        now = _utc(verification_time_utc, "verification_time_utc")
        if not issued < expires:
            raise ValueError("attestation validity interval is empty or reversed")
        if not issued <= now < expires:
            raise ValueError("attestation is not valid at verification time")

        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature, canonical_payload(envelope)
            )
        except InvalidSignature as exc:
            raise ValueError("Ed25519 signature verification failed") from exc

        return {
            "status": "SIGNATURE_VALID",
            "key_id": key_id,
            "role": role,
            "subject_sha256": subject,
            "identity_status": "PINNED_KEY_ONLY",
            "trusted_time_status": "NOT_ESTABLISHED_BY_THIS_MODULE",
            "revocation_status": "NOT_CHECKED",
            "custody_status": "NOT_ESTABLISHED_BY_THIS_MODULE",
            "replay_status": "NOT_CHECKED_NO_DURABLE_NONCE_LEDGER",
        }
    except Exception as exc:
        # Fail closed for malformed external inputs; never let parser/type errors escape.
        return {"status": "BLOCKED", "reason": f"invalid attestation or trust policy: {type(exc).__name__}: {exc}"}


def verify_attestation_json(
    raw: bytes,
    *,
    trust_roots: Mapping[str, Mapping[str, Any]],
    expected_role: str,
    expected_subject_sha256: str,
    verification_time_utc: str,
) -> dict[str, Any]:
    """Strictly parse original envelope bytes, then verify its detached signature."""
    try:
        envelope = parse_attestation_json(raw)
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "reason": f"invalid attestation JSON: {type(exc).__name__}: {exc}",
        }
    return verify_attestation(
        envelope,
        trust_roots=trust_roots,
        expected_role=expected_role,
        expected_subject_sha256=expected_subject_sha256,
        verification_time_utc=verification_time_utc,
    )


def verify_artifact_bytes(
    envelope: Mapping[str, Any],
    artifact_bytes: bytes,
    *,
    trust_roots: Mapping[str, Mapping[str, Any]],
    expected_role: str,
    verification_time_utc: str,
) -> dict[str, Any]:
    """Verify signature and bind it to the exact original artifact bytes."""
    if type(artifact_bytes) is not bytes:
        return {"status": "BLOCKED", "reason": "artifact must be supplied as exact built-in raw bytes"}
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    result = verify_attestation(
        envelope,
        trust_roots=trust_roots,
        expected_role=expected_role,
        expected_subject_sha256=digest,
        verification_time_utc=verification_time_utc,
    )
    if result.get("status") != "SIGNATURE_VALID":
        return result
    return {**result, "artifact_byte_length": len(artifact_bytes),
            "artifact_sha256": digest,
            "byte_integrity_status": "MATCHED"}
