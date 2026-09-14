import json
from pathlib import Path
import pandas as pd

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
