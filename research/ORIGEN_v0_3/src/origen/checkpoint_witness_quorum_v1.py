"""Research-only independent checkpoint witness quorum verifier.

This module verifies a root-signed witness registry and distinct Ed25519
witness statements over the exact same signed checkpoint pair and RFC 6962
consistency proof. The registry root, registry sequence floor, log key, and
verification clock are still supplied by the caller. Successful verification
therefore remains BLOCKED_PROVENANCE and does not establish gossip or global
split-view detection.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.transparency_checkpoint_consistency_v1 import (
    CheckpointConsistencyInspection,
    verify_checkpoint_consistency,
)

REGISTRY_SCHEMA = "origen.checkpoint-witness-registry.v1"
WITNESS_SCHEMA = "origen.checkpoint-witness-statement.v1"
REGISTRY_DOMAIN = b"ORIGEN-CHECKPOINT-WITNESS-REGISTRY-V1\x00"
WITNESS_DOMAIN = b"ORIGEN-CHECKPOINT-WITNESS-STATEMENT-V1\x00"
MAX_REGISTRY_BYTES = 131_072
MAX_WITNESS_BYTES = 16_384
MAX_REGISTRY_WITNESSES = 64
MAX_STATEMENTS = 64
MAX_JSON_DEPTH = 24
MAX_SEQUENCE = (1 << 63) - 1
MAX_TREE_SIZE = (1 << 63) - 1
MAX_WITNESS_AGE_SECONDS = 86_400
MAX_WITNESS_SKEW_SECONDS = 3_600
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")

WITNESS_REMAINING_BLOCKERS = (
    "WITNESS_REGISTRY_ROOT_NOT_INDEPENDENTLY_PROVISIONED",
    "WITNESS_REGISTRY_SEQUENCE_FLOOR_NOT_EXTERNALLY_PERSISTED",
    "LOG_SIGNING_KEY_NOT_INDEPENDENTLY_PROVISIONED",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "CROSS_WITNESS_GOSSIP_AND_GLOBAL_SPLIT_VIEW_DETECTION_NOT_VERIFIED",
    "WITNESS_OPERATOR_INDEPENDENCE_NOT_INSTITUTIONALLY_ESTABLISHED",
    "RFC3161_TIME_STAMP_NOT_VERIFIED",
    "PHYSICAL_CUSTODY_AND_ARTIFACT_TRUTH_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class VerifiedWitnessRegistry:
    registry_id: str
    registry_sequence: int
    root_key_id: str
    registry_sha256: str
    log_id: str
    minimum_witness_quorum: int
    maximum_witness_age_seconds: int
    maximum_witness_time_skew_seconds: int
    issued_at_utc: datetime
    not_before_utc: datetime
    expires_at_utc: datetime
    active_witness_count: int


@dataclass(frozen=True, slots=True)
class CheckpointWitnessQuorumInspection:
    registry: VerifiedWitnessRegistry
    checkpoint_consistency: CheckpointConsistencyInspection
    witness_statement_sha256: tuple[str, ...]
    agreeing_witness_ids: tuple[str, ...]
    agreeing_witness_key_ids: tuple[str, ...]
    witness_quorum_required: int
    witness_quorum_observed: int
    witness_quorum_verified: bool
    agreement_status: str
    split_view_detection_status: str
    trust_anchor_source: str
    registry_sequence_source: str
    verification_clock_source: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _pairs_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_float(value: str) -> None:
    raise ValueError("floating-point JSON numbers are not accepted")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not accepted: {value}")


def _parse_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        raise ValueError("JSON integer exceeds signed 64-bit range")
    parsed = int(value)
    if not -(1 << 63) <= parsed <= MAX_SEQUENCE:
        raise ValueError("JSON integer exceeds signed 64-bit range")
    return parsed


def _validate_depth(raw: bytes) -> None:
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
        elif byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError("JSON exceeds maximum nesting depth")
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _load_canonical(raw: bytes, *, maximum: int, label: str) -> dict[str, object]:
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum:
        raise ValueError(f"{label} must be exact bytes within the size limit")
    _validate_depth(raw)
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_int=_parse_integer,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{label} must be bounded valid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    if raw != _canonical(value):
        raise ValueError(f"{label} must use canonical UTF-8 JSON")
    return value


def _exact_fields(value: dict[str, object], fields: set[str], label: str) -> None:
    if set(value) != fields:
        raise ValueError(f"{label} fields mismatch")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def _integer(value: object, field: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an exact integer in {minimum}..{maximum}")
    return value


def _b64(value: object, field: str, expected_length: int) -> bytes:
    if type(value) is not str:
        raise ValueError(f"{field} must be base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field} is not valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field} must use canonical base64")
    if len(decoded) != expected_length:
        raise ValueError(f"{field} must decode to exactly {expected_length} bytes")
    return decoded


def _timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _UTC.fullmatch(value):
        raise ValueError(f"{field} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc


def _utc_instant(value: object, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field} timezone is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError(f"{field} timezone offset must be an exact timedelta")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError(f"{field} cannot be normalized to UTC") from exc


def verify_signed_witness_registry(
    raw_registry_bytes: bytes,
    *,
    pinned_registry_root_public_key_bytes: bytes,
    expected_registry_root_key_id: str,
    expected_registry_id: str,
    expected_log_id: str,
    minimum_registry_sequence: int,
    verification_time: datetime,
) -> VerifiedWitnessRegistry:
    """Verify a root-signed witness registry relative to caller-supplied pins.

    The root public key, key ID, registry ID, minimum sequence, and clock are
    security-critical deployment inputs. They are not authenticated by this
    function. Production provisioning is deliberately not implemented here.
    """
    if type(pinned_registry_root_public_key_bytes) is not bytes or len(pinned_registry_root_public_key_bytes) != 32:
        raise ValueError("pinned registry root public key must be exactly 32 bytes")
    root_key_id = _identifier(expected_registry_root_key_id, "expected_registry_root_key_id")
    registry_id = _identifier(expected_registry_id, "expected_registry_id")
    log_id = _identifier(expected_log_id, "expected_log_id")
    sequence_floor = _integer(
        minimum_registry_sequence, "minimum_registry_sequence",
        minimum=1, maximum=MAX_SEQUENCE,
    )
    now = _utc_instant(verification_time, "verification_time")
    document = _load_canonical(
        raw_registry_bytes, maximum=MAX_REGISTRY_BYTES, label="witness registry"
    )
    _exact_fields(document, {
        "schema_version", "registry_id", "registry_sequence", "root_key_id",
        "issued_at_utc", "not_before_utc", "expires_at_utc", "log_id",
        "minimum_witness_quorum", "maximum_witness_age_seconds",
        "maximum_witness_time_skew_seconds", "witnesses", "signature_b64",
    }, "witness registry")
    if document["schema_version"] != REGISTRY_SCHEMA:
        raise ValueError("unsupported witness registry schema")
    if _identifier(document["registry_id"], "registry_id") != registry_id:
        raise ValueError("witness registry ID does not match pinned expectation")
    if _identifier(document["root_key_id"], "root_key_id") != root_key_id:
        raise ValueError("witness registry root key ID does not match pinned root")
    if _identifier(document["log_id"], "log_id") != log_id:
        raise ValueError("witness registry log ID does not match expected log")
    sequence = _integer(
        document["registry_sequence"], "registry_sequence",
        minimum=1, maximum=MAX_SEQUENCE,
    )
    if sequence < sequence_floor:
        raise ValueError("witness registry sequence is below external minimum")
    issued = _timestamp(document["issued_at_utc"], "issued_at_utc")
    not_before = _timestamp(document["not_before_utc"], "not_before_utc")
    expires = _timestamp(document["expires_at_utc"], "expires_at_utc")
    if not (issued <= not_before <= now < expires):
        raise ValueError("witness registry is not currently valid")
    if issued > now:
        raise ValueError("witness registry issue time is in the future")
    quorum = _integer(
        document["minimum_witness_quorum"], "minimum_witness_quorum",
        minimum=2, maximum=MAX_REGISTRY_WITNESSES,
    )
    max_age = _integer(
        document["maximum_witness_age_seconds"], "maximum_witness_age_seconds",
        minimum=1, maximum=MAX_WITNESS_AGE_SECONDS,
    )
    max_skew = _integer(
        document["maximum_witness_time_skew_seconds"], "maximum_witness_time_skew_seconds",
        minimum=0, maximum=MAX_WITNESS_SKEW_SECONDS,
    )
    entries = document["witnesses"]
    if type(entries) is not list or not 2 <= len(entries) <= MAX_REGISTRY_WITNESSES:
        raise ValueError(f"witnesses must contain 2..{MAX_REGISTRY_WITNESSES} entries")

    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    seen_public: set[bytes] = set()
    active_count = 0
    for index, entry in enumerate(entries):
        label = f"witnesses[{index}]"
        if type(entry) is not dict:
            raise ValueError(f"{label} must be an object")
        _exact_fields(entry, {
            "witness_id", "key_id", "public_key_b64", "valid_from_utc",
            "valid_until_utc", "revoked",
        }, label)
        witness_id = _identifier(entry["witness_id"], f"{label}.witness_id")
        key_id = _identifier(entry["key_id"], f"{label}.key_id")
        public_key = _b64(entry["public_key_b64"], f"{label}.public_key_b64", 32)
        valid_from = _timestamp(entry["valid_from_utc"], f"{label}.valid_from_utc")
        valid_until = _timestamp(entry["valid_until_utc"], f"{label}.valid_until_utc")
        if valid_from > valid_until:
            raise ValueError(f"{label} validity interval is inverted")
        if type(entry["revoked"]) is not bool:
            raise ValueError(f"{label}.revoked must be an exact boolean")
        if witness_id in seen_ids or key_id in seen_keys:
            raise ValueError("duplicate witness identity or key identifier")
        if public_key in seen_public:
            raise ValueError("witness public key is reused across identities")
        seen_ids.add(witness_id)
        seen_keys.add(key_id)
        seen_public.add(public_key)
        if not entry["revoked"] and valid_from <= now <= valid_until:
            active_count += 1
    if quorum > active_count:
        raise ValueError("minimum witness quorum exceeds active registry membership")

    signature = _b64(document["signature_b64"], "signature_b64", 64)
    unsigned = dict(document)
    unsigned.pop("signature_b64")
    try:
        Ed25519PublicKey.from_public_bytes(pinned_registry_root_public_key_bytes).verify(
            signature, REGISTRY_DOMAIN + _canonical(unsigned)
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("witness registry root signature verification failed") from exc

    return VerifiedWitnessRegistry(
        registry_id=registry_id,
        registry_sequence=sequence,
        root_key_id=root_key_id,
        registry_sha256=hashlib.sha256(raw_registry_bytes).hexdigest(),
        log_id=log_id,
        minimum_witness_quorum=quorum,
        maximum_witness_age_seconds=max_age,
        maximum_witness_time_skew_seconds=max_skew,
        issued_at_utc=issued,
        not_before_utc=not_before,
        expires_at_utc=expires,
        active_witness_count=active_count,
    )


def verify_checkpoint_witness_quorum(
    raw_registry_bytes: bytes,
    raw_witness_statement_bytes: Sequence[bytes],
    raw_old_checkpoint_bytes: bytes,
    raw_new_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    *,
    pinned_registry_root_public_key_bytes: bytes,
    expected_registry_root_key_id: str,
    expected_registry_id: str,
    minimum_registry_sequence: int,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_new_tree_size: int,
    verification_time: datetime,
) -> CheckpointWitnessQuorumInspection:
    """Verify a registry, append-only proof, and distinct witness quorum.

    Every witness statement must bind the exact registry, old/new checkpoint
    bytes, and consistency-proof bytes. All statements must agree on the same
    new root and tree size. Invalid or duplicate statements fail the entire
    batch. Cross-batch gossip and persistent equivocation detection are not
    provided; the result always remains BLOCKED_PROVENANCE.
    """
    if type(raw_witness_statement_bytes) not in (tuple, list):
        raise TypeError("raw_witness_statement_bytes must be a tuple or list")
    if not 1 <= len(raw_witness_statement_bytes) <= MAX_STATEMENTS:
        raise ValueError(f"witness statements must contain 1..{MAX_STATEMENTS} entries")
    registry = verify_signed_witness_registry(
        raw_registry_bytes,
        pinned_registry_root_public_key_bytes=pinned_registry_root_public_key_bytes,
        expected_registry_root_key_id=expected_registry_root_key_id,
        expected_registry_id=expected_registry_id,
        expected_log_id=expected_log_id,
        minimum_registry_sequence=minimum_registry_sequence,
        verification_time=verification_time,
    )
    consistency = verify_checkpoint_consistency(
        raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_key_id=expected_log_key_id,
        minimum_new_tree_size=minimum_new_tree_size,
        verification_time=verification_time,
    )
    old_digest = hashlib.sha256(raw_old_checkpoint_bytes).hexdigest()
    new_digest = hashlib.sha256(raw_new_checkpoint_bytes).hexdigest()
    proof_digest = hashlib.sha256(raw_consistency_proof_bytes).hexdigest()
    now = _utc_instant(verification_time, "verification_time")

    registry_doc = _load_canonical(
        raw_registry_bytes, maximum=MAX_REGISTRY_BYTES, label="witness registry"
    )
    entries_by_id = {entry["witness_id"]: entry for entry in registry_doc["witnesses"]}
    seen_witness_ids: set[str] = set()
    seen_key_ids: set[str] = set()
    seen_statement_hashes: set[str] = set()
    statement_hashes: list[str] = []
    witness_ids: list[str] = []
    key_ids: list[str] = []
    issued_times: list[datetime] = []

    for index, raw_statement in enumerate(raw_witness_statement_bytes):
        label = f"witness statement[{index}]"
        statement = _load_canonical(
            raw_statement, maximum=MAX_WITNESS_BYTES, label=label
        )
        _exact_fields(statement, {
            "schema_version", "registry_id", "registry_sequence", "registry_sha256",
            "witness_id", "key_id", "log_id", "old_checkpoint_sha256",
            "new_checkpoint_sha256", "old_tree_size", "new_tree_size",
            "old_root_sha256", "new_root_sha256", "consistency_proof_sha256",
            "issued_at_utc", "signature_b64",
        }, label)
        if statement["schema_version"] != WITNESS_SCHEMA:
            raise ValueError(f"{label} has an unsupported schema")
        if _identifier(statement["registry_id"], f"{label}.registry_id") != registry.registry_id:
            raise ValueError(f"{label} registry ID mismatch")
        if _integer(statement["registry_sequence"], f"{label}.registry_sequence",
                    minimum=1, maximum=MAX_SEQUENCE) != registry.registry_sequence:
            raise ValueError(f"{label} registry sequence mismatch")
        if _digest(statement["registry_sha256"], f"{label}.registry_sha256") != registry.registry_sha256:
            raise ValueError(f"{label} does not bind exact registry bytes")
        witness_id = _identifier(statement["witness_id"], f"{label}.witness_id")
        key_id = _identifier(statement["key_id"], f"{label}.key_id")
        if witness_id in seen_witness_ids or key_id in seen_key_ids:
            raise ValueError("duplicate witness identity or signing key in quorum")
        entry = entries_by_id.get(witness_id)
        if entry is None:
            raise ValueError(f"{label} witness is not present in signed registry")
        if entry["key_id"] != key_id:
            raise ValueError(f"{label} key ID does not match registry")
        if entry["revoked"] is not False:
            raise ValueError(f"{label} witness key is revoked")
        valid_from = _timestamp(entry["valid_from_utc"], f"{label} registry valid_from")
        valid_until = _timestamp(entry["valid_until_utc"], f"{label} registry valid_until")
        issued = _timestamp(statement["issued_at_utc"], f"{label}.issued_at_utc")
        if not (registry.not_before_utc <= issued < registry.expires_at_utc):
            raise ValueError(f"{label} was issued outside signed registry validity")
        if not (valid_from <= issued <= valid_until):
            raise ValueError(f"{label} was issued outside witness key validity")
        if issued > now:
            raise ValueError(f"{label} is issued in the future")
        if issued < consistency.new_issued_at_utc:
            raise ValueError(f"{label} predates the checkpoint it attests")
        if (now - issued).total_seconds() > registry.maximum_witness_age_seconds:
            raise ValueError(f"{label} exceeds maximum witness statement age")
        if _identifier(statement["log_id"], f"{label}.log_id") != registry.log_id:
            raise ValueError(f"{label} log ID mismatch")
        expected_digests = (
            ("old_checkpoint_sha256", old_digest),
            ("new_checkpoint_sha256", new_digest),
            ("consistency_proof_sha256", proof_digest),
            ("old_root_sha256", consistency.old_root_sha256),
            ("new_root_sha256", consistency.new_root_sha256),
        )
        for field, expected in expected_digests:
            if _digest(statement[field], f"{label}.{field}") != expected:
                raise ValueError(f"{label} {field} does not match verified bytes")
        if _integer(statement["old_tree_size"], f"{label}.old_tree_size",
                    minimum=1, maximum=MAX_TREE_SIZE) != consistency.old_tree_size:
            raise ValueError(f"{label} old tree size mismatch")
        if _integer(statement["new_tree_size"], f"{label}.new_tree_size",
                    minimum=1, maximum=MAX_TREE_SIZE) != consistency.new_tree_size:
            raise ValueError(f"{label} new tree size mismatch")

        signature = _b64(statement["signature_b64"], f"{label}.signature_b64", 64)
        unsigned = dict(statement)
        unsigned.pop("signature_b64")
        public_key = _b64(entry["public_key_b64"], f"{label} registry public key", 32)
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                signature, WITNESS_DOMAIN + _canonical(unsigned)
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError(f"{label} Ed25519 signature verification failed") from exc

        statement_digest = hashlib.sha256(raw_statement).hexdigest()
        if statement_digest in seen_statement_hashes:
            raise ValueError("duplicate witness statement bytes")
        seen_statement_hashes.add(statement_digest)
        seen_witness_ids.add(witness_id)
        seen_key_ids.add(key_id)
        statement_hashes.append(statement_digest)
        witness_ids.append(witness_id)
        key_ids.append(key_id)
        issued_times.append(issued)

    if len(issued_times) > 1:
        skew = (max(issued_times) - min(issued_times)).total_seconds()
        if skew > registry.maximum_witness_time_skew_seconds:
            raise ValueError("witness statement issuance times exceed registry skew limit")
    if len(witness_ids) < registry.minimum_witness_quorum:
        raise ValueError("independent witness quorum threshold was not met")

    return CheckpointWitnessQuorumInspection(
        registry=registry,
        checkpoint_consistency=consistency,
        witness_statement_sha256=tuple(statement_hashes),
        agreeing_witness_ids=tuple(witness_ids),
        agreeing_witness_key_ids=tuple(key_ids),
        witness_quorum_required=registry.minimum_witness_quorum,
        witness_quorum_observed=len(witness_ids),
        witness_quorum_verified=True,
        agreement_status="QUORUM_AGREES_ON_EXACT_CHECKPOINT_AND_CONSISTENCY_PROOF",
        split_view_detection_status="CROSS_BATCH_GOSSIP_NOT_VERIFIED",
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        registry_sequence_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=WITNESS_REMAINING_BLOCKERS,
    )
