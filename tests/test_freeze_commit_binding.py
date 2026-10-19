import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/pipeline/freeze_prediction.py"
IMPORT_FREEZE = f"import sys; sys.path.insert(0, r'{SCRIPT.parent}'); import importlib.util; "


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Exact5 test")
    (repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-qm", "fixture")
    return repo, git(repo, "rev-parse", "HEAD")


def test_binding_accepts_matching_clean_head(tmp_path):
    repo, sha = make_repo(tmp_path)
    proc = subprocess.run([sys.executable, "-c",
        f"{IMPORT_FREEZE}s=importlib.util.spec_from_file_location('f', r'{SCRIPT}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.verify_commit_binding('{sha}', r'{repo}'))"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == sha


def test_binding_rejects_valid_but_unrelated_sha(tmp_path):
    repo, sha = make_repo(tmp_path)
    unrelated = "0" * 40 if sha != "0" * 40 else "1" * 40
    proc = subprocess.run([sys.executable, "-c",
        f"{IMPORT_FREEZE}s=importlib.util.spec_from_file_location('f', r'{SCRIPT}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify_commit_binding('{unrelated}', r'{repo}')"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "does not match checked-out HEAD" in proc.stderr


def test_binding_rejects_tracked_worktree_changes(tmp_path):
    repo, sha = make_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed after commit\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-c",
        f"{IMPORT_FREEZE}s=importlib.util.spec_from_file_location('f', r'{SCRIPT}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify_commit_binding('{sha}', r'{repo}')"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "tracked changes" in proc.stderr


def test_binding_rejects_missing_git_checkout(tmp_path):
    proc = subprocess.run([sys.executable, "-c",
        f"{IMPORT_FREEZE}s=importlib.util.spec_from_file_location('f', r'{SCRIPT}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify_commit_binding('{ 'a' * 40 }', r'{tmp_path}')"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "Git checkout is required" in proc.stderr


def test_binding_rejects_malformed_sha(tmp_path):
    repo, _ = make_repo(tmp_path)
    proc = subprocess.run([sys.executable, "-c",
        f"{IMPORT_FREEZE}s=importlib.util.spec_from_file_location('f', r'{SCRIPT}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify_commit_binding('not-a-sha', r'{repo}')"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "full 40-character Git SHA" in proc.stderr


def test_cli_refuses_mismatch_without_publishing(tmp_path):
    repo, sha = make_repo(tmp_path)
    portfolio = tmp_path / "portfolio.csv"
    combos = []
    for a in range(1, 29):
        for b in range(a + 1, 29):
            for c in range(b + 1, 29):
                for d in range(c + 1, 29):
                    for e in range(d + 1, 29):
                        combos.append(f"{a:02d}-{b:02d}-{c:02d}-{d:02d}-{e:02d}")
                        if len(combos) == 30:
                            break
                    if len(combos) == 30: break
                if len(combos) == 30: break
            if len(combos) == 30: break
        if len(combos) == 30: break
    pd.DataFrame({"combo": combos}).to_csv(portfolio, index=False)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({"state":"PASS","target":12250,"inputs":{"history":{"contest_max":12249,"sha256":"a"*64},"ranking":{"sha256":"b"*64}}}), encoding="utf-8")
    ledger = tmp_path / "ledger"
    mismatch = "0" * 40 if sha != "0" * 40 else "1" * 40
    proc = subprocess.run([sys.executable, str(SCRIPT), "--target", "12250", "--portfolio", str(portfolio),
        "--preflight", str(preflight), "--model-version", "test", "--commit-sha", mismatch,
        "--ledger-dir", str(ledger), "--repo-root", str(repo)], cwd=repo, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "does not match checked-out HEAD" in proc.stderr
    assert not (ledger / "target_12250.json").exists()


def test_cli_records_verified_head(tmp_path):
    repo, sha = make_repo(tmp_path)
    portfolio = tmp_path / "portfolio.csv"
    combos = []
    for a in range(1, 29):
        for b in range(a + 1, 29):
            for c in range(b + 1, 29):
                for d in range(c + 1, 29):
                    for e in range(d + 1, 29):
                        combos.append(f"{a:02d}-{b:02d}-{c:02d}-{d:02d}-{e:02d}")
                        if len(combos) == 30: break
                    if len(combos) == 30: break
                if len(combos) == 30: break
            if len(combos) == 30: break
        if len(combos) == 30: break
    pd.DataFrame({"combo": combos}).to_csv(portfolio, index=False)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({"state":"PASS","target":12250,"inputs":{"history":{"contest_max":12249,"sha256":"a"*64},"ranking":{"sha256":"b"*64}}}), encoding="utf-8")
    ledger = tmp_path / "ledger"
    proc = subprocess.run([sys.executable, str(SCRIPT), "--target", "12250", "--portfolio", str(portfolio),
        "--preflight", str(preflight), "--model-version", "test", "--commit-sha", sha,
        "--ledger-dir", str(ledger), "--repo-root", str(repo)], cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    registration = json.loads((ledger / "target_12250.json").read_text(encoding="utf-8"))
    assert registration["commit_sha"] == sha
    assert len(registration["lines"]) == 30


def test_competing_cli_freezes_publish_exactly_one_registration(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    repo, sha = make_repo(tmp_path)
    portfolio = tmp_path / "portfolio.csv"
    combos = []
    for a in range(1, 29):
        for b in range(a + 1, 29):
            for c in range(b + 1, 29):
                for d in range(c + 1, 29):
                    for e in range(d + 1, 29):
                        combos.append(f"{a:02d}-{b:02d}-{c:02d}-{d:02d}-{e:02d}")
                        if len(combos) == 30:
                            break
                    if len(combos) == 30: break
                if len(combos) == 30: break
            if len(combos) == 30: break
        if len(combos) == 30: break
    pd.DataFrame({"combo": combos}).to_csv(portfolio, index=False)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({
        "state": "PASS", "target": 12250,
        "inputs": {"history": {"contest_max": 12249, "sha256": "a" * 64},
                   "ranking": {"sha256": "b" * 64}},
    }), encoding="utf-8")
    ledger = tmp_path / "ledger"
    barrier = Barrier(2)

    def run_once():
        barrier.wait()
        return subprocess.run([
            sys.executable, str(SCRIPT), "--target", "12250", "--portfolio", str(portfolio),
            "--preflight", str(preflight), "--model-version", "test", "--commit-sha", sha,
            "--ledger-dir", str(ledger), "--repo-root", str(repo),
        ], cwd=repo, capture_output=True, text=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run_once(), range(2)))
    assert sum(r.returncode == 0 for r in results) == 1, [(r.returncode, r.stderr) for r in results]
    rejected = next(r for r in results if r.returncode != 0)
    assert "already exists" in rejected.stderr
    registration = json.loads((ledger / "target_12250.json").read_text(encoding="utf-8"))
    assert registration["commit_sha"] == sha
    assert len(registration["lines"]) == 30
    assert not list(ledger.glob(".*.tmp"))
