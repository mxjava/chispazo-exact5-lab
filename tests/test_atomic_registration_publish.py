import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import freeze_prediction

publish_immutable_registration = freeze_prediction.publish_immutable_registration


def _staged_files(directory):
    return list(directory.glob(".*.tmp"))


def test_registration_is_published_with_exact_contents_and_no_temp_file(tmp_path):
    dest = tmp_path / "target_12311.json"
    serialized = json.dumps({"target": 12311, "complete": True}, separators=(",", ":"))

    publish_immutable_registration(dest, serialized)

    assert dest.read_text(encoding="utf-8") == serialized
    assert _staged_files(tmp_path) == []


def test_competing_publishers_cannot_overwrite_each_other(tmp_path):
    dest = tmp_path / "target_12311.json"
    barrier = Barrier(12)

    def worker(i):
        barrier.wait()
        payload = json.dumps({"writer": i, "complete": True})
        try:
            publish_immutable_registration(dest, payload)
            return (i, "published")
        except SystemExit as exc:
            assert "already exists" in str(exc)
            return (i, "rejected")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(worker, range(12)))

    assert sum(status == "published" for _, status in results) == 1
    stored = json.loads(dest.read_text(encoding="utf-8"))
    assert stored["complete"] is True
    assert stored["writer"] in range(12)
    winner = stored["writer"]
    expected = json.dumps({"writer": winner, "complete": True})
    assert dest.read_text(encoding="utf-8") == expected
    assert _staged_files(tmp_path) == []


def test_existing_registration_bytes_are_never_replaced(tmp_path):
    dest = tmp_path / "target_12311.json"
    dest.write_text('{"original":true}', encoding="utf-8")
    with pytest.raises(SystemExit, match="already exists"):
        publish_immutable_registration(dest, '{"replacement":true}')
    assert dest.read_text(encoding="utf-8") == '{"original":true}'
    assert _staged_files(tmp_path) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows os.rename no-replace fallback")
def test_windows_rename_fallback_publishes_when_hard_links_are_denied(tmp_path, monkeypatch):
    dest = tmp_path / "target_12311.json"
    serialized = '{"published":"via-rename"}'

    def deny_hard_links(_source, _destination):
        raise PermissionError("simulated hard-link restriction")

    monkeypatch.setattr(freeze_prediction.os, "link", deny_hard_links)
    publish_immutable_registration(dest, serialized)

    assert dest.read_text(encoding="utf-8") == serialized
    assert _staged_files(tmp_path) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows os.rename no-replace fallback")
def test_windows_rename_fallback_preserves_existing_destination(tmp_path, monkeypatch):
    dest = tmp_path / "target_12311.json"
    original = '{"original":"must-remain"}'
    dest.write_text(original, encoding="utf-8")

    def deny_hard_links(_source, _destination):
        raise PermissionError("simulated hard-link restriction")

    monkeypatch.setattr(freeze_prediction.os, "link", deny_hard_links)
    with pytest.raises(SystemExit, match="already exists"):
        publish_immutable_registration(dest, '{"replacement":true}')

    assert dest.read_text(encoding="utf-8") == original
    assert _staged_files(tmp_path) == []
