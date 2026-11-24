"""Verify supplied original artifact bytes against an unverified manifest.

This establishes byte-level consistency only. It does not authenticate the
source, acquisition channel, signer, timestamp, custody, or institutional role.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .physical_evidence_manifest_v1 import (
    PhysicalArtifactClaim,
    PhysicalManifestTarget,
    REQUIRED_ARTIFACT_TYPES,
    UnverifiedPhysicalEvidenceManifest,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
_CONTEST_ID = re.compile(r"[1-9][0-9]{0,11}\\Z")


@dataclass(frozen=True, slots=True)
class ArtifactByteIntegrityCheck:
    """Digest/length match for one supplied artifact; not a provenance receipt."""

    sha256: str
    byte_length: int


def _validated_expected_artifacts(
    manifest: UnverifiedPhysicalEvidenceManifest,
) -> dict[str, PhysicalArtifactClaim]:
    """Recheck every field this verifier relies on, even for frozen instances.

    Frozen dataclasses can still be mutated deliberately with object.__setattr__.
    Exact outer type checks therefore do not establish field invariants.
    """
    target = manifest.target
    if type(target) is not PhysicalManifestTarget:
        raise TypeError("manifest target must be an exact PhysicalManifestTarget")
    if type(target.modality) is not str or target.modality != "CLASSIC":
        raise ValueError("manifest target modality must be exact CLASSIC")
    if type(target.contest_id) is not str or not _CONTEST_ID.fullmatch(target.contest_id):
        raise ValueError("manifest target contest ID is malformed")

    claims = manifest.artifacts
    if type(claims) is not tuple or len(claims) != len(REQUIRED_ARTIFACT_TYPES):
        raise TypeError("manifest artifacts must be an exact tuple of all required claims")

    expected: dict[str, PhysicalArtifactClaim] = {}
    artifact_types: set[str] = set()
    for index, claim in enumerate(claims):
        if type(claim) is not PhysicalArtifactClaim:
            raise TypeError(f"manifest artifact claim {index} has an unexpected type")
        if type(claim.artifact_type) is not str or claim.artifact_type not in REQUIRED_ARTIFACT_TYPES:
            raise ValueError(f"manifest artifact claim {index} has an invalid artifact type")
        if claim.artifact_type in artifact_types:
            raise ValueError("manifest artifact claims contain duplicate artifact types")
        artifact_types.add(claim.artifact_type)
        if type(claim.sha256) is not str or not _SHA256.fullmatch(claim.sha256):
            raise ValueError(f"manifest artifact claim {index} has a malformed SHA-256")
        if claim.sha256 in expected:
            raise ValueError("manifest artifact claims contain duplicate SHA-256 digests")
        if type(claim.byte_length) is not int or claim.byte_length <= 0:
            raise ValueError(f"manifest artifact claim {index} has an invalid byte length")
        if type(claim.contest_id) is not str or claim.contest_id != target.contest_id:
            raise ValueError(f"manifest artifact claim {index} is not bound to its target contest")
        expected[claim.sha256] = claim

    if artifact_types != REQUIRED_ARTIFACT_TYPES:
        missing = sorted(REQUIRED_ARTIFACT_TYPES - artifact_types)
        raise ValueError(f"manifest artifact claims omit required artifact types: {missing}")
    return expected


def verify_declared_artifact_bytes(
    manifest: UnverifiedPhysicalEvidenceManifest,
    artifacts_by_sha256: dict[str, bytes],
) -> tuple[ArtifactByteIntegrityCheck, ...]:
    """Require exactly the manifest artifact set and verify every byte string.

    The caller must supply immutable, exact bytes keyed by the lowercase
    SHA-256 declared in the parsed manifest. Missing, extra, mutable, malformed,
    wrong-length, or wrong-digest inputs fail closed.
    """
    if type(manifest) is not UnverifiedPhysicalEvidenceManifest:
        raise TypeError("manifest must be an exact UnverifiedPhysicalEvidenceManifest")
    if type(artifacts_by_sha256) is not dict:
        raise TypeError("artifacts_by_sha256 must be an exact dict")
    # A str subclass can override hashing/equality. Reject it before set
    # construction or dictionary lookup so key comparison cannot execute
    # caller-controlled methods at this integrity boundary.
    if any(type(key) is not str for key in artifacts_by_sha256):
        raise TypeError("artifact digest keys must be exact str")
    expected = _validated_expected_artifacts(manifest)
    supplied = set(artifacts_by_sha256)
    if supplied != set(expected):
        missing = sorted(set(expected) - supplied)
        extra = sorted(supplied - set(expected))
        raise ValueError(
            f"artifact byte set mismatch; missing={missing}, unexpected={extra}"
        )

    checks: list[ArtifactByteIntegrityCheck] = []
    for digest, claim in expected.items():
        original = artifacts_by_sha256[digest]
        if type(original) is not bytes:
            raise TypeError(f"artifact {digest} must be exact immutable bytes")
        actual_length = len(original)
        if actual_length != claim.byte_length:
            raise ValueError(
                f"artifact {digest} byte length mismatch: "
                f"declared={claim.byte_length}, actual={actual_length}"
            )
        actual_digest = hashlib.sha256(original).hexdigest()
        if actual_digest != digest:
            raise ValueError(
                f"artifact {digest} SHA-256 mismatch: actual={actual_digest}"
            )
        checks.append(ArtifactByteIntegrityCheck(digest, actual_length))
    return tuple(checks)
