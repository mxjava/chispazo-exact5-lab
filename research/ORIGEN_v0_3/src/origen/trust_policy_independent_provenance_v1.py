"""Fail-closed composition of signed policy, receipt attestation and provenance gate.

The signed policy is verified from its original envelope bytes and the receipt
root attestation is verified before the independent provenance adapter is
called. The adapter is deliberately still unprovisioned and must return only
BLOCKED_PROVENANCE. This module cannot release provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from .trust_policy_receipt_chain_v1 import (
    RootAttestationChainResult,
    verify_policy_bound_receipt_attestation,
)


@dataclass(frozen=True, slots=True)
class PolicyBoundIndependentProvenanceResult:
    """Diagnostic result; not a capability and never an eligibility decision."""

    policy_sequence: int
    root_key_id: str
    policy_envelope_sha256: str
    receipt_issuer_id: str
    receipt_key_id: str
    receipt_signed_payload_sha256: str
    provenance_status: ProvenanceStatus
    scope: str = "ROOT_ATTESTATION_VERIFIED_PROVENANCE_BLOCKED"


def verify_policy_bound_independent_provenance(
    original_receipt_bytes: bytes,
    original_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> PolicyBoundIndependentProvenanceResult:
    """Verify the policy/receipt chain, then invoke the independent fail-closed gate.

    The function accepts original bytes, never a caller-created VerifiedTrustPolicy
    or CryptographicallyVerifiedReceipt. The lower-level chain derives the
    VerifiedTrustPolicy from the signed envelope and passes its policy directly
    to verify_receipt_attestation.

    The independent adapter is called only after both cryptographic checks
    succeed, and receives the exact same immutable receipt-bytes object. Until
    an independently provisioned backend exists, its only valid result is
    BLOCKED_PROVENANCE. Any other return type/value is treated as a contract
    violation and raises RuntimeError.

    The pinned root, key ID, sequence floor and verification clock are still
    caller/deployment inputs. This function does not authenticate their
    provisioning, provide durable anti-rollback state, or verify physical
    evidence, nested signatures, RFC 3161 tokens, ledger inclusion, witnesses
    or custody. Its result is diagnostic only and is not an unforgeable
    capability.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(original_policy_envelope_bytes) is not bytes:
        raise TypeError("original_policy_envelope_bytes must be exact bytes")

    chain = verify_policy_bound_receipt_attestation(
        original_receipt_bytes,
        original_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    if type(chain) is not RootAttestationChainResult or chain.scope != "ROOT_ATTESTATION_ONLY":
        raise RuntimeError("signed-policy/receipt verifier returned an unexpected result")

    status = verify_independent_provenance(original_receipt_bytes)
    if (
        type(status) is not ProvenanceStatus
        or status is not ProvenanceStatus.BLOCKED_PROVENANCE
    ):
        raise RuntimeError(
            "independent provenance adapter violated its fail-closed contract"
        )

    return PolicyBoundIndependentProvenanceResult(
        policy_sequence=chain.policy_sequence,
        root_key_id=chain.root_key_id,
        policy_envelope_sha256=chain.policy_envelope_sha256,
        receipt_issuer_id=chain.receipt.verified_issuer_id,
        receipt_key_id=chain.receipt.verified_key_id,
        receipt_signed_payload_sha256=chain.receipt.signed_payload_sha256,
        provenance_status=status,
    )
