import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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


def _evaluate(registration, history, ranking, trusted_sha256, *, out=None):
    command = [
        sys.executable, str(EVALUATE_SCRIPT), "--registration", str(registration),
        "--history", str(history), "--ranking", str(ranking),
        "--trusted-registration-sha256", trusted_sha256,
        "--result", "1", "2", "3", "4", "5",
    ]
    if out is not None:
        command.extend(["--out", str(out)])
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _inject_duplicate_and_recompute_checksum(registration, marker, replacement, trusted_sha256):
    raw = registration.read_text(encoding="utf-8")
    assert marker in raw
    ambiguous = raw.replace(marker, replacement, 1)

    # Recompute over the value json.loads() exposes (last duplicate key wins).
    # The differing shadowed value must not change the trusted semantic payload.
    parsed = json.loads(ambiguous)
    unsigned = {key: value for key, value in parsed.items() if key != "registration_sha256"}
    recomputed = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert recomputed == trusted_sha256
    ambiguous, count = re.subn(
        r'("registration_sha256"\s*:\s*")[0-9a-f]{64}("$)',
        lambda match: f"{match.group(1)}{recomputed}{match.group(2)}",
        ambiguous,
        count=1,
        flags=re.MULTILINE,
    )
    assert count == 1
    registration.write_text(ambiguous, encoding="utf-8")


def test_original_frozen_artifacts_are_accepted(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)

    evaluation = _evaluate(registration, history, ranking, trusted_sha256)

    assert evaluation.returncode == 0, evaluation.stderr
    report = json.loads(evaluation.stdout)
    assert report["registration_sha256"] == trusted_sha256
    assert report["history_sha256"] == _sha256(history)
    assert report["ranking_sha256"] == _sha256(ranking)
    assert len(report["lines"]) == 30


def test_valid_evaluation_replaces_existing_output_atomically(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    report_path = tmp_path / "evaluation.json"
    report_path.write_text('{"stale": true}\n', encoding="utf-8")

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode == 0, evaluation.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report == json.loads(evaluation.stdout)
    assert "stale" not in report
    assert not list(tmp_path.glob(".evaluation.json.*.tmp"))


def test_evaluator_rejects_history_changed_after_freeze(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    history.write_bytes(history.read_bytes().replace(b"1,2,3,4,5", b"1,2,3,4,6"))

    evaluation = _evaluate(registration, history, ranking, trusted_sha256)

    assert evaluation.returncode != 0, evaluation.stdout
    assert "history artifact SHA-256" in evaluation.stderr


def test_integrity_failure_does_not_leave_stale_output_file(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    history.write_bytes(history.read_bytes().replace(b"1,2,3,4,5", b"1,2,3,4,6"))
    report_path = tmp_path / "evaluation.json"
    report_path.write_text('{"stale": true}\n', encoding="utf-8")

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode != 0
    assert "history artifact SHA-256" in evaluation.stderr
    assert not evaluation.stdout.strip()
    assert not report_path.exists()


def test_evaluation_output_cannot_alias_an_input_artifact(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    original_history = history.read_bytes()

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=history
    )

    assert evaluation.returncode != 0
    assert "output path must not overlap an input artifact" in evaluation.stderr
    assert not evaluation.stdout.strip()
    assert history.read_bytes() == original_history


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


def test_portfolio_replacement_cannot_change_scored_lines(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["lines"][0] = "02-03-04-05-06"
    unsigned = {key: value for key, value in payload.items() if key != "registration_sha256"}
    payload["registration_sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    registration.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_path = tmp_path / "tampered-evaluation.json"

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode != 0
    assert "externally trusted" in evaluation.stderr
    assert not evaluation.stdout.strip()
    assert not report_path.exists()


def test_missing_artifact_is_rejected_without_uncaught_error(tmp_path):
    registration, _history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)

    evaluation = _evaluate(registration, tmp_path / "missing.csv", ranking, trusted_sha256)

    assert evaluation.returncode != 0
    assert "history artifact cannot be read" in evaluation.stderr


@pytest.mark.parametrize(
    "invalid_json",
    [
        "{",
        '{"target":',
        '{"nested":' + "[" * 10000 + "0" + "]" * 10000 + "}",
    ],
    ids=["malformed", "truncated", "excessive-nesting"],
)
def test_invalid_or_truncated_registration_has_no_evaluation_output(tmp_path, invalid_json):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    registration.write_text(invalid_json, encoding="utf-8")
    report_path = tmp_path / "invalid-registration-evaluation.json"

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode != 0
    assert "invalid or unreadable prospective registration" in evaluation.stderr
    assert "Traceback" not in evaluation.stderr
    assert not evaluation.stdout.strip()
    assert not report_path.exists()


def test_missing_registration_has_no_evaluation_output(tmp_path):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    registration.unlink()
    report_path = tmp_path / "missing-registration-evaluation.json"

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode != 0
    assert "invalid or unreadable prospective registration" in evaluation.stderr
    assert "Traceback" not in evaluation.stderr
    assert not evaluation.stdout.strip()
    assert not report_path.exists()


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


@pytest.mark.parametrize(
    ("marker", "replacement"),
    [
        ('"target": 2,', '"target": 99,\n  "target": 2,'),
        ('"state": "PASS",', '"state": "BLOCKED",\n    "state": "PASS",'),
    ],
    ids=["top-level", "nested"],
)
def test_evaluator_rejects_duplicate_registration_keys_before_reporting(
    tmp_path, marker, replacement
):
    registration, history, ranking, trusted_sha256 = _freeze_fixture(tmp_path)
    _inject_duplicate_and_recompute_checksum(
        registration, marker, replacement, trusted_sha256
    )
    report_path = tmp_path / "evaluation.json"

    evaluation = _evaluate(
        registration, history, ranking, trusted_sha256, out=report_path
    )

    assert evaluation.returncode != 0, evaluation.stdout
    assert not evaluation.stdout.strip()
    assert not report_path.exists()
