import json
from pathlib import Path
import pandas as pd
import pytest

from src.v264.CHISPAZO_V264_EVIDENCE_FIREWALL import evidence

ROOT = Path(__file__).resolve().parents[1]

def test_v264_firewall_is_closed():
    r = json.loads((ROOT/'reports/v264_firewall100_report.json').read_text(encoding='utf-8'))
    assert len(r['parent_live_exact5']) == 5
    assert r['state'] == 'RESEARCH_ONLY_NO_EDGE'
    assert r['oos_approved_tests'] == []
    assert r['policy']['production_concentration_allowed'] is False


def test_v264_exactset_null_dominates():
    e = json.loads((ROOT/'reports/v264_summary.json').read_text(encoding='utf-8'))
    assert e['evaluated'] == 10087
    assert abs(e['posterior_uniform'] - 1.0) < 1e-12
    assert e['e_value'] < 1.0
    assert abs(e['top30_mass_lift'] - 1.0) < 1e-12


def test_v264_oos_no_holm_approved_depth():
    t = pd.read_csv(ROOT/'reports/v264_oos_depth_tests_100.csv')
    assert len(t) > 0
    assert (t['p_holm'] >= 0.05).all()


@pytest.mark.parametrize(('exact_rank', 'message'), [
    (None, 'finite numeric integers'),
    ('not-a-rank', 'finite numeric integers'),
    ('inf', 'finite numeric integers'),
    ('-inf', 'finite numeric integers'),
    ('NaN', 'finite numeric integers'),
    ('30.9', 'must be integers'),
    ('30.00000000000000001', 'must be integers'),
    ('0', 'between 1 and 98280'),
    ('-1', 'between 1 and 98280'),
    ('98281', 'between 1 and 98280'),
])
def test_evidence_rejects_invalid_exact_ranks_from_csv(tmp_path, exact_rank, message):
    metadata = tmp_path / 'metadata.csv'
    pd.DataFrame({'strategy': ['control'], 'exact_rank': [exact_rank]}).to_csv(metadata, index=False)

    with pytest.raises(ValueError, match=message):
        evidence(metadata)


@pytest.mark.parametrize('columns', [
    {'exact_rank': [30]},
    {'strategy': ['control']},
])
def test_evidence_rejects_missing_required_metadata_columns(tmp_path, columns):
    metadata = tmp_path / 'metadata.csv'
    pd.DataFrame(columns).to_csv(metadata, index=False)

    with pytest.raises(ValueError, match='metadata missing required columns'):
        evidence(metadata)


def test_evidence_accepts_valid_integer_ranks_from_csv(tmp_path):
    metadata = tmp_path / 'metadata.csv'
    pd.DataFrame({
        'strategy': ['control', 'control', 'control'],
        'exact_rank': ['1', '30.0', '98280'],
    }).to_csv(metadata, index=False)

    summaries, tests, approved = evidence(metadata)

    assert len(summaries) == 1
    assert summaries[0]['strategy'] == 'control'
    assert summaries[0]['n'] == 3
    assert summaries[0]['mean_rank'] == pytest.approx((1 + 30 + 98280) / 3)
    assert len(tests) == 6
    assert approved == []
