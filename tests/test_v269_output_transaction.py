import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"
spec = importlib.util.spec_from_file_location("v267_integrated", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(vals):
    return {f"R{i+1}": vals[i] for i in range(5)}


def inputs(tmp_path, duplicate_metadata=False, duplicate_history=False, bad_draw=None, availability=True):
    contests = list(range(1000, 1140))
    history = pd.DataFrame({
        "CONCURSO": contests,
        "R1": [1.0] * 140, "R2": [2.0] * 140, "R3": [3.0] * 140,
        "R4": [4.0] * 140, "R5": [5.0] * 140,
    })
    closes = pd.date_range("2026-01-01 18:00:00", periods=140, freq="D")
    metadata = pd.DataFrame({
        "CONCURSO": contests,
        "sphere_set_id": ["S1"] * 140,
        "machine_id": ["M1"] * 140,
        "available_before_close": [availability] * 140,
        "close_time_local": closes.astype(str),
        "metadata_known_time_local": (closes - pd.Timedelta(hours=1)).astype(str),
    })
    if bad_draw is not None:
        history.loc[history.index[20], "R5"] = bad_draw
    if duplicate_history:
        history = pd.concat([history, history.iloc[[0]]], ignore_index=True)
    if duplicate_metadata:
        metadata = pd.concat([metadata, metadata.iloc[[0]]], ignore_index=True)
    hp, mp = tmp_path / "history.csv", tmp_path / "metadata.csv"
    history.to_csv(hp, index=False)
    metadata.to_csv(mp, index=False)
    return hp, mp


def invoke(tmp_path, **kwargs):
    hp, mp = inputs(tmp_path, **kwargs)
    out = tmp_path / "out"
    return subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True), out


def test_valid_unique_join_reports_exact_sample_and_coverage(tmp_path):
    proc, out = invoke(tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((out / "v265_physical_eval_report.json").read_text())
    assert report["n"] == 130
    assert report["joined_rows"] == 140
    assert report["metadata_coverage_fraction_of_history"] == 1.0
    assert report["decision"] == "RESEARCH_ONLY_MULTIPLICITY_CONTROL_REQUIRED"
    assert report["research_edge"] is False
    assert report["actionable_for_betting"] is False


def test_duplicate_metadata_fails_closed(tmp_path):
    proc, out = invoke(tmp_path, duplicate_metadata=True)
    assert proc.returncode != 0
    assert "metadata has duplicate CONCURSO IDs" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_duplicate_history_fails_closed(tmp_path):
    proc, out = invoke(tmp_path, duplicate_history=True)
    assert proc.returncode != 0
    assert "history has duplicate CONCURSO IDs" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_incomplete_metadata_coverage_fails_closed(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp).iloc[:-1]
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-incomplete-metadata"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "metadata CONCURSO coverage must exactly match history" in proc.stderr
    assert "missing_metadata=[1139]" in proc.stderr
    assert not (out / "v265_physical_prequential.csv").exists()
    assert not (out / "v265_physical_eval_report.json").exists()


def test_extra_metadata_contests_fail_closed(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp)
    metadata.loc[len(metadata)] = [99999, "S1", "M1", True, "2026-06-01 18:00:00", "2026-06-01 17:00:00"]
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-extra-metadata"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "metadata CONCURSO coverage must exactly match history" in proc.stderr
    assert "extra_metadata=[99999]" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_invalid_availability_in_burn_in_fails_closed(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp, dtype={"available_before_close": "string"})
    metadata.loc[0, "available_before_close"] = "unknown"
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-invalid-burn-availability"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "invalid available_before_close" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


@pytest.mark.parametrize("ids", [[1001.5], ["bad"], [float("inf")]])
def test_invalid_contest_keys_fail_closed(ids):
    with pytest.raises(ValueError, match="finite integer"):
        mod.validate_contest_keys(pd.DataFrame({"CONCURSO": ids}), "history")


def test_integral_contest_ids_normalize_to_int64():
    got = mod.validate_contest_keys(pd.DataFrame({"CONCURSO": ["1001", 1002.0]}), "metadata")
    assert got["CONCURSO"].tolist() == [1001, 1002]
    assert str(got["CONCURSO"].dtype) == "int64"


@pytest.mark.parametrize("vals,match", [
    ([1,2,3,4,4], "distinct"),
    ([0,2,3,4,5], "outside 1..28"),
    ([1,2,3,4,29], "outside 1..28"),
    ([1,2,3,4,5.5], "finite integer"),
    ([1,2,3,4,float("nan")], "finite integer"),
    ([1,2,3,4,"x"], "not numeric"),
])
def test_invalid_draws_rejected(vals, match):
    with pytest.raises(ValueError, match=match):
        mod.validate_draw_numbers(row(vals), 987)


def test_valid_draw_sorted():
    assert mod.validate_draw_numbers(row([5,1,28,9,13]), 123) == (1,5,9,13,28)


def test_availability_requires_explicit_boolean_encoding():
    assert mod.parse_availability("true", 1001) is True
    assert mod.parse_availability("no", 1001) is False
    with pytest.raises(ValueError, match="invalid available_before_close"):
        mod.parse_availability("maybe", 1001)


def test_holm_adjustment_known_case():
    got = mod.holm_adjust([0.01, 0.04, 0.03])
    assert np.allclose(got, [0.03, 0.06, 0.06])


def test_holm_rejects_invalid_pvalues():
    with pytest.raises(ValueError, match="p-values"):
        mod.holm_adjust([0.2, float("nan")])


def test_p_family_requires_candidate_and_exact_observed_p(tmp_path):
    path = tmp_path / "family.csv"
    pd.DataFrame({"candidate_id": ["physical_ensemble", "model_b"],
                  "p_one_sided": [0.03, 0.04]}).to_csv(path, index=False)
    adjusted, n = mod.read_p_family(path, "physical_ensemble", 0.03)
    assert adjusted == pytest.approx(0.06)
    assert n == 2
    with pytest.raises(ValueError, match="does not match"):
        mod.read_p_family(path, "physical_ensemble", 0.031)


def test_p_family_rejects_missing_candidate(tmp_path):
    path = tmp_path / "family.csv"
    pd.DataFrame({"candidate_id": ["other"], "p_one_sided": [0.03]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing from p-family"):
        mod.read_p_family(path, "physical_ensemble", 0.03)


def test_post_close_timestamp_rejected_even_when_flag_says_true(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp)
    metadata.loc[0, "metadata_known_time_local"] = metadata.loc[0, "close_time_local"]
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-post-close-time"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "must be strictly before close_time_local" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_unavailable_metadata_rejected_even_if_timestamps_precede_close(tmp_path):
    hp, mp = inputs(tmp_path, availability=True)
    metadata = pd.read_csv(mp)
    metadata.loc[0, "available_before_close"] = False
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-unavailable-flag"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "must be available before close for every history row" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_missing_preclose_timestamp_column_rejected(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp).drop(columns=["metadata_known_time_local"])
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-missing-time"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "metadata_known_time_local" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_invalid_local_timestamp_rejected(tmp_path):
    hp, mp = inputs(tmp_path)
    metadata = pd.read_csv(mp)
    metadata.loc[0, "close_time_local"] = "not-a-time"
    metadata.to_csv(mp, index=False)
    out = tmp_path / "out-invalid-time"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "invalid close_time_local timestamp" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_invalid_availability_fails_cli(tmp_path):
    proc, out = invoke(tmp_path, availability="maybe")
    assert proc.returncode != 0
    assert "invalid available_before_close" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


@pytest.mark.parametrize("bad_draw", [5.5, 29, float("inf")])
def test_invalid_history_draw_fails_cli(tmp_path, bad_draw):
    proc, out = invoke(tmp_path, bad_draw=bad_draw)
    assert proc.returncode != 0
    assert not (out / "v265_physical_eval_report.json").exists()


def test_nonpositive_contest_ids_rejected():
    with pytest.raises(ValueError, match="positive integers"):
        mod.validate_contest_keys(pd.DataFrame({"CONCURSO": [0, 1001]}), "history")


def test_p_family_rejects_blank_or_whitespace_duplicate_ids(tmp_path):
    blank = tmp_path / "blank.csv"
    pd.DataFrame({"candidate_id": ["   "], "p_one_sided": [0.03]}).to_csv(blank, index=False)
    with pytest.raises(ValueError, match="non-empty and unique"):
        mod.read_p_family(blank, "physical_ensemble", 0.03)
    duplicate = tmp_path / "duplicate.csv"
    pd.DataFrame({"candidate_id": ["model_a", " model_a "], "p_one_sided": [0.03, 0.04]}).to_csv(duplicate, index=False)
    with pytest.raises(ValueError, match="non-empty and unique"):
        mod.read_p_family(duplicate, "model_a", 0.03)


def test_metadata_regime_ids_must_be_nonempty(tmp_path):
    hp, mp = inputs(tmp_path)
    md = pd.read_csv(mp)
    md.loc[4, "machine_id"] = "   "
    md.to_csv(mp, index=False)
    out = tmp_path / "out-empty-machine"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "machine_id must be present and non-empty" in proc.stderr
    assert not (out / "v265_physical_eval_report.json").exists()


def test_cli_rejects_invalid_prior_and_burn(tmp_path):
    hp, mp = inputs(tmp_path)
    for args, expected in [(["--prior-set", "0"], "--prior-set must be finite and > 0"),
                           (["--prior-machine", "nan"], "--prior-machine must be finite and > 0"),
                           (["--burn", "-1"], "--burn must be >= 0")]:
        out = tmp_path / ("out-" + str(len(list(tmp_path.iterdir()))))
        proc = subprocess.run([
            sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
            "--out-dir", str(out), *args,
        ], capture_output=True, text=True)
        assert proc.returncode != 0
        assert expected in proc.stderr
        assert not (out / "v265_physical_eval_report.json").exists()


def test_report_binds_results_to_input_hashes_and_parameters(tmp_path):
    proc, out = invoke(tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((out / "v265_physical_eval_report.json").read_text())
    assert report["model_version"] == "V269.2-preclose-timestamp-integrity"
    assert len(report["input_sha256"]["history"]) == 64
    assert len(report["input_sha256"]["metadata"]) == 64
    assert report["input_sha256"]["p_family"] is None
    assert report["parameters"]["burn"] == 10
    assert report["chronology"] == "ascending CONCURSO ID; score first, then update counts"


def test_invalid_p_family_publishes_no_outputs(tmp_path):
    hp, mp = inputs(tmp_path)
    family = tmp_path / "bad_family.csv"
    pd.DataFrame({"candidate_id": ["other"], "p_one_sided": [0.03]}).to_csv(family, index=False)
    out = tmp_path / "out-invalid-family"
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--p-family", str(family), "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "missing from p-family" in proc.stderr
    assert not (out / "v265_physical_prequential.csv").exists()
    assert not (out / "v265_physical_eval_report.json").exists()
    assert not list(out.glob(".*.tmp"))


def test_failed_rerun_removes_stale_success_artifacts(tmp_path):
    hp, mp = inputs(tmp_path)
    out = tmp_path / "out-stale"
    out.mkdir()
    (out / "v265_physical_prequential.csv").write_text("STALE CSV\n")
    (out / "v265_physical_eval_report.json").write_text('{"decision":"STALE"}')
    # Bad draw fails before a new report is produced.
    history = pd.read_csv(hp)
    history.loc[20, "R5"] = 5.5
    history.to_csv(hp, index=False)
    proc = subprocess.run([
        sys.executable, str(SCRIPT), "--history", str(hp), "--metadata", str(mp),
        "--burn", "10", "--out-dir", str(out),
    ], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "finite integer" in proc.stderr
    assert not (out / "v265_physical_prequential.csv").exists()
    assert not (out / "v265_physical_eval_report.json").exists()
    assert not list(out.glob(".*.tmp"))
