"""Research-only RFC 6962 consistency verifier for signed ORIGEN checkpoints.

This module verifies append-only consistency between two exact, Ed25519-signed
checkpoint byte strings. The signing key, minimum tree-size floor, and clock
remain caller-supplied; no independent witnesses or authenticated deployment
state are verified. Every successful result remains BLOCKED_PROVENANCE.
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
from origen.transparency_ledger_verifier_v1 import CHECKPOINT_DOMAIN, CHECKPOINT_SCHEMA

CONSISTENCY_PROOF_SCHEMA = "origen.transparency-ledger-consistency-proof.v1"
MAX_CHECKPOINT_BYTES = 16_384
MAX_CONSISTENCY_PROOF_BYTES = 16_384
MAX_CONSISTENCY_NODES = 64
MAX_TREE_SIZE = (1 << 63) - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:/@+-]{0,127}\\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
_UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\\Z")

CONSISTENCY_REMAINING_BLOCKERS = (
    "LOG_SIGNING_KEY_NOT_INDEPENDENTLY_PROVISIONED",
    "TREE_SIZE_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "CHECKPOINT_TIME_NOT_AUTHENTICATED",
    "INDEPENDENT_CHECKPOINT_WITNESS_QUORUM_NOT_VERIFIED",
    "LOG_GOVERNANCE_AND_SPLIT_VIEW_GOSSIP_NOT_VERIFIED",
    "CUSTODY_RECEIPTS_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED",
    "PHYSICAL_ARTIFACT_SEMANTICS_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class CheckpointConsistencyInspection:
    log_id: str
    key_id: str
    old_checkpoint_sha256: str
    new_checkpoint_sha256: str
    consistency_proof_sha256: str
    old_tree_size: int
    new_tree_size: int
    old_root_sha256: str
    new_root_sha256: str
    old_issued_at_utc: datetime
    new_issued_at_utc: datetime
    checkpoint_signatures_verified: bool
    consistency_verified: bool
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


def _parse_nodes(value: object) -> tuple[bytes, ...]:
    if type(value) is not list:
        raise ValueError("consistency_path_b64 must be an array")
    if len(value) > MAX_CONSISTENCY_NODES:
        raise ValueError(f"consistency proof exceeds {MAX_CONSISTENCY_NODES} nodes")
    nodes: list[bytes] = []
    for index, encoded in enumerate(value):
        node = _decode_canonical_base64(encoded, f"consistency_path_b64[{index}]")
        if len(node) != 32:
            raise ValueError(f"consistency_path_b64[{index}] must decode to exactly 32 bytes")
        nodes.append(node)
    return tuple(nodes)


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


def _parse_timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _UTC_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{field} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\\x01" + left + right).digest()


def _verify_consistency(
    old_tree_size: int,
    new_tree_size: int,
    old_root: bytes,
    new_root: bytes,
    proof_nodes: tuple[bytes, ...],
) -> None:
    """Verify the RFC 6962 consistency proof for 1 <= old_size <= new_size."""
    if old_tree_size > new_tree_size:
        raise ValueError("old checkpoint tree_size exceeds new checkpoint tree_size")
    if old_tree_size == new_tree_size:
        if proof_nodes:
            raise ValueError("same-size consistency proof must not contain nodes")
        if old_root != new_root:
            raise ValueError("same-size checkpoints have different Merkle roots")
        return
    if not proof_nodes:
        raise ValueError("consistency proof is incomplete")

    fn = old_tree_size - 1
    sn = new_tree_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1

    if fn == 0:
        first_root = old_root
        second_root = old_root
        remaining = proof_nodes
    else:
        first_root = proof_nodes[0]
        second_root = proof_nodes[0]
        remaining = proof_nodes[1:]

    for sibling in remaining:
        if sn == 0:
            raise ValueError("consistency proof contains extra nodes")
        if (fn & 1) == 1 or fn == sn:
            first_root = _node_hash(sibling, first_root)
            second_root = _node_hash(sibling, second_root)
            while (fn & 1) == 0 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            second_root = _node_hash(second_root, sibling)
        fn >>= 1
        sn >>= 1

    if sn != 0:
        raise ValueError("consistency proof is incomplete")
    if first_root != old_root or second_root != new_root:
        raise ValueError("consistency proof does not establish append-only checkpoint continuity")


def _verify_checkpoint(
    raw_checkpoint_bytes: bytes,
    *,
    public_key: Ed25519PublicKey,
    expected_log_id: str,
    expected_key_id: str,
    verified_at: datetime,
    label: str,
) -> tuple[int, bytes, datetime, str]:
    checkpoint = _load_canonical_object(
        raw_checkpoint_bytes,
        maximum=MAX_CHECKPOINT_BYTES,
        label=label,
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
        label,
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA:
        raise ValueError(f"{label} has an unsupported checkpoint schema")
    log_id = _identifier(checkpoint["log_id"], f"{label} log_id")
    key_id = _identifier(checkpoint["key_id"], f"{label} key_id")
    if log_id != expected_log_id:
        raise ValueError(f"{label} log_id does not match pinned expectation")
    if key_id != expected_key_id:
        raise ValueError(f"{label} key_id does not match pinned expectation")
    tree_size = checkpoint["tree_size"]
    if type(tree_size) is not int or not 1 <= tree_size <= MAX_TREE_SIZE:
        raise ValueError(f"{label} tree_size must be a positive signed 64-bit integer")
    root_hash = bytes.fromhex(_digest(checkpoint["root_hash"], f"{label} root_hash"))
    issued_at = _parse_timestamp(checkpoint["issued_at_utc"], f"{label} issued_at_utc")
    if issued_at > verified_at:
        raise ValueError(f"{label} issued_at_utc is later than supplied verification time")
    signature = _decode_canonical_base64(
        checkpoint["signature_b64"], f"{label} signature_b64"
    )
    if len(signature) != 64:
        raise ValueError(f"{label} Ed25519 signature must be exactly 64 bytes")
    unsigned = dict(checkpoint)
    unsigned.pop("signature_b64")
    try:
        public_key.verify(signature, CHECKPOINT_DOMAIN + _canonical(unsigned))
    except InvalidSignature as exc:
        raise ValueError(f"{label} Ed25519 signature verification failed") from exc
    return tree_size, root_hash, issued_at, hashlib.sha256(raw_checkpoint_bytes).hexdigest()


def verify_checkpoint_consistency(
    raw_old_checkpoint_bytes: bytes,
    raw_new_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    *,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_key_id: str,
    minimum_new_tree_size: int,
    verification_time: datetime,
) -> CheckpointConsistencyInspection:
    """Verify two signed checkpoints and their exact RFC 6962 consistency proof.

    A successful result proves cryptographic consistency only relative to the
    caller-supplied key, floor, and clock. It does not authenticate those
    inputs, prove independent witness agreement, or promote provenance.
    """
    if type(pinned_log_public_key_bytes) is not bytes or len(pinned_log_public_key_bytes) != 32:
        raise ValueError("pinned_log_public_key_bytes must be exactly 32 bytes")
    expected_log_id = _identifier(expected_log_id, "expected_log_id")
    expected_key_id = _identifier(expected_key_id, "expected_key_id")
    if type(minimum_new_tree_size) is not int or not 1 <= minimum_new_tree_size <= MAX_TREE_SIZE:
        raise ValueError("minimum_new_tree_size must be a positive signed 64-bit integer")
    verified_at = _utc_instant(verification_time, "verification_time")
    public_key = Ed25519PublicKey.from_public_bytes(pinned_log_public_key_bytes)

    old_size, old_root, old_time, old_sha256 = _verify_checkpoint(
        raw_old_checkpoint_bytes,
        public_key=public_key,
        expected_log_id=expected_log_id,
        expected_key_id=expected_key_id,
        verified_at=verified_at,
        label="old checkpoint",
    )
    new_size, new_root, new_time, new_sha256 = _verify_checkpoint(
        raw_new_checkpoint_bytes,
        public_key=public_key,
        expected_log_id=expected_log_id,
        expected_key_id=expected_key_id,
        verified_at=verified_at,
        label="new checkpoint",
    )
    if new_time < old_time:
        raise ValueError("new checkpoint time precedes old checkpoint time")
    if new_size < minimum_new_tree_size:
        raise ValueError("new checkpoint tree_size is below the caller-supplied monotonic floor")

    proof = _load_canonical_object(
        raw_consistency_proof_bytes,
        maximum=MAX_CONSISTENCY_PROOF_BYTES,
        label="consistency proof",
    )
    _exact_fields(
        proof,
        {
            "schema_version",
            "log_id",
            "old_checkpoint_sha256",
            "new_checkpoint_sha256",
            "old_tree_size",
            "new_tree_size",
            "consistency_path_b64",
        },
        "consistency proof",
    )
    if proof["schema_version"] != CONSISTENCY_PROOF_SCHEMA:
        raise ValueError("unsupported consistency-proof schema")
    if _identifier(proof["log_id"], "consistency proof log_id") != expected_log_id:
        raise ValueError("consistency proof log_id does not match pinned expectation")
    if _digest(proof["old_checkpoint_sha256"], "old_checkpoint_sha256") != old_sha256:
        raise ValueError("consistency proof does not bind exact old checkpoint bytes")
    if _digest(proof["new_checkpoint_sha256"], "new_checkpoint_sha256") != new_sha256:
        raise ValueError("consistency proof does not bind exact new checkpoint bytes")
    if type(proof["old_tree_size"]) is not int or proof["old_tree_size"] != old_size:
        raise ValueError("consistency proof old_tree_size does not match old checkpoint")
    if type(proof["new_tree_size"]) is not int or proof["new_tree_size"] != new_size:
        raise ValueError("consistency proof new_tree_size does not match new checkpoint")

    proof_nodes = _parse_nodes(proof["consistency_path_b64"])
    _verify_consistency(old_size, new_size, old_root, new_root, proof_nodes)

    return CheckpointConsistencyInspection(
        log_id=expected_log_id,
        key_id=expected_key_id,
        old_checkpoint_sha256=old_sha256,
        new_checkpoint_sha256=new_sha256,
        consistency_proof_sha256=hashlib.sha256(raw_consistency_proof_bytes).hexdigest(),
        old_tree_size=old_size,
        new_tree_size=new_size,
        old_root_sha256=old_root.hex(),
        new_root_sha256=new_root.hex(),
        old_issued_at_utc=old_time,
        new_issued_at_utc=new_time,
        checkpoint_signatures_verified=True,
        consistency_verified=True,
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        append_only_continuity_status="CONSISTENCY_VERIFIED_WITNESS_QUORUM_UNVERIFIED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=CONSISTENCY_REMAINING_BLOCKERS,
    )
