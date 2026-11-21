import numpy as np
import pytest

from src.v264.CHISPAZO_V264_EXACTSET_ANYTIME import stable_descending_order


def test_stable_descending_order_sorts_scores_and_breaks_ties_by_index():
    scores = np.array([0.2, 0.7, 0.7, 0.1, 0.2])
    assert stable_descending_order(scores).tolist() == [1, 2, 0, 4, 3]


def test_stable_descending_order_is_repeatable_for_flat_pmf():
    scores = np.ones(98_280, dtype=float) / 98_280
    first = stable_descending_order(scores)
    second = stable_descending_order(scores)
    assert np.array_equal(first, second)
    assert first[:30].tolist() == list(range(30))


@pytest.mark.parametrize("scores", [np.array([[1.0, 2.0]]), np.array([1.0, np.nan]), np.array([1.0, np.inf])])
def test_stable_descending_order_rejects_invalid_scores(scores):
    with pytest.raises(ValueError, match="finite one-dimensional"):
        stable_descending_order(scores)
