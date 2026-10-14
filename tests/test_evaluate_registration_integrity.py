import hashlib, json, subprocess, sys
from pathlib import Path
import pytest
from src.pipeline.evaluate_registration import verify_registration_payload

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "pipeline" / "evaluate_registration.py"


def fixture():
    import itertools
    lines=['-'.join(f'{n:02d}' for n in c) for c in itertools.islice(itertools.combinations(range(1,29),5),30)]
    p={"target":12250,"registered_at_utc":"2026-10-14T00:00:00+00:00","registered_at_mexico_city":"2026-10-13T18:00:00-06:00","commit_sha":"a"*40,"model_version":"test","history_max":12249,"history_sha256":"b"*64,"ranking_sha256":"c"*64,"preflight_state":"PASS","lines":lines}
    p["registration_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return p


def test_valid_registration_passes():
    assert verify_registration_payload(fixture())


def test_line_tampering_fails_even_if_old_checksum_kept():
    p=fixture(); p["lines"][0]="01-02-03-04-28"
    assert not verify_registration_payload(p)


def test_duplicate_lines_fail_with_recomputed_checksum():
    p=fixture(); p["lines"][-1]=p["lines"][0]
    p.pop("registration_sha256")
    p["registration_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    assert not verify_registration_payload(p)


def test_wrong_target_history_binding_fails_with_recomputed_checksum():
    p=fixture(); p["history_max"]=12248
    p.pop("registration_sha256")
    p["registration_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    assert not verify_registration_payload(p)


@pytest.mark.parametrize(("target", "history_max"), [
    (2, True), (1, False), (2, "1"), (2, 1.5), (2, 1.0),
    (2, -1), (2, 0), (2, 2), (2, 3),
])
def test_invalid_history_max_types_and_values_fail_with_recomputed_checksum(target, history_max):
    p=fixture(); p["target"]=target; p["history_max"]=history_max
    p.pop("registration_sha256")
    p["registration_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    assert not verify_registration_payload(p)

def test_missing_checksum_fails():
    p=fixture(); p.pop("registration_sha256")
    assert not verify_registration_payload(p)


def test_non_dict_fails():
    assert not verify_registration_payload([])


def test_registration_verifier_rejects_mismatched_timestamp_instants():
    p = fixture()
    p["registered_at_utc"] = "2026-01-01T12:00:00+00:00"
    p["registered_at_mexico_city"] = "2026-01-01T12:00:00-06:00"
    p.pop("registration_sha256")
    p["registration_sha256"] = hashlib.sha256(
        json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert not verify_registration_payload(p)


def test_evaluator_rejects_duplicate_json_keys_even_with_valid_payload_checksum(tmp_path):
    p = fixture()
    raw = json.dumps(p, separators=(",", ":"))
    raw = raw.replace('"target":12250', '"target":999,"target":12250', 1)
    registration = tmp_path / "ambiguous-registration.json"
    registration.write_text(raw, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--registration", str(registration),
         "--result", "1", "2", "3", "4", "5"],
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()


def test_evaluator_reads_a_valid_registration_file(tmp_path):
    registration = tmp_path / "registration.json"
    registration.write_text(json.dumps(fixture()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--registration", str(registration),
         "--result", "1", "2", "3", "4", "5"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["target"] == 12250


def test_evaluator_rejects_truncated_registration_without_traceback(tmp_path):
    registration = tmp_path / "truncated-registration.json"
    registration.write_text('{"target":', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--registration", str(registration),
         "--result", "1", "2", "3", "4", "5"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "invalid JSON" in result.stderr
    assert "Traceback" not in result.stderr
