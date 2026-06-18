from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.validator import validate_experiment_script


def test_validator_allows_workspace_script_with_safe_imports(tmp_path: Path) -> None:
    script = tmp_path / "experiment.py"
    script.write_text("import json\nfrom pathlib import Path\n", encoding="utf-8")

    result = validate_experiment_script(script, workspace=tmp_path)

    assert result.ok


def test_validator_rejects_disallowed_import(tmp_path: Path) -> None:
    script = tmp_path / "experiment.py"
    script.write_text("import socket\n", encoding="utf-8")

    result = validate_experiment_script(script, workspace=tmp_path)

    assert not result.ok
    assert "import not allowed: socket" in result.issues


def test_validator_rejects_script_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    script = tmp_path / "experiment.py"
    script.write_text("import json\n", encoding="utf-8")

    result = validate_experiment_script(script, workspace=workspace)

    assert not result.ok
    assert "experiment script must live inside workspace" in result.issues
