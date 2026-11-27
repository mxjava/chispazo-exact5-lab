"""Bind V2 sphere rows to the mapping-register claim and its original bytes.

This is a byte-integrity/structural binding helper only. A parsed manifest claim is
unverified input: this module does not authenticate its issuer, signature, custody,
trusted time, or institutional authority, and it does not parse the mapping format
or prove that the 28 printed-number assignments match the document.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .physical_evidence_manifest_v1 import PhysicalArtifactClaim

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
    row_count: int
    status: str = "MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED"


def verify_mapping_artifact_byte_binding(
    rows: Iterable[Mapping[str, Any]],
    claim: PhysicalArtifactClaim,
    original_bytes: bytes,
) -> MappingArtifactByteBinding:
    """Require all 28 V2 rows to bind to one manifest mapping claim and exact bytes.

    The claim must be the SPHERE-NUMBER-MAPPING-REGISTER claim parsed from the
    per-contest V1 manifest. The claim itself remains unverified. Mapping bytes
    are opaque here because the institutionally authoritative file format/parser
    has not been established.
    """
    if type(claim) is not PhysicalArtifactClaim:
        raise TypeError("claim must be an exact PhysicalArtifactClaim")
    if type(claim.artifact_type) is not str or claim.artifact_type != "SPHERE-NUMBER-MAPPING-REGISTER":
        raise ValueError("claim must be SPHERE-NUMBER-MAPPING-REGISTER")
    if (
        type(claim.contest_id) is not str
        or not _CONTEST_ID.fullmatch(claim.contest_id)
        or type(claim.source_object_id) is not str
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:/@+-]{0,127}", claim.source_object_id)
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
        row_count=28,
    )
