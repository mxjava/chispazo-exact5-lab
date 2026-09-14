from pathlib import Path
import pandas as pd

from src.validation.preflight import validate_history


def test_future_leakage_blocks(tmp_path: Path):
    p = tmp_path / "h.csv"
    pd.DataFrame({
        "concurso": [100, 101],
        "n1": [1, 2], "n2": [3, 4], "n3": [5, 6], "n4": [7, 8], "n5": [9, 10]
    }).to_csv(p, index=False)
    checks, _ = validate_history(p, target=101)
    m = {c.name: c.status for c in checks}
    assert m["no_future_leakage"] == "FAIL"


def test_clean_history_passes(tmp_path: Path):
    p = tmp_path / "h.csv"
    pd.DataFrame({
        "concurso": [100, 101],
        "n1": [1, 2], "n2": [3, 4], "n3": [5, 6], "n4": [7, 8], "n5": [9, 10]
    }).to_csv(p, index=False)
    checks, _ = validate_history(p, target=102)
    assert all(c.status == "PASS" for c in checks)
