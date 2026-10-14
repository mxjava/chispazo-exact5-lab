from pathlib import Path
import pandas as pd
import pytest
from src.validation import preflight_v2
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
    (('NaN', '2', '3', '4', '5'), 'numbers_numeric'),
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
    assert m['contest_contiguous']=='PASS'
    assert m['no_future_leakage']=='PASS'
    checks,_=validate_history(p,104)
    m={c.name:c.status for c in checks}
    assert m['history_ends_at_target_minus_1']=='FAIL'


def test_history_rejects_gaps_while_preserving_target_boundary_checks(tmp_path: Path):
    p=tmp_path/'gapped_history.csv'
    pd.DataFrame({
        'CONCURSO':[1,3,4],
        'R1':[1,1,1], 'R2':[2,2,2], 'R3':[3,3,3], 'R4':[4,4,4], 'R5':[5,5,5],
    }).to_csv(p,index=False)

    checks,_=validate_history(p,5)
    statuses={check.name:check.status for check in checks}

    assert statuses['contest_contiguous']=='FAIL'
    assert statuses['no_future_leakage']=='PASS'
    assert statuses['history_ends_at_target_minus_1']=='PASS'


def test_v266_invalid_contest_id_blocks_preflight_even_when_other_gates_pass(tmp_path: Path, monkeypatch):
    p=tmp_path/'invalid_contest.csv'
    _write_history(p,contest='-1')
    passing_check=[preflight_v2.Check('test_gate','PASS','valid control')]
    monkeypatch.setattr(preflight_v2,'validate_ranking',lambda path:(passing_check,{}))
    monkeypatch.setattr(preflight_v2,'validate_evidence',lambda firewall,exactset:(passing_check,{}))

    report=preflight_v2.run(p,2)
    statuses={check['name']:check['status'] for check in report['checks']}

    assert statuses['contest_positive']=='FAIL'
    assert all(check['status']=='PASS' for check in report['checks'] if check['name']!='contest_positive')
    assert report['state']=='BLOCKED'


def test_v266_invalid_draw_number_blocks_preflight_even_when_other_gates_pass(tmp_path: Path, monkeypatch):
    p=tmp_path/'invalid_draw.csv'
    _write_history(p,contest='1',numbers=('1.5','2','3','4','5'))
    passing_check=[preflight_v2.Check('test_gate','PASS','valid control')]
    monkeypatch.setattr(preflight_v2,'validate_ranking',lambda path:(passing_check,{}))
    monkeypatch.setattr(preflight_v2,'validate_evidence',lambda firewall,exactset:(passing_check,{}))

    report=preflight_v2.run(p,2)
    critical=[check for check in report['checks'] if check['critical']]

    assert next(check['status'] for check in critical if check['name']=='numbers_integer')=='FAIL'
    assert not all(check['status']=='PASS' for check in critical)
    assert report['state']=='BLOCKED'


def test_ranking_rejects_partial_universe(tmp_path: Path):
    p=tmp_path/'r.csv'
    pd.DataFrame({'combo':['01-02-03-04-05','01-02-03-04-06'],'score_ltr_ndcg_exact5':[0.1,0.2],'score_ltr_exact5_balanced':[0.2,0.3]}).to_csv(p,index=False)
    checks,_=validate_ranking(p)
    m={c.name:c.status for c in checks}
    assert m['ranking_full_universe']=='FAIL'
    assert EXACT5_UNIVERSE==98280
