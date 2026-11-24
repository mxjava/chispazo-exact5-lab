"""Strict structural parser for ORIGEN trust-receipt V2 time bindings.

V2 binds each output-seal timestamp proof to the exact declared signature digest,
and binds the receipt-attestation timestamp proof to the exact attestation
signature bytes. It reuses V1's strict shape and consistency checks after
validating the V2-only links. It does NOT verify RFC 3161/CMS tokens, TSA chains,
signer signatures, key ownership, identity, or physical provenance.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from dataclasses import dataclass, replace

from .trust_receipt_v1 import (
    MAX_TRUST_RECEIPT_BYTES,
    SCHEMA_VERSION as SCHEMA_VERSION_V1,
    UnverifiedTrustReceipt,
    _ROOT_FIELDS,
    _array,
    _digest,
    _identifier,
    _object,
    _parse_json_integer,
    _reject_json_constant,
    _reject_json_float,
    _timestamp,
    _unique_object,
    parse_unverified_receipt,
)

SCHEMA_VERSION_V2 = "origen.trust-receipt.v2"
MAX_TRUST_RECEIPT_JSON_DEPTH_V2 = 64


def _validate_json_nesting_depth_v2(raw: bytes) -> None:
    """Bound nested JSON containers before recursive V2 decoder/encoder work."""
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
            if depth > MAX_TRUST_RECEIPT_JSON_DEPTH_V2:
                raise ValueError(
                    "trust receipt exceeds maximum JSON nesting depth "
                    f"{MAX_TRUST_RECEIPT_JSON_DEPTH_V2}"
                )
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


_TIME_PROOF_FIELDS = {
    "authority_id", "event_id", "event_at_utc", "proof_sha256", "subject_sha256"
}
_OUTPUT_SEAL_FIELDS = {
    "target_contest_id", "generator_id", "created_at_utc", "portfolio_sha256",
    "seal_sha256", "signature_sha256", "timestamp_proof_sha256"
}


@dataclass(frozen=True, slots=True)
class TrustedTimeProofBindingV2:
    authority_id: str
    event_id: str
    event_at_utc: str
    proof_sha256: str
    subject_sha256: str


@dataclass(frozen=True, slots=True)
class OutputSealTimeBindingV2:
    seal_sha256: str
    signature_sha256: str
    created_at_utc: str
    timestamp_proof_sha256: str


@dataclass(frozen=True, slots=True)
class UnverifiedTrustReceiptV2:
    """V1 claims plus explicit V2 time-proof subject bindings; still unverified."""

    receipt: UnverifiedTrustReceipt
    trusted_time_proofs: tuple[TrustedTimeProofBindingV2, ...]
    output_seal_time_bindings: tuple[OutputSealTimeBindingV2, ...]
    raw_sha256: str


def parse_unverified_receipt_v2(raw: bytes) -> UnverifiedTrustReceiptV2:
    """Parse V2 and enforce exact proof-to-signature/time bindings.

    This validates declared relationships only. A proof digest is not a TSA
    token, and a matching timestamp string is not trusted time.
    """
    if type(raw) is not bytes:
        raise TypeError("trust receipt input must be exact bytes")
    if not raw or len(raw) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(f"trust receipt must contain 1..{MAX_TRUST_RECEIPT_BYTES} bytes")
    _validate_json_nesting_depth_v2(raw)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("trust receipt must be valid UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
            parse_int=_parse_json_integer,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("trust receipt is not valid bounded JSON") from exc
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    if raw != canonical:
        raise ValueError("trust receipt JSON must use canonical UTF-8 encoding")
    root = _object(payload, _ROOT_FIELDS, "receipt")
    if root["schema_version"] != SCHEMA_VERSION_V2:
        raise ValueError("unsupported trust receipt V2 schema_version")

    proof_rows = _array(
        root["trusted_time_proofs"], "trusted_time_proofs", minimum=3, maximum=4096
    )
    proofs = []
    for index, value in enumerate(proof_rows):
        item = _object(value, _TIME_PROOF_FIELDS, f"trusted_time_proofs[{index}]")
        proofs.append(
            TrustedTimeProofBindingV2(
                authority_id=_identifier(item["authority_id"], f"trusted_time_proofs[{index}].authority_id"),
                event_id=_identifier(item["event_id"], f"trusted_time_proofs[{index}].event_id"),
                event_at_utc=_timestamp(item["event_at_utc"], f"trusted_time_proofs[{index}].event_at_utc"),
                proof_sha256=_digest(item["proof_sha256"], f"trusted_time_proofs[{index}].proof_sha256"),
                subject_sha256=_digest(item["subject_sha256"], f"trusted_time_proofs[{index}].subject_sha256"),
            )
        )

    seal_rows = _array(root["output_seals"], "output_seals", minimum=2, maximum=2)
    seal_bindings = []
    for index, value in enumerate(seal_rows):
        item = _object(value, _OUTPUT_SEAL_FIELDS, f"output_seals[{index}]")
        seal_bindings.append(
            OutputSealTimeBindingV2(
                seal_sha256=_digest(item["seal_sha256"], f"output_seals[{index}].seal_sha256"),
                signature_sha256=_digest(item["signature_sha256"], f"output_seals[{index}].signature_sha256"),
                created_at_utc=_timestamp(item["created_at_utc"], f"output_seals[{index}].created_at_utc"),
                timestamp_proof_sha256=_digest(item["timestamp_proof_sha256"], f"output_seals[{index}].timestamp_proof_sha256"),
            )
        )

    # Delegate all unchanged V1 receipt invariants to the already-tested parser.
    v1_document = copy.deepcopy(payload)
    v1_document["schema_version"] = SCHEMA_VERSION_V1
    for item in v1_document["trusted_time_proofs"]:
        item.pop("subject_sha256")
    for item in v1_document["output_seals"]:
        item.pop("timestamp_proof_sha256")
    v1_raw = json.dumps(
        v1_document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    receipt = parse_unverified_receipt(v1_raw)

    proof_by_digest = {item.proof_sha256: item for item in proofs}
    attestation_proof_ref = receipt.attestation.timestamp_proof_sha256
    all_references = (
        attestation_proof_ref,
        *(item.timestamp_proof_sha256 for item in seal_bindings),
    )
    if len(set(all_references)) != 3:
        raise ValueError("receipt and output seal timestamp proof references must be distinct")

    attestation_proof = proof_by_digest.get(attestation_proof_ref)
    if attestation_proof is None:
        raise ValueError("receipt attestation timestamp proof must reference a declared V2 proof")
    attestation_signature = base64.b64decode(
        receipt.attestation.signature_b64, validate=True
    )
    expected_attestation_subject = hashlib.sha256(attestation_signature).hexdigest()
    if attestation_proof.subject_sha256 != expected_attestation_subject:
        raise ValueError("receipt attestation timestamp proof must bind to its signature bytes")

    for index, (seal, binding) in enumerate(zip(receipt.output_seals, seal_bindings)):
        proof = proof_by_digest.get(binding.timestamp_proof_sha256)
        if proof is None:
            raise ValueError(
                f"output_seals[{index}] timestamp proof must reference a declared V2 proof"
            )
        if proof.subject_sha256 != seal.signature_sha256:
            raise ValueError(
                f"output_seals[{index}] timestamp proof subject must match signature_sha256"
            )
        if proof.event_at_utc != seal.created_at_utc:
            raise ValueError(
                f"output_seals[{index}] timestamp proof time must match created_at_utc"
            )

    raw_digest = hashlib.sha256(raw).hexdigest()
    receipt = replace(receipt, raw_sha256=raw_digest)
    return UnverifiedTrustReceiptV2(
        receipt=receipt,
        trusted_time_proofs=tuple(proofs),
        output_seal_time_bindings=tuple(seal_bindings),
        raw_sha256=raw_digest,
    )
