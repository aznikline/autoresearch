from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ALLOWED_IMPORTS = {"argparse", "json", "pathlib", "__future__"}
FORBIDDEN_CALLS = {"__import__", "eval", "exec", "compile", "breakpoint"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: tuple[str, ...] = ()


def validate_experiment_script(
    path: Path,
    *,
    workspace: Path,
    allowed_imports: tuple[str, ...] = (),
) -> ValidationResult:
    issues: list[str] = []
    resolved_path = path.resolve()
    resolved_workspace = workspace.resolve()
    if not resolved_path.is_relative_to(resolved_workspace):
        issues.append("experiment script must live inside workspace")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return ValidationResult(False, (f"syntax error: {exc}",))

    effective_imports = ALLOWED_IMPORTS | set(allowed_imports)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in effective_imports:
                    issues.append(f"import not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root not in effective_imports:
                issues.append(f"import not allowed: {node.module}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FORBIDDEN_CALLS
        ):
            issues.append(f"call not allowed: {node.func.id}")
    return ValidationResult(not issues, tuple(issues))
