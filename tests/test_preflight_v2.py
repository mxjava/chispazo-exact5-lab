from pathlib import Path
import pandas as pd
import pytest
from src.validation.preflight_v2 import validate_history, validate_ranking, EXACT5_UNIVERSE


def _write_history(path: Path, contest='1', numbers=('1', '2', '3', '4', '5')):
    pd.DataFrame({
        'CONCURSO': [contest],
        'R1': [numbers[0]], 'R2': [numbers[1]], 'R3': [numbers[2]],
        'R4': [numbers[3]], 'R5': [numbers[4]],
    }).to_csv(path, index=False)


@pytest.mark.parametrize(('contest', 'failed_check'), [
    (None, 'contest_numeric'),
    ('not-a-number', 'contest_numeric'),
    ('Infinity', 'contest_finite'),
    ('-Infinity', 'contest_finite'),
    ('1.5', 'contest_integer'),
    ('1.00000000000000000001', 'contest_integer'),
    ('0', 'contest_positive'),
    ('-1', 'contest_positive'),
])
def test_history_rejects_invalid_contest_ids_from_csv(tmp_path: Path, contest, failed_check):
    p = tmp_path / 'h.csv'
    _write_history(p, contest=contest)

    checks, _ = validate_history(p, None)
    statuses = {check.name: check.status for check in checks}

    assert statuses[failed_check] == 'FAIL'
    assert 'contest_unique' not in statuses


@pytest.mark.parametrize(('numbers', 'failed_check'), [
    ((None, '2', '3', '4', '5'), 'numbers_numeric'),
    (('not-a-number', '2', '3', '4', '5'), 'numbers_numeric'),
    (('Infinity', '2', '3', '4', '5'), 'numbers_finite'),
    (('-Infinity', '2', '3', '4', '5'), 'numbers_finite'),
    (('1.5', '2', '3', '4', '5'), 'numbers_integer'),
    (('1.00000000000000000001', '2', '3', '4', '5'), 'numbers_integer'),
    (('0', '2', '3', '4', '5'), 'numbers_range_1_28'),
    (('29', '2', '3', '4', '5'), 'numbers_range_1_28'),
    (('1', '1', '3', '4', '5'), 'five_unique_numbers'),
])
def test_history_rejects_invalid_draw_numbers_from_csv(tmp_path: Path, numbers, failed_check):
    p = tmp_path / 'h.csv'
    _write_history(p, numbers=numbers)

    checks, _ = validate_history(p, None)
    statuses = {check.name: check.status for check in checks}

    assert statuses[failed_check] == 'FAIL'


def test_history_accepts_valid_integer_values_from_csv(tmp_path: Path):
    p = tmp_path / 'h.csv'
    _write_history(p, contest='7.0', numbers=('1.0', '8', '13', '21', '28'))

    checks, _ = validate_history(p, None)
    statuses = {check.name: check.status for check in checks}

    for name in (
        'contest_numeric', 'contest_finite', 'contest_integer', 'contest_positive',
        'numbers_numeric', 'numbers_finite', 'numbers_integer',
        'numbers_range_1_28', 'five_unique_numbers',
    ):
        assert statuses[name] == 'PASS'


def test_history_requires_target_minus_one(tmp_path: Path):
    p=tmp_path/'h.csv'
    pd.DataFrame({'CONCURSO':[102,101,100],'R1':[1,2,3],'R2':[4,5,6],'R3':[7,8,9],'R4':[10,11,12],'R5':[13,14,15],'FECHA':['2026-01-03','2026-01-02','2026-01-01']}).to_csv(p,index=False)
    checks,_=validate_history(p,103)
    m={c.name:c.status for c in checks}
    assert m['history_ends_at_target_minus_1']=='PASS'
    checks,_=validate_history(p,104)
    m={c.name:c.status for c in checks}
    assert m['history_ends_at_target_minus_1']=='FAIL'


def test_ranking_rejects_partial_universe(tmp_path: Path):
    p=tmp_path/'r.csv'
    pd.DataFrame({'combo':['01-02-03-04-05','01-02-03-04-06'],'score_ltr_ndcg_exact5':[0.1,0.2],'score_ltr_exact5_balanced':[0.2,0.3]}).to_csv(p,index=False)
    checks,_=validate_ranking(p)
    m={c.name:c.status for c in checks}
    assert m['ranking_full_universe']=='FAIL'
    assert EXACT5_UNIVERSE==98280
