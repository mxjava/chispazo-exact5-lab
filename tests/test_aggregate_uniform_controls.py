import json
from pathlib import Path

import pytest

from src.pipeline.aggregate_uniform_controls import aggregate_control_reports, main
from src.pipeline.evaluate_uniform_portfolio import evaluate_uniform_portfolio
from src.pipeline.generate_uniform_portfolio import generate_uniform_portfolio, write_portfolio


def make_report(tmp_path: Path, contest_id: int, seed: int):
    portfolio = tmp_path / f"portfolio_{contest_id}.csv"
    with portfolio.open("w", newline="", encoding="utf-8") as stream:
        write_portfolio(generate_uniform_portfolio(seed, 10), seed, stream)
    report = evaluate_uniform_portfolio(portfolio, contest_id, [1, 7, 12, 21, 26])
    path = tmp_path / f"evaluation_{contest_id}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path, report


def test_aggregates_distinct_completed_control_reports(tmp_path):
    first_path, first = make_report(tmp_path, 12390, 20261123)
    second_path, second = make_report(tmp_path, 12391, 20261124)
    result = aggregate_control_reports([first_path, second_path])

    assert result["status"] == "AGGREGATED_CONTROL_ONLY"
    assert result["contest_count"] == 2
    assert result["contest_ids"] == [12390, 12391]
    assert result["total_lines"] == 20
    assert sum(result["observed_hit_distribution"].values()) == 20
    assert result["observed_exact5_count"] == (
        first["exact5_count"] + second["exact5_count"]
    )
    assert result["expected_exact5_count_under_uniform_null"] == pytest.approx(
        first["uniform_null"]["expected_exact5_count"]
        + second["uniform_null"]["expected_exact5_count"]
    )
    assert result["predictive_claim"] is False
    assert result["prospective_registration_created"] is False


def test_rejects_duplicate_contests(tmp_path):
    first_path, _ = make_report(tmp_path, 12390, 20261123)
    second_path, _ = make_report(tmp_path, 12390, 20261124)
    with pytest.raises(ValueError, match="duplicate contest_id"):
        aggregate_control_reports([first_path, second_path])


def test_allows_same_fixed_portfolio_across_distinct_draws(tmp_path):
    portfolio = tmp_path / "fixed_portfolio.csv"
    with portfolio.open("w", newline="", encoding="utf-8") as stream:
        write_portfolio(generate_uniform_portfolio(20261123, 10), 20261123, stream)
    reports = []
    for contest_id, result in [(12390, [1, 7, 12, 21, 26]), (12391, [2, 8, 13, 22, 27])]:
        report = evaluate_uniform_portfolio(portfolio, contest_id, result)
        path = tmp_path / f"evaluation_{contest_id}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        reports.append(path)
    aggregate = aggregate_control_reports(reports)
    assert aggregate["contest_count"] == 2
    assert aggregate["portfolio_sha256"][0] == aggregate["portfolio_sha256"][1]


def test_rejects_predictive_or_tampered_report(tmp_path):
    first_path, _ = make_report(tmp_path, 12390, 20261123)
    report = json.loads(first_path.read_text(encoding="utf-8"))
    report["predictive_claim"] = True
    first_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid predictive"):
        aggregate_control_reports([first_path])


def test_cli_writes_aggregate_json(tmp_path):
    first_path, _ = make_report(tmp_path, 12390, 20261123)
    second_path, _ = make_report(tmp_path, 12391, 20261124)
    output = tmp_path / "aggregate.json"
    import contextlib
    import io
    from unittest.mock import patch
    stdout = io.StringIO()
    with patch("sys.argv", [
        "aggregate_uniform_controls",
        "--reports", str(first_path), str(second_path),
        "--out", str(output),
    ]), contextlib.redirect_stdout(stdout):
        assert main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["contest_count"] == 2
    assert "AGGREGATED_CONTROL_ONLY" in stdout.getvalue()
