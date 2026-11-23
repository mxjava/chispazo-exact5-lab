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
