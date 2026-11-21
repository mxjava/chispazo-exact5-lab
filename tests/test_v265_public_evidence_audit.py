import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v265_public_evidence.py"
DATA = ROOT / "data" / "physical-metadata" / "V265_PUBLIC_PROCEDURE_TIMELINE_20261121.json"

SPEC = importlib.util.spec_from_file_location("audit_v265_public_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _document():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_public_procedure_chronology_places_weighing_after_close():
    result = MODULE.audit(_document())
    assert result["procedure_chronology_validated"] is True
    assert any(x["activity"] == "2.1" for x in result["preclose_procedure_events"])
    assert any(x["activity"] == "3.1" for x in result["preclose_procedure_events"])
    assert any(x["activity"] == "5.1-5.5" for x in result["postclose_events"])


def test_cs11_is_post_draw_and_not_a_same_draw_preclose_feature():
    result = MODULE.audit(_document())
    assert any(x["activity"] == "13.1-13.6" for x in result["postclose_events"])
    assert result["same_draw_preclose_physical_values_located"] == []


def test_public_inventory_capability_is_not_per_draw_rfid_evidence():
    doc = _document()
    assert "all machines and spheres are stated to have RFID recognition" in doc["public_hardware_evidence"]["facts"]
    assert doc["public_data_status"]["draw_level_rfid_ids_or_read_logs_located"] is False
    result = MODULE.audit(doc)
    assert result["measured_per_draw_mechanism_evidence"] is False


def test_v265_does_not_pass_anytime_gate_or_prove_physical_bias():
    result = MODULE.audit(_document())
    assert result["evidence_of_physical_bias"] is False
    assert result["prospective_edge"] is False
    assert result["v265_actionability_gate_complete"] is False
    assert "anytime e-value gate" in " ".join(result["blockers"])


def test_audit_rejects_duplicate_or_misordered_procedure_events():
    doc = _document()
    doc["events"][3]["order"] = doc["events"][2]["order"]
    try:
        MODULE.audit(doc)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate event order should be rejected")


def test_audit_rejects_weighing_before_sales_close():
    doc = _document()
    doc["events"][2], doc["events"][3] = doc["events"][3], doc["events"][2]
    doc["events"][2]["order"] = 3
    doc["events"][3]["order"] = 4
    try:
        MODULE.audit(doc)
    except ValueError as exc:
        assert "weighing, loading, draw and CS-11 chronology" in str(exc)
    else:
        raise AssertionError("weighing-before-close chronology should be rejected")


def test_audit_rejects_fractional_event_order():
    doc = _document()
    doc["events"][3]["order"] = 2.5
    try:
        MODULE.audit(doc)
    except ValueError as exc:
        assert "positive integers" in str(exc)
    else:
        raise AssertionError("fractional event order should be rejected")
