"""Direct, fail-closed composition of signed policy and receipt verification.

This module deliberately accepts original policy-envelope bytes rather than a
caller-supplied VerifiedTrustPolicy object. It verifies the envelope against the
separately supplied deployment anchor, then passes only the policy produced by
that verification call into the receipt-attestation verifier.

The result is scoped to the root receipt attestation. It is NOT independent
physical provenance, trusted time, nested signer/custodian authentication,
artifact-byte verification, ledger inclusion, or production eligibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .trust_policy_envelope_v1 import verify_signed_trust_policy
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)


@dataclass(frozen=True, slots=True)
class RootAttestationChainResult:
    """Evidence that one receipt root signature verified under one signed policy.

    This result is not an unforgeable Python capability and must not be treated
    as an authenticated-provenance decision by downstream code.
    """

    policy_sequence: int
    root_key_id: str
    policy_envelope_sha256: str
    receipt: CryptographicallyVerifiedReceipt
    scope: str = "ROOT_ATTESTATION_ONLY"


def verify_policy_bound_receipt_attestation(
    original_receipt_bytes: bytes,
    original_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> RootAttestationChainResult:
    """Verify policy envelope first, then receipt attestation in one call chain.

    All security-critical deployment inputs remain caller-supplied:
    root public key, root key ID, minimum sequence, and verification clock.
    They MUST be provisioned by a separately controlled deployment boundary.
    This function does not authenticate that provisioning.

    Passing a preconstructed VerifiedTrustPolicy is intentionally unsupported.
    The policy is derived internally from the original signed envelope bytes.
    """
    verified_policy = verify_signed_trust_policy(
        original_policy_envelope_bytes,
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
    return RootAttestationChainResult(
        policy_sequence=verified_policy.policy_sequence,
        root_key_id=verified_policy.root_key_id,
        policy_envelope_sha256=verified_policy.envelope_sha256,
        receipt=verified_receipt,
    )
