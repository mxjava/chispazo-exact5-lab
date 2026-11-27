"""Strict structural parser for a per-contest ORIGEN physical-evidence manifest.

This parser checks declarations and cross-references only. It does not read or
re-hash original artifacts, verify signatures, authenticate identities, validate
RFC 3161 tokens, prove ledger inclusion, or establish independent custody.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

MAX_PHYSICAL_MANIFEST_BYTES = 1_048_576
MAX_PHYSICAL_MANIFEST_JSON_DEPTH = 64
SCHEMA_VERSION = "origen.physical-evidence-manifest.v1"

_CHISPAZO_LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")
_CLASSIC_CLOSE_SLOT = (21, 0, 0, 0)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTEST_ID = re.compile(r"[1-9][0-9]{0,11}\Z")
_LOCAL_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z\Z"
)
_MEDIA_TYPE = re.compile(r"(?:application|text|image|video)/[A-Za-z0-9.+-]+\Z")
_SIGNATURE_ALGORITHMS = {"ed25519", "ecdsa-p256-sha256", "rsa-pss-sha256"}

# Four records listed in the Chispazo Acta attachment matrix, plus the Acta,
# other procedure-controlled media/records and ORIGEN physical-support records.
REQUIRED_ARTIFACT_TYPES = frozenset({
    "DRAW-ACTA",
    "SALES-CLOSE-SUMMARY",
    "CS11-WINNING-NUMBERS",
    "POST-DRAW-SUMMARY",
    "WEIGHING-STRIP",
    "PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA",
    "SCALE-CALIBRATION-CERTIFICATE",
    "EQUIPMENT-URN-RECORD",
    "SPHERE-NUMBER-MAPPING-REGISTER",
    "CS12-ROOM-ACCESS-REGISTER",
    "SEGOB-OIC-CUSTODY-RECORD",
    "DRAW-RECORDING-FULL",
    "DRAW-RECORDING-EDITED",
    "WINNER-RELATION-REPORT-WITH-SIGNATURE",
    "MJF-TRANSACTION-FILE",
    "MJF-SIGNATURE-PRINTED-FORM",
    "CS02-DAILY-EQUIPMENT-INSPECTION",
})

# Policy 2 + policy 11: commissioned representatives and SEGOB inspector
# whose roles/signatures must appear on the draw Acta.
_ACTA_REQUIRED_ROLES = frozenset({
    "GENERAL-DIRECTORATE-REPRESENTATIVE",
    "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
    "INFORMATION-TECHNOLOGY-REPRESENTATIVE",
    "SEGOB-INSPECTOR",
})

# Activity 5.4: the weighing responsible signs; SGVO, SEGOB and DG review/rubric.
_WEIGHING_STRIP_REQUIRED_ROLES = frozenset({
    "SPHERE-WEIGHING-RESPONSIBLE",
    "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
    "SEGOB-INSPECTOR",
    "GENERAL-DIRECTORATE-REPRESENTATIVE",
})

_IT_REQUIRED_ROLE = frozenset({"INFORMATION-TECHNOLOGY-REPRESENTATIVE"})
_CS02_REQUIRED_ROLES = frozenset({
    "EQUIPMENT-OPERATOR",
    "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
})
_REQUIRED_ROLES_BY_ARTIFACT = {
    "PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA": _IT_REQUIRED_ROLE,
    "WINNER-RELATION-REPORT-WITH-SIGNATURE": _IT_REQUIRED_ROLE,
    "MJF-SIGNATURE-PRINTED-FORM": _IT_REQUIRED_ROLE,
    "CS02-DAILY-EQUIPMENT-INSPECTION": _CS02_REQUIRED_ROLES,
}

_SIGNED_ARTIFACT_TYPES = frozenset({
    "DRAW-ACTA",
    "WEIGHING-STRIP",
    "PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA",
    "WINNER-RELATION-REPORT-WITH-SIGNATURE",
    "MJF-SIGNATURE-PRINTED-FORM",
    "CS02-DAILY-EQUIPMENT-INSPECTION",
})

_ROOT_FIELDS = {
    "schema_version", "target", "artifacts", "signatures",
    "custody_events", "trusted_time_proofs", "ledger_anchor",
}


@dataclass(frozen=True, slots=True)
class PhysicalManifestTarget:
    modality: str
    contest_id: str
    draw_date_local: str
    draw_close_at_utc: str


@dataclass(frozen=True, slots=True)
class PhysicalArtifactClaim:
    artifact_type: str
    sha256: str
    byte_length: int
    contest_id: str
    source_id: str
    source_object_id: str
    media_type: str


@dataclass(frozen=True, slots=True)
class PhysicalSignatureClaim:
    artifact_sha256: str
    subject_id: str
    role: str
    key_id: str
    algorithm: str
    signature_sha256: str


@dataclass(frozen=True, slots=True)
class PhysicalCustodyEventClaim:
    event_id: str
    artifact_sha256: str
    custodian_subject_id: str
    custodian_role: str
    received_at_utc: str
    receipt_sha256: str
    timestamp_proof_sha256: str


@dataclass(frozen=True, slots=True)
class PhysicalTimeProofClaim:
    authority_id: str
    event_id: str
    event_at_utc: str
    proof_sha256: str


@dataclass(frozen=True, slots=True)
class PhysicalLedgerAnchorClaim:
    ledger_id: str
    entry_id: str
    previous_head_sha256: str
    head_sha256: str
    inclusion_proof_sha256: str


@dataclass(frozen=True, slots=True)
class UnverifiedPhysicalEvidenceManifest:
    """Parsed declarations only; this type is never an authenticated receipt."""

    target: PhysicalManifestTarget
    artifacts: tuple[PhysicalArtifactClaim, ...]
    signatures: tuple[PhysicalSignatureClaim, ...]
    custody_events: tuple[PhysicalCustodyEventClaim, ...]
    trusted_time_proofs: tuple[PhysicalTimeProofClaim, ...]
    ledger_anchor: PhysicalLedgerAnchorClaim
    raw_sha256: str


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not accepted: {value}")


def _reject_json_float(value: str) -> None:
    raise ValueError("floating-point JSON numbers are not accepted in physical manifests")


def _parse_json_integer(value: str) -> int:
    negative = value.startswith("-")
    digits = value[1:] if negative else value
    limit = "9223372036854775808" if negative else "9223372036854775807"
    if len(digits) > len(limit) or (len(digits) == len(limit) and digits > limit):
        raise ValueError("JSON integer exceeds signed 64-bit range")
    return int(value)


def _validate_json_nesting_depth(raw: bytes) -> None:
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
            if depth > MAX_PHYSICAL_MANIFEST_JSON_DEPTH:
                raise ValueError(
                    "physical manifest exceeds maximum JSON nesting depth "
                    f"{MAX_PHYSICAL_MANIFEST_JSON_DEPTH}"
                )
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


def _object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        extra = sorted(actual - fields)
        raise ValueError(f"{label} fields mismatch; missing={missing}, unexpected={extra}")
    return value


def _array(value: object, label: str, *, minimum: int, maximum: int) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} must be an array with {minimum}..{maximum} entries")
    return value


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical non-empty identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def _positive_integer(value: object, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _timestamp(value: object, field: str) -> str:
    if type(value) is not str or not _UTC_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{field} must be a canonical UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc
    return value


def _parse_target(value: object) -> PhysicalManifestTarget:
    item = _object(
        value,
        {"modality", "contest_id", "draw_date_local", "draw_close_at_utc"},
        "target",
    )
    if type(item["modality"]) is not str or item["modality"] != "CLASSIC":
        raise ValueError("physical evidence manifests are restricted to CLASSIC targets")
    contest_id = item["contest_id"]
    if type(contest_id) is not str or not _CONTEST_ID.fullmatch(contest_id):
        raise ValueError("target.contest_id must be a canonical positive decimal contest ID")
    draw_date = item["draw_date_local"]
    if type(draw_date) is not str or not _LOCAL_DATE.fullmatch(draw_date):
        raise ValueError("target.draw_date_local must use YYYY-MM-DD")
    try:
        parsed_date = date.fromisoformat(draw_date)
    except ValueError as exc:
        raise ValueError("target.draw_date_local is not a valid calendar date") from exc
    close_at = _timestamp(item["draw_close_at_utc"], "target.draw_close_at_utc")
    instant = datetime.fromisoformat(close_at[:-1] + "+00:00")
    local = instant.astimezone(_CHISPAZO_LOCAL_TIMEZONE)
    if (local.hour, local.minute, local.second, local.microsecond) != _CLASSIC_CLOSE_SLOT:
        raise ValueError(
            "CLASSIC draw_close_at_utc must resolve to the official 21:00 "
            "America/Mexico_City close slot"
        )
    if local.date() != parsed_date:
        raise ValueError("target.draw_date_local does not match the Mexico City close date")
    return PhysicalManifestTarget("CLASSIC", contest_id, draw_date, close_at)


def _parse_artifact(
    value: object,
    index: int,
    target_id: str,
) -> PhysicalArtifactClaim:
    item = _object(
        value,
        {
            "artifact_type", "sha256", "byte_length", "contest_id",
            "source_id", "source_object_id", "media_type",
        },
        f"artifacts[{index}]",
    )
    artifact_type = item["artifact_type"]
    if type(artifact_type) is not str or artifact_type not in REQUIRED_ARTIFACT_TYPES:
        raise ValueError(f"artifacts[{index}].artifact_type is not an allowed required type")
    contest_id = item["contest_id"]
    if type(contest_id) is not str or not _CONTEST_ID.fullmatch(contest_id):
        raise ValueError(f"artifacts[{index}].contest_id is not canonical")
    if contest_id != target_id:
        raise ValueError("every physical artifact must bind to the target contest")
    media_type = item["media_type"]
    if type(media_type) is not str or not _MEDIA_TYPE.fullmatch(media_type):
        raise ValueError(f"artifacts[{index}].media_type must be a canonical MIME type")
    is_recording = artifact_type in {"DRAW-RECORDING-FULL", "DRAW-RECORDING-EDITED"}
    claims_video = media_type.startswith("video/")
    if is_recording != claims_video:
        raise ValueError(
            f"artifacts[{index}].media_type is incompatible with {artifact_type}: "
            "draw recordings must use video/* and non-recording artifacts must not"
        )
    return PhysicalArtifactClaim(
        artifact_type=artifact_type,
        sha256=_digest(item["sha256"], f"artifacts[{index}].sha256"),
        byte_length=_positive_integer(item["byte_length"], f"artifacts[{index}].byte_length"),
        contest_id=contest_id,
        source_id=_identifier(item["source_id"], f"artifacts[{index}].source_id"),
        source_object_id=_identifier(item["source_object_id"], f"artifacts[{index}].source_object_id"),
        media_type=media_type,
    )


def _parse_signature(
    value: object,
    index: int,
    artifact_digests: set[str],
) -> PhysicalSignatureClaim:
    item = _object(
        value,
        {
            "artifact_sha256", "subject_id", "role", "key_id",
            "algorithm", "signature_sha256",
        },
        f"signatures[{index}]",
    )
    artifact_sha = _digest(item["artifact_sha256"], f"signatures[{index}].artifact_sha256")
    if artifact_sha not in artifact_digests:
        raise ValueError("signature references an artifact digest absent from the manifest")
    algorithm = item["algorithm"]
    if type(algorithm) is not str or algorithm not in _SIGNATURE_ALGORITHMS:
        raise ValueError(f"signatures[{index}].algorithm is unsupported")
    return PhysicalSignatureClaim(
        artifact_sha256=artifact_sha,
        subject_id=_identifier(item["subject_id"], f"signatures[{index}].subject_id"),
        role=_identifier(item["role"], f"signatures[{index}].role"),
        key_id=_identifier(item["key_id"], f"signatures[{index}].key_id"),
        algorithm=algorithm,
        signature_sha256=_digest(item["signature_sha256"], f"signatures[{index}].signature_sha256"),
    )


def _parse_time_proof(value: object, index: int) -> PhysicalTimeProofClaim:
    item = _object(
        value,
        {"authority_id", "event_id", "event_at_utc", "proof_sha256"},
        f"trusted_time_proofs[{index}]",
    )
    return PhysicalTimeProofClaim(
        authority_id=_identifier(item["authority_id"], f"trusted_time_proofs[{index}].authority_id"),
        event_id=_identifier(item["event_id"], f"trusted_time_proofs[{index}].event_id"),
        event_at_utc=_timestamp(item["event_at_utc"], f"trusted_time_proofs[{index}].event_at_utc"),
        proof_sha256=_digest(item["proof_sha256"], f"trusted_time_proofs[{index}].proof_sha256"),
    )


def _parse_custody_event(
    value: object,
    index: int,
    artifact_digests: set[str],
) -> PhysicalCustodyEventClaim:
    item = _object(
        value,
        {
            "event_id", "artifact_sha256", "custodian_subject_id",
            "custodian_role", "received_at_utc", "receipt_sha256",
            "timestamp_proof_sha256",
        },
        f"custody_events[{index}]",
    )
    artifact_sha = _digest(item["artifact_sha256"], f"custody_events[{index}].artifact_sha256")
    if artifact_sha not in artifact_digests:
        raise ValueError("custody event references an artifact digest absent from the manifest")
    return PhysicalCustodyEventClaim(
        event_id=_identifier(item["event_id"], f"custody_events[{index}].event_id"),
        artifact_sha256=artifact_sha,
        custodian_subject_id=_identifier(item["custodian_subject_id"], f"custody_events[{index}].custodian_subject_id"),
        custodian_role=_identifier(item["custodian_role"], f"custody_events[{index}].custodian_role"),
        received_at_utc=_timestamp(item["received_at_utc"], f"custody_events[{index}].received_at_utc"),
        receipt_sha256=_digest(item["receipt_sha256"], f"custody_events[{index}].receipt_sha256"),
        timestamp_proof_sha256=_digest(item["timestamp_proof_sha256"], f"custody_events[{index}].timestamp_proof_sha256"),
    )


def _parse_ledger_anchor(value: object) -> PhysicalLedgerAnchorClaim:
    item = _object(
        value,
        {
            "ledger_id", "entry_id", "previous_head_sha256",
            "head_sha256", "inclusion_proof_sha256",
        },
        "ledger_anchor",
    )
    previous = _digest(item["previous_head_sha256"], "ledger_anchor.previous_head_sha256")
    head = _digest(item["head_sha256"], "ledger_anchor.head_sha256")
    if previous == head:
        raise ValueError("ledger head must advance beyond the previous head")
    return PhysicalLedgerAnchorClaim(
        ledger_id=_identifier(item["ledger_id"], "ledger_anchor.ledger_id"),
        entry_id=_identifier(item["entry_id"], "ledger_anchor.entry_id"),
        previous_head_sha256=previous,
        head_sha256=head,
        inclusion_proof_sha256=_digest(item["inclusion_proof_sha256"], "ledger_anchor.inclusion_proof_sha256"),
    )


def parse_unverified_physical_manifest(raw: bytes) -> UnverifiedPhysicalEvidenceManifest:
    """Parse bounded canonical JSON and validate declarations without authenticating them."""
    if type(raw) is not bytes:
        raise TypeError("physical manifest input must be exact bytes")
    if not raw or len(raw) > MAX_PHYSICAL_MANIFEST_BYTES:
        raise ValueError(
            f"physical manifest must contain 1..{MAX_PHYSICAL_MANIFEST_BYTES} bytes"
        )
    _validate_json_nesting_depth(raw)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("physical manifest must be valid UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
            parse_int=_parse_json_integer,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("physical manifest is not valid bounded JSON") from exc
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    if raw != canonical:
        raise ValueError("physical manifest JSON must use canonical UTF-8 encoding")
    root = _object(payload, _ROOT_FIELDS, "manifest")
    if root["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported physical manifest schema_version")

    target = _parse_target(root["target"])
    artifact_values = _array(
        root["artifacts"], "artifacts",
        minimum=len(REQUIRED_ARTIFACT_TYPES),
        maximum=len(REQUIRED_ARTIFACT_TYPES),
    )
    artifacts = tuple(
        _parse_artifact(item, index, target.contest_id)
        for index, item in enumerate(artifact_values)
    )
    artifact_types = [item.artifact_type for item in artifacts]
    if len(set(artifact_types)) != len(artifact_types):
        raise ValueError("artifacts contain duplicate artifact types")
    if set(artifact_types) != REQUIRED_ARTIFACT_TYPES:
        missing = sorted(REQUIRED_ARTIFACT_TYPES - set(artifact_types))
        raise ValueError(f"artifacts are missing required types: {missing}")
    artifact_digests = {item.sha256 for item in artifacts}
    if len(artifact_digests) != len(artifacts):
        raise ValueError("different required artifact types must bind distinct original-byte digests")
    source_object_ids = [item.source_object_id for item in artifacts]
    if len(set(source_object_ids)) != len(source_object_ids):
        raise ValueError("artifacts contain duplicate source_object_id values")

    signature_values = _array(root["signatures"], "signatures", minimum=1, maximum=256)
    signatures = tuple(
        _parse_signature(item, index, artifact_digests)
        for index, item in enumerate(signature_values)
    )
    signature_digests = [item.signature_sha256 for item in signatures]
    if len(set(signature_digests)) != len(signature_digests):
        raise ValueError("signatures contain duplicate signature digests")
    signature_subject_artifacts = [
        (item.subject_id, item.artifact_sha256) for item in signatures
    ]
    if len(set(signature_subject_artifacts)) != len(signature_subject_artifacts):
        raise ValueError("a subject may declare only one signature per artifact")
    key_subjects: dict[str, str] = {}
    for claim in signatures:
        prior_subject = key_subjects.setdefault(claim.key_id, claim.subject_id)
        if prior_subject != claim.subject_id:
            raise ValueError("a signer key_id cannot be bound to multiple subject IDs")
    signatures_by_artifact: dict[str, list[PhysicalSignatureClaim]] = {}
    for claim in signatures:
        signatures_by_artifact.setdefault(claim.artifact_sha256, []).append(claim)
    artifact_by_type = {item.artifact_type: item for item in artifacts}
    for artifact_type in _SIGNED_ARTIFACT_TYPES:
        digest = artifact_by_type[artifact_type].sha256
        if not signatures_by_artifact.get(digest):
            raise ValueError(f"{artifact_type} must have at least one declared signature")

    acta_digest = artifact_by_type["DRAW-ACTA"].sha256
    acta_roles = {item.role for item in signatures_by_artifact.get(acta_digest, [])}
    if not _ACTA_REQUIRED_ROLES.issubset(acta_roles):
        raise ValueError("DRAW-ACTA signatures are missing policy-2 or SEGOB roles")
    for artifact_type, required_roles in _REQUIRED_ROLES_BY_ARTIFACT.items():
        artifact_digest = artifact_by_type[artifact_type].sha256
        declared_roles = {
            item.role for item in signatures_by_artifact.get(artifact_digest, [])
        }
        if not required_roles.issubset(declared_roles):
            raise ValueError(f"{artifact_type} signatures are missing required roles")

    strip_digest = artifact_by_type["WEIGHING-STRIP"].sha256
    strip_signatures = signatures_by_artifact.get(strip_digest, [])
    strip_roles = {item.role for item in strip_signatures}
    strip_subjects = {item.subject_id for item in strip_signatures}
    if (
        len(strip_signatures) != len(_WEIGHING_STRIP_REQUIRED_ROLES)
        or strip_roles != _WEIGHING_STRIP_REQUIRED_ROLES
        or len(strip_subjects) != len(_WEIGHING_STRIP_REQUIRED_ROLES)
    ):
        raise ValueError(
            "WEIGHING-STRIP must have exactly four distinct signers in the activity-5.4 roles"
        )

    custody_values = _array(
        root["custody_events"], "custody_events",
        minimum=len(REQUIRED_ARTIFACT_TYPES), maximum=4096,
    )
    custody_events = tuple(
        _parse_custody_event(item, index, artifact_digests)
        for index, item in enumerate(custody_values)
    )
    custody_event_ids = [item.event_id for item in custody_events]
    if len(set(custody_event_ids)) != len(custody_event_ids):
        raise ValueError("custody_events contain duplicate event IDs")
    receipt_digests = [item.receipt_sha256 for item in custody_events]
    if len(set(receipt_digests)) != len(receipt_digests):
        raise ValueError("custody_events contain duplicate receipt digests")
    custody_artifact_digests = {item.artifact_sha256 for item in custody_events}
    if custody_artifact_digests != artifact_digests:
        raise ValueError("every required artifact must have at least one custody event")

    time_values = _array(
        root["trusted_time_proofs"], "trusted_time_proofs",
        minimum=1, maximum=4096,
    )
    time_proofs = tuple(
        _parse_time_proof(item, index)
        for index, item in enumerate(time_values)
    )
    time_proof_digests = [item.proof_sha256 for item in time_proofs]
    if len(set(time_proof_digests)) != len(time_proof_digests):
        raise ValueError("trusted_time_proofs contain duplicate proof digests")
    time_event_keys = [(item.authority_id, item.event_id) for item in time_proofs]
    if len(set(time_event_keys)) != len(time_event_keys):
        raise ValueError("trusted_time_proofs contain duplicate authority/event identities")
    time_by_digest = {item.proof_sha256: item for item in time_proofs}
    for event in custody_events:
        proof = time_by_digest.get(event.timestamp_proof_sha256)
        if proof is None:
            raise ValueError("custody event timestamp proof is not declared")
        if proof.event_id != event.event_id:
            raise ValueError("custody event ID must match its referenced time-proof event ID")
        if proof.event_at_utc != event.received_at_utc:
            raise ValueError("custody received_at_utc must match its referenced time proof")

    signer_subjects = {item.subject_id for item in signatures}
    custodian_subjects = {item.custodian_subject_id for item in custody_events}
    if signer_subjects.intersection(custodian_subjects):
        raise ValueError("signer and custodian claims must be separate")
    time_authorities = {item.authority_id for item in time_proofs}
    if time_authorities.intersection(signer_subjects | custodian_subjects):
        raise ValueError("trusted time authority IDs must be distinct from signers and custodians")

    source_ids = {item.source_id for item in artifacts}
    if source_ids.intersection(signer_subjects | custodian_subjects | time_authorities):
        raise ValueError(
            "artifact source IDs must be distinct from signers, custodians, "
            "and trusted time authorities"
        )

    ledger = _parse_ledger_anchor(root["ledger_anchor"])
    # A ledger is a separate trust participant, not merely another label in
    # the manifest. Reject aliases with the artifact source, any signer,
    # any custodian, or any trusted-time authority before exposing the
    # explicitly unverified parsed object.
    ledger_participants = (
        source_ids | signer_subjects | custodian_subjects | time_authorities
    )
    if ledger.ledger_id in ledger_participants:
        raise ValueError(
            "ledger ID must be distinct from artifact sources, signers, "
            "custodians, and trusted time authorities"
        )
    return UnverifiedPhysicalEvidenceManifest(
        target=target,
        artifacts=artifacts,
        signatures=signatures,
        custody_events=custody_events,
        trusted_time_proofs=time_proofs,
        ledger_anchor=ledger,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
    )
