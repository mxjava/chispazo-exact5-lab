"""Non-circular RFC 3161 binding for an exact Classic custody record.

This diagnostic timestamps the canonical custody-record bytes, not the detached
custodian signature. The distinction is deliberate: the current V3 custody
signature payload includes the root receipt digest, while the root-signed
receipt carries the timestamp-proof digest. Timestamping that signature and
including the token in that same receipt would create a circular dependency.

A successful result therefore proves only that the exact record bytes fall
inside a caller-pinned TSA time interval relative to the record's claimed
receipt and Classic close. It does NOT prove that the detached custodian
signature itself existed before close, nor does it authenticate the TSA root,
clock, revocation state, or institutional authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .custody_receipt_verifier_v3 import (
    ReceiptCustodyChainInspectionV3,
    verify_receipt_and_custody_v3,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_verifier_v2 import _utc_instant
from .rfc3161_tsa_verifier_v1 import (
    RFC3161Inspection,
    verify_rfc3161_timestamp_token,
)
from .trust_receipt_v1 import parse_unverified_receipt

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\\Z")

CUSTODY_RECORD_TIMESTAMP_BLOCKERS = (
    "DETACHED_CUSTODY_SIGNATURE_ITSELF_NOT_TIME_STAMPED",
    "TSA_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "TSA_CERTIFICATE_REVOCATION_STATUS_NOT_CHECKED",
    "TSA_POLICY_OID_NOT_AUTHORIZED_BY_AUTHENTICATED_DEPLOYMENT_POLICY",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
)


@dataclass(frozen=True, slots=True)
class CustodyRecordTimestampInspectionV1:
    """Diagnostic record-time result; not an authenticated provenance capability."""

    custody_chain: ReceiptCustodyChainInspectionV3
    timestamp: RFC3161Inspection
    timestamp_proof_sha256: str
    timestamp_event_id: str
    accuracy_lower_bound_utc: datetime
    accuracy_upper_bound_utc: datetime
    record_existence_interval_preclose_verified: bool
    timestamp_binding_status: str
    detached_signature_timestamped: bool
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _record_utc(value: object, field: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError(f"{field} must be canonical UTC RFC3339 ending in Z")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid UTC timestamp") from exc
    return result


def custody_record_timestamp_event_id(record_sha256: str) -> str:
    """Return the deterministic receipt event ID for one exact custody record."""
    if type(record_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", record_sha256):
        raise ValueError("record_sha256 must be lowercase SHA-256 hex")
    return f"custody-record-sha256:{record_sha256}"


def verify_receipt_custody_record_timestamp_v1(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    custody_record_bytes: bytes,
    portfolio_bytes: bytes,
    custody_signature_bytes: bytes,
    custodian_key_id: str,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
    timestamp_token_der: bytes,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_tsa_authority_id: str,
    expected_nonce: int,
) -> CustodyRecordTimestampInspectionV1:
    """Verify the V3 receipt/custody chain and a root-receipt-bound RFC 3161 token.

    The timestamp token's message imprint is recomputed over the exact canonical
    custody-record bytes. Its token digest, deterministic event ID, authority ID,
    and genTime must each match one proof claim in the original root-signed
    receipt. The full RFC 3161 accuracy interval must be after the claimed
    custodian receipt time and strictly before the declared Classic close.
    """
    if type(expected_tsa_authority_id) is not str or not _IDENTIFIER.fullmatch(
        expected_tsa_authority_id
    ):
        raise ValueError("expected_tsa_authority_id must be a canonical identifier")
    if type(expected_nonce) is not int or expected_nonce < 1:
        raise ValueError("expected_nonce must be an exact positive integer")

    # Snapshot an untrusted caller tzinfo exactly once, then pass the stable UTC
    # instant to both verifiers. Their subsequent UTC normalization is stable.
    verified_at = _utc_instant(verification_time, "verification_time")
    custody_chain = verify_receipt_and_custody_v3(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        custody_record_bytes,
        portfolio_bytes,
        custody_signature_bytes,
        custodian_key_id,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    timestamp = verify_rfc3161_timestamp_token(
        timestamp_token_der,
        custody_record_bytes,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        verification_time=verified_at,
        expected_nonce=expected_nonce,
    )

    receipt = parse_unverified_receipt(original_receipt_bytes)
    event_id = custody_record_timestamp_event_id(custody_chain.custody_record_sha256)
    matching_proofs = [
        proof for proof in receipt.trusted_time_proofs
        if proof.proof_sha256 == timestamp.token_sha256
    ]
    if len(matching_proofs) != 1:
        raise ValueError(
            "RFC 3161 token digest must match exactly one root-receipt time-proof claim"
        )
    proof = matching_proofs[0]
    if proof.authority_id != expected_tsa_authority_id:
        raise ValueError("RFC 3161 proof authority does not match expected TSA authority ID")
    if proof.event_id != event_id:
        raise ValueError("RFC 3161 proof event ID does not bind the exact custody-record digest")
    proof_time = _record_utc(proof.event_at_utc, "trusted_time_proof.event_at_utc")
    if proof_time != timestamp.gen_time_utc:
        raise ValueError("RFC 3161 genTime does not match the root-receipt proof event time")

    # The custody verifier has already validated canonical JSON bytes and the
    # record schema. Decode those exact bytes only to read its two chronology
    # anchors; do not reserialize or hash a reconstructed object.
    record = json.loads(custody_record_bytes[:-1].decode("utf-8"))
    received_at = _record_utc(record["received_at_utc"], "received_at_utc")
    close_at = _record_utc(record["official_draw_close_at_utc"], "official_draw_close_at_utc")
    if type(timestamp.accuracy_microseconds) is not int:
        raise ValueError(
            "RFC 3161 accuracy is absent; a bounded pre-close interval cannot be established"
        )
    if timestamp.accuracy_microseconds < 0:
        raise ValueError("RFC 3161 accuracy must be non-negative")

    accuracy = timedelta(microseconds=timestamp.accuracy_microseconds)
    lower_bound = timestamp.gen_time_utc - accuracy
    upper_bound = timestamp.gen_time_utc + accuracy
    if lower_bound < received_at:
        raise ValueError(
            "RFC 3161 lower accuracy bound precedes the custodian received_at_utc claim"
        )
    if upper_bound >= close_at:
        raise ValueError(
            "RFC 3161 upper accuracy bound must be strictly before the Classic draw close"
        )

    blockers = tuple(dict.fromkeys(
        tuple(custody_chain.remaining_blockers) + CUSTODY_RECORD_TIMESTAMP_BLOCKERS
    ))
    return CustodyRecordTimestampInspectionV1(
        custody_chain=custody_chain,
        timestamp=timestamp,
        timestamp_proof_sha256=hashlib.sha256(timestamp_token_der).hexdigest(),
        timestamp_event_id=event_id,
        accuracy_lower_bound_utc=lower_bound,
        accuracy_upper_bound_utc=upper_bound,
        record_existence_interval_preclose_verified=True,
        timestamp_binding_status=(
            "EXACT_CUSTODY_RECORD_ONLY_RELATIVE_TO_CALLER_SUPPLIED_TSA_ROOT"
        ),
        detached_signature_timestamped=False,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
