"""Concurrency regression tests for the ORIGEN append-only event ledger."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from origen.search_ledger import append_event, audit_ledger


def test_concurrent_appends_preserve_one_valid_chain_and_unique_ids(tmp_path: Path):
    ledger = tmp_path / "prospective.jsonl"

    def append(index: int) -> str:
        return append_event(
            ledger,
            {
                "event_id": f"event-{index:03d}",
                "timestamp_utc": f"2026-11-24T12:{index // 60:02d}:{index % 60:02d}Z",
                "event_type": "prospective_snapshot",
                "frame_id": "classic-2026-11-24",
                "details": {"ordinal": index},
            },
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        digests = list(pool.map(append, range(48)))

    result = audit_ledger(ledger)
    assert len(digests) == 48
    assert result["state"] == "PASS"
    assert result["events"] == 48
    assert result["errors"] == []
