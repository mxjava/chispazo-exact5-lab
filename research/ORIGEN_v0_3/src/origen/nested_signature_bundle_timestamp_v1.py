"""Detached RFC 3161 proof that an exact nested-signature bundle existed by a bounded time.

The bundle is deliberately a sidecar: nested signatures do not sign their own
TSA token digest, avoiding a circular signature/token dependency. The token
imprints the exact manifest bytes, policy bytes, every original artifact byte
string, and every exact detached signature byte string. The ledger must separately commit this sidecar before
it can be treated as part of the full evidence chain. All caller pins remain
unauthenticated and every result remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from .physical_evidence_verifier_v2 import CLASSIC_PHYSICAL_POLICY_DOMAIN, _utc_instant
from .physical_evidence_verifier_v3 import verify_physical_evidence_signatures_v3
from .rfc3161_tsa_verifier_v1 import RFC3161Inspection, verify_rfc3161_timestamp_token
from .trust_policy_envelope_v3 import verify_signed_trust_policy_v3

SCHEMA_VERSION = "origen.nested-signature-bundle-timestamp.v1"
MAX_BUNDLE_BYTES = 8 * 1024 * 1024
MAX_SIGNATURES = 256
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class NestedSignatureTimestampItemV1:
    artifact_sha256: str
    subject_id: str
    claimed_role: str
    key_id: str
    signature_sha256: str
    signature_exists_by_timestamp_upper_bound: bool
    key_validity_at_timestamp_status: str
    role_authorization_at_timestamp_status: str
    key_authorization_at_creation_status: str


@dataclass(frozen=True, slots=True)
class NestedSignatureBundleTimestampInspectionV1:
    manifest_sha256: str
    manifest_commitment_sha256: str
    policy_envelope_sha256: str
    bundle_sha256: str
    timestamp_token_sha256: str
    timestamp_event_id: str
    timestamp: RFC3161Inspection
    accuracy_lower_bound_utc: datetime
    accuracy_upper_bound_utc: datetime
    classic_draw_close_at_utc: datetime
    signatures_timestamped: int
    signature_results: tuple[NestedSignatureTimestampItemV1, ...]
    signature_existence_preclose_verified: bool
    key_authorization_at_creation_status: str
    ledger_binding_status: str
    trust_anchor_source: str
    verification_clock_source: str
    revocation_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


REMAINING_BLOCKERS = (
    "TSA_ROOT_PIN_AND_EXPECTED_POLICY_OID_ARE_CALLER_SUPPLIED",
    "TSA_CERTIFICATE_REVOCATION_AND_OCSP_FRESHNESS_NOT_VERIFIED",
    "VERIFICATION_CLOCK_IS_CALLER_SUPPLIED",
    "SIGNATURE_BUNDLE_SIDECAR_NOT_YET_BOUND_IN_LEDGER_ENTRY",
    "KEY_AUTHORIZATION_AT_SIGNATURE_CREATION_REQUIRES_A_SIGNER_CHALLENGE_BOUND_IN_SIGNATURE",
    "INSTITUTIONAL_SIGNER_IDENTITY_AND_DELEGATION_NOT_AUTHENTICATED",
    "PHYSICAL_ARTIFACT_ORIGIN_AND_INDEPENDENT_CUSTODY_NOT_AUTHENTICATED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


def _snapshot_artifact_bytes(value: object, manifest) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError("artifact_bytes_by_sha256 must be an exact dict")
    try:
        items = tuple(value.items())
    except RuntimeError as exc:
        raise ValueError("artifact byte map changed while being snapshotted") from exc
    if len(items) != len(value):
        raise ValueError("artifact byte map changed while being snapshotted")

    copied: dict[str, bytes] = {}
    for digest, raw in items:
        if type(digest) is not str or not _SHA256.fullmatch(digest):
            raise ValueError("artifact byte map keys must be lowercase SHA-256 digests")
        if type(raw) is not bytes:
            raise TypeError("artifact byte map values must be exact immutable bytes")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("artifact byte map digest does not bind exact bytes")
        copied[digest] = raw

    claims = {item.sha256: item for item in manifest.artifacts}
    if set(copied) != set(claims):
        missing = sorted(set(claims) - set(copied))
        extra = sorted(set(copied) - set(claims))
        raise ValueError(
            "artifact byte map must exactly match manifest claims; "
            f"missing={missing}, unexpected={extra}"
        )
    for digest, claim in claims.items():
        if len(copied[digest]) != claim.byte_length:
            raise ValueError(f"artifact byte length does not match manifest claim: {claim.artifact_type}")
    return copied


def _snapshot_signature_bytes(value: object, manifest) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError("signature_bytes_by_sha256 must be an exact dict")
    try:
        items = tuple(value.items())
    except RuntimeError as exc:
        raise ValueError("signature byte map changed while being snapshotted") from exc
    if len(items) != len(value):
        raise ValueError("signature byte map changed while being snapshotted")

    copied: dict[str, bytes] = {}
    for digest, raw in items:
        if type(digest) is not str or not _SHA256.fullmatch(digest):
            raise ValueError("signature byte map keys must be lowercase SHA-256 digests")
        if type(raw) is not bytes or len(raw) != 64:
            raise ValueError("every nested Ed25519 signature must be exactly 64 immutable bytes")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("signature byte map digest does not bind exact bytes")
        copied[digest] = raw

    expected = {item.signature_sha256 for item in manifest.signatures}
    if len(expected) != len(manifest.signatures) or len(expected) > MAX_SIGNATURES:
        raise ValueError("manifest nested signature set is duplicated or exceeds its bound")
    if set(copied) != expected:
        missing = sorted(expected - set(copied))
        extra = sorted(set(copied) - expected)
        raise ValueError(
            "signature byte map must exactly match manifest claims; "
            f"missing={missing}, unexpected={extra}"
        )
    return copied


def _validate_policy_oid(value: object) -> str:
    if type(value) is not str:
        raise ValueError("expected_tsa_policy_oid must be a canonical numeric OID")
    arcs = value.split(".")
    if len(arcs) < 2 or any(
        not arc.isascii()
        or not arc.isdigit()
        or (len(arc) > 1 and arc.startswith("0"))
        for arc in arcs
    ):
        raise ValueError("expected_tsa_policy_oid must be a canonical numeric OID")
    first, second = int(arcs[0]), int(arcs[1])
    if first not in (0, 1, 2) or (first < 2 and second > 39):
        raise ValueError("expected_tsa_policy_oid has invalid first two arcs")
    return value


def canonical_manifest_content_bytes_v1(raw_manifest_bytes: bytes) -> bytes:
    """Return canonical manifest content with only the ledger proof digest omitted.

    The inclusion-proof digest depends on the ledger entry. A later ledger entry
    must commit to this timestamp bundle, so including that digest in the bundle
    would create a cycle. All other manifest claims remain in these bytes.
    """
    if type(raw_manifest_bytes) is not bytes or not raw_manifest_bytes:
        raise ValueError("raw_manifest_bytes must be non-empty exact bytes")
    parse_unverified_physical_manifest(raw_manifest_bytes)
    document = json.loads(raw_manifest_bytes.decode("utf-8"))
    document["ledger_anchor"].pop("inclusion_proof_sha256")
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_nested_signature_bundle_timestamp_payload_v1(
    raw_manifest_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
) -> bytes:
    """Canonical sidecar payload for normalized manifest, policy, artifacts and signatures.

    Only ledger_anchor.inclusion_proof_sha256 is omitted from the manifest
    content because it depends on the ledger entry that will later commit to
    this bundle. All other manifest claims and exact artifact/signature bytes
    are included. The token is a detached sidecar, not a nested-signature claim.
    """
    if type(raw_manifest_bytes) is not bytes or not raw_manifest_bytes:
        raise ValueError("raw_manifest_bytes must be non-empty exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    normalized_manifest_bytes = canonical_manifest_content_bytes_v1(raw_manifest_bytes)
    artifacts = _snapshot_artifact_bytes(artifact_bytes_by_sha256, manifest)
    signatures = _snapshot_signature_bytes(signature_bytes_by_sha256, manifest)
    claims_by_digest = {item.signature_sha256: item for item in manifest.signatures}
    artifact_claims_by_digest = {item.sha256: item for item in manifest.artifacts}
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "policy_domain": CLASSIC_PHYSICAL_POLICY_DOMAIN,
        "manifest_commitment_sha256": hashlib.sha256(normalized_manifest_bytes).hexdigest(),
        "normalized_manifest_bytes_b64": base64.b64encode(normalized_manifest_bytes).decode("ascii"),
        "policy_envelope_sha256": hashlib.sha256(signed_policy_envelope_bytes).hexdigest(),
        "policy_envelope_bytes_b64": base64.b64encode(signed_policy_envelope_bytes).decode("ascii"),
        "artifacts": [
            {
                "artifact_type": artifact_claims_by_digest[digest].artifact_type,
                "sha256": digest,
                "byte_length": artifact_claims_by_digest[digest].byte_length,
                "bytes_b64": base64.b64encode(artifacts[digest]).decode("ascii"),
            }
            for digest in sorted(artifacts)
        ],
        "signatures": [
            {
                "artifact_sha256": claims_by_digest[digest].artifact_sha256,
                "subject_id": claims_by_digest[digest].subject_id,
                "role": claims_by_digest[digest].role,
                "key_id": claims_by_digest[digest].key_id,
                "algorithm": claims_by_digest[digest].algorithm,
                "signature_sha256": digest,
                "signature_bytes_b64": base64.b64encode(signatures[digest]).decode("ascii"),
            }
            for digest in sorted(signatures)
        ],
    }
    payload = json.dumps(
        bundle,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if len(payload) > MAX_BUNDLE_BYTES:
        raise ValueError("nested signature timestamp bundle exceeds the size limit")
    return payload


def verify_nested_signature_bundle_timestamp_v1(
    raw_manifest_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    timestamp_token_der: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_tsa_policy_oid: str,
    expected_nonce: int,
    verification_time: datetime,
) -> NestedSignatureBundleTimestampInspectionV1:
    """Prove exact nested-signature bytes existed by a bounded pre-close time.

    This proves existence by the RFC 3161 accuracy upper bound, not the exact
    signing instant. Without a nonce/challenge included in each signer's signed
    payload, a signer could have created a signature before key activation and
    obtained its timestamp afterward. Key authorization at creation therefore
    remains explicitly unproven.
    """
    verified_at = _utc_instant(verification_time, "verification_time")
    if type(timestamp_token_der) is not bytes or not timestamp_token_der:
        raise ValueError("timestamp_token_der must be non-empty exact bytes")
    if type(expected_nonce) is not int or not 1 <= expected_nonce <= (1 << 63) - 1:
        raise ValueError("expected_nonce must be an exact positive signed-64-bit integer")

    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    if manifest.target.modality != "CLASSIC":
        raise ValueError("nested signature timestamp bundle is restricted to CLASSIC")
    close_at = datetime.fromisoformat(
        manifest.target.draw_close_at_utc.replace("Z", "+00:00")
    )
    close_at = _utc_instant(close_at, "manifest CLASSIC draw close")

    artifacts = _snapshot_artifact_bytes(artifact_bytes_by_sha256, manifest)
    signatures = _snapshot_signature_bytes(signature_bytes_by_sha256, manifest)
    payload = canonical_nested_signature_bundle_timestamp_payload_v1(
        raw_manifest_bytes,
        signed_policy_envelope_bytes,
        artifacts,
        signatures,
    )
    bundle_sha256 = hashlib.sha256(payload).hexdigest()
    manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()
    manifest_commitment_sha256 = hashlib.sha256(
        canonical_manifest_content_bytes_v1(raw_manifest_bytes)
    ).hexdigest()
    policy_sha256 = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()

    physical = verify_physical_evidence_signatures_v3(
        raw_manifest_bytes,
        artifacts,
        signatures,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    if physical.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("physical signature verifier returned an unexpected provenance status")
    if physical.signatures_verified != len(manifest.signatures):
        raise RuntimeError("physical signature verifier did not verify the complete manifest signature set")
    if physical.manifest_sha256 != manifest_sha256:
        raise RuntimeError("physical signature verifier did not bind the exact manifest bytes")

    policy = verify_signed_trust_policy_v3(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    expected_oid = _validate_policy_oid(expected_tsa_policy_oid)
    timestamp = verify_rfc3161_timestamp_token(
        timestamp_token_der,
        payload,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        verification_time=verified_at,
        expected_nonce=expected_nonce,
    )
    if timestamp.policy_oid != expected_oid:
        raise ValueError("RFC 3161 policy OID does not match the caller-pinned expectation")
    if timestamp.provenance_status != "BLOCKED_PROVENANCE" or not timestamp.nonce_verified:
        raise RuntimeError("RFC 3161 verifier did not preserve its fail-closed nonce-verified result")
    if type(timestamp.accuracy_microseconds) is not int or timestamp.accuracy_microseconds < 0:
        raise ValueError("RFC 3161 accuracy is required for a bounded signature-existence interval")

    accuracy = timedelta(microseconds=timestamp.accuracy_microseconds)
    lower_bound = timestamp.gen_time_utc - accuracy
    upper_bound = timestamp.gen_time_utc + accuracy
    if upper_bound >= close_at:
        raise ValueError("nested signature bundle timestamp accuracy upper bound must be strictly before CLASSIC close")
    if lower_bound < policy.issued_at_utc or lower_bound < policy.not_before_utc:
        raise ValueError("nested signature bundle timestamp accuracy interval precedes signed policy effectiveness")
    if upper_bound >= policy.expires_at_utc:
        raise ValueError("nested signature bundle timestamp accuracy interval crosses policy expiry")

    keys = {
        (key.issuer_id, key.key_id): key
        for key in policy.policy.issuer_keys
    }
    authorizations = {
        (issuer_id, key_id, role, artifact_type)
        for issuer_id, key_id, role, artifact_types in policy.key_authorizations
        for artifact_type in artifact_types
    }
    artifact_types = {item.sha256: item.artifact_type for item in manifest.artifacts}
    results = []
    for claim in manifest.signatures:
        key = keys.get((claim.subject_id, claim.key_id))
        if key is None:
            raise ValueError("nested signature signer is absent from the timestamped signed policy")
        if key.revoked:
            raise ValueError("nested signature signer key is revoked in the timestamped signed policy")
        if not (
            key.valid_from_utc <= lower_bound
            and upper_bound <= key.valid_until_utc
        ):
            raise ValueError("nested signature timestamp interval crosses signer key validity")
        artifact_type = artifact_types[claim.artifact_sha256]
        if (
            claim.subject_id,
            claim.key_id,
            claim.role,
            artifact_type,
        ) not in authorizations:
            raise ValueError("nested signature role/artifact is not authorized by the timestamped signed policy")
        results.append(NestedSignatureTimestampItemV1(
            artifact_sha256=claim.artifact_sha256,
            subject_id=claim.subject_id,
            claimed_role=claim.role,
            key_id=claim.key_id,
            signature_sha256=claim.signature_sha256,
            signature_exists_by_timestamp_upper_bound=True,
            key_validity_at_timestamp_status="VALID_FOR_FULL_TIMESTAMP_ACCURACY_INTERVAL",
            role_authorization_at_timestamp_status="SIGNED_POLICY_MATCH_ONLY",
            key_authorization_at_creation_status="UNPROVEN_NO_SIGNER_CHALLENGE_BOUND_TO_SIGNATURE",
        ))

    token_sha256 = hashlib.sha256(timestamp_token_der).hexdigest()
    return NestedSignatureBundleTimestampInspectionV1(
        manifest_sha256=manifest_sha256,
        manifest_commitment_sha256=manifest_commitment_sha256,
        policy_envelope_sha256=policy_sha256,
        bundle_sha256=bundle_sha256,
        timestamp_token_sha256=token_sha256,
        timestamp_event_id=f"nested-signature-bundle-sha256:{bundle_sha256}",
        timestamp=timestamp,
        accuracy_lower_bound_utc=lower_bound,
        accuracy_upper_bound_utc=upper_bound,
        classic_draw_close_at_utc=close_at,
        signatures_timestamped=len(results),
        signature_results=tuple(results),
        signature_existence_preclose_verified=True,
        key_authorization_at_creation_status="UNPROVEN_NO_SIGNER_CHALLENGE_BOUND_TO_SIGNATURE",
        ledger_binding_status="NOT_BOUND_TO_LEDGER_ENTRY",
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        revocation_status="NOT_CHECKED",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=REMAINING_BLOCKERS,
    )
