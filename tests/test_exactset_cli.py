from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "v264" / "CHISPAZO_V264_EXACTSET_ANYTIME.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_help_does_not_start_model():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--history" in result.stdout
    assert "--out-dir" in result.stdout
    assert "--warmup" in result.stdout


def test_history_and_output_are_required():
    result = run_cli()
    assert result.returncode == 2
    assert "--history" in result.stderr
    assert "--out-dir" in result.stderr


def test_warmup_must_be_at_least_two():
    result = run_cli(
        "--history", "history.csv",
        "--out-dir", "out",
        "--warmup", "1",
    )
    assert result.returncode == 2
    assert "--warmup must be >= 2" in result.stderr
