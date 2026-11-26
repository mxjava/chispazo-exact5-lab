import unittest
from src.portfolio_benchmark import _line_mask, canonical_registration_hash, validate_records, benchmark

class PortfolioBenchmarkTests(unittest.TestCase):
    def test_line_mask(self):
        self.assertEqual(_line_mask("01-02-03-04-05").bit_count(), 5)

    def test_rejects_duplicate_numbers(self):
        with self.assertRaisesRegex(ValueError, "invalid_line_numbers"):
            _line_mask("01-01-03-04-05")

    def test_requires_30_distinct_lines(self):
        record = {"target":123,"modality":"CLASSIC","commit_sha":"a"*40,
                  "registered_at_utc":"2026-11-01T10:00:00Z","sales_cutoff_utc":"2026-11-01T12:00:00Z",
                  "lines":["01-02-03-04-05"]*30}
        record["registration_sha256"] = canonical_registration_hash(record)
        with self.assertRaisesRegex(ValueError, "portfolio_lines_must_be_distinct"):
            validate_records({"schema":"EXACT5_FROZEN_PORTFOLIOS_V1","records":[record]},
                             {"123":record["registration_sha256"]},{123:31})

    def test_rejects_post_cutoff_registration(self):
        record = {"target":123,"modality":"CLASSIC","commit_sha":"a"*40,
                  "registered_at_utc":"2026-11-01T13:00:00Z","sales_cutoff_utc":"2026-11-01T12:00:00Z",
                  "lines":[f"{i:02d}-20-21-22-23" for i in range(1,19)] +
                          [f"{i:02d}-24-25-26-27" for i in range(1,13)]}
        record["registration_sha256"] = canonical_registration_hash(record)
        with self.assertRaisesRegex(ValueError, "registration_not_pre_cutoff"):
            validate_records({"schema":"EXACT5_FROZEN_PORTFOLIOS_V1","records":[record]},
                             {"123":record["registration_sha256"]},{123:31})

    def test_random_null_reproducible_and_research_only(self):
        masks = [_line_mask(f"{i:02d}-20-21-22-23") for i in range(1,19)] + [_line_mask(f"{i:02d}-24-25-26-27") for i in range(1,13)]
        record = {"target":123,"masks":masks,"result_mask":_line_mask("01-02-03-04-05")}
        a = benchmark([record], replicates=999, seed=17)
        self.assertEqual(a, benchmark([record], replicates=999, seed=17))
        self.assertEqual(a["state"], "RESEARCH_ONLY_NO_EDGE")
        self.assertGreaterEqual(a["empirical_upper_tail_p"]["mean_best_hits"], .001)

if __name__ == "__main__":
    unittest.main()
