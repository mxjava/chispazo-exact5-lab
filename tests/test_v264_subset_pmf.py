import numpy as np
import pytest
from itertools import combinations

from src.v264.CHISPAZO_V264_EXACTSET_ANYTIME import U, e5, p_set, subset_pmf


def test_subset_pmf_normalizes_over_complete_98280_universe():
    combos = np.asarray(list(combinations(range(1, 29), 5)), dtype=np.int16)
    signal = np.linspace(-2.0, 3.0, 28)
    pmf = subset_pmf(signal, 0.3, combos)
    assert len(pmf) == U == 98_280
    assert np.all(pmf > 0)
    assert np.isclose(pmf.sum(), 1.0, rtol=1e-12, atol=1e-12)


def test_subset_pmf_matches_single_set_probability():
    combos = np.asarray([[1, 4, 9, 17, 28], [2, 5, 11, 19, 23]])
    signal = np.linspace(-1.0, 1.0, 28)
    pmf = subset_pmf(signal, 0.6, combos)
    assert np.isclose(pmf[0], p_set(signal, 0.6, combos[0]), rtol=1e-13)


def test_uniform_signal_gives_uniform_probability_for_every_subset():
    combos = np.asarray(list(combinations(range(1, 29), 5)), dtype=np.int16)
    pmf = subset_pmf(np.ones(28), 0.6, combos)
    assert np.allclose(pmf, 1.0 / U, rtol=1e-12, atol=1e-15)


@pytest.mark.parametrize("combos", [
    np.asarray([[1, 2, 3, 4, 4]]),
    np.asarray([[0, 2, 3, 4, 5]]),
    np.asarray([[1, 2, 3, 4, 29]]),
    np.asarray([[1, 2, 3, 4]]),
])
def test_subset_pmf_rejects_invalid_combination_matrix(combos):
    with pytest.raises(ValueError):
        subset_pmf(np.zeros(28), 0.3, combos)
