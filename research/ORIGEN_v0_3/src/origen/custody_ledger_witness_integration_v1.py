"""Research-only composition of V3 custody, RFC 3161, Merkle ledger and witnesses.

The exact detached custodian signature is timestamped as a sidecar. The
physical manifest binds that sidecar through an additional trusted-time-proof
claim (not by mutating the already-signed receipt). The manifest is then bound
to a Merkle ledger inclusion/consistency proof and independently re-verified
witness observation batches. Every successful diagnostic remains
BLOCKED_PROVENANCE: all roots, sequence floors and the clock are caller inputs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from .checkpoint_witness_gossip_v1 import (
    MAX_OBSERVATION_BATCHES,
    WitnessGossipInspection,
    WitnessObservationBatch,
    inspect_witness_gossip,
)
from .custody_receipt_verifier_v3 import CUSTODY_SIGNER_ROLE
from .custody_signature_timestamp_integration_v1 import (
    CustodySignatureTimestampInspectionV1,
    custody_signature_timestamp_event_id,
    verify_receipt_custody_signature_timestamp_v1,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_manifest_v1 import (
    UnverifiedPhysicalEvidenceManifest,
    parse_unverified_physical_manifest,
)
from .physical_evidence_verifier_v2 import (
    CLASSIC_PHYSICAL_POLICY_DOMAIN,
    PhysicalEvidenceSignatureInspection,
    _utc_instant,
)
from .physical_evidence_verifier_v3 import verify_physical_evidence_signatures_v3
from .transparency_checkpoint_consistency_v1 import (
    ConsistentLedgerInclusionInspection,
    verify_ledger_inclusion_with_checkpoint_continuity,
)

COMPOSITION_REMAINING_BLOCKERS = (
    "NESTED_SIGNATURES_PROVE_CRYPTOGRAPHIC_CONSISTENCY_NOT_INSTITUTIONAL_IDENTITY",
    "TSA_ROOT_AND_LOG_ROOT_ARE_CALLER_SUPPLIED_NOT_OUT_OF_BAND_PROVISIONED",
    "WITNESS_REGISTRY_ROOT_IS_CALLER_SUPPLIED_NOT_OUT_OF_BAND_PROVISIONED",
    "ANTI_ROLLBACK_FLOORS_ARE_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_IS_CALLER_SUPPLIED_NOT_AUTHENTICATED",
    "WITNESS_COLLECTOR_IDENTITY_AND_BATCH_CUSTODY_ARE_NOT_AUTHENTICATED",
    "NO_DURABLE_INDEPENDENT_GOSSIP_PERSISTENCE_OR_GLOBAL_COVERAGE",
    "WITNESS_OPERATOR_LEGAL_INDEPENDENCE_IS_NOT_ESTABLISHED",
    "CUSTODIAN_LEGAL_IDENTITY_AND_INSTITUTIONAL_DELEGATION_ARE_NOT_AUTHENTICATED",
    "PHYSICAL_ARTIFACT_ORIGIN_AND_DRAW_EVENT_TRUTH_ARE_NOT_AUTHENTICATED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class CustodyLedgerWitnessInspectionV1:
    """Diagnostic composition; never an authenticated provenance capability."""

    custody_timestamp: CustodySignatureTimestampInspectionV1
    physical_signatures: PhysicalEvidenceSignatureInspection
    ledger: ConsistentLedgerInclusionInspection
    witness_gossip: WitnessGossipInspection
    manifest_sha256: str
    custody_record_artifact_sha256: str
    timestamp_token_sha256: str
    timestamp_event_id: str
    ledger_checkpoint_sha256: str
    ledger_checkpoint_observed_in_witness_batches: bool
    witness_comparison_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _manifest_binds_signature_timestamp(
    manifest: UnverifiedPhysicalEvidenceManifest,
    *,
    custody_timestamp: CustodySignatureTimestampInspectionV1,
    original_receipt_bytes: bytes,
    custody_record_bytes: bytes,
    timestamp_token_der: bytes,
) -> str:
    """Bind exact V3 custody bytes and detached RFC 3161 sidecar to manifest claims."""
    chain = custody_timestamp.custody_chain
    target = manifest.target
    if hashlib.sha256(original_receipt_bytes).hexdigest() != chain.receipt_sha256:
        raise RuntimeError("V3 custody verifier returned a mismatched exact receipt digest")
    if hashlib.sha256(custody_record_bytes).hexdigest() != chain.custody_record_sha256:
        raise RuntimeError("V3 custody verifier returned a mismatched exact custody-record digest")
    if custody_timestamp.signature_sha256 != chain.custody_signature_sha256:
        raise RuntimeError("custody timestamp and V3 verifier disagree on exact signature digest")
    if target.modality != "CLASSIC":
        raise ValueError("custody ledger composition requires a CLASSIC physical manifest")
    if target.contest_id != str(chain.target_contest_id):
        raise ValueError("physical manifest contest_id does not match verified V3 custody target")

    artifact_matches = [
        item for item in manifest.artifacts
        if item.artifact_type == "SEGOB-OIC-CUSTODY-RECORD"
    ]
    if len(artifact_matches) != 1:
        raise ValueError("manifest must contain exactly one SEGOB-OIC-CUSTODY-RECORD artifact")
    artifact = artifact_matches[0]
    if artifact.sha256 != chain.custody_record_sha256:
        raise ValueError("manifest custody-record artifact digest does not match exact V3 record bytes")
    if artifact.byte_length != len(custody_record_bytes):
        raise ValueError("manifest custody-record artifact length does not match exact V3 record bytes")

    try:
        record = json.loads(custody_record_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("verified custody record cannot be decoded for manifest cross-binding") from exc
    if type(record) is not dict:
        raise ValueError("verified custody record must be a JSON object")
    if record.get("target_contest_id") != chain.target_contest_id:
        raise ValueError("exact custody record contest ID does not match verified V3 target")
    if record.get("custodian_id") != chain.custodian_id:
        raise ValueError("exact custody record custodian ID does not match verified V3 custodian")
    close_at = record.get("official_draw_close_at_utc")
    received_at = record.get("received_at_utc")
    if type(close_at) is not str or target.draw_close_at_utc != close_at:
        raise ValueError("manifest draw close does not match exact V3 custody record")
    if type(received_at) is not str:
        raise ValueError("V3 custody record has no canonical received_at_utc claim")

    custody_events = [
        item for item in manifest.custody_events
        if item.artifact_sha256 == artifact.sha256
    ]
    if len(custody_events) != 1:
        raise ValueError("manifest must contain exactly one custody event for the V3 custody record")
    event = custody_events[0]
    if event.custodian_subject_id != chain.custodian_id:
        raise ValueError("manifest custodian subject does not match verified V3 custodian ID")
    if event.custodian_role != CUSTODY_SIGNER_ROLE:
        raise ValueError("manifest custody role does not match the V3 external-custodian role")
    if event.receipt_sha256 != chain.receipt_sha256:
        raise ValueError("manifest custody receipt digest does not match exact root-signed receipt bytes")
    if event.received_at_utc != received_at:
        raise ValueError("manifest custody receipt time does not match exact V3 custody record")
    if event.event_id == custody_timestamp.timestamp_event_id:
        raise ValueError("signature timestamp event must not be reused as the custody receipt event")

    signature_sha256 = custody_timestamp.signature_sha256
    expected_event_id = custody_signature_timestamp_event_id(signature_sha256)
    if custody_timestamp.timestamp_event_id != expected_event_id:
        raise RuntimeError("custody timestamp verifier returned a mismatched signature event ID")
    token_sha256 = hashlib.sha256(timestamp_token_der).hexdigest()
    if custody_timestamp.timestamp.token_sha256 != token_sha256:
        raise RuntimeError("RFC 3161 verifier returned a mismatched exact token digest")
    authority_id = (
        "tsa-root-sha256:"
        + custody_timestamp.timestamp.tsa_root_certificate_sha256
    )
    proofs = [
        item for item in manifest.trusted_time_proofs
        if item.event_id == expected_event_id
        and item.authority_id == authority_id
    ]
    if len(proofs) != 1:
        raise ValueError(
            "manifest must contain exactly one trusted-time proof for the exact detached custody signature"
        )
    proof = proofs[0]
    if proof.proof_sha256 != token_sha256:
        raise ValueError("manifest signature-time proof digest does not match exact RFC 3161 token bytes")
    token_time = custody_timestamp.timestamp.gen_time_utc
    try:
        declared_time = datetime.fromisoformat(proof.event_at_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("manifest signature-time event is not a valid timestamp") from exc
    if declared_time != token_time:
        raise ValueError("manifest signature-time event does not match RFC 3161 genTime")
    if expected_event_id == event.event_id:
        raise ValueError("signature timestamp event must remain separate from custody receipt event")
    return artifact.sha256


def verify_custody_timestamp_ledger_witness_v1(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    custody_record_bytes: bytes,
    portfolio_bytes: bytes,
    custody_signature_bytes: bytes,
    custodian_key_id: str,
    timestamp_token_der: bytes,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_nonce: int,
    raw_manifest_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_old_checkpoint_bytes: bytes,
    raw_new_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    witness_observation_batches: tuple[WitnessObservationBatch, ...],
    *,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_new_tree_size: int,
    pinned_registry_root_public_key_bytes: bytes,
    expected_registry_root_key_id: str,
    expected_registry_id: str,
    minimum_registry_sequence: int,
    verification_time: datetime,
) -> CustodyLedgerWitnessInspectionV1:
    """Verify and compose exact custody signature time, manifest, ledger and witnesses.

    The verification clock is normalized once at this boundary. The exact
    ledger checkpoint must occur as an old or new checkpoint in at least one
    independently supplied witness batch. Gossip findings are returned as
    diagnostics; a split view is never converted into a successful status.
    """
    verified_at = _utc_instant(verification_time, "verification_time")
    custody_timestamp = verify_receipt_custody_signature_timestamp_v1(
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
        timestamp_token_der=timestamp_token_der,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        expected_nonce=expected_nonce,
    )
    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    physical_signatures = verify_physical_evidence_signatures_v3(
        raw_manifest_bytes,
        artifact_bytes_by_sha256,
        signature_bytes_by_sha256,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    if type(physical_signatures) is not PhysicalEvidenceSignatureInspection:
        raise TypeError("physical signature verifier returned an unexpected result type")
    if physical_signatures.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("physical signature verifier did not preserve BLOCKED_PROVENANCE")
    if (
        physical_signatures.manifest_sha256 != manifest.raw_sha256
        or physical_signatures.policy_envelope_sha256
        != custody_timestamp.custody_chain.policy_envelope_sha256
        or physical_signatures.policy_domain != CLASSIC_PHYSICAL_POLICY_DOMAIN
        or physical_signatures.policy_sequence != custody_timestamp.custody_chain.policy_sequence
        or physical_signatures.artifact_count != len(manifest.artifacts)
        or physical_signatures.signatures_verified != len(manifest.signatures)
    ):
        raise RuntimeError("nested physical signatures are not bound to the exact custody policy and manifest")
    if artifact_bytes_by_sha256.get(custody_timestamp.custody_chain.custody_record_sha256) != custody_record_bytes:
        raise ValueError("exact custody-record bytes are absent from the verified physical artifact map")
    custody_artifact_sha256 = _manifest_binds_signature_timestamp(
        manifest,
        custody_timestamp=custody_timestamp,
        original_receipt_bytes=original_receipt_bytes,
        custody_record_bytes=custody_record_bytes,
        timestamp_token_der=timestamp_token_der,
    )

    ledger = verify_ledger_inclusion_with_checkpoint_continuity(
        raw_manifest_bytes,
        raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_key_id=expected_log_key_id,
        minimum_new_tree_size=minimum_new_tree_size,
        verification_time=verified_at,
    )
    # This composition API accepts only an immutable, bounded tuple. Do
    # not iterate a caller-controlled lazy iterable or mutable list before
    # the gossip verifier applies its own resource and cryptographic checks.
    if type(witness_observation_batches) is not tuple:
        raise TypeError("witness_observation_batches must be an exact tuple")
    if not 2 <= len(witness_observation_batches) <= MAX_OBSERVATION_BATCHES:
        raise ValueError(
            "witness_observation_batches must contain "
            f"2..{MAX_OBSERVATION_BATCHES} immutable batches"
        )

    gossip = inspect_witness_gossip(
        witness_observation_batches,
        pinned_registry_root_public_key_bytes=pinned_registry_root_public_key_bytes,
        expected_registry_root_key_id=expected_registry_root_key_id,
        expected_registry_id=expected_registry_id,
        minimum_registry_sequence=minimum_registry_sequence,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_log_key_id=expected_log_key_id,
        minimum_new_tree_size=minimum_new_tree_size,
        verification_time=verified_at,
    )

    # Only inspect exact checkpoint bytes after every immutable batch has
    # passed registry, checkpoint, consistency and witness-quorum verification.
    checkpoint_sha256 = ledger.inclusion.checkpoint_sha256
    observed = any(
        hashlib.sha256(batch.raw_old_checkpoint_bytes).hexdigest() == checkpoint_sha256
        or hashlib.sha256(batch.raw_new_checkpoint_bytes).hexdigest() == checkpoint_sha256
        for batch in witness_observation_batches
    )
    if not observed:
        raise ValueError(
            "exact ledger checkpoint is absent from every verified witness observation batch"
        )

    if (
        custody_timestamp.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
        or ledger.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
        or gossip.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
    ):
        raise RuntimeError("a composed verifier returned an unexpected non-blocked provenance status")

    blockers = tuple(dict.fromkeys(
        tuple(custody_timestamp.remaining_blockers)
        + tuple(physical_signatures.remaining_blockers)
        + tuple(ledger.remaining_blockers)
        + tuple(gossip.remaining_blockers)
        + COMPOSITION_REMAINING_BLOCKERS
    ))
    return CustodyLedgerWitnessInspectionV1(
        custody_timestamp=custody_timestamp,
        physical_signatures=physical_signatures,
        ledger=ledger,
        witness_gossip=gossip,
        manifest_sha256=manifest.raw_sha256,
        custody_record_artifact_sha256=custody_artifact_sha256,
        timestamp_token_sha256=hashlib.sha256(timestamp_token_der).hexdigest(),
        timestamp_event_id=custody_timestamp.timestamp_event_id,
        ledger_checkpoint_sha256=checkpoint_sha256,
        ledger_checkpoint_observed_in_witness_batches=observed,
        witness_comparison_status=gossip.comparison_status,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
