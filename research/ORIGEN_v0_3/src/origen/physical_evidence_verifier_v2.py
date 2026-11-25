"""Research-only verifier for nested physical-evidence Ed25519 signatures.

This module verifies exact artifact bytes and detached signatures relative to a
caller-supplied, signed trust-policy envelope. Policy v1 does not bind signer
roles, and the caller-supplied root, sequence floor, and clock are not
independently provisioned. Therefore every result remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from origen.trust_policy_envelope_v2 import (
    VerifiedTrustPolicyV2,
    verify_signed_trust_policy_v2,
)

CLASSIC_PHYSICAL_POLICY_DOMAIN = "origen.chispazo.classic.provenance"
from origen.trust_verifier_v1 import TrustedIssuerKey

SIGNATURE_PAYLOAD_DOMAIN = "origen.physical-evidence-signature.v1"
ROLE_AUTHORIZATION_UNVERIFIED = "UNVERIFIED_CLAIM_ONLY"

PHYSICAL_SIGNATURE_REMAINING_BLOCKERS = (
    "DEPLOYMENT_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "ANTI_ROLLBACK_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "SIGNER_ROLE_AUTHORIZATION_NOT_BOUND_TO_POLICY_V1",
    "RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED",
    "EXTERNAL_LEDGER_INCLUSION_AND_HEAD_NOT_VERIFIED",
    "CUSTODY_RECEIPT_SIGNATURES_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED",
    "PHYSICAL_ARTIFACT_SEMANTICS_AND_INDEPENDENT_CUSTODY_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class NestedSignatureVerification:
    artifact_sha256: str
    subject_id: str
    claimed_role: str
    key_id: str
    signature_sha256: str
    signature_verified: bool
    role_authorization_status: str


@dataclass(frozen=True, slots=True)
class PhysicalEvidenceSignatureInspection:
    manifest_sha256: str
    policy_envelope_sha256: str
    policy_domain: str
    policy_sequence: int
    verification_time_utc: datetime
    artifact_count: int
    signatures_verified: int
    signature_results: tuple[NestedSignatureVerification, ...]
    trust_anchor_source: str
    anti_rollback_source: str
    verification_clock_source: str
    role_authorization_status: str
    trusted_time_status: str
    ledger_status: str
    custody_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _utc_instant(value: object, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field} timezone offset is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError(f"{field} timezone offset must be an exact timedelta")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise ValueError(f"{field} cannot be normalized to UTC") from exc


def canonical_physical_manifest_signature_payload(raw_manifest_bytes: bytes) -> bytes:
    """Return the common signing payload with signature digests excluded.

    Every nested signer signs the same complete manifest claim set. The
    signature_sha256 values are omitted to avoid a circular digest dependency;
    they are checked independently against the supplied signature bytes.
    """
    if type(raw_manifest_bytes) is not bytes:
        raise TypeError("raw_manifest_bytes must be exact bytes")
    parse_unverified_physical_manifest(raw_manifest_bytes)
    document = json.loads(raw_manifest_bytes.decode("utf-8"))
    for signature_claim in document["signatures"]:
        signature_claim.pop("signature_sha256")
    return _canonical_json({
        "domain": SIGNATURE_PAYLOAD_DOMAIN,
        "manifest_claims": document,
    })


def _exact_bytes_mapping(value: object, field: str) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError(f"{field} must be an exact dict")
    snapshot: dict[str, bytes] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise TypeError(f"{field} keys must be exact strings")
        if type(item) is not bytes:
            raise TypeError(f"{field} values must be exact bytes")
        snapshot[key] = item
    return snapshot


def verify_physical_evidence_signatures(
    raw_manifest_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    *,
    signed_policy_envelope_bytes: bytes,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    expected_policy_domain: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> PhysicalEvidenceSignatureInspection:
    """Verify manifest-bound artifact bytes and nested Ed25519 signatures.

    This verifier does not authenticate claimed roles, RFC 3161 tokens,
    external ledger proofs, custodian receipts, physical-event truth, or
    independent custody. All trust-policy deployment inputs remain caller-
    supplied. The result can never represent authenticated provenance.
    """
    if type(raw_manifest_bytes) is not bytes:
        raise TypeError("raw_manifest_bytes must be exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")

    verified_at = _utc_instant(verification_time, "verification_time")
    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    artifact_bytes = _exact_bytes_mapping(
        artifact_bytes_by_sha256, "artifact_bytes_by_sha256"
    )
    signature_bytes = _exact_bytes_mapping(
        signature_bytes_by_sha256, "signature_bytes_by_sha256"
    )

    artifacts_by_digest = {item.sha256: item for item in manifest.artifacts}
    if set(artifact_bytes) != set(artifacts_by_digest):
        raise ValueError(
            "artifact byte map must contain exactly the manifest artifact digests"
        )
    for digest, claim in artifacts_by_digest.items():
        original = artifact_bytes[digest]
        if len(original) != claim.byte_length:
            raise ValueError(
                f"artifact byte length mismatch for {claim.artifact_type}"
            )
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError(
                f"artifact SHA-256 mismatch for {claim.artifact_type}"
            )

    expected_signature_digests = {
        item.signature_sha256 for item in manifest.signatures
    }
    if set(signature_bytes) != expected_signature_digests:
        raise ValueError(
            "signature byte map must contain exactly the manifest signature digests"
        )
    for digest, original in signature_bytes.items():
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError("signature SHA-256 does not match manifest claim")

    verified_policy: VerifiedTrustPolicyV2 = verify_signed_trust_policy_v2(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=expected_policy_domain,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    if type(verified_policy) is not VerifiedTrustPolicyV2:
        raise TypeError("policy verifier returned an unexpected result type")
    if verified_policy.policy_domain != CLASSIC_PHYSICAL_POLICY_DOMAIN:
        raise ValueError(
            "CLASSIC physical evidence requires policy domain "
            f"{CLASSIC_PHYSICAL_POLICY_DOMAIN}"
        )
    issuer_keys = verified_policy.policy.issuer_keys
    if type(issuer_keys) is not tuple:
        raise ValueError("verified policy issuer_keys must be an exact tuple")

    keys_by_identity: dict[tuple[str, str], TrustedIssuerKey] = {}
    for index, key in enumerate(issuer_keys):
        if type(key) is not TrustedIssuerKey:
            raise ValueError(f"verified policy issuer_keys[{index}] has an invalid type")
        identity = (key.issuer_id, key.key_id)
        if identity in keys_by_identity:
            raise ValueError("verified policy contains duplicate signer identities")
        keys_by_identity[identity] = key

    payload = canonical_physical_manifest_signature_payload(raw_manifest_bytes)
    results: list[NestedSignatureVerification] = []
    for index, claim in enumerate(manifest.signatures):
        if claim.algorithm != "ed25519":
            raise ValueError(
                f"signatures[{index}] uses an unsupported algorithm for this verifier"
            )
        identity = (claim.subject_id, claim.key_id)
        key = keys_by_identity.get(identity)
        if key is None:
            raise ValueError(
                f"signatures[{index}] signer subject/key is absent from verified policy"
            )
        if key.revoked:
            raise ValueError(f"signatures[{index}] signer key is revoked")
        if not (key.valid_from_utc <= verified_at <= key.valid_until_utc):
            raise ValueError(
                f"signatures[{index}] signer key is outside policy validity at verification time"
            )
        signature = signature_bytes[claim.signature_sha256]
        try:
            Ed25519PublicKey.from_public_bytes(key.public_key_bytes).verify(
                signature, payload
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError(
                f"signatures[{index}] nested Ed25519 signature verification failed"
            ) from exc
        results.append(NestedSignatureVerification(
            artifact_sha256=claim.artifact_sha256,
            subject_id=claim.subject_id,
            claimed_role=claim.role,
            key_id=claim.key_id,
            signature_sha256=claim.signature_sha256,
            signature_verified=True,
            role_authorization_status=ROLE_AUTHORIZATION_UNVERIFIED,
        ))

    return PhysicalEvidenceSignatureInspection(
        manifest_sha256=manifest.raw_sha256,
        policy_envelope_sha256=verified_policy.envelope_sha256,
        policy_domain=verified_policy.policy_domain,
        policy_sequence=verified_policy.policy_sequence,
        verification_time_utc=verified_at,
        artifact_count=len(manifest.artifacts),
        signatures_verified=len(results),
        signature_results=tuple(results),
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        role_authorization_status=ROLE_AUTHORIZATION_UNVERIFIED,
        trusted_time_status="UNVERIFIED_RFC3161_REQUIRED",
        ledger_status="UNVERIFIED_EXTERNAL_INCLUSION_REQUIRED",
        custody_status="UNVERIFIED_INDEPENDENT_RECEIPTS_REQUIRED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=PHYSICAL_SIGNATURE_REMAINING_BLOCKERS,
    )
