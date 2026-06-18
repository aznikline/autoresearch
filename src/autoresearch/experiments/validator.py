from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ALLOWED_IMPORTS = {"argparse", "json", "pathlib", "__future__"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: tuple[str, ...] = ()


def validate_experiment_script(path: Path, *, workspace: Path) -> ValidationResult:
    issues: list[str] = []
    resolved_path = path.resolve()
    resolved_workspace = workspace.resolve()
    if not resolved_path.is_relative_to(resolved_workspace):
        issues.append("experiment script must live inside workspace")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return ValidationResult(False, (f"syntax error: {exc}",))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in ALLOWED_IMPORTS:
                    issues.append(f"import not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root not in ALLOWED_IMPORTS:
                issues.append(f"import not allowed: {node.module}")
    return ValidationResult(not issues, tuple(issues))
