"""Non-circular RFC 3161 timestamping of the V3 detached custody signature.

The V3 custody signature already binds the exact receipt digest and custody
record. Timestamping those exact signature bytes in a detached RFC 3161
sidecar avoids putting a timestamp-token digest into the receipt that the
signature itself signs. No receipt schema or V3 signature payload is changed.
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

_SIGNATURE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

CUSTODY_SIGNATURE_TIMESTAMP_BLOCKERS = (
    "TSA_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "TSA_CERTIFICATE_REVOCATION_STATUS_NOT_CHECKED",
    "TSA_POLICY_OID_NOT_AUTHORIZED_BY_AUTHENTICATED_DEPLOYMENT_POLICY",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "DETACHED_TIMESTAMP_SIDECAR_NOT_ANCHORED_IN_EXTERNAL_WITNESSED_LEDGER",
)


@dataclass(frozen=True, slots=True)
class CustodySignatureTimestampInspectionV1:
    """Diagnostic result; never an authenticated provenance capability."""

    custody_chain: ReceiptCustodyChainInspectionV3
    timestamp: RFC3161Inspection
    signature_sha256: str
    timestamp_event_id: str
    accuracy_lower_bound_utc: datetime
    accuracy_upper_bound_utc: datetime
    detached_signature_timestamped: bool
    signature_existence_interval_preclose_verified: bool
    timestamp_proof_is_detached_sidecar: bool
    timestamp_binding_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def custody_signature_timestamp_event_id(signature_sha256: str) -> str:
    """Return a deterministic event ID for one exact detached signature."""
    if type(signature_sha256) is not str or not _SIGNATURE_SHA256.fullmatch(
        signature_sha256
    ):
        raise ValueError("signature_sha256 must be lowercase SHA-256 hex")
    return f"custody-signature-sha256:{signature_sha256}"


def _record_utc(value: object, field: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError(f"{field} must be canonical UTC RFC3339 ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid UTC timestamp") from exc


def verify_receipt_custody_signature_timestamp_v1(
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
    expected_nonce: int,
) -> CustodySignatureTimestampInspectionV1:
    """Verify the V3 chain and timestamp the exact detached signature bytes.

    Verification order is intentional:
      1. Verify the root receipt, signed policy, exact custody record, and
         detached custodian signature using the existing V3 verifier.
      2. Verify the RFC 3161 message imprint over the exact 64 signature bytes.
      3. Require the full TSA accuracy interval to start no earlier than the
         record's claimed receipt time and end strictly before Classic 21:00.

    The timestamp token is a detached sidecar and is NOT inserted into the
    root-signed receipt. The V3 signature already includes the receipt digest;
    timestamping that signature and then adding the token digest to the same
    receipt would create a cycle. The sidecar is transitively bound to the
    receipt and record because V3 verifies the signature over both exact digests.

    Root pins, TSA root, nonce, anti-rollback floor and clock are still caller
    inputs. The result therefore always remains BLOCKED_PROVENANCE.
    """
    if type(expected_nonce) is not int or expected_nonce < 1:
        raise ValueError("expected_nonce must be an exact positive integer")

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
    signature_sha256 = hashlib.sha256(custody_signature_bytes).hexdigest()
    if signature_sha256 != custody_chain.custody_signature_sha256:
        raise RuntimeError("V3 custody verifier returned a different signature digest")

    timestamp = verify_rfc3161_timestamp_token(
        timestamp_token_der,
        custody_signature_bytes,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        verification_time=verified_at,
        expected_nonce=expected_nonce,
    )

    # V3 has already validated canonical record bytes, unique JSON keys, schema,
    # CLASSIC modality, target and close. Read only the two chronology anchors;
    # never reserialize or hash a reconstructed record.
    record = json.loads(custody_record_bytes[:-1].decode("utf-8"))
    received_at = _record_utc(record["received_at_utc"], "received_at_utc")
    close_at = _record_utc(
        record["official_draw_close_at_utc"], "official_draw_close_at_utc"
    )
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

    policy_window = custody_chain.receipt_policy
    if (
        lower_bound < policy_window.policy_not_before_utc
        or upper_bound >= policy_window.policy_expires_at_utc
    ):
        raise ValueError(
            "RFC 3161 signature accuracy interval falls outside signed V3 policy validity interval"
        )
    if (
        lower_bound < custody_chain.custodian_key_valid_from_utc
        or upper_bound > custody_chain.custodian_key_valid_until_utc
    ):
        raise ValueError(
            "RFC 3161 signature accuracy interval falls outside custodian key validity interval"
        )

    blockers = tuple(dict.fromkeys(
        tuple(custody_chain.remaining_blockers)
        + CUSTODY_SIGNATURE_TIMESTAMP_BLOCKERS
    ))
    return CustodySignatureTimestampInspectionV1(
        custody_chain=custody_chain,
        timestamp=timestamp,
        signature_sha256=signature_sha256,
        timestamp_event_id=custody_signature_timestamp_event_id(signature_sha256),
        accuracy_lower_bound_utc=lower_bound,
        accuracy_upper_bound_utc=upper_bound,
        detached_signature_timestamped=True,
        signature_existence_interval_preclose_verified=True,
        timestamp_proof_is_detached_sidecar=True,
        timestamp_binding_status=(
            "EXACT_V3_DETACHED_SIGNATURE_BYTES_RELATIVE_TO_CALLER_SUPPLIED_TSA_ROOT"
        ),
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
