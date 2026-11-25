"""Research-only RFC 6962-style inclusion verifier for ORIGEN ledger entries.

This module verifies an exact manifest-bound ledger entry against an Ed25519-
signed Merkle checkpoint. The log key, tree-size floor, and verification clock
remain caller-supplied. No append-only consistency proof or independent log
witness is checked, so provenance always remains BLOCKED_PROVENANCE.
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

from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest

ENTRY_SCHEMA = "origen.transparency-ledger-entry.v1"
CHECKPOINT_SCHEMA = "origen.transparency-ledger-checkpoint.v1"
CHECKPOINT_DOMAIN = b"origen.transparency-ledger-checkpoint.v1\x00"
MAX_ENTRY_BYTES = 65_536
MAX_CHECKPOINT_BYTES = 16_384
MAX_PROOF_NODES = 64
MAX_TREE_SIZE = (1 << 63) - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")

LEDGER_REMAINING_BLOCKERS = (
    "LOG_SIGNING_KEY_NOT_INDEPENDENTLY_PROVISIONED",
    "TREE_SIZE_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "CHECKPOINT_TIME_NOT_AUTHENTICATED",
    "APPEND_ONLY_CONSISTENCY_NOT_VERIFIED",
    "INDEPENDENT_LOG_WITNESS_OR_GOSSIP_NOT_VERIFIED",
    "CUSTODY_RECEIPTS_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED",
    "PHYSICAL_ARTIFACT_SEMANTICS_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class TransparencyLedgerInspection:
    ledger_id: str
    entry_id: str
    manifest_sha256: str
    ledger_entry_sha256: str
    log_id: str
    key_id: str
    tree_size: int
    leaf_index: int
    checkpoint_sha256: str
    checkpoint_signature_verified: bool
    inclusion_verified: bool
    trust_anchor_source: str
    anti_rollback_source: str
    verification_clock_source: str
    append_only_continuity_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not accepted: {value}")


def _reject_float(value: str) -> None:
    raise ValueError("floating-point JSON numbers are not accepted")


def _parse_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    limit = "9223372036854775808" if value.startswith("-") else "9223372036854775807"
    if len(digits) > len(limit) or (len(digits) == len(limit) and digits > limit):
        raise ValueError("JSON integer exceeds signed 64-bit range")
    return int(value)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _load_canonical_object(raw: bytes, *, maximum: int, label: str) -> dict[str, object]:
    if type(raw) is not bytes:
        raise TypeError(f"{label} must be exact bytes")
    if not raw or len(raw) > maximum:
        raise ValueError(f"{label} must contain 1..{maximum} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
            parse_int=_parse_integer,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{label} must be bounded valid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    if raw != _canonical(value):
        raise ValueError(f"{label} must use canonical UTF-8 JSON encoding")
    return value


def _exact_fields(value: dict[str, object], fields: set[str], label: str) -> None:
    if set(value) != fields:
        missing = sorted(fields - set(value))
        extra = sorted(set(value) - fields)
        raise ValueError(f"{label} fields mismatch; missing={missing}, unexpected={extra}")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def _utc_instant(value: object, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field} timezone offset is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError(f"{field} timezone offset must be an exact timedelta")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError(f"{field} cannot be normalized to UTC") from exc


def _parse_utc_timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _UTC_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{field} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc


def _decode_canonical_base64(value: object, field: str) -> bytes:
    if type(value) is not str or not value:
        raise ValueError(f"{field} must be non-empty canonical base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(f"{field} is not valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field} must use canonical base64 encoding")
    return decoded


def _proof_nodes(value: object, field: str) -> tuple[bytes, ...]:
    if type(value) not in (tuple, list):
        raise TypeError(f"{field} must be an exact tuple or list")
    if len(value) > MAX_PROOF_NODES:
        raise ValueError(f"{field} exceeds {MAX_PROOF_NODES} nodes")
    nodes: list[bytes] = []
    for index, node in enumerate(value):
        if type(node) is not bytes or len(node) != 32:
            raise ValueError(f"{field}[{index}] must be exactly 32 bytes")
        nodes.append(node)
    return tuple(nodes)


def _leaf_hash(leaf: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + leaf).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _verify_inclusion(
    leaf: bytes,
    leaf_index: int,
    tree_size: int,
    audit_path: tuple[bytes, ...],
    expected_root: bytes,
) -> None:
    fn = leaf_index
    sn = tree_size - 1
    calculated = _leaf_hash(leaf)
    for index, sibling in enumerate(audit_path):
        if sn == 0:
            raise ValueError("inclusion proof contains extra nodes")
        if (fn & 1) == 1 or fn == sn:
            calculated = _node_hash(sibling, calculated)
            while (fn & 1) == 0 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            calculated = _node_hash(calculated, sibling)
        fn >>= 1
        sn >>= 1
    if sn != 0:
        raise ValueError("inclusion proof is incomplete")
    if calculated != expected_root:
        raise ValueError("ledger entry is not included in the signed checkpoint root")


def _parse_entry(
    raw_entry_bytes: bytes,
    *,
    ledger_id: str,
    entry_id: str,
    manifest_sha256: str,
    artifact_sha256s: tuple[str, ...],
) -> dict[str, object]:
    entry = _load_canonical_object(
        raw_entry_bytes, maximum=MAX_ENTRY_BYTES, label="ledger entry"
    )
    _exact_fields(
        entry,
        {
            "schema_version",
            "ledger_id",
            "entry_id",
            "manifest_sha256",
            "artifact_sha256s",
        },
        "ledger entry",
    )
    if entry["schema_version"] != ENTRY_SCHEMA:
        raise ValueError("unsupported ledger entry schema")
    if _identifier(entry["ledger_id"], "ledger entry ledger_id") != ledger_id:
        raise ValueError("ledger entry ledger_id does not match manifest")
    if _identifier(entry["entry_id"], "ledger entry entry_id") != entry_id:
        raise ValueError("ledger entry entry_id does not match manifest")
    if _digest(entry["manifest_sha256"], "ledger entry manifest_sha256") != manifest_sha256:
        raise ValueError("ledger entry manifest_sha256 does not match exact manifest bytes")
    claimed_artifacts = entry["artifact_sha256s"]
    if type(claimed_artifacts) is not list:
        raise ValueError("ledger entry artifact_sha256s must be an array")
    parsed_artifacts = tuple(
        _digest(item, f"ledger entry artifact_sha256s[{index}]")
        for index, item in enumerate(claimed_artifacts)
    )
    if parsed_artifacts != tuple(sorted(set(parsed_artifacts))):
        raise ValueError("ledger entry artifact digests must be unique and sorted")
    if parsed_artifacts != artifact_sha256s:
        raise ValueError("ledger entry artifact digests do not match manifest")
    return entry


def verify_transparency_ledger_inclusion(
    raw_manifest_bytes: bytes,
    raw_ledger_entry_bytes: bytes,
    raw_signed_checkpoint_bytes: bytes,
    inclusion_path: tuple[bytes, ...] | list[bytes],
    *,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_key_id: str,
    minimum_tree_size: int,
    leaf_index: int,
    verification_time: datetime,
) -> TransparencyLedgerInspection:
    """Verify exact manifest binding, signed checkpoint and RFC 6962 inclusion.

    This is a diagnostic primitive only. The pin, monotonic floor, and clock
    are caller-supplied. It does not verify checkpoint consistency across
    tree sizes, independent witnesses, log governance, or custody.
    """
    if type(raw_manifest_bytes) is not bytes:
        raise TypeError("raw_manifest_bytes must be exact bytes")
    if type(pinned_log_public_key_bytes) is not bytes or len(pinned_log_public_key_bytes) != 32:
        raise ValueError("pinned_log_public_key_bytes must be exactly 32 bytes")
    expected_log_id = _identifier(expected_log_id, "expected_log_id")
    expected_key_id = _identifier(expected_key_id, "expected_key_id")
    if type(minimum_tree_size) is not int or not 1 <= minimum_tree_size <= MAX_TREE_SIZE:
        raise ValueError("minimum_tree_size must be a positive signed 64-bit integer")
    if type(leaf_index) is not int or not 0 <= leaf_index <= MAX_TREE_SIZE:
        raise ValueError("leaf_index must be a non-negative signed 64-bit integer")
    verified_at = _utc_instant(verification_time, "verification_time")

    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    artifact_sha256s = tuple(sorted(item.sha256 for item in manifest.artifacts))
    entry_bytes = raw_ledger_entry_bytes
    _parse_entry(
        entry_bytes,
        ledger_id=manifest.ledger_anchor.ledger_id,
        entry_id=manifest.ledger_anchor.entry_id,
        manifest_sha256=manifest.raw_sha256,
        artifact_sha256s=artifact_sha256s,
    )

    checkpoint = _load_canonical_object(
        raw_signed_checkpoint_bytes,
        maximum=MAX_CHECKPOINT_BYTES,
        label="signed ledger checkpoint",
    )
    _exact_fields(
        checkpoint,
        {
            "schema_version",
            "log_id",
            "key_id",
            "tree_size",
            "root_hash",
            "issued_at_utc",
            "signature_b64",
        },
        "signed ledger checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA:
        raise ValueError("unsupported signed ledger checkpoint schema")
    log_id = _identifier(checkpoint["log_id"], "checkpoint log_id")
    key_id = _identifier(checkpoint["key_id"], "checkpoint key_id")
    if log_id != expected_log_id:
        raise ValueError("checkpoint log_id does not match pinned expectation")
    if key_id != expected_key_id:
        raise ValueError("checkpoint key_id does not match pinned expectation")
    tree_size = checkpoint["tree_size"]
    if type(tree_size) is not int or not 1 <= tree_size <= MAX_TREE_SIZE:
        raise ValueError("checkpoint tree_size must be a positive signed 64-bit integer")
    if tree_size < minimum_tree_size:
        raise ValueError("checkpoint tree_size is below the caller-supplied monotonic floor")
    if type(leaf_index) is not int or leaf_index >= tree_size:
        raise ValueError("leaf_index must be smaller than checkpoint tree_size")
    root_hex = _digest(checkpoint["root_hash"], "checkpoint root_hash")
    root_hash = bytes.fromhex(root_hex)
    issued_at = _parse_utc_timestamp(checkpoint["issued_at_utc"], "checkpoint issued_at_utc")
    if issued_at > verified_at:
        raise ValueError("checkpoint issued_at_utc is later than supplied verification time")

    signature = _decode_canonical_base64(checkpoint["signature_b64"], "checkpoint signature_b64")
    if len(signature) != 64:
        raise ValueError("checkpoint Ed25519 signature must be exactly 64 bytes")
    unsigned_checkpoint = dict(checkpoint)
    unsigned_checkpoint.pop("signature_b64")
    signed_payload = CHECKPOINT_DOMAIN + _canonical(unsigned_checkpoint)
    try:
        Ed25519PublicKey.from_public_bytes(pinned_log_public_key_bytes).verify(
            signature, signed_payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("signed ledger checkpoint signature verification failed") from exc

    proof = _proof_nodes(inclusion_path, "inclusion_path")
    _verify_inclusion(
        entry_bytes,
        leaf_index,
        tree_size,
        proof,
        root_hash,
    )
    return TransparencyLedgerInspection(
        ledger_id=manifest.ledger_anchor.ledger_id,
        entry_id=manifest.ledger_anchor.entry_id,
        manifest_sha256=manifest.raw_sha256,
        ledger_entry_sha256=hashlib.sha256(entry_bytes).hexdigest(),
        log_id=log_id,
        key_id=key_id,
        tree_size=tree_size,
        leaf_index=leaf_index,
        checkpoint_sha256=hashlib.sha256(raw_signed_checkpoint_bytes).hexdigest(),
        checkpoint_signature_verified=True,
        inclusion_verified=True,
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        append_only_continuity_status="UNVERIFIED_NO_CONSISTENCY_PROOF",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=LEDGER_REMAINING_BLOCKERS,
    )
