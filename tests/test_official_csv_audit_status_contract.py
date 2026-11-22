"""Regression guard for the official CSV audit's fail-closed status contract."""
import ast
from pathlib import Path


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
