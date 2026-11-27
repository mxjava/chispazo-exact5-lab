from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APPENDER = REPO_ROOT / "src" / "data" / "append_verified_result.py"


@pytest.mark.parametrize(
    "source_url",
    [
        "https://www.loterianacional.gob.mx/Chispazo/Resultados",
        "https://www.loterianacional.gob.mx/Mascarillas/Mascarillas",
        "https://www.loterianacional.gob.mx/Documentos/Acta/12398.pdf",
    ],
)
def test_append_is_fail_closed_and_does_not_mutate_any_file(tmp_path, source_url):
    history = tmp_path / "history.csv"
    provenance = tmp_path / "provenance.csv"
    original_history = b"CONCURSO,R1,R2,R3,R4,R5\n12397,5,20,23,26,28\n"
    history.write_bytes(original_history)

    result = subprocess.run(
        [
            sys.executable,
            str(APPENDER),
            "--history",
            str(history),
            "--contest",
            "12398",
            "--date",
            "2026-11-26",
            "--numbers",
            "1",
            "2",
            "3",
            "4",
            "5",
            "--source-url",
            source_url,
            "--provenance",
            str(provenance),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "BLOCKED" in result.stderr
    assert "Article 15 Acta" in result.stderr
    assert "no file changes" in result.stderr
    assert history.read_bytes() == original_history
    assert not provenance.exists()
