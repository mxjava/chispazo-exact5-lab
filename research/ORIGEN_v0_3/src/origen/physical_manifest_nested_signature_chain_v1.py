"""Research-only composition of receipt, manifest, bytes, and nested signatures.

A successful inspection verifies cryptographic consistency relative to a
caller-supplied VerifiedTrustPolicy. It does not authenticate policy-anchor
provisioning, signer roles, signature creation time, TSA, ledger, custody,
physical truth, or prospective eligibility. Provenance always remains blocked.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_manifest_v1 import (
    parse_unverified_physical_manifest,
)
from .trust_artifact_bytes_v1 import (
    PhysicalManifestBindingCheck,
    verify_independent_provenance_with_physical_manifest,
)
from .trust_policy_envelope_v1 import (
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from .trust_verifier_v1 import TrustedIssuerKey


SIGNATURE_PAYLOAD_DOMAIN = "origen.physical-evidence-signature.v1"
ROLE_AUTHORIZATION_UNVERIFIED = "UNVERIFIED_CLAIM_ONLY"
SIGNATURE_CHAIN_STATUS = (
    "RECEIPT_MANIFEST_AND_NESTED_SIGNATURES_VERIFIED_NOT_AUTHENTICATED"
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")

NESTED_SIGNATURE_REMAINING_BLOCKERS = (
    "DEPLOYMENT_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "ANTI_ROLLBACK_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "SIGNER_ROLE_AUTHORIZATION_NOT_BOUND_TO_POLICY_V1",
    "NESTED_SIGNATURE_CREATION_TIME_NOT_INDEPENDENTLY_PROVEN",
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
class PhysicalEvidenceSignatureChainInspection:
    binding: PhysicalManifestBindingCheck
    policy_envelope_sha256: str
    policy_sequence: int
    verification_time_utc: datetime
    artifact_count: int
    signatures_verified: int
    signature_results: tuple[NestedSignatureVerification, ...]
    trust_anchor_source: str
    anti_rollback_source: str
    verification_clock_source: str
    role_authorization_status: str
    signature_creation_time_status: str
    trusted_time_status: str
    ledger_status: str
    custody_status: str
    provenance_status: ProvenanceStatus
    status: str
    remaining_blockers: tuple[str, ...]


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
    """Build the common domain-separated payload signed by every manifest signer.

    The complete manifest claim set is covered. Only signature_sha256 fields
    are omitted to avoid a circular dependency; the detached signature bytes
    are independently bound by those SHA-256 claims.
    """
    if type(raw_manifest_bytes) is not bytes:
        raise TypeError("raw_manifest_bytes must be exact bytes")
    parse_unverified_physical_manifest(raw_manifest_bytes)
    document = json.loads(raw_manifest_bytes.decode("utf-8"))
    for signature_claim in document["signatures"]:
        signature_claim.pop("signature_sha256")
    return json.dumps(
        {
            "domain": SIGNATURE_PAYLOAD_DOMAIN,
            "manifest_claims": document,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _snapshot_bytes_mapping(value: object, field: str) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError(f"{field} must be an exact dict")
    try:
        items = tuple(value.items())
    except RuntimeError as exc:
        raise ValueError(f"{field} changed while being snapshotted") from exc
    if len(items) != len(value):
        raise ValueError(f"{field} changed while being snapshotted")

    snapshot: dict[str, bytes] = {}
    for key, item in items:
        if type(key) is not str:
            raise TypeError(f"{field} keys must be exact built-in strings")
        if type(item) is not bytes:
            raise TypeError(f"{field} values must be exact immutable bytes")
        snapshot[key] = item
    return snapshot


def _snapshot_policy_keys(policy: VerifiedTrustPolicy, verified_at: datetime):
    trust_policy = policy.policy
    if type(trust_policy.issuer_keys) is not tuple:
        raise ValueError("verified policy issuer_keys must be an exact tuple")
    if not 1 <= len(trust_policy.issuer_keys) <= 256:
        raise ValueError("verified policy issuer_keys must contain 1..256 entries")

    by_identity: dict[tuple[str, str], TrustedIssuerKey] = {}
    seen_public_keys: set[bytes] = set()
    for index, key in enumerate(trust_policy.issuer_keys):
        if type(key) is not TrustedIssuerKey:
            raise ValueError(
                f"verified policy issuer_keys[{index}] has an invalid type"
            )
        if (
            type(key.issuer_id) is not str
            or not _IDENTIFIER.fullmatch(key.issuer_id)
            or type(key.key_id) is not str
            or not _IDENTIFIER.fullmatch(key.key_id)
        ):
            raise ValueError(
                f"verified policy issuer_keys[{index}] identity is not canonical"
            )
        if type(key.public_key_bytes) is not bytes or len(key.public_key_bytes) != 32:
            raise ValueError(
                f"verified policy issuer_keys[{index}] public key must be 32 immutable bytes"
            )
        if type(key.revoked) is not bool:
            raise ValueError(
                f"verified policy issuer_keys[{index}] revoked flag must be boolean"
            )
        valid_from = _utc_instant(
            key.valid_from_utc, f"issuer_keys[{index}].valid_from_utc"
        )
        valid_until = _utc_instant(
            key.valid_until_utc, f"issuer_keys[{index}].valid_until_utc"
        )
        if valid_from > valid_until:
            raise ValueError(
                f"verified policy issuer_keys[{index}] validity interval is inverted"
            )
        identity = (key.issuer_id, key.key_id)
        if identity in by_identity:
            raise ValueError("verified policy contains duplicate signer identities")
        if key.public_key_bytes in seen_public_keys:
            raise ValueError("verified policy reuses one public key across identities")
        seen_public_keys.add(key.public_key_bytes)
        by_identity[identity] = key
    return by_identity


def verify_independent_provenance_with_nested_signatures(
    original_receipt_bytes: bytes,
    *,
    original_manifest_bytes: bytes,
    verified_trust_policy: VerifiedTrustPolicy,
    verification_time: datetime,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
) -> PhysicalEvidenceSignatureChainInspection:
    """Verify receipt/manifest byte binding and every nested manifest signature.

    The artifact map must contain the exact 17 physical artifact byte strings
    plus the exact manifest bytes, keyed by their SHA-256 digests. The signature
    map must contain exactly the detached signature bytes declared by the
    manifest. Signer identity/key lookup is against the issuer keys in the
    already-verified policy envelope.

    Policy v1 does not authorize roles, and the manifest has no per-signature
    trusted timestamp. The function therefore reports role strings only as
    claims, makes no pre-close signature-existence assertion, and always
    returns BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(original_manifest_bytes) is not bytes:
        raise TypeError("original_manifest_bytes must be exact bytes")
    if type(verified_trust_policy) is not VerifiedTrustPolicy:
        raise TypeError("verified_trust_policy must be an exact VerifiedTrustPolicy")
    if type(verification_time) is not datetime:
        raise TypeError("verification_time must be an exact datetime")

    verified_at = _utc_instant(verification_time, "verification_time")
    artifact_bytes = _snapshot_bytes_mapping(
        artifact_bytes_by_sha256, "artifact_bytes_by_sha256"
    )
    signature_bytes = _snapshot_bytes_mapping(
        signature_bytes_by_sha256, "signature_bytes_by_sha256"
    )

    # This first composes VerifiedTrustPolicy -> receipt attestation -> exact
    # receipt/manifest claims -> all original physical artifact bytes.
    binding = verify_independent_provenance_with_physical_manifest(
        original_receipt_bytes,
        original_manifest_bytes=original_manifest_bytes,
        verified_trust_policy=verified_trust_policy,
        verification_time=verified_at,
        artifact_bytes_by_sha256=artifact_bytes,
    )
    if binding.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("physical manifest binding returned an unknown provenance status")

    manifest = parse_unverified_physical_manifest(original_manifest_bytes)
    expected_signature_digests = {
        item.signature_sha256 for item in manifest.signatures
    }
    if set(signature_bytes) != expected_signature_digests:
        missing = sorted(expected_signature_digests - set(signature_bytes))
        extra = sorted(set(signature_bytes) - expected_signature_digests)
        raise ValueError(
            "nested signature byte set mismatch; "
            f"missing={missing}, unexpected={extra}"
        )
    for digest, original in signature_bytes.items():
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError("nested signature SHA-256 does not match manifest claim")

    keys_by_identity = _snapshot_policy_keys(verified_trust_policy, verified_at)
    payload = canonical_physical_manifest_signature_payload(original_manifest_bytes)
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
        valid_from = _utc_instant(
            key.valid_from_utc, f"signatures[{index}] key.valid_from_utc"
        )
        valid_until = _utc_instant(
            key.valid_until_utc, f"signatures[{index}] key.valid_until_utc"
        )
        if not valid_from <= verified_at <= valid_until:
            raise ValueError(
                f"signatures[{index}] signer key is outside policy validity at verification time"
            )
        try:
            Ed25519PublicKey.from_public_bytes(key.public_key_bytes).verify(
                signature_bytes[claim.signature_sha256], payload
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

    return PhysicalEvidenceSignatureChainInspection(
        binding=binding,
        policy_envelope_sha256=verified_trust_policy.envelope_sha256,
        policy_sequence=verified_trust_policy.policy_sequence,
        verification_time_utc=verified_at,
        artifact_count=len(manifest.artifacts),
        signatures_verified=len(results),
        signature_results=tuple(results),
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        role_authorization_status=ROLE_AUTHORIZATION_UNVERIFIED,
        signature_creation_time_status="NOT_INDEPENDENTLY_PROVEN",
        trusted_time_status="UNVERIFIED_RFC3161_REQUIRED",
        ledger_status="UNVERIFIED_EXTERNAL_INCLUSION_REQUIRED",
        custody_status="UNVERIFIED_INDEPENDENT_RECEIPTS_REQUIRED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        status=SIGNATURE_CHAIN_STATUS,
        remaining_blockers=NESTED_SIGNATURE_REMAINING_BLOCKERS,
    )


def verify_independent_provenance_with_signed_policy_and_nested_signatures(
    original_receipt_bytes: bytes,
    *,
    original_manifest_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
) -> PhysicalEvidenceSignatureChainInspection:
    """Verify raw signed policy bytes before composing the complete signature chain.

    This is the deployment-facing composition entry point. It deliberately does
    not accept a caller-constructed VerifiedTrustPolicy. The policy object is
    created inside this call by verifying the exact signed envelope against the
    supplied root pin, key ID, sequence floor, and one normalized verification
    instant; only that verifier-created object is passed into the receipt,
    manifest, original-byte, and nested-signature chain.

    The root pin, expected key ID, sequence floor, and original clock remain
    caller/deployment supplied and unauthenticated. A successful result remains
    BLOCKED_PROVENANCE and does not authenticate institutional provenance.
    """
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")

    # Sample an untrusted tzinfo exactly once. Both policy verification and the
    # downstream receipt/signature checks receive this same immutable UTC instant.
    verified_at = _utc_instant(verification_time, "verification_time")
    verified_policy = verify_signed_trust_policy(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    return verify_independent_provenance_with_nested_signatures(
        original_receipt_bytes,
        original_manifest_bytes=original_manifest_bytes,
        verified_trust_policy=verified_policy,
        verification_time=verified_at,
        artifact_bytes_by_sha256=artifact_bytes_by_sha256,
        signature_bytes_by_sha256=signature_bytes_by_sha256,
    )
