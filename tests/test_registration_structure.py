import json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"/"pipeline"))
from freeze_prediction import sha256_bytes, verify_registration_payload

def valid_payload():
    lines=[]
    # Deterministically enumerate first 30 valid combinations.
    for a in range(1,29):
        for b in range(a+1,29):
            for c in range(b+1,29):
                for d in range(c+1,29):
                    for e in range(d+1,29):
                        lines.append(f"{a:02d}-{b:02d}-{c:02d}-{d:02d}-{e:02d}")
                        if len(lines)==30: break
                    if len(lines)==30: break
                if len(lines)==30: break
            if len(lines)==30: break
        if len(lines)==30: break
    p={
      "target":12311,"history_max":12310,"commit_sha":"a"*40,
      "history_sha256":"b"*64,"ranking_sha256":"c"*64,
      "model_version":"V266.1","preflight_state":"PASS",
      "registered_at_utc":"2026-10-14T12:00:00+00:00",
      "registered_at_mexico_city":"2026-10-14T06:00:00-06:00",
      "lines":lines
    }
    p["registration_sha256"]=sha256_bytes(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
    return p

def rehash(p):
    p.pop("registration_sha256",None)
    p["registration_sha256"]=sha256_bytes(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
    return p

def test_valid_complete_registration_passes():
    assert verify_registration_payload(valid_payload())

def test_one_line_cannot_pass_even_with_valid_checksum():
    p=valid_payload(); p["lines"]=p["lines"][:1]; rehash(p)
    assert not verify_registration_payload(p)

def test_duplicate_line_cannot_pass_even_with_valid_checksum():
    p=valid_payload(); p["lines"][1]=p["lines"][0]; rehash(p)
    assert not verify_registration_payload(p)

def test_noncanonical_or_out_of_range_line_rejected():
    p=valid_payload(); p["lines"][0]="01-02-03-04-29"; rehash(p)
    assert not verify_registration_payload(p)

def test_wrong_history_max_rejected_even_with_valid_checksum():
    p=valid_payload(); p["history_max"]-=1; rehash(p)
    assert not verify_registration_payload(p)

@pytest.mark.parametrize(("target", "history_max"), [
    (2, True), (1, False), (2, "1"), (2, 1.5), (2, 1.0),
    (2, -1), (2, 0), (2, 2), (2, 3),
])
def test_invalid_history_max_types_and_values_rejected_with_valid_checksum(target, history_max):
    p=valid_payload(); p["target"]=target; p["history_max"]=history_max; rehash(p)
    assert not verify_registration_payload(p)

def test_missing_hash_metadata_rejected():
    p=valid_payload(); del p["history_sha256"]; rehash(p)
    assert not verify_registration_payload(p)

def test_missing_commit_sha_rejected():
    p=valid_payload(); p["commit_sha"]="abc"; rehash(p)
    assert not verify_registration_payload(p)

def test_changed_payload_without_rehash_fails_checksum():
    p=valid_payload(); p["model_version"]="other"
    assert not verify_registration_payload(p)
