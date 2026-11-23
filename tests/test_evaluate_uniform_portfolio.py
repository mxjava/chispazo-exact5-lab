import contextlib
import csv
import io
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipeline.evaluate_uniform_portfolio import (
    MODE,
    evaluate_uniform_portfolio,
    main,
)
from src.pipeline.generate_uniform_portfolio import generate_uniform_portfolio, write_portfolio


def write_generated(path: Path, seed: int = 20261123, lines: int = 30):
    with path.open("w", newline="", encoding="utf-8") as stream:
        write_portfolio(generate_uniform_portfolio(seed, lines), seed, stream)


def test_evaluates_real_generator_output_as_control_only(tmp_path):
    portfolio = tmp_path / "portfolio.csv"
    write_generated(portfolio)
    report = evaluate_uniform_portfolio(portfolio, 12390, [1, 7, 12, 21, 26])

    assert report["status"] == "EVALUATED_CONTROL_ONLY"
    assert report["mode"] == MODE
    assert report["contest_id"] == 12390
    assert report["seed"] == 20261123
    assert report["line_count"] == 30
    assert sum(report["hit_distribution"].values()) == 30
    assert report["best_hits"] == max(line["hits"] for line in report["lines"])
    assert report["exact5_count"] == report["hit_distribution"]["5"]
    assert report["predictive_claim"] is False
    assert report["prospective_registration_created"] is False
    assert len(report["portfolio_sha256"]) == 64


def test_rejects_csv_without_uniform_mode_marker(tmp_path):
    portfolio = tmp_path / "portfolio.csv"
    write_generated(portfolio, lines=5)
    text = portfolio.read_text(encoding="utf-8").replace(MODE, "PREDICTIVE_CANDIDATE")
    portfolio.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="not explicitly marked"):
        evaluate_uniform_portfolio(portfolio, 12390, [1, 7, 12, 21, 26])


def test_rejects_duplicate_combinations(tmp_path):
    portfolio = tmp_path / "portfolio.csv"
    write_generated(portfolio, lines=5)
    rows = list(csv.DictReader(portfolio.open(encoding="utf-8")))
    rows[-1]["combo"] = rows[0]["combo"]
    with portfolio.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["rank", "combo", "mode", "seed"])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_uniform_portfolio(portfolio, 12390, [1, 7, 12, 21, 26])


@pytest.mark.parametrize("result", [[1, 1, 2, 3, 4], [0, 2, 3, 4, 5], [1, 2, 3, 4]])
def test_rejects_invalid_draw_result(tmp_path, result):
    portfolio = tmp_path / "portfolio.csv"
    write_generated(portfolio, lines=5)
    with pytest.raises(ValueError, match="exactly five"):
        evaluate_uniform_portfolio(portfolio, 12390, result)


def test_cli_writes_json_report_atomically(tmp_path):
    portfolio = tmp_path / "portfolio.csv"
    output = tmp_path / "evaluation.json"
    write_generated(portfolio, lines=5)
    stdout = io.StringIO()
    with patch("sys.argv", [
        "evaluate_uniform_portfolio",
        "--portfolio", str(portfolio),
        "--contest-id", "12390",
        "--result", "1", "7", "12", "21", "26",
        "--out", str(output),
    ]), contextlib.redirect_stdout(stdout):
        assert main() == 0
    import json
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "EVALUATED_CONTROL_ONLY"
    assert report["line_count"] == 5
    assert "EVALUATED_CONTROL_ONLY" in stdout.getvalue()
