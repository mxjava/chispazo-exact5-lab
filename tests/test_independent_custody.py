import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from src.validation.independent_custody import CustodyError, validate_receipt


def fixture(tmp_path: Path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"immutable prediction bytes")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    close = "2026-12-01T23:00:00Z"
    manifest = {
        "contest_id": 12399, "modality": "CLASSIC", "candidate_id": "candidate-A",
        "source_commit_sha": "a" * 40, "payload_sha256": digest,
        "input_history_sha256": "c" * 64, "input_max_contest_id": 12398,
        "generated_at_utc": "2026-12-01T21:59:00Z",
        "scheduled_close_at_utc": close,
    }
    manifest_bytes = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    receipt = {
        "schema_version": "1.1", "receipt_type": "INDEPENDENT_CUSTODY_RECEIPT",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "contest_id": 12399, "modality": "CLASSIC", "candidate_id": "candidate-A",
        "source_commit_sha": "a" * 40, "payload_sha256": digest,
        "payload_size_bytes": len(payload.read_bytes()),
        "received_at_utc": "2026-12-01T22:00:00Z", "official_close_at_utc": close,
        "originator_identity": "https://github.com/example/generator",
        "custodian_identity": "https://custodian.example/attestor",
        "retention_uri": "https://vault.example/object/abc",
        "retention_object_version": "version-0001",
        "independent_retrieval_test": True,
    }
    now = dt.datetime(2026, 12, 1, 22, 30, tzinfo=dt.timezone.utc)
    return manifest, receipt, payload, now, manifest_bytes


def test_accepts_valid_independent_receipt_structure(tmp_path):
    manifest, receipt, payload, now, manifest_bytes = fixture(tmp_path)
    result = validate_receipt(manifest, receipt, payload.read_bytes(),
                              manifest_bytes=manifest_bytes,
                              expected_custodian_identity=receipt["custodian_identity"], now=now)
    assert result["status"] == "CUSTODY_RECEIPT_VALIDATED_PENDING_SIGNATURE_VERIFICATION"


@pytest.mark.parametrize("mutation, message", [
    (lambda r: r.update(custodian_identity="attacker"), "custodian identity"),
    (lambda r: r.update(originator_identity=r["custodian_identity"]), "must be distinct"),
    (lambda r: r.update(received_at_utc="2026-12-01T23:00:00Z"), "at/after official close"),
    (lambda r: r.update(independent_retrieval_test=False), "retrieval test"),
    (lambda r: r.update(payload_size_bytes=1), "payload_size_bytes"),
    (lambda r: r.update(modality="THREE"), "CLASSIC"),
])
def test_rejects_adversarial_receipt_mutations(tmp_path, mutation, message):
    manifest, receipt, payload, now = fixture(tmp_path)
    mutation(receipt)
    with pytest.raises(CustodyError, match=message):
        validate_receipt(manifest, receipt, payload.read_bytes(),
                              manifest_bytes=manifest_bytes,
                         expected_custodian_identity="https://custodian.example/attestor", now=now)


def test_rejects_manifest_metadata_changed_after_receipt(tmp_path):
    manifest, receipt, payload, now, manifest_bytes = fixture(tmp_path)
    changed_manifest = dict(manifest)
    changed_manifest["input_history_sha256"] = "d" * 64
    changed_manifest_bytes = json.dumps(
        changed_manifest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    with pytest.raises(CustodyError, match="manifest_sha256"):
        validate_receipt(
            changed_manifest, receipt, payload.read_bytes(),
            manifest_bytes=changed_manifest_bytes,
            expected_custodian_identity=receipt["custodian_identity"], now=now,
        )


def test_rejects_manifest_object_not_matching_captured_bytes(tmp_path):
    manifest, receipt, payload, now, manifest_bytes = fixture(tmp_path)
    with pytest.raises(CustodyError, match="does not match the exact captured manifest bytes"):
        validate_receipt(
            manifest, receipt, payload.read_bytes(),
            manifest_bytes=b'{"contest_id":999}',
            expected_custodian_identity=receipt["custodian_identity"], now=now,
        )


def test_rejects_payload_byte_mutation(tmp_path):
    manifest, receipt, payload, now = fixture(tmp_path)
    payload.write_bytes(b"tampered bytes")
    with pytest.raises(CustodyError, match="payload bytes"):
        validate_receipt(manifest, receipt, payload.read_bytes(),
                              manifest_bytes=manifest_bytes,
                         expected_custodian_identity=receipt["custodian_identity"], now=now)


def test_rejects_duplicate_json_keys(tmp_path):
    from src.validation.independent_custody import _load_json
    path = tmp_path / "duplicate.json"
    path.write_text('{"contest_id": 1, "contest_id": 2}', encoding="utf-8")
    with pytest.raises(CustodyError, match="duplicate JSON key"):
        _load_json(path)



def test_rejects_receipt_predating_manifest_generation(tmp_path):
    manifest, receipt, payload, now = fixture(tmp_path)
    receipt["received_at_utc"] = "2026-12-01T21:58:00Z"
    with pytest.raises(CustodyError, match="predates manifest generation"):
        validate_receipt(manifest, receipt, payload.read_bytes(),
                              manifest_bytes=manifest_bytes,
                         expected_custodian_identity=receipt["custodian_identity"], now=now)


def test_signature_verification_requires_rekor_integrated_timestamp(tmp_path, monkeypatch):
    import subprocess
    from src.validation.independent_custody import verify_signature

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""))
    receipt_path = tmp_path / "receipt.json"
    bundle_path = tmp_path / "bundle.json"
    receipt_path.write_text('{"receipt":"placeholder"}', encoding="utf-8")
    bundle_path.write_text(json.dumps({
        "verificationMaterial": {
            "tlogEntries": [{"integratedTime": 1796162520}]
        }
    }), encoding="utf-8")
    timestamp = verify_signature(receipt_path.read_bytes(), bundle_path.read_bytes(), "trusted-identity", "trusted-issuer")
    assert timestamp.tzinfo == dt.timezone.utc
    assert timestamp.year == 2026



def test_signature_verification_uses_identical_snapshots_for_cosign_and_rekor(tmp_path, monkeypatch):
    import subprocess
    from src.validation.independent_custody import verify_signature

    receipt_path = tmp_path / "receipt.json"
    bundle_path = tmp_path / "bundle.json"
    original_receipt = b'{"receipt":"original"}'
    original_bundle = json.dumps({
        "verificationMaterial": {"tlogEntries": [{"integratedTime": 1796162520}]}
    }).encode("utf-8")
    receipt_path.write_bytes(original_receipt)
    bundle_path.write_bytes(original_bundle)

    observed = {}
    def mutate_originals_after_cosign_starts(command, **kwargs):
        signed_receipt = Path(command[-1])
        signed_bundle = Path(command[command.index("--bundle") + 1])
        observed["receipt_snapshot"] = signed_receipt.read_bytes()
        observed["bundle_snapshot"] = signed_bundle.read_bytes()
        observed["receipt_is_snapshot"] = signed_receipt != receipt_path
        observed["bundle_is_snapshot"] = signed_bundle != bundle_path
        receipt_path.write_bytes(b'{"receipt":"swapped"}')
        bundle_path.write_text(json.dumps({
            "verificationMaterial": {"tlogEntries": [{"integratedTime": 1796169999}]}
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", mutate_originals_after_cosign_starts)
    timestamp = verify_signature(receipt_path.read_bytes(), bundle_path.read_bytes(), "trusted-identity", "trusted-issuer")
    assert observed["receipt_snapshot"] == original_receipt
    assert observed["bundle_snapshot"] == original_bundle
    assert observed["receipt_is_snapshot"] is True
    assert observed["bundle_is_snapshot"] is True
    assert timestamp == dt.datetime.fromtimestamp(1796162520, tz=dt.timezone.utc)

def test_signature_verification_rejects_bundle_without_rekor_timestamp(tmp_path, monkeypatch):
    import subprocess
    from src.validation.independent_custody import verify_signature

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""))
    receipt_path = tmp_path / "receipt.json"
    bundle_path = tmp_path / "bundle.json"
    receipt_path.write_text('{"receipt":"placeholder"}', encoding="utf-8")
    bundle_path.write_text('{"verificationMaterial": {"tlogEntries": []}}', encoding="utf-8")
    with pytest.raises(CustodyError, match="no transparency-log timestamp"):
        verify_signature(receipt_path, bundle_path, "trusted-identity", "trusted-issuer")
