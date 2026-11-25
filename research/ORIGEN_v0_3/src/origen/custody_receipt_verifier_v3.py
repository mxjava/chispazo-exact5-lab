"""Fail-closed V3 verifier for a detached, signed Classic custody receipt.

The verifier binds one exact custody-record byte string and one exact portfolio
to a custodian claim in the original signed trust receipt. The custodian key,
role, and artifact type must be authorized by the same V3 policy envelope
that authenticates the receipt root attester. This proves only cryptographic
consistency relative to caller-supplied trust inputs; provenance stays blocked.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .custody import (
    MAX_CUSTODY_RECORD_BYTES,
    canonical_json_bytes,
    verify_seal_record,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_verifier_v2 import (
    CLASSIC_PHYSICAL_POLICY_DOMAIN,
    _utc_instant,
)
from .receipt_policy_integration_v3 import (
    ReceiptPolicyInspectionV3,
    verify_receipt_attestation_with_policy_v3,
)
from .trust_policy_envelope_v3 import (
    VerifiedTrustPolicyV3,
    verify_signed_trust_policy_v3,
)
from .trust_receipt_v1 import parse_unverified_receipt
from .trust_verifier_v1 import TrustedIssuerKey

CUSTODY_SIGNATURE_DOMAIN = "origen.custody-receipt-signature.v3"
CUSTODY_SIGNER_ROLE = "external-custodian"
CUSTODY_ARTIFACT_TYPE = "EXACT5-CUSTODY-RECORD"
CUSTODY_ROLE_STATUS = "SIGNED_POLICY_MATCH_ONLY_NOT_INSTITUTIONALLY_AUTHENTICATED"

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_UTC_Z = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z\Z"
)

CUSTODY_REMAINING_BLOCKERS = (
    "CUSTODIAN_LEGAL_IDENTITY_AND_INSTITUTIONAL_DELEGATION_NOT_AUTHENTICATED",
    "CUSTODIAN_INDEPENDENCE_NOT_PROVEN_BY_SEPARATE_ADMINISTRATIVE_CONTROL",
    "CUSTODY_RECORD_ORIGIN_STORAGE_AND_CLOCK_NOT_AUTHENTICATED",
    "CUSTODY_SIGNATURE_TRUSTED_TIME_NOT_VERIFIED",
    "DEPLOYMENT_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "ANTI_ROLLBACK_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class ReceiptCustodyChainInspectionV3:
    """Diagnostic result; not a capability or eligibility decision."""

    receipt_policy: ReceiptPolicyInspectionV3
    receipt_sha256: str
    custody_record_sha256: str
    custody_record_internal_sha256: str
    portfolio_sha256: str
    custody_signature_sha256: str
    custodian_id: str
    custodian_key_id: str
    target_contest_id: int
    covered_generator_id: str
    policy_envelope_sha256: str
    policy_sequence: int
    verification_time_utc: datetime
    custody_signature_verified: bool
    role_authorization_status: str
    trust_anchor_source: str
    anti_rollback_source: str
    verification_clock_source: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("custody record contains a duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"custody record rejects non-standard JSON constant {value}")


def _reject_float(value: str) -> None:
    raise ValueError("custody record does not permit floating-point JSON numbers")


def _validate_json_depth(raw: bytes, maximum: int = 16) -> None:
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
            if depth > maximum:
                raise ValueError(f"custody record exceeds maximum JSON depth {maximum}")
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


def _parse_exact_custody_record(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes:
        raise TypeError("custody_record_bytes must be exact bytes")
    if not 1 <= len(raw) <= MAX_CUSTODY_RECORD_BYTES:
        raise ValueError(
            f"custody_record_bytes must contain 1..{MAX_CUSTODY_RECORD_BYTES} bytes"
        )
    if not raw.endswith(b"\n"):
        raise ValueError("custody record must end with exactly one LF")
    if raw.endswith(b"\n\n") or b"\r" in raw:
        raise ValueError("custody record must use one canonical LF terminator")
    _validate_json_depth(raw)
    try:
        document = json.loads(
            raw[:-1].decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("custody record must be bounded valid UTF-8 JSON") from exc
    if type(document) is not dict:
        raise ValueError("custody record JSON root must be an exact object")
    if raw != canonical_json_bytes(document) + b"\n":
        raise ValueError("custody record must use canonical UTF-8 JSON bytes")
    for field in (
        "generated_at_utc",
        "received_at_utc",
        "official_draw_close_at_utc",
    ):
        value = document.get(field)
        if type(value) is not str or not _UTC_Z.fullmatch(value):
            raise ValueError(
                f"{field} must use canonical UTC RFC3339 with seconds and Z"
            )
    if type(document.get("source_commit")) is not str or not _SHA40.fullmatch(
        document["source_commit"]
    ):
        raise ValueError("source_commit must be a full lowercase Git SHA-1")
    return document


def canonical_custody_signature_payload(
    custody_record_bytes: bytes,
    receipt_sha256: str,
    custodian_key_id: str,
) -> bytes:
    """Build the domain-separated bytes signed by the detached custodian key.

    The receipt digest binds the custody record to one exact original receipt.
    The record digest binds all custody claims, including its internal chain
    link, generator/custodian IDs, target and pre-close chronology.
    """
    if type(custody_record_bytes) is not bytes:
        raise TypeError("custody_record_bytes must be exact bytes")
    if type(receipt_sha256) is not str or not _SHA256.fullmatch(receipt_sha256):
        raise ValueError("receipt_sha256 must be lowercase SHA-256")
    if type(custodian_key_id) is not str or not _IDENTIFIER.fullmatch(custodian_key_id):
        raise ValueError("custodian_key_id must be a canonical identifier")
    record = _parse_exact_custody_record(custody_record_bytes)
    document = {
        "domain": CUSTODY_SIGNATURE_DOMAIN,
        "record_sha256": hashlib.sha256(custody_record_bytes).hexdigest(),
        "record_internal_sha256": record.get("record_sha256"),
        "receipt_sha256": receipt_sha256,
        "custodian_id": record.get("custodian_id"),
        "custodian_key_id": custodian_key_id,
        "role": CUSTODY_SIGNER_ROLE,
        "artifact_type": CUSTODY_ARTIFACT_TYPE,
        "target_contest_id": record.get("target_contest_id"),
        "portfolio_sha256": record.get("portfolio_sha256"),
    }
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def verify_receipt_and_custody_v3(
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
) -> ReceiptCustodyChainInspectionV3:
    """Verify V3 receipt attestation plus one exact signed custody record.

    The caller's time is normalized once before either verifier is invoked.
    Root pin, root key ID, sequence floor and clock are still caller supplied.
    The receipt's other custodian claims, nested physical signatures, RFC3161,
    ledger consistency/witnesses, and institutional identity remain blockers.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")
    if type(portfolio_bytes) is not bytes:
        raise TypeError("portfolio_bytes must be exact bytes")
    if type(custody_signature_bytes) is not bytes or len(custody_signature_bytes) != 64:
        raise ValueError("custody_signature_bytes must be exactly 64 immutable bytes")
    if type(custodian_key_id) is not str or not _IDENTIFIER.fullmatch(custodian_key_id):
        raise ValueError("custodian_key_id must be a canonical identifier")
    if type(pinned_root_public_key_bytes) is not bytes or len(pinned_root_public_key_bytes) != 32:
        raise ValueError("pinned_root_public_key_bytes must be exactly 32 immutable bytes")

    verified_at = _utc_instant(verification_time, "verification_time")
    receipt_policy = verify_receipt_attestation_with_policy_v3(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    if type(receipt_policy) is not ReceiptPolicyInspectionV3:
        raise TypeError("receipt policy verifier returned an unexpected result type")
    if receipt_policy.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("receipt policy verifier did not preserve BLOCKED_PROVENANCE")

    policy: VerifiedTrustPolicyV3 = verify_signed_trust_policy_v3(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    if type(policy) is not VerifiedTrustPolicyV3:
        raise TypeError("V3 policy verifier returned an unexpected result type")
    if (
        policy.envelope_sha256 != receipt_policy.policy_envelope_sha256
        or policy.policy_sequence != receipt_policy.policy_sequence
        or policy.policy_domain != receipt_policy.policy_domain
    ):
        raise RuntimeError("receipt and custody verifiers consumed different V3 policy identities")

    receipt = parse_unverified_receipt(original_receipt_bytes)
    record = _parse_exact_custody_record(custody_record_bytes)
    valid, reason = verify_seal_record(record, portfolio_bytes)
    if not valid:
        raise ValueError(f"custody seal record verification failed: {reason}")

    receipt_sha256 = hashlib.sha256(original_receipt_bytes).hexdigest()
    custody_record_sha256 = hashlib.sha256(custody_record_bytes).hexdigest()
    portfolio_sha256 = hashlib.sha256(portfolio_bytes).hexdigest()

    if record["modality"] != "CLASSIC":
        raise ValueError("custody record is not CLASSIC")
    if str(record["target_contest_id"]) != receipt.target.contest_id:
        raise ValueError("custody record target contest does not match original receipt")
    if record["official_draw_close_at_utc"] != receipt.target.draw_close_at_utc:
        raise ValueError("custody record Classic close does not match original receipt")
    if record["candidate_spec_sha256"] != receipt.commitments.candidate_sha256:
        raise ValueError("custody candidate digest does not match receipt commitment")
    if record["environment_manifest_sha256"] != receipt.commitments.environment_sha256:
        raise ValueError("custody environment digest does not match receipt commitment")
    matching_seals = [
        seal for seal in receipt.output_seals
        if seal.portfolio_sha256 == portfolio_sha256
        and seal.generator_id == record["generator_id"]
    ]
    if len(matching_seals) != 1:
        raise ValueError(
            "custody record must bind exactly one receipt output seal by portfolio and generator"
        )

    if type(receipt.custodians) is not tuple:
        raise ValueError("receipt custodians must be an exact tuple")
    matching_claims = [
        claim for claim in receipt.custodians
        if claim.subject_id == record["custodian_id"]
    ]
    if len(matching_claims) != 1:
        raise ValueError("custody record must match exactly one receipt custodian claim")
    claim = matching_claims[0]
    if claim.role != CUSTODY_SIGNER_ROLE:
        raise ValueError("receipt custodian claim has an unauthorized custody role")
    if claim.receipt_sha256 != custody_record_sha256:
        raise ValueError("receipt custodian claim does not bind exact original custody-record bytes")

    if record["custodian_id"] == receipt.attestation.issuer_id:
        raise ValueError("custodian and receipt root attester must be distinct")
    if custodian_key_id == expected_root_key_id:
        raise ValueError("custodian key ID must be distinct from pinned policy root key ID")
    if custodian_key_id == receipt.attestation.key_id or custodian_key_id in {
        signer.key_id for signer in receipt.signers
    }:
        raise ValueError("custodian key ID must be distinct from receipt and physical signer key IDs")

    keys = policy.policy.issuer_keys
    if type(keys) is not tuple:
        raise ValueError("verified V3 issuer keys must be an exact tuple")
    matches = [
        key for key in keys
        if type(key) is TrustedIssuerKey
        and key.issuer_id == record["custodian_id"]
        and key.key_id == custodian_key_id
    ]
    if len(matches) != 1:
        raise ValueError("custodian issuer/key is unknown or ambiguous in verified V3 policy")
    key = matches[0]
    if key.revoked:
        raise ValueError("custodian key is revoked")
    if not key.valid_from_utc <= verified_at <= key.valid_until_utc:
        raise ValueError("custodian key is outside verified V3 policy validity")

    authorized = False
    if type(policy.key_authorizations) is not tuple:
        raise ValueError("verified V3 key authorizations must be an exact tuple")
    for item in policy.key_authorizations:
        if (
            type(item) is tuple
            and len(item) == 4
            and item[0] == record["custodian_id"]
            and item[1] == custodian_key_id
            and item[2] == CUSTODY_SIGNER_ROLE
            and type(item[3]) is tuple
            and CUSTODY_ARTIFACT_TYPE in item[3]
        ):
            authorized = True
            break
    if not authorized:
        raise ValueError(
            "custodian issuer/key is not authorized for external-custodian "
            "and EXACT5-CUSTODY-RECORD by the signed V3 policy"
        )

    payload = canonical_custody_signature_payload(
        custody_record_bytes,
        receipt_sha256,
        custodian_key_id,
    )
    try:
        Ed25519PublicKey.from_public_bytes(key.public_key_bytes).verify(
            custody_signature_bytes, payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("detached custody Ed25519 signature verification failed") from exc

    blockers = tuple(receipt_policy.remaining_blockers) + CUSTODY_REMAINING_BLOCKERS
    return ReceiptCustodyChainInspectionV3(
        receipt_policy=receipt_policy,
        receipt_sha256=receipt_sha256,
        custody_record_sha256=custody_record_sha256,
        custody_record_internal_sha256=record["record_sha256"],
        portfolio_sha256=portfolio_sha256,
        custody_signature_sha256=hashlib.sha256(custody_signature_bytes).hexdigest(),
        custodian_id=record["custodian_id"],
        custodian_key_id=custodian_key_id,
        target_contest_id=record["target_contest_id"],
        covered_generator_id=record["generator_id"],
        policy_envelope_sha256=policy.envelope_sha256,
        policy_sequence=policy.policy_sequence,
        verification_time_utc=verified_at,
        custody_signature_verified=True,
        role_authorization_status=CUSTODY_ROLE_STATUS,
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
