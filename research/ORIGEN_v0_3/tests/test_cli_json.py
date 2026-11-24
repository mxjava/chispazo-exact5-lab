"""Adversarial tests for strict JSON ingestion at the ORIGEN CLI boundary."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from origen.cli import _frames, _load


class TestStrictCliJson(unittest.TestCase):
    def test_load_rejects_duplicate_top_level_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"protocol_status":"DRAFT","protocol_status":"PREREGISTERED"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unambiguous_finite_json"):
                _load(path)

    def test_load_rejects_duplicate_nested_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"gates":{"independent_custody":false,"independent_custody":true}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unambiguous_finite_json"):
                _load(path)

    def test_load_rejects_non_finite_json_constants(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "input.json"
                path.write_text('{"score":' + token + '}', encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "unambiguous_finite_json"):
                    _load(path)

    def test_load_accepts_unambiguous_finite_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"p_values":{"primary":0.01},"alpha":0.05}', encoding="utf-8")
            self.assertEqual(_load(path), {"p_values": {"primary": 0.01}, "alpha": 0.05})

    def test_frames_rejects_duplicate_keys_with_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frames.jsonl"
            path.write_text('{"frame_id":"f1"}\n{"frame_id":"f2","frame_id":"attacker"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid_json_line_2"):
                _frames(path)

    def test_frames_rejects_non_finite_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frames.jsonl"
            path.write_text('{"frame_id":"f1","score":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid_json_line_1"):
                _frames(path)


if __name__ == "__main__":
    unittest.main()
