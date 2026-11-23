from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from origen.custody import (
    GENESIS, build_seal_record, read_record, sha256_bytes,
    verify_seal_record, verify_record_chain, write_record_exclusive,
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
            candidate_spec_sha256="f" * 64,
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
        self.assertEqual(verify_seal_record(record, raw), (True, "seal verified; external identity, timestamp, and custody assertions remain unverified"))

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

    def test_boolean_history_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "integer exactly"):
            self.make_record(history_max_contest_id=True)

    def test_wrong_chain_link_rejected(self):
        record, raw = self.make_record()
        ok, reason = verify_seal_record(record, raw, expected_previous="e" * 64)
        self.assertFalse(ok)
        self.assertIn("chain link", reason)

    def test_generator_and_custodian_must_be_distinct(self):
        with self.assertRaisesRegex(ValueError, "identities must be distinct"):
            self.make_record(custodian_id="generator-test")

    def test_equal_generation_and_receipt_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "strictly follow"):
            self.make_record(received_at_utc="2026-11-20T17:00:00Z")

    def test_verifier_rejects_boolean_target_id_even_with_rehashed_record(self):
        record, raw = self.make_record()
        record["target_contest_id"] = True
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        import hashlib
        record["record_sha256"] = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        ok, reason = verify_seal_record(record, raw)
        self.assertFalse(ok)
        self.assertIn("target_contest_id", reason)

    def test_verifier_rejects_unknown_or_missing_schema_fields(self):
        record, raw = self.make_record()
        record.pop("candidate_spec_sha256")
        ok, reason = verify_seal_record(record, raw)
        self.assertFalse(ok)
        self.assertIn("exact v1 schema", reason)

    def test_empty_chain_is_not_reported_as_verified(self):
        ok, reason = verify_record_chain([], {})
        self.assertFalse(ok)
        self.assertEqual(reason, "custody chain must contain at least one record")

    def test_full_chain_verifies(self):
        first, raw1 = self.make_record()
        second, raw2 = self.make_record(
            target_contest_id=12251,
            history_max_contest_id=12250,
            previous_record_sha256=first["record_sha256"],
            generated_at_utc="2026-11-20T18:01:00Z",
            received_at_utc="2026-11-20T18:02:00Z",
            official_draw_close_at_utc="2026-11-20T19:00:00Z",
        )
        self.assertEqual(
            verify_record_chain([first, second], {12250: raw1, 12251: raw2}),
            (True, "verified 2 ordered custody records"),
        )

    def test_external_head_anchor_detects_deleted_tail(self):
        first, raw1 = self.make_record()
        second, raw2 = self.make_record(
            target_contest_id=12251, history_max_contest_id=12250,
            previous_record_sha256=first["record_sha256"],
            generated_at_utc="2026-11-20T18:01:00Z",
            received_at_utc="2026-11-20T18:02:00Z",
            official_draw_close_at_utc="2026-11-20T19:00:00Z",
        )
        ok, reason = verify_record_chain(
            [first], {12250: raw1}, expected_final_hash=second["record_sha256"]
        )
        self.assertFalse(ok)
        self.assertIn("tail truncation", reason)

    def test_chain_detects_deleted_middle_record(self):
        first, raw1 = self.make_record()
        second, raw2 = self.make_record(
            target_contest_id=12251, history_max_contest_id=12250,
            previous_record_sha256=first["record_sha256"],
            generated_at_utc="2026-11-20T18:01:00Z",
            received_at_utc="2026-11-20T18:02:00Z",
            official_draw_close_at_utc="2026-11-20T19:00:00Z",
        )
        third, raw3 = self.make_record(
            target_contest_id=12252, history_max_contest_id=12251,
            previous_record_sha256=second["record_sha256"],
            generated_at_utc="2026-11-20T19:01:00Z",
            received_at_utc="2026-11-20T19:02:00Z",
            official_draw_close_at_utc="2026-11-20T20:00:00Z",
        )
        ok, reason = verify_record_chain([first, third], {12250: raw1, 12252: raw3})
        self.assertFalse(ok)
        self.assertIn("chain link", reason)

    def test_chain_rejects_reordered_records(self):
        first, raw1 = self.make_record()
        second, raw2 = self.make_record(
            target_contest_id=12251, history_max_contest_id=12250,
            previous_record_sha256=first["record_sha256"],
            generated_at_utc="2026-11-20T18:01:00Z",
            received_at_utc="2026-11-20T18:02:00Z",
            official_draw_close_at_utc="2026-11-20T19:00:00Z",
        )
        ok, reason = verify_record_chain([second, first], {12250: raw1, 12251: raw2})
        self.assertFalse(ok)
        self.assertIn("chain link", reason)

    def test_chain_rejects_duplicate_target(self):
        first, raw = self.make_record()
        duplicate = dict(first)
        ok, reason = verify_record_chain([first, duplicate], {12250: raw})
        self.assertFalse(ok)
        self.assertIn("duplicate", reason)

    def test_exclusive_writer_rejects_bad_digest(self):
        record, _ = self.make_record()
        record["custodian_id"] = "forged"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                write_record_exclusive(Path(tmp) / "forged.json", record)

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

    def test_read_record_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_bytes(b'{"outer":{"x":1,"x":2}}\n')
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                read_record(path)

    def test_read_record_rejects_non_finite_json_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_bytes(b'{"value":NaN}\n')
            with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                read_record(path)

    def test_read_record_rejects_oversized_file_before_json_decode(self):
        from origen.custody import MAX_CUSTODY_RECORD_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized.json"
            path.write_bytes(b" " * (MAX_CUSTODY_RECORD_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "maximum size"):
                read_record(path)

    def test_read_record_rejects_excessive_json_nesting(self):
        from origen.custody import MAX_CUSTODY_RECORD_JSON_DEPTH
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep.json"
            depth = MAX_CUSTODY_RECORD_JSON_DEPTH + 1
            path.write_bytes((b"[" * depth) + b"0" + (b"]" * depth) + b"\n")
            with self.assertRaisesRegex(ValueError, "maximum nesting depth"):
                read_record(path)

    def test_read_record_ignores_brackets_inside_json_strings_for_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brackets-in-string.json"
            brackets = "[" * 40
            path.write_bytes(b'{"value":"' + brackets.encode("ascii") + b'"}\\n')
            self.assertEqual(read_record(path), {"value": brackets})
    def test_read_record_rejects_floating_point_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "float.json"
            path.write_bytes(b'{"value":1.25}\n')
            with self.assertRaisesRegex(ValueError, "floating-point JSON numbers"):
                read_record(path)

    def test_read_record_rejects_noncanonical_json_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "noncanonical.json"
            path.write_bytes(b'{"value": 1}\n')
            with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON"):
                read_record(path)

    def test_non_utc_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            self.make_record(generated_at_utc="2026-11-20T11:00:00-06:00")

    def test_invalid_numbers_rejected(self):
        raw = portfolio_bytes().replace(b"02-", b"29-", 1)
        with self.assertRaises(ValueError):
            self.make_record(portfolio=raw)

    def test_builder_rejects_non_30_line_classic_portfolio(self):
        with self.assertRaisesRegex(ValueError, "exactly 30 lines"):
            self.make_record(expected_lines=1)

    def test_verifier_rejects_self_consistent_short_portfolio_record(self):
        record, raw = self.make_record()
        short = raw.splitlines()[0] + b"\n"
        import hashlib
        record["portfolio_sha256"] = hashlib.sha256(short).hexdigest()
        record["custodian_recomputed_sha256"] = record["portfolio_sha256"]
        record["portfolio_line_count"] = 1
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        record["record_sha256"] = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        ok, reason = verify_seal_record(record, short)
        self.assertFalse(ok)
        self.assertEqual(reason, "portfolio_line_count must equal 30")

if __name__ == "__main__":
    unittest.main()
