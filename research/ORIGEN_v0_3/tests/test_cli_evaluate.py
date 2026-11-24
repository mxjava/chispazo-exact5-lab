"""CLI integration tests for the declared, unverified anytime e-value input."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from origen import cli


class TestEvaluateCliEValueForwarding(unittest.TestCase):
    def test_cli_forwards_declared_evalue_without_claiming_verification(self):
        payload = {
            "observations": [{"p_alt": 0.1, "p_null": 1 / 98280}],
            "protocol_status": "DRAFT",
            "family_p_values": {"primary": 0.5},
            "primary_test_id": "primary",
            "gates": {},
            "exact5_max_log_e_value": 3.25,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            output = io.StringIO()
            with patch("sys.argv", ["origen", "evaluate", "--file", str(path)]):
                with patch("origen.cli.evaluate_log_scores", return_value={
                    "state": "NO_EDGE_EVIDENCE",
                    "exact5_e_value_provenance": "CALLER_DECLARED_UNVERIFIED",
                }) as evaluator:
                    with contextlib.redirect_stdout(output):
                        cli.main()

        kwargs = evaluator.call_args.kwargs
        self.assertEqual(kwargs["exact5_max_log_e_value"], 3.25)
        self.assertEqual(kwargs["protocol_status"], "DRAFT")
        self.assertEqual(
            json.loads(output.getvalue())["exact5_e_value_provenance"],
            "CALLER_DECLARED_UNVERIFIED",
        )

    def test_cli_omitted_evalue_is_forwarded_as_none(self):
        payload = {
            "observations": [{"p_alt": 0.1, "p_null": 1 / 98280}],
            "protocol_status": "DRAFT",
            "family_p_values": {"primary": 0.5},
            "primary_test_id": "primary",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch("sys.argv", ["origen", "evaluate", "--file", str(path)]):
                with patch("origen.cli.evaluate_log_scores", return_value={}) as evaluator:
                    with contextlib.redirect_stdout(io.StringIO()):
                        cli.main()
        self.assertIsNone(evaluator.call_args.kwargs["exact5_max_log_e_value"])


if __name__ == "__main__":
    unittest.main()
