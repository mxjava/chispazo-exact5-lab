from collections import Counter
from io import StringIO

from src.pipeline.generate_optimal_4hit_portfolio import (
    LINES,
    MODE,
    count_covered_draws,
    generate_portfolio,
    write_portfolio,
)


def test_seed_reproduces_balanced_maximum_4hit_coverage_portfolio():
    first, gains = generate_portfolio(20261123)
    second, gains_again = generate_portfolio(20261123)

    assert first == second
    assert gains == gains_again
    assert len(first) == LINES == 30
    assert len(set(first)) == 30
    assert all(len(ticket) == 5 and tuple(sorted(ticket)) == ticket for ticket in first)
    assert all(all(1 <= value <= 28 for value in ticket) for ticket in first)
    assert gains == [116] * 30
    assert count_covered_draws(first) == 3480
    frequencies = Counter(value for ticket in first for value in ticket)
    assert sorted(frequencies.values()) == [5] * 18 + [6] * 10


def test_csv_is_explicitly_non_predictive():
    portfolio, _ = generate_portfolio(20261123)
    stream = StringIO()
    write_portfolio(portfolio, 20261123, stream)
    rows = stream.getvalue().strip().splitlines()
    assert rows[0] == "rank,combo,mode,seed"
    assert len(rows) == 31
    assert all(MODE in row for row in rows[1:])


def test_checked_in_csv_matches_generator_and_full_outcome_histogram():
    import csv
    from pathlib import Path
    from itertools import combinations

    expected, gains = generate_portfolio(20261123)
    artifact = Path(__file__).resolve().parents[1] / "runs" / "optimal_4hit_coverage_20261123.csv"
    with artifact.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    actual = [tuple(int(value) for value in row["combo"].split("-")) for row in rows]
    assert actual == expected
    assert len(actual) == 30 and len(set(actual)) == 30
    assert all(row["mode"] == MODE and row["seed"] == "20261123" for row in rows)
    assert gains == [116] * 30

    # Independent enumeration of every possible winning 5-set.
    tickets = [set(ticket) for ticket in actual]
    histogram = {4: 0, 5: 0}
    for draw in combinations(range(1, 29), 5):
        best = max(len(set(draw) & ticket) for ticket in tickets)
        if best >= 4:
            histogram[best] += 1
    assert histogram == {4: 3450, 5: 30}
    assert sum(histogram.values()) == 3480
