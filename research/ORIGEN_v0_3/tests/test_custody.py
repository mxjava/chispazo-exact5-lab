from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from origen.custody import (
    GENESIS, build_seal_record, read_record, sha256_bytes,
    verify_seal_record, write_record_exclusive,
)


def portfolio_bytes() -> bytes:
    rows = []
    for a in range(1, 31):
        nums = sorted([a % 28 + 1, (a + 4) % 28 + 1, (a + 8) % 28 + 1,
                       (a + 12) % 28 + 1, (a + 16) % 28 + 1])
        row = "-".join(f"{n:02d}" for n in nums)
        if row not in rows:
            rows.append(row)
    # deterministic unique fallback combinations
    n = 1
    while len(rows) < 30:
        combo = sorted({n, n + 1, n + 2, n + 3, n + 4})
        if len(combo) == 5 and combo[-1] <= 28:
            row = "-".join(f"{v:02d}" for v in combo)
            if row not in rows:
                rows.append(row)
        n += 1
    return ("\n".join(rows[:30]) + "\n").encode()


class CustodyTests(unittest.TestCase):
    def make_record(self, portfolio=None, **overrides):
        data = portfolio if portfolio is not None else portfolio_bytes()
        values = dict(
            candidate_id="CANDIDATE-DRYRUN-1",
            target_contest_id=12250,
            history_max_contest_id=12249,
            modality="CLASSIC",
            history_sha256="a" * 64,
            source_commit="b" * 40,
            environment_manifest_sha256="c" * 64,
            portfolio=data,
            generator_id="generator-test",
            generated_at_utc="2026-11-20T17:00:00Z",
            generator_clock_source="dry-run-clock",
            custodian_id="custodian-test",
            received_at_utc="2026-11-20T17:01:00Z",
            custodian_clock_source="independent-dry-run-clock",
            custodian_recomputed_sha256=sha256_bytes(data),
            official_draw_close_at_utc="2026-11-20T18:00:00Z",
            official_draw_close_source="dry-run-only",
            previous_record_sha256=GENESIS,
        )
        values.update(overrides)
        return build_seal_record(**values), data

    def test_valid_seal_verifies(self):
        record, raw = self.make_record()
        self.assertEqual(verify_seal_record(record, raw), (True, "seal verified; independent assertions still require external corroboration"))

    def test_tampered_portfolio_rejected(self):
        record, raw = self.make_record()
        changed = raw.replace(b"\n", b"\n", 1) + b" "
        ok, reason = verify_seal_record(record, changed)
        self.assertFalse(ok)
        self.assertIn("LF", reason)

    def test_record_mutation_rejected(self):
        record, raw = self.make_record()
        record["custodian_id"] = "attacker"
        ok, reason = verify_seal_record(record, raw)
        self.assertFalse(ok)
        self.assertEqual(reason, "record digest mismatch")

    def test_wrong_custodian_hash_rejected_at_build(self):
        raw = portfolio_bytes()
        with self.assertRaisesRegex(ValueError, "custodian hash"):
            self.make_record(portfolio=raw, custodian_recomputed_sha256="d" * 64)

    def test_late_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError, "precede draw close"):
            self.make_record(received_at_utc="2026-11-20T18:00:00Z")

    def test_wrong_modality_rejected(self):
        with self.assertRaisesRegex(ValueError, "CLASSIC"):
            self.make_record(modality="TRES")

    def test_history_cutoff_must_precede_target(self):
        with self.assertRaisesRegex(ValueError, "exactly target"):
            self.make_record(history_max_contest_id=12250)

    def test_wrong_chain_link_rejected(self):
        record, raw = self.make_record()
        ok, reason = verify_seal_record(record, raw, expected_previous="e" * 64)
        self.assertFalse(ok)
        self.assertIn("chain link", reason)

    def test_record_file_is_exclusive(self):
        record, _ = self.make_record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "12250.json"
            write_record_exclusive(path, record)
            self.assertEqual(read_record(path), record)
            with self.assertRaises(FileExistsError):
                write_record_exclusive(path, record)

    def test_duplicate_portfolio_lines_rejected(self):
        raw = portfolio_bytes()
        lines = raw.decode().splitlines()
        lines[-1] = lines[0]
        duplicate = ("\n".join(lines) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "unique"):
            self.make_record(portfolio=duplicate)

    def test_non_utc_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            self.make_record(generated_at_utc="2026-11-20T11:00:00-06:00")

    def test_invalid_numbers_rejected(self):
        raw = portfolio_bytes().replace(b"01-", b"29-", 1)
        with self.assertRaises(ValueError):
            self.make_record(portfolio=raw)

if __name__ == "__main__":
    unittest.main()
