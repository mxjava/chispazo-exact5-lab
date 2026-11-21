import datetime as dt
import hashlib
import itertools
import json

from src.validation import independent_custody as custody


def _canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def test_main_rejects_rekor_time_before_manifest_generation(tmp_path, monkeypatch, capsys):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    generated = now - dt.timedelta(seconds=90)
    received = now - dt.timedelta(seconds=30)
    integrated = generated - dt.timedelta(seconds=1)
    close = now + dt.timedelta(hours=1)

    payload_bytes = ("\n".join(
        "-".join(f"{number:02d}" for number in combo)
        for combo in itertools.islice(itertools.combinations(range(1, 29), 5), 30)
    ) + "\n").encode("utf-8")
    schedule_bytes = b"official schedule evidence fixture"
    payload_path = tmp_path / "portfolio.txt"
    schedule_path = tmp_path / "schedule.bin"
    manifest_path = tmp_path / "manifest.json"
    receipt_path = tmp_path / "receipt.json"
    bundle_path = tmp_path / "bundle.json"

    payload_path.write_bytes(payload_bytes)
    schedule_path.write_bytes(schedule_bytes)
    bundle_path.write_bytes(b"{}")
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    schedule_sha = hashlib.sha256(schedule_bytes).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "contest_id": 12399,
        "modality": "CLASSIC",
        "candidate_id": "candidate-A",
        "source_commit_sha": "a" * 40,
        "input_history_sha256": "c" * 64,
        "input_max_contest_id": 12398,
        "payload_sha256": payload_sha,
        "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
        "scheduled_close_at_utc": close.isoformat().replace("+00:00", "Z"),
        "timezone": "UTC",
        "status": "READY_FOR_ATTESTATION",
        "schedule_source_url": "https://www.loterianacional.gob.mx/Chispazo/Chispazo",
        "schedule_source_sha256": schedule_sha,
        "schedule_source_archive_path": "data/schedule-evidence/official-schedule-fixture.html",
    }
    manifest_bytes = _canonical_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)

    receipt = {
        "schema_version": "1.1",
        "receipt_type": "INDEPENDENT_CUSTODY_RECEIPT",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "contest_id": 12399,
        "modality": "CLASSIC",
        "candidate_id": "candidate-A",
        "source_commit_sha": "a" * 40,
        "payload_sha256": payload_sha,
        "payload_size_bytes": len(payload_bytes),
        "received_at_utc": received.isoformat().replace("+00:00", "Z"),
        "official_close_at_utc": close.isoformat().replace("+00:00", "Z"),
        "originator_identity": "https://github.com/example/generator",
        "custodian_identity": "https://custodian.example/attestor",
        "retention_uri": "https://vault.example/object/abc",
        "retention_object_version": "version-0001",
        "independent_retrieval_test": True,
    }
    receipt_path.write_bytes(_canonical_bytes(receipt))

    # Exercise main() end-to-end through parsing, file capture and receipt
    # validation. Only the external Cosign call is isolated; Rekor time remains
    # the adversarial value returned by verify_signature.
    monkeypatch.setattr(custody, "verify_signature", lambda *args: integrated)
    result = custody.main([
        "--manifest", str(manifest_path),
        "--receipt", str(receipt_path),
        "--payload", str(payload_path),
        "--schedule-evidence", str(schedule_path),
        "--bundle", str(bundle_path),
        "--custodian-identity", receipt["custodian_identity"],
        "--oidc-issuer", "https://token.actions.githubusercontent.com",
    ])

    assert result == 2
    assert "Rekor timestamp must strictly follow manifest generation" in capsys.readouterr().err
