import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.pipeline.generate_uniform_portfolio import (
    UNIVERSE,
    format_combo,
    generate_uniform_portfolio,
    unrank_combination,
    write_portfolio,
    main,
)


class UniformPortfolioTests(unittest.TestCase):
    def test_unrank_first_and_last(self):
        self.assertEqual(unrank_combination(0), (1, 2, 3, 4, 5))
        self.assertEqual(unrank_combination(UNIVERSE - 1), (24, 25, 26, 27, 28))

    def test_unrank_is_bijective_for_small_space(self):
        self.assertEqual(
            [unrank_combination(i, n=6, r=3) for i in range(20)],
            [
                (1, 2, 3), (1, 2, 4), (1, 2, 5), (1, 2, 6),
                (1, 3, 4), (1, 3, 5), (1, 3, 6), (1, 4, 5),
                (1, 4, 6), (1, 5, 6), (2, 3, 4), (2, 3, 5),
                (2, 3, 6), (2, 4, 5), (2, 4, 6), (2, 5, 6),
                (3, 4, 5), (3, 4, 6), (3, 5, 6), (4, 5, 6),
            ],
        )

    def test_seed_is_reproducible_and_distinct(self):
        first = generate_uniform_portfolio(20261122, 30)
        second = generate_uniform_portfolio(20261122, 30)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 30)
        self.assertEqual(len(set(first)), 30)
        for combo in first:
            self.assertEqual(len(combo), 5)
            self.assertEqual(tuple(sorted(combo)), combo)
            self.assertTrue(all(1 <= value <= 28 for value in combo))

    def test_seed_has_versioned_golden_vector(self):
        self.assertEqual(
            generate_uniform_portfolio(20261122, 5),
            [
                (3, 4, 10, 11, 20),
                (5, 15, 17, 21, 25),
                (8, 9, 12, 16, 25),
                (5, 7, 11, 18, 19),
                (1, 4, 7, 11, 27),
            ],
        )

    def test_validation(self):
        for value in (0, -1, UNIVERSE + 1):
            with self.assertRaises(ValueError):
                generate_uniform_portfolio(1, value)
        with self.assertRaises(TypeError):
            generate_uniform_portfolio(True, 1)
        with self.assertRaises(ValueError):
            unrank_combination(UNIVERSE)

    def test_csv_marks_non_predictive_mode(self):
        output = io.StringIO()
        write_portfolio(generate_uniform_portfolio(7, 2), 7, output)
        self.assertIn("UNIFORM_COVERAGE_NOT_PREDICTIVE", output.getvalue())
        self.assertEqual(len(output.getvalue().strip().splitlines()), 3)
        self.assertEqual(format_combo((1, 2, 3, 4, 5)), "01-02-03-04-05")

    def test_cli_writes_reproducible_csv_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "portfolio.csv"
            stdout = io.StringIO()
            with patch("sys.argv", [
                "generate_uniform_portfolio", "--seed", "20261122",
                "--lines", "5", "--out", str(output_path),
            ]), contextlib.redirect_stdout(stdout):
                self.assertEqual(main(), 0)

            rows = output_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0], "rank,combo,mode,seed")
            self.assertTrue(all("UNIFORM_COVERAGE_NOT_PREDICTIVE" in row for row in rows[1:]))
            self.assertIn("lines=5", stdout.getvalue())

    def test_cli_stdout_mode_emits_valid_csv(self):
        stdout = io.StringIO()
        with patch("sys.argv", [
            "generate_uniform_portfolio", "--seed", "11", "--lines", "3",
        ]), contextlib.redirect_stdout(stdout):
            self.assertEqual(main(), 0)
        rows = stdout.getvalue().strip().splitlines()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], "rank,combo,mode,seed")


if __name__ == "__main__":
    unittest.main()
