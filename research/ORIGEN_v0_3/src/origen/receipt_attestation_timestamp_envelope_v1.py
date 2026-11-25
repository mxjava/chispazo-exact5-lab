"""Detached, non-circular RFC 3161 proof for the V1 receipt attestation.

The sidecar is an untrusted transport envelope. Its claims are re-derived from
the exact receipt bytes, the Ed25519 signature embedded in that receipt, and a
TSA-signed RFC 3161 token whose message imprint covers those exact signature
bytes. The V1 embedded timestamp_proof_sha256 remains a legacy signed claim;
it is deliberately not used as the token binding because doing so is circular.
Every successful inspection remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .independent_trust_adapter import ProvenanceStatus
from .rfc3161_tsa_verifier_v1 import MAX_TOKEN_BYTES, verify_rfc3161_timestamp_token
from .timestamp_authority_policy_v1 import verify_signed_timestamp_authority_policy
from .trust_policy_rfc3161_integration_v1 import (
    OutputSealTimestampEvidence,
    SignedRootAndOutputSealTimeInspection,
    inspect_signed_root_attestation_chain_with_output_seal_timestamps,
)
from .trust_receipt_v1 import parse_unverified_receipt

SCHEMA_VERSION = "origen.receipt-attestation-timestamp-proof.v1"
MAX_ENVELOPE_BYTES = 6 * 1024 * 1024
MAX_NONCE = (1 << 63) - 1
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class _DetachedEnvelope:
    receipt_sha256: str
    signature_sha256: str
    token_sha256: str
    authority_id: str
    expected_nonce: int
    token_der: bytes


@dataclass(frozen=True, slots=True)
class ReceiptAttestationTimestampInspection:
    receipt_sha256: str
    signature_sha256: str
    token_sha256: str
    legacy_embedded_proof_reference_sha256: str
    authority_id: str
    tsa_policy_oid: str
    gen_time_utc: datetime
    accuracy_microseconds: int
    tsa_certificate_sha256: str
    tsa_root_certificate_sha256: str
    certificate_chain_length: int
    nonce_verified: bool
    binding_status: str
    detached_envelope_sha256: str


@dataclass(frozen=True, slots=True)
class DetachedReceiptTimestampChainInspection:
    root_and_output_seals: SignedRootAndOutputSealTimeInspection
    receipt_attestation_timestamp: ReceiptAttestationTimestampInspection
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("detached receipt timestamp envelope contains a duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"detached receipt timestamp envelope rejects JSON constant {value}")


def _reject_float(value: str) -> None:
    raise ValueError("detached receipt timestamp envelope does not permit floating-point numbers")


def _parse_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        raise ValueError("detached receipt timestamp envelope integer exceeds signed 64-bit range")
    parsed = int(value)
    if not -(1 << 63) <= parsed <= MAX_NONCE:
        raise ValueError("detached receipt timestamp envelope integer exceeds signed 64-bit range")
    return parsed


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be lowercase SHA-256 hexadecimal")
    return value


def _parse_envelope(raw: bytes) -> _DetachedEnvelope:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_ENVELOPE_BYTES:
        raise ValueError(
            f"detached receipt timestamp envelope must be exact bytes within 1..{MAX_ENVELOPE_BYTES}"
        )
    try:
        text = raw.decode("ascii", errors="strict")
        document = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
            parse_int=_parse_integer,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("detached receipt timestamp envelope is not bounded canonical JSON") from exc
    if type(document) is not dict:
        raise ValueError("detached receipt timestamp envelope root must be an object")
    expected_fields = {
        "schema_version",
        "receipt_sha256",
        "signature_sha256",
        "token_sha256",
        "authority_id",
        "expected_nonce",
        "token_der_b64",
    }
    if set(document) != expected_fields:
        raise ValueError("detached receipt timestamp envelope fields do not match the exact V1 schema")
    canonical = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    if raw != canonical:
        raise ValueError("detached receipt timestamp envelope must use canonical ASCII JSON")
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported detached receipt timestamp envelope schema_version")
    receipt_digest = _digest(document["receipt_sha256"], "receipt_sha256")
    signature_digest = _digest(document["signature_sha256"], "signature_sha256")
    token_digest = _digest(document["token_sha256"], "token_sha256")
    authority_id = document["authority_id"]
    if type(authority_id) is not str or not _ID.fullmatch(authority_id):
        raise ValueError("authority_id must be a canonical non-empty identifier")
    nonce = document["expected_nonce"]
    if type(nonce) is not int or not 1 <= nonce <= MAX_NONCE:
        raise ValueError("expected_nonce must be an exact positive signed 64-bit integer")
    token_b64 = document["token_der_b64"]
    if type(token_b64) is not str or not token_b64:
        raise ValueError("token_der_b64 must be non-empty canonical base64")
    try:
        token_der = base64.b64decode(token_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("token_der_b64 is invalid base64") from exc
    if base64.b64encode(token_der).decode("ascii") != token_b64:
        raise ValueError("token_der_b64 is not canonical base64")
    if not 1 <= len(token_der) <= MAX_TOKEN_BYTES:
        raise ValueError("detached RFC 3161 token is empty or exceeds the verifier byte limit")
    if hashlib.sha256(token_der).hexdigest() != token_digest:
        raise ValueError("token_sha256 does not match the exact detached token bytes")
    return _DetachedEnvelope(
        receipt_sha256=receipt_digest,
        signature_sha256=signature_digest,
        token_sha256=token_digest,
        authority_id=authority_id,
        expected_nonce=nonce,
        token_der=token_der,
    )


def inspect_signed_root_attestation_chain_with_detached_receipt_timestamp(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
    signed_timestamp_authority_policy_bytes: bytes,
    output_seal_timestamp_evidence: tuple[OutputSealTimestampEvidence, ...],
    pinned_tsa_root_certificate_der: bytes,
    detached_receipt_timestamp_envelope_bytes: bytes,
) -> DetachedReceiptTimestampChainInspection:
    """Verify the root/policy chain, two output seals, and detached receipt timestamp.

    The detached envelope binds the exact original receipt digest and exact
    Ed25519 signature bytes. The RFC 3161 token's signed message imprint must
    cover those signature bytes. No timestamp digest is required inside the
    receipt signature preimage, so the V1 self-reference is avoided without
    dropping or rewriting any signed receipt field.
    """
    envelope = _parse_envelope(detached_receipt_timestamp_envelope_bytes)
    combined = inspect_signed_root_attestation_chain_with_output_seal_timestamps(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
        signed_timestamp_authority_policy_bytes=signed_timestamp_authority_policy_bytes,
        output_seal_timestamp_evidence=output_seal_timestamp_evidence,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
    )
    if combined.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("underlying root/output-seal inspection did not preserve BLOCKED_PROVENANCE")

    receipt = parse_unverified_receipt(original_receipt_bytes)
    receipt_digest = hashlib.sha256(original_receipt_bytes).hexdigest()
    if envelope.receipt_sha256 != receipt_digest:
        raise ValueError("detached envelope receipt_sha256 does not match the exact original receipt bytes")

    try:
        signature_bytes = base64.b64decode(receipt.attestation.signature_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("verified receipt attestation signature is not valid base64") from exc
    if len(signature_bytes) != 64:
        raise ValueError("verified V1 receipt attestation must contain exactly 64 Ed25519 signature bytes")
    signature_digest = hashlib.sha256(signature_bytes).hexdigest()
    if envelope.signature_sha256 != signature_digest:
        raise ValueError("detached envelope signature_sha256 does not match the exact receipt signature bytes")

    root_chain = combined.root_chain
    tsa_policy = verify_signed_timestamp_authority_policy(
        signed_timestamp_authority_policy_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=root_chain.policy_root_key_id,
        expected_trust_policy_envelope_sha256=root_chain.policy_envelope_sha256,
        expected_policy_sequence=root_chain.policy_sequence,
        verification_time=root_chain.verification_time_utc,
    )
    authorities_by_id = {item.authority_id: item for item in tsa_policy.authorities}
    authority = authorities_by_id.get(envelope.authority_id)
    if authority is None:
        raise ValueError("detached receipt timestamp authority is not authorized by the root-signed TSA policy")
    if authority.revoked:
        raise ValueError("detached receipt timestamp authority is revoked by the root-signed TSA policy")
    if not (
        authority.valid_from_utc
        <= root_chain.verification_time_utc
        <= authority.valid_until_utc
    ):
        raise ValueError("detached receipt timestamp authority is outside its signed validity interval")

    tsa_root_digest = hashlib.sha256(pinned_tsa_root_certificate_der).hexdigest()
    if tsa_root_digest != authority.root_certificate_sha256:
        raise ValueError("detached receipt timestamp TSA root does not match the root-signed authority policy")

    timestamp = verify_rfc3161_timestamp_token(
        envelope.token_der,
        signature_bytes,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=authority.root_certificate_sha256,
        verification_time=root_chain.verification_time_utc,
        expected_nonce=envelope.expected_nonce,
    )
    if timestamp.token_sha256 != envelope.token_sha256:
        raise ValueError("verified RFC 3161 token digest changed during verification")
    if timestamp.policy_oid not in authority.policy_oids:
        raise ValueError("detached receipt RFC 3161 policy OID is not authorized for this TSA authority")
    if not (
        authority.valid_from_utc
        <= timestamp.gen_time_utc
        <= authority.valid_until_utc
    ):
        raise ValueError("detached receipt RFC 3161 genTime is outside the TSA authority policy validity interval")

    signed_at = datetime.fromisoformat(receipt.attestation.signed_at_utc[:-1] + "+00:00")
    if timestamp.gen_time_utc != signed_at:
        raise ValueError("detached receipt RFC 3161 genTime does not match signed_at_utc")
    if timestamp.accuracy_microseconds is None:
        raise ValueError("detached receipt RFC 3161 accuracy is absent")
    close_at = datetime.fromisoformat(receipt.target.draw_close_at_utc[:-1] + "+00:00")
    upper_time_bound = timestamp.gen_time_utc + timedelta(
        microseconds=timestamp.accuracy_microseconds
    )
    if upper_time_bound >= close_at:
        raise ValueError("detached receipt RFC 3161 genTime plus accuracy is not strictly before Classic close")

    blockers = tuple(
        item for item in combined.remaining_blockers
        if item != "RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED"
    ) + (
        "RECEIPT_V1_EMBEDDED_TIMESTAMP_REFERENCE_NOT_USED_AS_PROOF_BINDING",
        "DETACHED_RECEIPT_TIMESTAMP_ENVELOPE_SOURCE_AND_CUSTODY_NOT_AUTHENTICATED",
        "TSA_NONCE_REQUEST_ORIGIN_NOT_AUTHENTICATED",
    )
    inspection = ReceiptAttestationTimestampInspection(
        receipt_sha256=receipt_digest,
        signature_sha256=signature_digest,
        token_sha256=timestamp.token_sha256,
        legacy_embedded_proof_reference_sha256=receipt.attestation.timestamp_proof_sha256,
        authority_id=envelope.authority_id,
        tsa_policy_oid=timestamp.policy_oid,
        gen_time_utc=timestamp.gen_time_utc,
        accuracy_microseconds=timestamp.accuracy_microseconds,
        tsa_certificate_sha256=timestamp.tsa_certificate_sha256,
        tsa_root_certificate_sha256=timestamp.tsa_root_certificate_sha256,
        certificate_chain_length=timestamp.certificate_chain_length,
        nonce_verified=timestamp.nonce_verified,
        binding_status="RFC3161_IMPRINT_MATCHES_EXACT_RECEIPT_SIGNATURE_BYTES",
        detached_envelope_sha256=hashlib.sha256(detached_receipt_timestamp_envelope_bytes).hexdigest(),
    )
    return DetachedReceiptTimestampChainInspection(
        root_and_output_seals=combined,
        receipt_attestation_timestamp=inspection,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
