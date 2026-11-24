"""Research-only composition of signed policy and receipt-root verification.

This inspector proves two narrow cryptographic statements relative to caller-
supplied inputs. It deliberately does not promote independent provenance:
the deployment root, anti-rollback state, and clock are not provisioned by this
repository, and the external evidence layers remain unauthenticated.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from .trust_policy_envelope_v1 import (
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from .trust_verifier_v1 import verify_receipt_attestation


ROOT_CHAIN_REMAINING_BLOCKERS = (
    "DEPLOYMENT_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "ANTI_ROLLBACK_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "TRUST_POLICY_REVOCATION_FRESHNESS_NOT_AUTHENTICATED",
    "NESTED_SIGNER_SIGNATURES_NOT_VERIFIED",
    "CUSTODIAN_IDENTITY_AND_RECEIPT_SIGNATURES_NOT_VERIFIED",
    "RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED",
    "EXTERNAL_LEDGER_INCLUSION_AND_HEAD_NOT_VERIFIED",
    "ORIGINAL_PHYSICAL_ARTIFACT_BYTES_AND_CUSTODY_NOT_VERIFIED",
    "TWO_PRE_CLOSE_SEAL_SIGNATURES_AND_INDEPENDENT_RECEIPTS_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class RootAttestationInspection:
    """Diagnostic only; never an authentication or production capability."""

    policy_signature_verified_against_supplied_anchor: bool
    receipt_signature_verified_under_policy: bool
    policy_sequence: int
    policy_root_key_id: str
    policy_envelope_sha256: str
    receipt_sha256: str
    signed_payload_sha256: str
    verified_issuer_id: str
    verified_key_id: str
    verification_time_utc: datetime
    deployment_anchor_source: str
    anti_rollback_source: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def inspect_signed_root_attestation_chain(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> RootAttestationInspection:
    """Inspect policy->receipt Ed25519 signatures without enabling provenance.

    The caller-supplied root key, key ID, sequence floor, and verification
    clock are deliberately labelled unauthenticated. This function re-verifies
    the signed envelope from original bytes rather than accepting a caller-
    constructed VerifiedTrustPolicy object.

    Even when both Ed25519 signatures verify, verify_independent_provenance()
    remains the authoritative production boundary and returns
    BLOCKED_PROVENANCE. This function has no authenticated/eligible status.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")

    verified_policy: VerifiedTrustPolicy = verify_signed_trust_policy(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    verified_receipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_policy.policy,
        verification_time=verification_time,
    )

    # This call is intentionally retained: successful root signatures do not
    # bypass the adapter's independent-provenance kill switch.
    provenance_status = verify_independent_provenance(original_receipt_bytes)
    if provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("unexpected provenance status; fail-closed invariant violated")

    return RootAttestationInspection(
        policy_signature_verified_against_supplied_anchor=True,
        receipt_signature_verified_under_policy=True,
        policy_sequence=verified_policy.policy_sequence,
        policy_root_key_id=verified_policy.root_key_id,
        policy_envelope_sha256=verified_policy.envelope_sha256,
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        signed_payload_sha256=verified_receipt.signed_payload_sha256,
        verified_issuer_id=verified_receipt.verified_issuer_id,
        verified_key_id=verified_receipt.verified_key_id,
        verification_time_utc=verified_receipt.verified_at_utc,
        deployment_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=provenance_status,
        remaining_blockers=ROOT_CHAIN_REMAINING_BLOCKERS,
    )
