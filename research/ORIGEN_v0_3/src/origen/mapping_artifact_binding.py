"""Bind V2 sphere rows to mapping bytes declared by an unverified V1 manifest.

The public entry point accepts the original manifest bytes, not a caller-created
PhysicalArtifactClaim. Parsing still yields unverified declarations: this module
does not authenticate issuer, signatures, custody, trusted time, or authority,
and it does not parse the mapping format or prove its 28 assignments.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .physical_evidence_manifest_v1 import (
    PhysicalArtifactClaim,
    parse_unverified_physical_manifest,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTEST_ID = re.compile(r"[1-9][0-9]{0,11}\Z")
_SPHERE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:/@+-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class MappingArtifactByteBinding:
    """Successful byte match; deliberately not an authenticated provenance receipt."""

    contest_id: str
    source_object_id: str
    sha256: str
    byte_length: int
    manifest_sha256: str
    row_count: int
    status: str = "MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED"


def verify_mapping_artifact_byte_binding(
    rows: Iterable[Mapping[str, Any]],
    original_manifest_bytes: bytes,
    original_mapping_bytes: bytes,
) -> MappingArtifactByteBinding:
    """Parse original manifest bytes, select its unique mapping claim, and bind rows.

    The manifest parser validates canonical structure only. It does not
    authenticate the manifest or its declarations. The exact original mapping
    bytes must match the mapping claim extracted from those parsed bytes.
    """
    if type(original_manifest_bytes) is not bytes:
        raise TypeError("original_manifest_bytes must be exact immutable bytes")
    manifest = parse_unverified_physical_manifest(original_manifest_bytes)
    mapping_claims = tuple(
        item for item in manifest.artifacts
        if item.artifact_type == "SPHERE-NUMBER-MAPPING-REGISTER"
    )
    if len(mapping_claims) != 1:
        raise ValueError("manifest must contain exactly one mapping-register claim")
    claim = mapping_claims[0]
    return _verify_mapping_claim_byte_binding(
        rows, claim, original_mapping_bytes, manifest_sha256=manifest.raw_sha256
    )


def _verify_mapping_claim_byte_binding(
    rows: Iterable[Mapping[str, Any]],
    claim: PhysicalArtifactClaim,
    original_bytes: bytes,
    *,
    manifest_sha256: str = "0" * 64,
) -> MappingArtifactByteBinding:
    """Internal structural check for a claim already extracted from parsed bytes."""
    if type(claim) is not PhysicalArtifactClaim:
        raise TypeError("claim must be an exact PhysicalArtifactClaim")
    if type(claim.artifact_type) is not str or claim.artifact_type != "SPHERE-NUMBER-MAPPING-REGISTER":
        raise ValueError("claim must be SPHERE-NUMBER-MAPPING-REGISTER")
    if (
        type(claim.contest_id) is not str
        or not _CONTEST_ID.fullmatch(claim.contest_id)
        or type(claim.source_object_id) is not str
        or not _SPHERE_ID.fullmatch(claim.source_object_id)
        or type(claim.sha256) is not str
        or not _SHA256.fullmatch(claim.sha256)
        or type(claim.byte_length) is not int
        or claim.byte_length <= 0
    ):
        raise ValueError("mapping manifest claim is malformed")
    if type(original_bytes) is not bytes:
        raise TypeError("original mapping artifact must be exact immutable bytes")
    if len(original_bytes) != claim.byte_length:
        raise ValueError("mapping artifact byte length does not match manifest claim")
    actual_digest = hashlib.sha256(original_bytes).hexdigest()
    if actual_digest != claim.sha256:
        raise ValueError("mapping artifact SHA-256 does not match manifest claim")

    if type(rows) not in (list, tuple) or len(rows) != 28:
        raise ValueError("exactly 28 V2 sphere rows are required")
    sphere_ids: set[str] = set()
    printed_numbers: set[str] = set()
    for index, row in enumerate(rows):
        if type(row) is not dict:
            raise TypeError(f"row {index} must be an exact dict")
        target_id = row.get("target_contest_id")
        artifact_ref = row.get("mapping_artifact_ref")
        artifact_digest = row.get("mapping_artifact_sha256")
        if type(target_id) is not str or target_id != claim.contest_id:
            raise ValueError("V2 target contest does not match mapping manifest claim")
        if type(artifact_ref) is not str or artifact_ref != claim.source_object_id:
            raise ValueError("V2 mapping artifact reference does not match manifest claim")
        if type(artifact_digest) is not str or artifact_digest != claim.sha256:
            raise ValueError("V2 mapping artifact digest does not match manifest claim")
        sphere_id = row.get("sphere_id")
        printed_number = row.get("printed_number")
        if type(sphere_id) is not str or not _SPHERE_ID.fullmatch(sphere_id):
            raise ValueError(f"row {index} has a malformed sphere_id")
        if type(printed_number) is not str or not re.fullmatch(
            r"(?:[1-9]|1[0-9]|2[0-8])", printed_number
        ):
            raise ValueError(f"row {index} has a printed_number outside 1..28")
        sphere_ids.add(sphere_id)
        printed_numbers.add(printed_number)
    if len(sphere_ids) != 28 or printed_numbers != {str(number) for number in range(1, 29)}:
        raise ValueError("V2 rows must contain 28 unique spheres and printed numbers 1..28")

    return MappingArtifactByteBinding(
        contest_id=claim.contest_id,
        source_object_id=claim.source_object_id,
        sha256=claim.sha256,
        byte_length=claim.byte_length,
        manifest_sha256=manifest_sha256,
        row_count=28,
    )
