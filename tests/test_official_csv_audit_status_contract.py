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
    assert check([]) is True
