from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from origen import cli


class PhysicalIntakeV2CliTests(unittest.TestCase):
    def test_v2_cli_passes_independent_verification_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "evidence.csv"
            csv_path.write_text("header\\n", encoding="utf-8")
            manifest_path = root / "verified.json"
            manifest_path.write_text(json.dumps({
                "custody_refs": ["RECEIPT-1"],
                "timestamp_refs": ["TSA-1"],
                "source_refs": ["DOC-1"],
                "calibration_refs": ["a" * 64],
                "continuity_targets": ["12301"],
            }), encoding="utf-8")
            output = io.StringIO()
            with patch("sys.argv", [
                "origen", "validate-physical-v2", "--file", str(csv_path),
                "--verification-file", str(manifest_path),
            ]), patch("origen.cli.evaluate_temporal_csv", return_value={"status": "ELIGIBILITY_REVIEWED"}) as evaluate:
                with contextlib.redirect_stdout(output):
                    cli.main()
            self.assertEqual(json.loads(output.getvalue())["status"], "ELIGIBILITY_REVIEWED")
            kwargs = evaluate.call_args.kwargs
            self.assertEqual(kwargs["verified_custody_refs"], {"RECEIPT-1"})
            self.assertEqual(kwargs["verified_timestamp_refs"], {"TSA-1"})
            self.assertEqual(kwargs["verified_source_refs"], {"DOC-1"})
            self.assertEqual(kwargs["verified_calibration_refs"], {"a" * 64})
            self.assertEqual(kwargs["verified_continuity_targets"], {"12301"})

    def test_v2_cli_rejects_unknown_verification_manifest_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "evidence.csv"
            csv_path.write_text("header\\n", encoding="utf-8")
            manifest_path = root / "verified.json"
            manifest_path.write_text(json.dumps({"trust_me": True}), encoding="utf-8")
            with patch("sys.argv", [
                "origen", "validate-physical-v2", "--file", str(csv_path),
                "--verification-file", str(manifest_path),
            ]):
                with self.assertRaisesRegex(ValueError, "unsupported keys"):
                    cli.main()


if __name__ == "__main__":
    unittest.main()
