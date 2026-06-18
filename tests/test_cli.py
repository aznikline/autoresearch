from __future__ import annotations

import json
from pathlib import Path

from autoresearch.cli import main


def test_cli_init_writes_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "config.yaml"

    exit_code = main(["init", "--path", str(target)])

    assert exit_code == 0
    assert target.exists()
    assert "wrote" in capsys.readouterr().out


def test_cli_run_auto_approve_completes(config_file: Path, capsys) -> None:
    exit_code = main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "A tiny empirical ML idea",
            "--run-id",
            "test-run",
            "--auto-approve",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "done"
    assert payload["stages_completed"] == 12


def test_cli_status_reports_missing_run(tmp_path: Path, capsys) -> None:
    exit_code = main(["status", str(tmp_path / "missing")])

    assert exit_code == 1
    assert "not found" in capsys.readouterr().out
