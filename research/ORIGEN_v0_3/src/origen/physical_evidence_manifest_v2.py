"""Modality-aware V2 structural parser for Chispazo physical-evidence manifests.

V1 remains CLASSIC-only and unchanged. V2 separates the 15:00 De las Tres
workflow from the 21:00 Clásico workflow. This parser validates declarations
only; it does not hash original objects, verify signatures/TSA tokens, prove
custody, or authenticate the source.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .physical_evidence_manifest_v1 import (
    MAX_PHYSICAL_MANIFEST_BYTES,
    MAX_PHYSICAL_MANIFEST_JSON_DEPTH,
    REQUIRED_ARTIFACT_TYPES as V1_REQUIRED_ARTIFACT_TYPES,
    _ACTA_REQUIRED_ROLES,
    _REQUIRED_ROLES_BY_ARTIFACT,
    _SIGNED_ARTIFACT_TYPES,
    _WEIGHING_STRIP_REQUIRED_ROLES,
    _array,
    _object,
    _parse_artifact,
    _parse_custody_event,
    _parse_ledger_anchor,
    _parse_signature,
    _parse_time_proof,
    _validate_json_nesting_depth,
    _unique_object,
    _reject_json_constant,
    _reject_json_float,
    _parse_json_integer,
)

SCHEMA_VERSION = "origen.physical-evidence-manifest.v2"
_CHISPAZO_LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")
_MODALITY_CLOSE_HOUR = {"DE_LAS_TRES": 15, "CLASSIC": 21}
_NIGHTLY_ONLY_ARTIFACTS = frozenset({
    "MJF-TRANSACTION-FILE",
    "MJF-SIGNATURE-PRINTED-FORM",
})
_REQUIRED_ARTIFACT_TYPES = frozenset(V1_REQUIRED_ARTIFACT_TYPES - _NIGHTLY_ONLY_ARTIFACTS)
_ROOT_FIELDS = {
    "schema_version", "target", "artifacts", "signatures",
    "custody_events", "trusted_time_proofs", "ledger_anchor",
}


@dataclass(frozen=True, slots=True)
class PhysicalManifestTargetV2:
    modality: str
    contest_id: str
    draw_date_local: str
    sales_close_at_utc: str
    draw_event_at_utc: str


@dataclass(frozen=True, slots=True)
class UnverifiedPhysicalEvidenceManifestV2:
    """Parsed structural claims only; never an authenticated evidence receipt."""

    target: PhysicalManifestTargetV2
    artifacts: tuple
    signatures: tuple
    custody_events: tuple
    trusted_time_proofs: tuple
    ledger_anchor: object
    raw_sha256: str


def _parse_target_v2(value: object) -> PhysicalManifestTargetV2:
    item = _object(
        value,
        {
            "modality", "contest_id", "draw_date_local",
            "sales_close_at_utc", "draw_event_at_utc",
        },
        "target",
    )
    modality = item["modality"]
    if type(modality) is not str or modality not in _MODALITY_CLOSE_HOUR:
        raise ValueError("target.modality must be DE_LAS_TRES or CLASSIC")
    contest_id = item["contest_id"]
    if type(contest_id) is not str or not contest_id.isascii() or not contest_id.isdecimal() or contest_id.startswith("0") or len(contest_id) > 12:
        raise ValueError("target.contest_id must be a canonical positive decimal contest ID")
    draw_date = item["draw_date_local"]
    if type(draw_date) is not str or len(draw_date) != 10:
        raise ValueError("target.draw_date_local must use YYYY-MM-DD")
    try:
        parsed_date = date.fromisoformat(draw_date)
    except ValueError as exc:
        raise ValueError("target.draw_date_local is not a valid calendar date") from exc
    if parsed_date.isoformat() != draw_date:
        raise ValueError("target.draw_date_local must be canonical YYYY-MM-DD")

    close_raw = item["sales_close_at_utc"]
    event_raw = item["draw_event_at_utc"]
    from .physical_evidence_manifest_v1 import _timestamp
    close_text = _timestamp(close_raw, "target.sales_close_at_utc")
    event_text = _timestamp(event_raw, "target.draw_event_at_utc")
    close = datetime.fromisoformat(close_text[:-1] + "+00:00")
    event = datetime.fromisoformat(event_text[:-1] + "+00:00")
    local_close = close.astimezone(_CHISPAZO_LOCAL_TIMEZONE)
    local_event = event.astimezone(_CHISPAZO_LOCAL_TIMEZONE)
    expected_hour = _MODALITY_CLOSE_HOUR[modality]
    if (local_close.hour, local_close.minute, local_close.second, local_close.microsecond) != (expected_hour, 0, 0, 0):
        raise ValueError(
            f"{modality} sales_close_at_utc must resolve to {expected_hour:02d}:00 "
            "America/Mexico_City"
        )
    if local_close.date() != parsed_date:
        raise ValueError("target.draw_date_local does not match the Mexico City sales-close date")
    if event < close:
        raise ValueError("target.draw_event_at_utc cannot precede the automatic sales close")
    if local_event.date() != parsed_date:
        raise ValueError("target.draw_event_at_utc must resolve to the target Mexico City draw date")
    return PhysicalManifestTargetV2(
        modality=modality,
        contest_id=contest_id,
        draw_date_local=draw_date,
        sales_close_at_utc=close_text,
        draw_event_at_utc=event_text,
    )


def parse_unverified_physical_manifest_v2(raw: bytes) -> UnverifiedPhysicalEvidenceManifestV2:
    """Parse bounded canonical V2 JSON while retaining every claim as unverified."""
    if type(raw) is not bytes:
        raise TypeError("physical manifest input must be exact bytes")
    if not raw or len(raw) > MAX_PHYSICAL_MANIFEST_BYTES:
        raise ValueError(
            f"physical manifest must contain 1..{MAX_PHYSICAL_MANIFEST_BYTES} bytes"
        )
    _validate_json_nesting_depth(raw)
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
            parse_int=_parse_json_integer,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("physical manifest is not valid bounded UTF-8 JSON") from exc
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    if raw != canonical:
        raise ValueError("physical manifest JSON must use canonical UTF-8 encoding")
    root = _object(payload, _ROOT_FIELDS, "manifest")
    if root["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported physical manifest schema_version")

    target = _parse_target_v2(root["target"])
    expected_types = set(_REQUIRED_ARTIFACT_TYPES)
    if target.modality == "CLASSIC":
        expected_types.update(_NIGHTLY_ONLY_ARTIFACTS)
    artifact_values = _array(
        root["artifacts"], "artifacts",
        minimum=0, maximum=len(V1_REQUIRED_ARTIFACT_TYPES),
    )
    artifacts = tuple(
        _parse_artifact(item, index, target.contest_id)
        for index, item in enumerate(artifact_values)
    )
    artifact_types = [item.artifact_type for item in artifacts]
    if len(set(artifact_types)) != len(artifact_types):
        raise ValueError("artifacts contain duplicate artifact types")
    if set(artifact_types) != expected_types:
        missing = sorted(expected_types - set(artifact_types))
        unexpected = sorted(set(artifact_types) - expected_types)
        raise ValueError(
            f"artifacts do not match {target.modality} requirements; "
            f"missing={missing}, unexpected={unexpected}"
        )
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

    signatures_by_artifact: dict[str, list] = {}
    for claim in signatures:
        signatures_by_artifact.setdefault(claim.artifact_sha256, []).append(claim)
    artifact_by_type = {item.artifact_type: item for item in artifacts}
    signed_types = set(_SIGNED_ARTIFACT_TYPES)
    if target.modality == "DE_LAS_TRES":
        signed_types.difference_update(_NIGHTLY_ONLY_ARTIFACTS)
    for artifact_type in signed_types:
        digest = artifact_by_type[artifact_type].sha256
        if not signatures_by_artifact.get(digest):
            raise ValueError(f"{artifact_type} must have at least one declared signature")

    acta_digest = artifact_by_type["DRAW-ACTA"].sha256
    acta_roles = {item.role for item in signatures_by_artifact.get(acta_digest, [])}
    if not _ACTA_REQUIRED_ROLES.issubset(acta_roles):
        raise ValueError("DRAW-ACTA signatures are missing policy-2 or SEGOB roles")
    required_roles_by_artifact = {
        key: roles for key, roles in _REQUIRED_ROLES_BY_ARTIFACT.items()
        if key in expected_types
    }
    for artifact_type, required_roles in required_roles_by_artifact.items():
        digest = artifact_by_type[artifact_type].sha256
        declared_roles = {item.role for item in signatures_by_artifact.get(digest, [])}
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
        minimum=len(expected_types), maximum=4096,
    )
    custody_events = tuple(
        _parse_custody_event(item, index, artifact_digests)
        for index, item in enumerate(custody_values)
    )
    event_ids = [item.event_id for item in custody_events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("custody_events contain duplicate event IDs")
    receipt_digests = [item.receipt_sha256 for item in custody_events]
    if len(set(receipt_digests)) != len(receipt_digests):
        raise ValueError("custody_events contain duplicate receipt digests")
    if {item.artifact_sha256 for item in custody_events} != artifact_digests:
        raise ValueError("every required artifact must have at least one custody event")

    time_values = _array(
        root["trusted_time_proofs"], "trusted_time_proofs",
        minimum=1, maximum=4096,
    )
    time_proofs = tuple(
        _parse_time_proof(item, index) for index, item in enumerate(time_values)
    )
    proof_digests = [item.proof_sha256 for item in time_proofs]
    if len(set(proof_digests)) != len(proof_digests):
        raise ValueError("trusted_time_proofs contain duplicate proof digests")
    time_keys = [(item.authority_id, item.event_id) for item in time_proofs]
    if len(set(time_keys)) != len(time_keys):
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
            "and trusted-time authorities"
        )

    ledger = _parse_ledger_anchor(root["ledger_anchor"])
    return UnverifiedPhysicalEvidenceManifestV2(
        target=target,
        artifacts=artifacts,
        signatures=signatures,
        custody_events=custody_events,
        trusted_time_proofs=time_proofs,
        ledger_anchor=ledger,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
    )
