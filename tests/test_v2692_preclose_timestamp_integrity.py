import itertools
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "v265" / "CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"


def make_inputs(tmp_path, *, available=True, known_offset_hours=-1, omit_known=False):
    n = 40
    contests = list(range(2001, 2001 + n))
    draws = [tuple(sorted(((i * 5 + j) % 28) + 1 for j in range(5))) for i in range(n)]
    history = pd.DataFrame({"CONCURSO": contests, **{f"R{k+1}": [draw[k] for draw in draws] for k in range(5)}})
    close = pd.date_range("2026-01-01 18:00:00", periods=n, freq="D")
    known = close + pd.Timedelta(hours=known_offset_hours)
    metadata = pd.DataFrame({
        "CONCURSO": contests,
        "sphere_set_id": ["S1"] * n,
        "machine_id": ["M1"] * n,
        "available_before_close": [available] * n,
        "close_time_local": close.astype(str),
        "metadata_known_time_local": known.astype(str),
    })
    if omit_known:
        metadata = metadata.drop(columns=["metadata_known_time_local"])
    hp, mp = tmp_path / "history.csv", tmp_path / "metadata.csv"
    history.to_csv(hp, index=False)
    metadata.to_csv(mp, index=False)
    return hp, mp


def run(tmp_path, *, available=True, known_offset_hours=-1, omit_known=False):
    hp, mp = make_inputs(tmp_path, available=available, known_offset_hours=known_offset_hours, omit_known=omit_known)
    out = tmp_path / "out"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    return proc, out


def test_valid_preclose_timestamps_pass(tmp_path):
    proc, out = run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((out / "v265_physical_eval_report.json").read_text())
    assert report["model_version"] == "V269.2-preclose-timestamp-integrity"
    assert report["all_metadata_available_before_close"] is True


def test_timestamp_at_or_after_close_fails_even_if_flag_true(tmp_path):
    proc, out = run(tmp_path, known_offset_hours=0)
    assert proc.returncode != 0
    assert "must be strictly before close_time_local" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_false_availability_flag_fails_closed(tmp_path):
    proc, out = run(tmp_path, available=False)
    assert proc.returncode != 0
    assert "must be available before close for every history row" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_missing_timestamp_column_fails_closed(tmp_path):
    proc, out = run(tmp_path, omit_known=True)
    assert proc.returncode != 0
    assert "metadata_known_time_local" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()
