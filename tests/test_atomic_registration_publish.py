import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
from freeze_prediction import publish_immutable_registration


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
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob(".*.tmp")) == []


def test_existing_registration_bytes_are_never_replaced(tmp_path):
    dest = tmp_path / "target_12311.json"
    dest.write_text('{"original":true}', encoding="utf-8")
    with pytest.raises(SystemExit, match="already exists"):
        publish_immutable_registration(dest, '{"replacement":true}')
    assert dest.read_text(encoding="utf-8") == '{"original":true}'
    assert list(tmp_path.glob(".*.tmp")) == []
