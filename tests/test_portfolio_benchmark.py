import csv
import itertools
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from src.portfolio_benchmark import (
    _line_mask, benchmark, canonical_draw_hash, canonical_registration_hash, exact_uniform_portfolio_null,
    load_draws, validate_records,
)

def native_record(target=123, registered="2026-11-01T10:00:00+00:00"):
    record = {
        "target": target, "registered_at_utc": registered,
        "registered_at_mexico_city": datetime.fromisoformat(registered).astimezone(ZoneInfo("America/Mexico_City")).isoformat(),
        "commit_sha": "a" * 40, "model_version": "V294",
        "history_max": target - 1, "history_sha256": "b" * 64,
        "ranking_sha256": "c" * 64, "preflight_state": "PASS",
        "gate_summary": {"state": "PASS", "failed_checks": []},
        "lines": ["-".join(f"{n:02d}" for n in combo)
                  for combo in itertools.islice(itertools.combinations(range(1, 29), 5), 30)],
    }
    record["registration_sha256"] = canonical_registration_hash(record)
    return record

def draw_row():
    return {"CONCURSO":"123","MODALITY":"CLASSIC","R1":"1","R2":"2","R3":"3","R4":"4","R5":"5",
            "SOURCE_URL":"https://www.loterianacional.gob.mx/resultado/123",
            "SOURCE_SHA256":"d"*64,"VERIFICATION":"OFFICIAL_PAGE_VERIFIED"}

class PortfolioBenchmarkTests(unittest.TestCase):
    def test_line_mask(self):
        self.assertEqual(_line_mask("01-02-03-04-05").bit_count(), 5)

    def test_rejects_duplicate_numbers(self):
        with self.assertRaisesRegex(ValueError, "invalid_line_numbers"):
            _line_mask("01-01-03-04-05")

    def test_accepts_native_frozen_registration_with_external_cutoff(self):
        record = native_record()
        draw = draw_row()
        anchors = {"123": canonical_draw_hash(draw)}
        draws = {123: _line_mask("01-02-03-04-05")}
        result = validate_records({"schema":"EXACT5_NATIVE_REGISTRATIONS_V1","records":[record]},
            {"123":record["registration_sha256"]},
            {"123":{"modality":"CLASSIC","sales_cutoff_utc":"2026-11-01T12:00:00Z"}}, draws)
        self.assertEqual(len(result[0]["masks"]), 30)

    def test_rejects_native_registration_with_failed_gate_summary(self):
        record = native_record()
        record["gate_summary"] = {"state": "BLOCKED", "failed_checks": ["exact5_anytime"]}
        record["registration_sha256"] = canonical_registration_hash(record)
        with self.assertRaisesRegex(ValueError, "registration_gate_summary_not_pass"):
            validate_records({"schema":"EXACT5_NATIVE_REGISTRATIONS_V1","records":[record]},
                {"123":record["registration_sha256"]},
                {"123":{"modality":"CLASSIC","sales_cutoff_utc":"2026-11-01T12:00:00Z"}},
                {123:_line_mask("01-02-03-04-05")})

    def test_rejects_registration_after_external_cutoff(self):
        record = native_record(registered="2026-11-01T13:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "registration_not_pre_cutoff"):
            validate_records({"schema":"EXACT5_NATIVE_REGISTRATIONS_V1","records":[record]},
                {"123":record["registration_sha256"]},
                {"123":{"modality":"CLASSIC","sales_cutoff_utc":"2026-11-01T12:00:00Z"}},
                {123:_line_mask("01-02-03-04-05")})

    def test_rejects_inconsistent_native_registration_timestamps(self):
        record = native_record()
        record["registered_at_mexico_city"] = "2026-11-01T05:00:00-06:00"
        record["registration_sha256"] = canonical_registration_hash(record)
        with self.assertRaisesRegex(ValueError, "invalid_registration_timestamps"):
            validate_records({"schema":"EXACT5_NATIVE_REGISTRATIONS_V1","records":[record]},
                {"123":record["registration_sha256"]},
                {"123":{"modality":"CLASSIC","sales_cutoff_utc":"2026-11-01T12:00:00Z"}},
                {123:_line_mask("01-02-03-04-05")})

    def test_rejects_unanchored_or_tampered_registration(self):
        record = native_record()
        record["lines"][0] = "01-02-03-04-06"
        with self.assertRaisesRegex(ValueError, "registration_hash_mismatch"):
            validate_records({"schema":"EXACT5_NATIVE_REGISTRATIONS_V1","records":[record]},
                {"123":record["registration_sha256"]},
                {"123":{"modality":"CLASSIC","sales_cutoff_utc":"2026-11-01T12:00:00Z"}},
                {123:_line_mask("01-02-03-04-05")})

    def test_requires_independent_draw_hash_anchor(self):
        row = draw_row()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"draws.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer=csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader(); writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "draw_hash_not_in_external_anchor_file"):
                load_draws(path, {})

    def test_exact_uniform_null_matches_30_over_98280_exact5_mass(self):
        null = exact_uniform_portfolio_null(30)
        self.assertEqual(null["universe"], 98280)
        self.assertAlmostEqual(null["probability_best_hits_at_least_k"]["5"], 30/98280, places=14)
        self.assertAlmostEqual(null["expected_best_hits"],
            sum(null["probability_best_hits_at_least_k"].values()), places=14)

    def test_exact_uniform_null_reference_probabilities(self):
        null = exact_uniform_portfolio_null(30)
        tail = null["probability_best_hits_at_least_k"]
        self.assertAlmostEqual(tail["3"], 0.5590777643899736, places=14)
        self.assertAlmostEqual(tail["4"], 0.034814704405994656, places=14)
        self.assertAlmostEqual(tail["5"], 30/98280, places=14)
        self.assertAlmostEqual(null["expected_best_hits"], 2.5932521779452404, places=13)

    def test_exact_uniform_null_rejects_invalid_portfolio_size(self):
        for value in (0, -1, 98281, True, 30.0):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "lines_must_be_integer"):
                    exact_uniform_portfolio_null(value)

    def test_random_null_reproducible_and_research_only(self):
        masks = [_line_mask("-".join(f"{n:02d}" for n in c))
                 for c in itertools.islice(itertools.combinations(range(1, 29), 5), 30)]
        record = {"target":123,"masks":masks,"result_mask":_line_mask("01-02-03-04-05")}
        a = benchmark([record], replicates=999, seed=17)
        self.assertEqual(a, benchmark([record], replicates=999, seed=17))
        self.assertEqual(a["state"], "RESEARCH_ONLY_NO_EDGE")
        self.assertGreaterEqual(a["empirical_upper_tail_p"]["mean_best_hits"], .001)

if __name__ == "__main__":
    unittest.main()
