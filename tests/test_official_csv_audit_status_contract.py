"""Regression guards for the official CSV audit's fail-closed contracts."""
import ast
from pathlib import Path


def _load_pure_function(script: Path, function_name: str):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(module, str(script), "exec"), namespace)
    return namespace[function_name]


def test_missing_canonical_ids_force_blocked_audit_status():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "audit_status"
                for target in node.targets)
    )
    expression = ast.unparse(assignment.value)
    assert "canonical_not_in_official" in expression
    assert "BLOCKED_CANONICAL_CONFLICTS" in expression


def test_post_baseline_continuity_accepts_latest_observed_maximum():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "post_baseline_ids_are_contiguous")
    assert check([12250, 12251, 12388]) is False
    assert check(list(range(12250, 12389))) is True


def test_post_baseline_continuity_fails_closed_on_gaps():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "post_baseline_ids_are_contiguous")
    assert check([12250, 12252, 12253]) is False
    assert check([]) is False


def test_daily_pair_structure_accepts_two_consecutive_odd_even_ids():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "analyze_daily_pair_structure")
    result = check(
        [
            ["5924", "01/01/2018"],
            ["5923", "01/01/2018"],
            ["5925", "02/01/2018"],
            ["5926", "02/01/2018"],
        ],
        0,
        1,
    )
    assert result["observed_dates"] == 2
    assert result["dates_matching_two_consecutive_odd_even_ids"] == 2
    assert result["post_transition_ids_contiguous"] is True
    assert result["anomaly_count"] == 0
    assert result["classification"] == "STRUCTURAL_PATTERN_ONLY_NO_MODALITY_ASSERTION"


def test_daily_pair_structure_fails_closed_on_missing_or_wrong_pairs():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "analyze_daily_pair_structure")
    result = check(
        [
            ["5923", "01/01/2018"],
            ["5925", "02/01/2018"],
            ["5927", "02/01/2018"],
            ["5928", "03/01/2018"],
            ["5930", "03/01/2018"],
        ],
        0,
        1,
    )
    assert result["dates_with_other_row_count"] == 1
    assert result["anomaly_count"] == 3
    assert result["post_transition_ids_contiguous"] is False
    assert {item["reason"] for item in result["anomalies"]} == {
        "EXPECTED_TWO_CONSECUTIVE_IDS_ODD_THEN_EVEN"
    }


def test_daily_pair_structure_does_not_project_rule_before_transition():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "analyze_daily_pair_structure")
    result = check(
        [
            ["558", "19/10/2002"],
            ["559", "19/10/2002"],
            ["5923", "25/09/2017"],
            ["5924", "25/09/2017"],
        ],
        0,
        1,
    )
    assert result["observed_dates"] == 1
    assert result["anomaly_count"] == 0


def test_schema_mapping_requires_unique_required_columns():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    resolve = _load_pure_function(script, "resolve_column_mapping")
    aliases = {
        "draw_id": {"concurso"},
        "date": {"fecha"},
        "n1": {"r1"}, "n2": {"r2"}, "n3": {"r3"},
        "n4": {"r4"}, "n5": {"r5"},
    }
    mapping, missing = resolve(["CONCURSO", "FECHA", "R1", "R2", "R3", "R4", "R5"], aliases)
    assert missing == []
    assert mapping == {"draw_id": 0, "date": 1, "n1": 2, "n2": 3, "n3": 4, "n4": 5, "n5": 6}


def test_schema_mapping_rejects_ambiguous_and_missing_required_columns():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    resolve = _load_pure_function(script, "resolve_column_mapping")
    aliases = {
        "draw_id": {"concurso"}, "date": {"fecha"},
        "n1": {"r1"}, "n2": {"r2"}, "n3": {"r3"},
        "n4": {"r4"}, "n5": {"r5"},
    }
    mapping, missing = resolve(["CONCURSO", "FECHA", "R1", "R1", "R3", "R4", "R5"], aliases)
    assert "n1" in missing
    assert "n2" in missing
    assert "n1" not in mapping
    assert "n2" not in mapping


def test_official_csv_rows_must_match_header_width():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    check = _load_pure_function(script, "row_width_is_valid")
    assert check(["1", "2", "3"], ["a", "b", "c"]) is True
    assert check(["1", "2", "3", "extra"], ["a", "b", "c"]) is False
    assert check(["1", "2"], ["a", "b", "c"]) is False


def test_canonical_baseline_is_pinned_to_immutable_commit_and_digest():
    script = Path(__file__).parents[1] / "scripts" / "audit_official_chispazo_csv.py"
    source = script.read_text(encoding="utf-8")
    assert "CANONICAL_BASELINE_COMMIT = \"8fc7d6fd503e1ac7be6b504daef099404c8ca064\"" in source
    assert "CANONICAL_BASELINE_SHA256 = \"5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a\"" in source
    assert "if canonical_sha256 != CANONICAL_BASELINE_SHA256" in source
