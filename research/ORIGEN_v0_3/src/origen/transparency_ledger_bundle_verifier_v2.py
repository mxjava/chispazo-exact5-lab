"""Research-only V2 ledger leaf binding an RFC 3161 nested-signature sidecar.

The V2 leaf commits to both the canonical timestamp-bundle digest and the
exact RFC 3161 token DER digest. The manifest continues to commit to the
inclusion-proof digest; the timestamp bundle omits only that digest to avoid
a cycle. Every result remains BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .independent_trust_adapter import ProvenanceStatus
from .nested_signature_bundle_timestamp_v1 import (
    NestedSignatureBundleTimestampInspectionV1,
    canonical_nested_signature_bundle_timestamp_payload_v1,
    verify_nested_signature_bundle_timestamp_v1,
)
from .physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from .physical_evidence_verifier_v2 import _utc_instant
from .transparency_ledger_verifier_v1 import (
    CHECKPOINT_DOMAIN,
    CHECKPOINT_SCHEMA,
    LEDGER_REMAINING_BLOCKERS,
    MAX_TREE_SIZE,
    _decode_canonical_base64,
    _digest,
    _exact_fields,
    _identifier,
    _load_canonical_object,
    _manifest_commitment_sha256,
    _parse_inclusion_proof,
    _parse_utc_timestamp,
    _verify_inclusion,
)

ENTRY_SCHEMA_V2 = "origen.transparency-ledger-entry.v2"
MAX_TIMESTAMP_BUNDLE_BYTES = 8 * 1024 * 1024

BUNDLE_LEDGER_REMAINING_BLOCKERS = tuple(dict.fromkeys((
    *LEDGER_REMAINING_BLOCKERS,
    "TSA_ROOT_AND_POLICY_OID_NOT_INDEPENDENTLY_PROVISIONED",
    "TSA_CERTIFICATE_REVOCATION_AND_OCSP_FRESHNESS_NOT_VERIFIED",
    "VERIFICATION_CLOCK_NOT_INDEPENDENTLY_AUTHENTICATED",
    "SIGNER_KEY_AUTHORIZATION_AT_CREATION_REMAINS_UNPROVEN",
    "INSTITUTIONAL_SIGNER_IDENTITY_AND_DELEGATION_NOT_AUTHENTICATED",
    "PHYSICAL_ARTIFACT_ORIGIN_AND_INDEPENDENT_CUSTODY_NOT_AUTHENTICATED",
)))


@dataclass(frozen=True, slots=True)
class TransparencyLedgerBundleInspectionV2:
    ledger_id: str
    entry_id: str
    manifest_sha256: str
    manifest_commitment_sha256: str
    ledger_entry_sha256: str
    inclusion_proof_sha256: str
    timestamp_bundle_sha256: str
    timestamp_token_sha256: str
    timestamp_bundle_bytes_verified: bool
    timestamp_token_digest_committed: bool
    timestamp_bundle_digest_committed: bool
    timestamp_existence_preclose_verified: bool
    timestamp_inspection: NestedSignatureBundleTimestampInspectionV1
    log_id: str
    key_id: str
    tree_size: int
    leaf_index: int
    checkpoint_sha256: str
    checkpoint_signature_verified: bool
    inclusion_verified: bool
    trust_anchor_source: str
    anti_rollback_source: str
    verification_clock_source: str
    append_only_continuity_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _snapshot_exact_byte_map(value: object, field: str) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError(f"{field} must be an exact dict")
    try:
        items = tuple(value.items())
    except RuntimeError as exc:
        raise ValueError(f"{field} changed while being snapshotted") from exc
    if len(items) != len(value):
        raise ValueError(f"{field} changed while being snapshotted")
    snapshot: dict[str, bytes] = {}
    for key, raw in items:
        if type(key) is not str:
            raise TypeError(f"{field} keys must be exact strings")
        if type(raw) is not bytes:
            raise TypeError(f"{field} values must be exact immutable bytes")
        snapshot[key] = raw
    return snapshot


def verify_transparency_ledger_bundle_inclusion_v2(
    raw_manifest_bytes: bytes,
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_signed_checkpoint_bytes: bytes,
    raw_timestamp_bundle_bytes: bytes,
    timestamp_token_der: bytes,
    signed_policy_envelope_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    *,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_tree_size: int,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_tsa_policy_oid: str,
    expected_nonce: int,
    verification_time: datetime,
) -> TransparencyLedgerBundleInspectionV2:
    """Verify the exact timestamp sidecar is committed by an included V2 leaf.

    This function rebuilds the sidecar from the original manifest, signed
    policy, artifact bytes and signature bytes. It then independently verifies
    the RFC 3161 token, exact V2 ledger-leaf fields, signed checkpoint and
    inclusion proof. The log/TSA roots, monotonic floor and clock are still
    request inputs; this is a diagnostic composition, not an independent trust
    provider or production authorization boundary.
    """
    if type(raw_manifest_bytes) is not bytes or not raw_manifest_bytes:
        raise ValueError("raw_manifest_bytes must be non-empty exact bytes")
    if type(raw_ledger_entry_bytes) is not bytes:
        raise TypeError("raw_ledger_entry_bytes must be exact bytes")
    if type(raw_inclusion_proof_bytes) is not bytes:
        raise TypeError("raw_inclusion_proof_bytes must be exact bytes")
    if type(raw_signed_checkpoint_bytes) is not bytes:
        raise TypeError("raw_signed_checkpoint_bytes must be exact bytes")
    if type(raw_timestamp_bundle_bytes) is not bytes or not raw_timestamp_bundle_bytes:
        raise ValueError("raw_timestamp_bundle_bytes must be non-empty exact bytes")
    if len(raw_timestamp_bundle_bytes) > MAX_TIMESTAMP_BUNDLE_BYTES:
        raise ValueError("raw_timestamp_bundle_bytes exceeds the sidecar size limit")
    if type(timestamp_token_der) is not bytes or not timestamp_token_der:
        raise ValueError("timestamp_token_der must be non-empty exact bytes")
    if type(pinned_log_public_key_bytes) is not bytes or len(pinned_log_public_key_bytes) != 32:
        raise ValueError("pinned_log_public_key_bytes must be exactly 32 bytes")
    if type(minimum_tree_size) is not int or not 1 <= minimum_tree_size <= MAX_TREE_SIZE:
        raise ValueError("minimum_tree_size must be a positive signed 64-bit integer")

    verified_at = _utc_instant(verification_time, "verification_time")
    expected_log_id = _identifier(expected_log_id, "expected_log_id")
    expected_log_key_id = _identifier(expected_log_key_id, "expected_log_key_id")

    # Snapshot both maps once and pass only those immutable-bytes snapshots to
    # the canonical builder and downstream verifier. This closes a TOCTOU gap
    # where a caller could mutate a mapping between the two verification steps.
    artifacts_snapshot = _snapshot_exact_byte_map(
        artifact_bytes_by_sha256, "artifact_bytes_by_sha256"
    )
    signatures_snapshot = _snapshot_exact_byte_map(
        signature_bytes_by_sha256, "signature_bytes_by_sha256"
    )
    # Reconstruct the sidecar from exact inputs; never trust a supplied digest
    # or a caller-created inspection object as a substitute for its bytes.
    rebuilt_bundle = canonical_nested_signature_bundle_timestamp_payload_v1(
        raw_manifest_bytes,
        signed_policy_envelope_bytes,
        artifacts_snapshot,
        signatures_snapshot,
    )
    if rebuilt_bundle != raw_timestamp_bundle_bytes:
        raise ValueError("timestamp bundle bytes do not equal the canonical exact-evidence sidecar")
    timestamp_inspection = verify_nested_signature_bundle_timestamp_v1(
        raw_manifest_bytes,
        signed_policy_envelope_bytes,
        artifacts_snapshot,
        signatures_snapshot,
        timestamp_token_der,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        pinned_tsa_root_certificate_der=pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256=expected_tsa_root_sha256,
        expected_tsa_policy_oid=expected_tsa_policy_oid,
        expected_nonce=expected_nonce,
        verification_time=verified_at,
    )
    bundle_sha256 = hashlib.sha256(raw_timestamp_bundle_bytes).hexdigest()
    token_sha256 = hashlib.sha256(timestamp_token_der).hexdigest()
    if timestamp_inspection.bundle_sha256 != bundle_sha256:
        raise RuntimeError("timestamp verifier did not bind the exact bundle bytes")
    if timestamp_inspection.timestamp_token_sha256 != token_sha256:
        raise RuntimeError("timestamp verifier did not bind the exact RFC 3161 token bytes")

    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    manifest_commitment = _manifest_commitment_sha256(raw_manifest_bytes)
    artifact_sha256s = tuple(sorted(item.sha256 for item in manifest.artifacts))
    entry = _load_canonical_object(
        raw_ledger_entry_bytes,
        maximum=65_536,
        label="V2 ledger entry",
    )
    _exact_fields(
        entry,
        {
            "schema_version",
            "ledger_id",
            "entry_id",
            "manifest_commitment_sha256",
            "artifact_sha256s",
            "timestamp_bundle_sha256",
            "timestamp_token_sha256",
        },
        "V2 ledger entry",
    )
    if entry["schema_version"] != ENTRY_SCHEMA_V2:
        raise ValueError("unsupported ledger entry schema; V2 timestamp commitment is required")
    ledger_id = _identifier(manifest.ledger_anchor.ledger_id, "manifest ledger_id")
    entry_id = _identifier(manifest.ledger_anchor.entry_id, "manifest entry_id")
    if _identifier(entry["ledger_id"], "V2 ledger entry ledger_id") != ledger_id:
        raise ValueError("V2 ledger entry ledger_id does not match manifest")
    if _identifier(entry["entry_id"], "V2 ledger entry entry_id") != entry_id:
        raise ValueError("V2 ledger entry entry_id does not match manifest")
    if _digest(entry["manifest_commitment_sha256"], "V2 manifest_commitment_sha256") != manifest_commitment:
        raise ValueError("V2 ledger entry manifest commitment does not match normalized manifest claims")
    claimed_artifacts = entry["artifact_sha256s"]
    if type(claimed_artifacts) is not list:
        raise ValueError("V2 ledger entry artifact_sha256s must be an array")
    parsed_artifacts = tuple(
        _digest(value, f"V2 artifact_sha256s[{index}]")
        for index, value in enumerate(claimed_artifacts)
    )
    if parsed_artifacts != tuple(sorted(set(parsed_artifacts))) or parsed_artifacts != artifact_sha256s:
        raise ValueError("V2 ledger entry artifact digests must be unique, sorted and exact")
    if _digest(entry["timestamp_bundle_sha256"], "timestamp_bundle_sha256") != bundle_sha256:
        raise ValueError("V2 ledger entry does not commit to the exact timestamp bundle SHA-256")
    if _digest(entry["timestamp_token_sha256"], "timestamp_token_sha256") != token_sha256:
        raise ValueError("V2 ledger entry does not commit to the exact RFC 3161 token SHA-256")

    checkpoint = _load_canonical_object(
        raw_signed_checkpoint_bytes,
        maximum=16_384,
        label="signed ledger checkpoint",
    )
    _exact_fields(
        checkpoint,
        {
            "schema_version",
            "log_id",
            "key_id",
            "tree_size",
            "root_hash",
            "issued_at_utc",
            "signature_b64",
        },
        "signed ledger checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA:
        raise ValueError("unsupported signed ledger checkpoint schema")
    log_id = _identifier(checkpoint["log_id"], "checkpoint log_id")
    key_id = _identifier(checkpoint["key_id"], "checkpoint key_id")
    if log_id != expected_log_id or key_id != expected_log_key_id:
        raise ValueError("checkpoint log/key identity does not match pinned expectation")
    tree_size = checkpoint["tree_size"]
    if type(tree_size) is not int or not 1 <= tree_size <= MAX_TREE_SIZE:
        raise ValueError("checkpoint tree_size must be a positive signed 64-bit integer")
    if tree_size < minimum_tree_size:
        raise ValueError("checkpoint tree_size is below the caller-supplied monotonic floor")
    root_hash = bytes.fromhex(_digest(checkpoint["root_hash"], "checkpoint root_hash"))
    issued_at = _parse_utc_timestamp(checkpoint["issued_at_utc"], "checkpoint issued_at_utc")
    if issued_at > verified_at:
        raise ValueError("checkpoint issued_at_utc is later than supplied verification time")
    signature = _decode_canonical_base64(checkpoint["signature_b64"], "checkpoint signature_b64")
    if len(signature) != 64:
        raise ValueError("checkpoint Ed25519 signature must be exactly 64 bytes")
    unsigned_checkpoint = dict(checkpoint)
    unsigned_checkpoint.pop("signature_b64")
    signed_payload = CHECKPOINT_DOMAIN + json.dumps(
        unsigned_checkpoint,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    try:
        Ed25519PublicKey.from_public_bytes(pinned_log_public_key_bytes).verify(
            signature, signed_payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("signed ledger checkpoint signature verification failed") from exc

    checkpoint_sha256 = hashlib.sha256(raw_signed_checkpoint_bytes).hexdigest()
    leaf_index, audit_path = _parse_inclusion_proof(
        raw_inclusion_proof_bytes,
        expected_proof_sha256=manifest.ledger_anchor.inclusion_proof_sha256,
        expected_ledger_id=ledger_id,
        expected_entry_id=entry_id,
        expected_log_id=log_id,
        expected_checkpoint_sha256=checkpoint_sha256,
    )
    if leaf_index >= tree_size:
        raise ValueError("proof leaf_index must be smaller than checkpoint tree_size")
    _verify_inclusion(
        raw_ledger_entry_bytes,
        leaf_index,
        tree_size,
        audit_path,
        root_hash,
    )

    return TransparencyLedgerBundleInspectionV2(
        ledger_id=ledger_id,
        entry_id=entry_id,
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        manifest_commitment_sha256=manifest_commitment,
        ledger_entry_sha256=hashlib.sha256(raw_ledger_entry_bytes).hexdigest(),
        inclusion_proof_sha256=hashlib.sha256(raw_inclusion_proof_bytes).hexdigest(),
        timestamp_bundle_sha256=bundle_sha256,
        timestamp_token_sha256=token_sha256,
        timestamp_bundle_bytes_verified=True,
        timestamp_token_digest_committed=True,
        timestamp_bundle_digest_committed=True,
        timestamp_existence_preclose_verified=timestamp_inspection.signature_existence_preclose_verified,
        timestamp_inspection=timestamp_inspection,
        log_id=log_id,
        key_id=key_id,
        tree_size=tree_size,
        leaf_index=leaf_index,
        checkpoint_sha256=checkpoint_sha256,
        checkpoint_signature_verified=True,
        inclusion_verified=True,
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        append_only_continuity_status="UNVERIFIED_NO_CONSISTENCY_PROOF_OR_INDEPENDENT_WITNESS",
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=BUNDLE_LEDGER_REMAINING_BLOCKERS,
    )
