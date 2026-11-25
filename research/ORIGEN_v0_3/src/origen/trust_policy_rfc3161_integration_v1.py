"""Fail-closed RFC 3161 integration for the two pre-close output-seal signatures.

This layer composes the signed policy/receipt chain with timestamp-token
verification. It verifies only the two output-seal signature byte strings.
The receipt-attestation timestamp proof is deliberately left unverified:
the V1 receipt signature currently covers its own timestamp-proof digest,
which makes timestamping that signature self-referential. No provenance
promotion is possible through this diagnostic.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from .independent_trust_adapter import ProvenanceStatus
from .rfc3161_tsa_verifier_v1 import verify_rfc3161_timestamp_token
from .trust_policy_integration_v1 import (
    ROOT_CHAIN_REMAINING_BLOCKERS,
    RootAttestationInspection,
    inspect_signed_root_attestation_chain,
)
from .trust_receipt_v1 import parse_unverified_receipt

MAX_OUTPUT_SEAL_SIGNATURE_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class OutputSealTimestampEvidence:
    """Exact detached TSA evidence for one output-seal signature."""

    event_id: str
    token_der: bytes
    signature_bytes: bytes
    expected_nonce: int


@dataclass(frozen=True, slots=True)
class OutputSealTimestampInspection:
    event_id: str
    proof_sha256: str
    signature_sha256: str
    token_sha256: str
    gen_time_utc: datetime
    accuracy_microseconds: int
    tsa_certificate_sha256: str
    tsa_root_certificate_sha256: str
    certificate_chain_length: int


@dataclass(frozen=True, slots=True)
class SignedRootAndOutputSealTimeInspection:
    root_chain: RootAttestationInspection
    output_seal_timestamps: tuple[OutputSealTimestampInspection, ...]
    timestamp_authority_id: str
    timestamp_authority_source: str
    tsa_root_anchor_source: str
    verification_clock_source: str
    nonce_source: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def inspect_signed_root_attestation_chain_with_output_seal_timestamps(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
    output_seal_timestamp_evidence: tuple[OutputSealTimestampEvidence, ...],
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_tsa_authority_id: str,
) -> SignedRootAndOutputSealTimeInspection:
    """Verify policy, receipt root signature and both output-seal TSA tokens.

    All trust anchors, sequence floor, verification clock, TSA authority label,
    and request nonces are caller-supplied and unauthenticated. The function
    accepts exact original receipt/policy/token/signature bytes only. It
    requires the RFC 3161 token digest to match the signed receipt reference,
    the token imprint to match the exact output-seal signature bytes, and
    genTime plus declared accuracy to fall strictly before the Classic close.

    The receipt-attestation timestamp token is NOT verified here. The V1
    attestation currently signs a receipt containing its own timestamp-proof
    digest; timestamping the signature bytes while the token digest is inside
    the signed payload would create a cryptographic self-reference. That
    requires a separately versioned detached-proof envelope, not a bypass.
    """
    root_chain = inspect_signed_root_attestation_chain(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    if root_chain.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("signed root chain did not preserve BLOCKED_PROVENANCE")

    if type(output_seal_timestamp_evidence) is not tuple or len(output_seal_timestamp_evidence) != 2:
        raise ValueError("exactly two output-seal timestamp evidence items are required")
    if type(expected_tsa_authority_id) is not str or not expected_tsa_authority_id:
        raise ValueError("expected_tsa_authority_id must be a non-empty exact string")

    receipt = parse_unverified_receipt(original_receipt_bytes)
    proofs_by_digest = {item.proof_sha256: item for item in receipt.trusted_time_proofs}
    seals_by_proof = {item.timestamp_proof_sha256: item for item in receipt.output_seals}
    if len(seals_by_proof) != 2:
        raise ValueError("receipt must bind two distinct output-seal timestamp proofs")

    seen_events = set()
    seen_tokens = set()
    inspections = []
    close_at = datetime.fromisoformat(
        receipt.target.draw_close_at_utc[:-1] + "+00:00"
    )

    for index, evidence in enumerate(output_seal_timestamp_evidence):
        if type(evidence) is not OutputSealTimestampEvidence:
            raise TypeError(
                f"output_seal_timestamp_evidence[{index}] must be an exact "
                "OutputSealTimestampEvidence"
            )
        if type(evidence.event_id) is not str or not evidence.event_id:
            raise ValueError(f"output_seal_timestamp_evidence[{index}].event_id is invalid")
        if evidence.event_id in seen_events:
            raise ValueError("output-seal timestamp evidence contains duplicate event IDs")
        seen_events.add(evidence.event_id)
        if type(evidence.token_der) is not bytes or not evidence.token_der:
            raise TypeError(f"output-seal timestamp evidence[{index}] token_der must be exact bytes")
        if (
            type(evidence.signature_bytes) is not bytes
            or not 1 <= len(evidence.signature_bytes) <= MAX_OUTPUT_SEAL_SIGNATURE_BYTES
        ):
            raise ValueError(
                f"output-seal timestamp evidence[{index}] signature_bytes must be "
                f"1..{MAX_OUTPUT_SEAL_SIGNATURE_BYTES} exact bytes"
            )
        if type(evidence.expected_nonce) is not int or evidence.expected_nonce < 1:
            raise ValueError(
                f"output-seal timestamp evidence[{index}].expected_nonce "
                "must be an exact positive integer"
            )

        token_sha256 = hashlib.sha256(evidence.token_der).hexdigest()
        if token_sha256 in seen_tokens:
            raise ValueError("output-seal timestamp evidence contains duplicate token bytes")
        seen_tokens.add(token_sha256)
        seal = seals_by_proof.get(token_sha256)
        proof = proofs_by_digest.get(token_sha256)
        if seal is None or proof is None:
            raise ValueError(
                "timestamp token SHA-256 does not match a signed output-seal proof reference"
            )
        if proof.event_id != evidence.event_id:
            raise ValueError("timestamp token event ID does not match the signed receipt claim")
        if proof.authority_id != expected_tsa_authority_id:
            raise ValueError("timestamp authority ID does not match the caller-pinned TSA authority")
        signature_sha256 = hashlib.sha256(evidence.signature_bytes).hexdigest()
        if signature_sha256 != seal.signature_sha256:
            raise ValueError(
                "exact output-seal signature bytes do not match the signed receipt digest"
            )

        timestamp = verify_rfc3161_timestamp_token(
            evidence.token_der,
            evidence.signature_bytes,
            pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
            expected_tsa_root_sha256=expected_tsa_root_sha256,
            verification_time=verification_time,
            expected_nonce=evidence.expected_nonce,
        )
        declared_event_time = datetime.fromisoformat(
            proof.event_at_utc[:-1] + "+00:00"
        )
        if timestamp.gen_time_utc != declared_event_time:
            raise ValueError("RFC3161 genTime does not match the signed trusted-time event")
        if timestamp.gen_time_utc != datetime.fromisoformat(
            seal.created_at_utc[:-1] + "+00:00"
        ):
            raise ValueError("RFC3161 genTime does not match the declared output-seal creation time")
        if timestamp.accuracy_microseconds is None:
            raise ValueError(
                "RFC3161 accuracy is absent; strict pre-close time bound cannot be established"
            )
        upper_time_bound = timestamp.gen_time_utc + timedelta(
            microseconds=timestamp.accuracy_microseconds
        )
        if upper_time_bound >= close_at:
            raise ValueError(
                "RFC3161 genTime plus accuracy is not strictly before the Classic draw close"
            )

        inspections.append(
            OutputSealTimestampInspection(
                event_id=proof.event_id,
                proof_sha256=token_sha256,
                signature_sha256=signature_sha256,
                token_sha256=timestamp.token_sha256,
                gen_time_utc=timestamp.gen_time_utc,
                accuracy_microseconds=timestamp.accuracy_microseconds,
                tsa_certificate_sha256=timestamp.tsa_certificate_sha256,
                tsa_root_certificate_sha256=timestamp.tsa_root_certificate_sha256,
                certificate_chain_length=timestamp.certificate_chain_length,
            )
        )

    if seen_tokens != set(seals_by_proof):
        raise ValueError("both output-seal timestamp proofs must be independently verified")
    if root_chain.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("output-seal timestamp verification changed provenance status")

    blockers = tuple(
        item for item in ROOT_CHAIN_REMAINING_BLOCKERS
        if item != "RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED"
    ) + (
        "RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED",
        "TSA_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
        "TSA_AUTHORITY_ID_AND_POLICY_OID_NOT_INSTITUTIONALLY_AUTHORIZED",
        "TSA_REVOCATION_FRESHNESS_NOT_CHECKED",
        "TSA_PATH_VALIDATION_NOT_FULL_RFC5280",
        "NESTED_OUTPUT_SEAL_SIGNATURES_AND_SIGNER_ROLES_NOT_VERIFIED",
    )
    return SignedRootAndOutputSealTimeInspection(
        root_chain=root_chain,
        output_seal_timestamps=tuple(inspections),
        timestamp_authority_id=expected_tsa_authority_id,
        timestamp_authority_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        tsa_root_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        nonce_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
