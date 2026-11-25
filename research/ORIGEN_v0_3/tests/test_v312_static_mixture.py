import math
import unittest

from origen.v312_static_mixture import (
    EXPERTS, UNIFORM, _expert_probability, _mixture_probability,
    evaluate_v312,
)


def fixture_rows(count=8):
    rows = []
    for i in range(count):
        rows.append({
            "contest": 5923 + 2 * i,
            "date": f"2020-01-{i+1:02d}",
            "numbers": [((i * 3 + j * 5) % 28) + 1 for j in range(5)],
            "draw_type": "DE_LAS_TRES",
        })
        rows.append({
            "contest": 5924 + 2 * i,
            "date": f"2020-01-{i+1:02d}",
            "numbers": [((i * 7 + j * 3 + 1) % 28) + 1 for j in range(5)],
            "draw_type": "CLASSIC",
        })
    return rows


class V312StaticMixtureTests(unittest.TestCase):
    def test_exactly_27_nonuniform_experts(self):
        self.assertEqual(len(EXPERTS), 27)

    def test_constant_signal_expert_is_uniform(self):
        probability = _expert_probability([1.0] * 28, 0.30, [1, 2, 3, 4, 5])
        self.assertAlmostEqual(probability, UNIFORM, places=14)

    def test_fixed_mixture_has_uniform_probability_floor(self):
        features = {name: [float(i % 4) for i in range(28)] for name in
                    ("freq50", "freq200", "freq800", "ewma16", "ewma32",
                     "ewma64", "hotgap", "duegap", "transition")}
        probability, experts = _mixture_probability(features, [1, 2, 3, 4, 5])
        self.assertEqual(len(experts), 27)
        self.assertGreaterEqual(probability, 0.5 * UNIFORM)

    def test_de_las_tres_rows_do_not_affect_classic_scores(self):
        rows = fixture_rows()
        baseline, _ = evaluate_v312(rows, warmup_classic=2)
        changed = [dict(r, numbers=[24, 25, 26, 27, 28])
                   if r["draw_type"] == "DE_LAS_TRES" else dict(r) for r in rows]
        altered, _ = evaluate_v312(changed, warmup_classic=2)
        self.assertEqual(baseline["cumulative_log_lift"], altered["cumulative_log_lift"])
        self.assertEqual(baseline["scored_targets"], altered["scored_targets"])

    def test_future_classic_rows_do_not_change_earlier_score(self):
        rows = fixture_rows()
        _, full_records = evaluate_v312(rows, warmup_classic=2)
        prefix_contest = full_records[0]["target_contest"]
        prefix_rows = [r for r in rows if r["contest"] <= prefix_contest]
        _, prefix_records = evaluate_v312(prefix_rows, warmup_classic=2)
        self.assertAlmostEqual(
            full_records[0]["log_lift_vs_uniform"],
            prefix_records[0]["log_lift_vs_uniform"],
            places=14,
        )

    def test_target_and_feature_cutoff_are_strictly_ordered(self):
        report, records = evaluate_v312(fixture_rows(), warmup_classic=2)
        self.assertEqual(report["classification"], "RESEARCH_ONLY_RETROSPECTIVE_NOT_EDGE_EVIDENCE")
        self.assertTrue(all(r["feature_cutoff_contest"] < r["target_contest"] for r in records))
        self.assertFalse(report["prospective_gates_satisfied"])

    def test_rejects_invalid_draws(self):
        rows = fixture_rows()
        rows[1]["numbers"] = [1, 1, 2, 3, 4]
        with self.assertRaises(ValueError):
            evaluate_v312(rows, warmup_classic=2)


if __name__ == "__main__":
    unittest.main()
