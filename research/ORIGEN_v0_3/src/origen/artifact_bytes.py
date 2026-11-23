"""Verify supplied original artifact bytes against an unverified manifest.

This establishes byte-level consistency only. It does not authenticate the
source, acquisition channel, signer, timestamp, custody, or institutional role.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .physical_evidence_manifest_v1 import UnverifiedPhysicalEvidenceManifest


@dataclass(frozen=True, slots=True)
class ArtifactByteIntegrityCheck:
    """Digest/length match for one supplied artifact; not a provenance receipt."""

    sha256: str
    byte_length: int


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
    expected = {item.sha256: item for item in manifest.artifacts}
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
