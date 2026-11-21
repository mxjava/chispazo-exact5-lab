"""Fail-closed verifier for an independently signed prospective custody receipt.

This module does not create custody evidence. It validates a receipt produced by
an independently operated custodian and verifies its Sigstore bundle with cosign.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class CustodyError(ValueError):
    pass


RECEIPT_KEYS = {
    "schema_version", "receipt_type", "manifest_sha256", "contest_id", "modality", "candidate_id",
    "source_commit_sha", "payload_sha256", "payload_size_bytes",
    "received_at_utc", "official_close_at_utc", "originator_identity",
    "custodian_identity", "retention_uri", "retention_object_version",
    "independent_retrieval_test",
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CustodyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _loads_json(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise CustodyError(f"{label} must be supplied as exact bytes")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CustodyError(f"cannot parse strict JSON {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CustodyError(f"{label} must contain a JSON object")
    return value


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError(f"manifest cannot be represented as strict JSON: {exc}") from exc


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CustodyError(f"cannot read strict JSON {path}: {exc}") from exc
    return _loads_json(raw, str(path))


def _utc(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str):
        raise CustodyError(f"{field} must be an ISO-8601 string")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CustodyError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise CustodyError(f"{field} must be timezone-aware UTC")
    return parsed.astimezone(dt.timezone.utc)


def _read_regular_file(path: Path, label: str) -> bytes:
    """Read one regular, non-symlink input into an immutable byte snapshot."""
    if path.is_symlink():
        raise CustodyError(f"{label} must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CustodyError(f"cannot open {label} as a regular file: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CustodyError(f"{label} must be a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read()
    except OSError as exc:
        raise CustodyError(f"cannot read {label}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def validate_receipt(
    manifest: dict[str, Any],
    receipt: dict[str, Any],
    payload_path: Path,
    *,
    manifest_bytes: bytes,
    expected_custodian_identity: str,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(manifest_bytes, bytes):
        raise CustodyError("manifest_bytes must be the exact captured manifest bytes")
    parsed_manifest = _loads_json(manifest_bytes, "captured manifest")
    if _canonical_json_bytes(parsed_manifest) != _canonical_json_bytes(manifest):
        raise CustodyError("manifest object does not match the exact captured manifest bytes")
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    missing = sorted(RECEIPT_KEYS - receipt.keys())
    extra = sorted(receipt.keys() - RECEIPT_KEYS)
    if missing or extra:
        raise CustodyError(f"receipt key mismatch; missing={missing}, extra={extra}")
    if receipt["schema_version"] != "1.1" or receipt["receipt_type"] != "INDEPENDENT_CUSTODY_RECEIPT":
        raise CustodyError("unsupported receipt schema or receipt_type")
    declared_manifest_digest = receipt["manifest_sha256"]
    if not isinstance(declared_manifest_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", declared_manifest_digest):
        raise CustodyError("manifest_sha256 must be a lowercase 64-hex SHA-256")
    if declared_manifest_digest != manifest_digest:
        raise CustodyError("receipt manifest_sha256 does not match the exact manifest bytes")
    contest_id = receipt["contest_id"]
    if isinstance(contest_id, bool) or not isinstance(contest_id, int) or contest_id <= 0:
        raise CustodyError("contest_id must be a positive integer")
    if receipt["modality"] != "CLASSIC":
        raise CustodyError("only CLASSIC custody receipts are accepted")
    for key in ("contest_id", "modality", "candidate_id", "source_commit_sha", "payload_sha256"):
        if receipt[key] != manifest.get(key):
            raise CustodyError(f"receipt/manifest mismatch: {key}")
    if not isinstance(receipt["candidate_id"], str) or not receipt["candidate_id"].strip():
        raise CustodyError("candidate_id must be non-empty")
    if not isinstance(receipt["source_commit_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", receipt["source_commit_sha"]):
        raise CustodyError("source_commit_sha must be a lowercase 40-hex SHA")
    digest = receipt["payload_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise CustodyError("payload_sha256 must be a lowercase 64-hex SHA-256")
    if not payload_path.is_file() or payload_path.is_symlink():
        raise CustodyError("payload must be an existing regular file (symlinks refused)")
    raw = payload_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise CustodyError("payload bytes do not match the receipt SHA-256")
    size = receipt["payload_size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size != len(raw):
        raise CustodyError("payload_size_bytes does not match actual payload bytes")
    originator = receipt["originator_identity"]
    custodian = receipt["custodian_identity"]
    if not isinstance(originator, str) or not originator.strip():
        raise CustodyError("originator_identity must be non-empty")
    if not isinstance(custodian, str) or not custodian.strip():
        raise CustodyError("custodian_identity must be non-empty")
    if custodian != expected_custodian_identity:
        raise CustodyError("custodian identity does not match externally configured trust policy")
    if custodian == originator:
        raise CustodyError("custodian and originator identities must be distinct")
    if not isinstance(receipt["retention_uri"], str) or not receipt["retention_uri"].startswith("https://"):
        raise CustodyError("retention_uri must identify an HTTPS retention location")
    if not isinstance(receipt["retention_object_version"], str) or not receipt["retention_object_version"].strip():
        raise CustodyError("retention_object_version must be non-empty")
    if receipt["independent_retrieval_test"] is not True:
        raise CustodyError("independent retrieval test must be explicitly true")
    received = _utc(receipt["received_at_utc"], "received_at_utc")
    close = _utc(receipt["official_close_at_utc"], "official_close_at_utc")
    generated = _utc(manifest.get("generated_at_utc"), "manifest.generated_at_utc")
    manifest_close = _utc(manifest.get("scheduled_close_at_utc"), "manifest.scheduled_close_at_utc")
    if close != manifest_close:
        raise CustodyError("receipt official close does not match manifest")
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        raise CustodyError("verification clock must be timezone-aware")
    if received < generated:
        raise CustodyError("custodian receipt predates manifest generation")
    if received >= close:
        raise CustodyError("custodian receipt was issued at/after official close")
    if received > current.astimezone(dt.timezone.utc) + dt.timedelta(minutes=2):
        raise CustodyError("custodian receipt timestamp is in the future")
    return {
        "status": "CUSTODY_RECEIPT_VALIDATED_PENDING_SIGNATURE_VERIFICATION",
        "contest_id": contest_id,
        "payload_sha256": actual,
        "payload_size_bytes": len(raw),
        "custodian_identity": custodian,
        "received_at_utc": received.isoformat().replace("+00:00", "Z"),
        "official_close_at_utc": close.isoformat().replace("+00:00", "Z"),
        "note": "Structural and byte-integrity checks passed; cryptographic verification is a separate mandatory step.",
    }


def verify_signature(
    receipt_path: Path, bundle_path: Path, identity: str, issuer: str
) -> dt.datetime:
    if not identity.strip() or not issuer.strip():
        raise CustodyError("trusted custodian identity and OIDC issuer must be configured explicitly")

    # Cosign and the timestamp parser must consume the exact same receipt and
    # bundle bytes. Never verify one path and then parse that mutable path again.
    receipt_bytes = _read_regular_file(receipt_path, "custody receipt")
    bundle_bytes = _read_regular_file(bundle_path, "Sigstore bundle")
    with tempfile.TemporaryDirectory(prefix="exact5-custody-verify-") as temporary:
        snapshot_dir = Path(temporary)
        receipt_snapshot = snapshot_dir / "receipt.json"
        bundle_snapshot = snapshot_dir / "bundle.json"
        receipt_snapshot.write_bytes(receipt_bytes)
        bundle_snapshot.write_bytes(bundle_bytes)
        receipt_snapshot.chmod(0o400)
        bundle_snapshot.chmod(0o400)
        command = [
            "cosign", "verify-blob", "--bundle", str(bundle_snapshot),
            "--certificate-identity", identity,
            "--certificate-oidc-issuer", issuer,
            str(receipt_snapshot),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise CustodyError("cosign is required but was not found") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "signature verification failed").strip()
            raise CustodyError(f"custodian signature verification failed: {detail}") from exc

        # Refuse even an unexpected mutation of the private snapshots during
        # verification. Parse the captured bundle bytes, not the source path.
        if receipt_snapshot.read_bytes() != receipt_bytes or bundle_snapshot.read_bytes() != bundle_bytes:
            raise CustodyError("receipt or Sigstore bundle changed during signature verification")
        bundle = _load_json(bundle_snapshot)

    material = bundle.get("verificationMaterial")
    entries = material.get("tlogEntries") if isinstance(material, dict) else None
    if not isinstance(entries, list) or not entries:
        raise CustodyError("verified Sigstore bundle has no transparency-log timestamp")
    timestamps: list[dt.datetime] = []
    for entry in entries:
        if not isinstance(entry, dict) or "integratedTime" not in entry:
            continue
        raw_time = entry["integratedTime"]
        if isinstance(raw_time, bool) or not isinstance(raw_time, (str, int)):
            continue
        try:
            timestamps.append(dt.datetime.fromtimestamp(int(raw_time), tz=dt.timezone.utc))
        except (ValueError, OverflowError, OSError):
            continue
    if len(timestamps) != 1:
        raise CustodyError("Sigstore bundle must contain exactly one valid Rekor integratedTime")
    return timestamps[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--custodian-identity", required=True)
    parser.add_argument("--oidc-issuer", required=True)
    args = parser.parse_args(argv)
    try:
        # Freeze all four inputs once. Structural validation, payload hashing,
        # Cosign verification and Rekor-time parsing then share those exact bytes.
        with tempfile.TemporaryDirectory(prefix="exact5-custody-input-") as temporary:
            snapshot_dir = Path(temporary)
            inputs = {
                "manifest": (args.manifest, "manifest.json"),
                "receipt": (args.receipt, "receipt.json"),
                "payload": (args.payload, "payload.bin"),
                "bundle": (args.bundle, "bundle.json"),
            }
            snapshots: dict[str, Path] = {}
            for label, (source_path, filename) in inputs.items():
                raw = _read_regular_file(source_path, label)
                snapshot = snapshot_dir / filename
                snapshot.write_bytes(raw)
                snapshot.chmod(0o400)
                snapshots[label] = snapshot

            manifest = _load_json(snapshots["manifest"])
            receipt = _load_json(snapshots["receipt"])
            manifest_bytes = snapshots["manifest"].read_bytes()
            report = validate_receipt(
                manifest, receipt, snapshots["payload"],
                manifest_bytes=manifest_bytes,
                expected_custodian_identity=args.custodian_identity,
            )
            integrated_at = verify_signature(
                snapshots["receipt"], snapshots["bundle"],
                args.custodian_identity, args.oidc_issuer,
            )
            received = _utc(report["received_at_utc"], "received_at_utc")
            close = _utc(report["official_close_at_utc"], "official_close_at_utc")
            if integrated_at < received - dt.timedelta(minutes=2):
                raise CustodyError("Rekor timestamp materially predates the custodian receipt time")
            if integrated_at >= close:
                raise CustodyError("custodian receipt signature entered transparency log at/after official close")
            report["status"] = "CUSTODY_ACCEPTED"
            report["signature"] = "COSIGN_VERIFIED"
            report["rekor_integrated_at_utc"] = integrated_at.isoformat().replace("+00:00", "Z")
            print(json.dumps(report, sort_keys=True, indent=2))
            return 0
    except (CustodyError, OSError) as exc:
        print(f"BLOCKED_PROVENANCE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
