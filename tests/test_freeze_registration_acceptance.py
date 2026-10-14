import itertools
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "pipeline" / "freeze_prediction.py"


def _inputs(tmp_path, *, target=12311, history_max=12310, state="PASS"):
    portfolio = tmp_path / "portfolio.csv"
    combos = ["-".join(map(str, c)) for c in list(itertools.combinations(range(1, 29), 5))[:30]]
    pd.DataFrame({"combo": combos}).to_csv(portfolio, index=False)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({
        "state": state, "target": target, "checks": [],
        "inputs": {"history": {"contest_max": history_max, "sha256": "a" * 64},
                   "ranking": {"sha256": "b" * 64}},
    }), encoding="utf-8")
    return portfolio, preflight


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Exact5 test"], cwd=repo, check=True)
    marker = repo / "tracked.txt"
    if not marker.exists():
        marker.write_text("committed\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    return repo, sha


def _run(tmp_path, *, target=12311, pre_target=12311, history_max=12310, state="PASS", sha=None,
         duplicate_preflight_state=False, malformed_preflight=False):
    portfolio, preflight = _inputs(tmp_path, target=pre_target, history_max=history_max, state=state)
    if malformed_preflight:
        preflight.write_text('{"state":', encoding="utf-8")
    elif duplicate_preflight_state:
        raw = preflight.read_text(encoding="utf-8")
        preflight.write_text(raw.replace('"state": "PASS"', '"state": "BLOCKED", "state": "PASS"', 1), encoding="utf-8")
    repo, head_sha = _repo(tmp_path)
    return subprocess.run([
        sys.executable, str(SCRIPT), "--target", str(target), "--portfolio", str(portfolio),
        "--preflight", str(preflight), "--model-version", "test-model",
        "--ledger-dir", str(tmp_path / "ledger"), "--repo-root", str(repo),
        "--commit-sha", head_sha if sha is None else sha,
    ], capture_output=True, text=True)


def test_valid_freeze_records_commit_timezone_and_exact_30_lines(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    entry = json.loads((tmp_path / "ledger" / "target_12311.json").read_text(encoding="utf-8"))
    expected_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path / "repo", check=True, capture_output=True, text=True).stdout.strip()
    assert entry["commit_sha"] == expected_sha
    assert entry["history_max"] == 12310
    assert len(entry["lines"]) == 30
    assert entry["gate_summary"]["failed_checks"] == []
    assert entry["registered_at_mexico_city"].endswith(("-06:00", "-05:00"))


def test_wrong_target_is_rejected(tmp_path):
    result = _run(tmp_path, target=12312, pre_target=12311)
    assert result.returncode != 0 and "target=" in result.stderr


def test_stale_history_is_rejected(tmp_path):
    result = _run(tmp_path, history_max=12309)
    assert result.returncode != 0 and "target-1" in result.stderr


def test_freezer_rejects_duplicate_preflight_keys(tmp_path):
    result = _run(tmp_path, duplicate_preflight_state=True)
    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()
    assert not (tmp_path / "ledger" / "target_12311.json").exists()


def test_freezer_rejects_truncated_preflight_without_traceback(tmp_path):
    result = _run(tmp_path, malformed_preflight=True)
    assert result.returncode != 0
    assert "invalid preflight JSON" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "ledger" / "target_12311.json").exists()


def test_short_commit_sha_is_rejected(tmp_path):
    result = _run(tmp_path, sha="deadbeef")
    assert result.returncode != 0 and "40-character" in result.stderr


def test_blocked_preflight_is_rejected(tmp_path):
    result = _run(tmp_path, state="BLOCKED")
    assert result.returncode != 0 and "not PASS" in result.stderr


def test_registration_verifier_rejects_mismatched_timestamp_instants(tmp_path):
    import hashlib
    from src.pipeline.freeze_prediction import verify_registration_payload

    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    entry = json.loads((tmp_path / "ledger" / "target_12311.json").read_text(encoding="utf-8"))
    entry["registered_at_utc"] = "2026-01-01T12:00:00+00:00"
    entry["registered_at_mexico_city"] = "2026-01-01T12:00:00-06:00"
    unsigned = {key: value for key, value in entry.items() if key != "registration_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    entry["registration_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_registration_payload(entry)
