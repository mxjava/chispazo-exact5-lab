import json
from pathlib import Path

import pytest

from src.validation.preflight_v2 import validate_evidence


def write_inputs(tmp_path: Path, state, approved, e_value=20.0):
    firewall = tmp_path / "firewall.json"
    exactset = tmp_path / "exactset.json"

    firewall.write_text(json.dumps({
        "state": state,
        "oos_approved_tests": approved,
    }), encoding="utf-8")
    exactset.write_text(json.dumps({"e_value": e_value}), encoding="utf-8")
    return firewall, exactset


def valid_row():
    return {
        "strategy": "independent_oos_strategy",
        "depth": 30,
        "n": 100,
        "hits": 5,
        "rate": 0.05,
        "null_rate": 30 / 98280,
        "lift": 163.8,
        "p_raw": 0.001,
        "p_holm": 0.01,
    }


@pytest.mark.parametrize("state", [
    "SOMETHING_NOT_APPROVED",
    "RESEARCH_ONLY_NO_EDGE",
    "BLOCKED",
    "UNKNOWN",
    None,
])
def test_rejects_unapproved_firewall_states(tmp_path, state):
    firewall, exactset = write_inputs(tmp_path, state, [valid_row()])
    checks, _ = validate_evidence(firewall, exactset)
    status = {check.name: check.status for check in checks}
    assert status["v264_oos_evidence"] == "FAIL"


@pytest.mark.parametrize("approved", [
    [],
    [{}],
    [{"test": "invented"}],
    [None],
    [{**valid_row(), "p_holm": 0.05}],
    [{**valid_row(), "n": 99}],
    [{**valid_row(), "lift": 1.01}],
    [{**valid_row(), "hits": 5, "rate": 0.01}],
])
def test_rejects_empty_or_invalid_approval_rows(tmp_path, approved):
    firewall, exactset = write_inputs(tmp_path, "PROMOTE_EXACT5", approved)
    checks, _ = validate_evidence(firewall, exactset)
    status = {check.name: check.status for check in checks}
    assert status["v264_oos_evidence"] == "FAIL"


def test_accepts_well_formed_approval_contract_and_threshold(tmp_path):
    firewall, exactset = write_inputs(
        tmp_path, "PROMOTE_EXACT5", [valid_row()], e_value=20.0
    )
    checks, _ = validate_evidence(firewall, exactset)
    status = {check.name: check.status for check in checks}
    assert status["v264_oos_evidence"] == "PASS"
    assert status["exactset_anytime_evalue"] == "PASS"


@pytest.mark.parametrize("e_value", [19.999, 0, -1, "NaN", "Infinity", None])
def test_rejects_invalid_or_subthreshold_evalue(tmp_path, e_value):
    firewall, exactset = write_inputs(
        tmp_path, "PROMOTE_EXACT5", [valid_row()], e_value=e_value
    )
    checks, _ = validate_evidence(firewall, exactset)
    status = {check.name: check.status for check in checks}
    assert status["exactset_anytime_evalue"] == "FAIL"


def test_preflight_rejects_duplicate_json_keys_in_evidence(tmp_path):
    from src.validation.preflight_v2 import validate_evidence

    firewall = tmp_path / "firewall.json"
    firewall.write_text(
        '{"state":"PROMOTE_EXACT5","state":"RESEARCH_ONLY_NO_EDGE",'
        '"oos_approved_tests":[]}',
        encoding="utf-8",
    )
    checks, _ = validate_evidence(firewall, None)
    statuses = {check.name: check.status for check in checks}
    assert statuses["firewall_report_valid"] == "FAIL"
    assert statuses["v264_oos_evidence"] == "FAIL"

    exactset = tmp_path / "exactset.json"
    exactset.write_text('{"e_value":20,"e_value":0}', encoding="utf-8")
    checks, _ = validate_evidence(None, exactset)
    statuses = {check.name: check.status for check in checks}
    assert statuses["exactset_summary_valid"] == "FAIL"
