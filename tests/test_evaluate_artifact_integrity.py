import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

from src.pipeline import evaluate_registration


ROOT = Path(__file__).resolve().parents[1]
FREEZE_SCRIPT = ROOT / "src" / "pipeline" / "freeze_prediction.py"
EVALUATE_SCRIPT = ROOT / "src" / "pipeline" / "evaluate_registration.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_fixture(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    history = artifacts / "history.csv"
    history.write_bytes(b"concurso,r1,r2,r3,r4,r5\n1,1,2,3,4,5\n")
    ranking = artifacts / "ranking.csv"
    ranking.write_bytes(b"combo,score_ltr_ndcg_exact5\n01-02-03-04-05,0.1\n")

    portfolio = tmp_path / "portfolio.csv"
    combos = [
        "-".join(map(str, combo))
        for combo in itertools.islice(itertools.combinations(range(1, 29), 5), 30)
    ]
    portfolio.write_text("combo\n" + "\n".join(combos) + "\n", encoding="utf-8")

    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({
        "state": "PASS",
        "target": 2,
        "checks": [],
        "inputs": {
            "history": {"contest_max": 1, "sha256": _sha256(history), "path": str(history)},
            "ranking": {"sha256": _sha256(ranking), "path": str(ranking)},
        },
    }), encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.invalid"],
        ["git", "config", "user.name", "Exact5 artifact test"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)
    (repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True, capture_output=True)
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    ledger = tmp_path / "ledger"
    freeze = subprocess.run([
        sys.executable, str(FREEZE_SCRIPT),
        "--target", "2", "--portfolio", str(portfolio), "--preflight", str(preflight),
        "--model-version", "artifact-integrity-test", "--ledger-dir", str(ledger),
        "--repo-root", str(repo), "--commit-sha", commit_sha,
    ], check=False, capture_output=True, text=True)
    assert freeze.returncode == 0, freeze.stderr
    registration = ledger / "target_2.json"
    trusted_registration_sha256 = json.loads(registration.read_text(encoding="utf-8"))[
        "registration_sha256"
    ]
    return registration, history, ranking, trusted_registration_sha256


def _evaluate(registration, history, ranking, trusted_sha256):
    return subprocess.run([
        sys.executable, str(EVALUATE_SCRIPT), "--registration", str(registration),
        "--history", str(history), "--ranking", str(ranking),
        "--trusted-registration-sha256", trusted_sha256,
        "--result", "1", "2", "3", "4", "5",
    ], check=False, capture_output=True, text=True)


def test_original_frozen_artifacts_are_accepted(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)

    evaluation = _evaluate(registration, history, ranking, trusted_sha256)

    assert evaluation.returncode == 0, evaluation.stderr
    report = json.loads(evaluation.stdout)
    assert report["registration_sha256"] == trusted_sha256
    assert report["history_sha256"] == _sha256(history)
    assert report["ranking_sha256"] == _sha256(ranking)


def test_evaluator_rejects_history_changed_after_freeze(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    history.write_bytes(history.read_bytes().replace(b"1,2,3,4,5", b"1,2,3,4,6"))

    evaluation = _evaluate(registration, history, ranking, trusted_sha256)

    assert evaluation.returncode != 0, evaluation.stdout
    assert "history artifact SHA-256" in evaluation.stderr


def test_evaluator_rejects_truncated_ranking_artifact(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    ranking.write_bytes(ranking.read_bytes()[:12])

    evaluation = _evaluate(registration, history, ranking, trusted_sha256)

    assert evaluation.returncode != 0
    assert "ranking artifact SHA-256" in evaluation.stderr


def test_evaluator_rejects_substituted_artifact(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    substitute = tmp_path / "substitute.csv"
    substitute.write_bytes(b"replacement artifact\n")

    evaluation = _evaluate(registration, history, substitute, trusted_sha256)

    assert evaluation.returncode != 0
    assert "ranking artifact SHA-256" in evaluation.stderr


def test_registration_sha_must_match_external_trust_anchor(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["history_sha256"] = "d" * 64
    unsigned = {key: value for key, value in payload.items() if key != "registration_sha256"}
    payload["registration_sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

    accepted, detail = evaluate_registration.verify_artifact_bindings(
        payload, history, ranking, trusted_sha256
    )

    assert not accepted
    assert "externally trusted" in detail


def test_missing_artifact_is_rejected_without_uncaught_error(tmp_path):
    registration, _history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)

    evaluation = _evaluate(registration, tmp_path / "missing.csv", ranking, trusted_sha256)

    assert evaluation.returncode != 0
    assert "history artifact cannot be read" in evaluation.stderr


def test_artifact_read_error_is_reported_as_integrity_failure(tmp_path, monkeypatch):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    payload = json.loads(registration.read_text(encoding="utf-8"))

    def fail_read(_path):
        raise PermissionError("synthetic read denial")

    monkeypatch.setattr(evaluate_registration, "sha256_file", fail_read)
    accepted, detail = evaluate_registration.verify_artifact_bindings(
        payload, history, ranking, trusted_sha256
    )

    assert not accepted
    assert "history artifact cannot be read" in detail
    assert "synthetic read denial" in detail


def test_untrusted_registration_path_fields_are_not_used(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["history_path"] = "../../outside/history.csv"
    unsigned = {key: value for key, value in payload.items() if key != "registration_sha256"}
    payload["registration_sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

    accepted, detail = evaluate_registration.verify_artifact_bindings(
        payload, history, ranking, trusted_sha256
    )

    assert not accepted
    assert "externally trusted" in detail
