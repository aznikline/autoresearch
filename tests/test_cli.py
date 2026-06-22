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


def test_cli_completion_audit_writes_report_and_fails_when_incomplete(
    tmp_path: Path,
    capsys,
) -> None:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "completion.json"

    exit_code = main(
        [
            "audit-completion",
            "--root",
            str(root),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["complete"] is False
    assert "MD-002" in payload["blocked_requirements"]
    assert json.loads(output.read_text()) == payload


def test_cli_recover_rejects_nonrecoverable_run(config_file: Path, capsys) -> None:
    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "test idea",
            "--run-id",
            "cli-recover-done",
            "--auto-approve",
        ]
    ) == 0
    run_dir = json.loads(capsys.readouterr().out)["run_dir"]

    assert main(["recover", run_dir, "--config", str(config_file)]) == 2
    assert "not recoverable" in capsys.readouterr().err


def test_cli_capabilities_reports_verified_contract_without_integration_upgrade(
    config_file: Path,
    capsys,
) -> None:
    exit_code = main(["capabilities", "--config", str(config_file)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "level": "contract_supported",
        "profile": "ml-systems-efficiency",
        "venue_id": "mlsys",
        "venue_year": 2026,
        "venue_track": "main",
        "venue_contract_status": "verified",
        "blockers": ["real integration evidence missing"],
    }


def test_cli_reference_bundle_rejects_default_synthetic_run(
    config_file: Path,
    tmp_path: Path,
    capsys,
) -> None:
    config_file.write_text(
        config_file.read_text(encoding="utf-8").replace(
            'research:\n  topic: "test idea"',
            'research:\n  topic: "test idea"\n  profile: "computer-vision"\n'
            '  venue_id: "cvpr"\n  venue_year: 2026',
        ),
        encoding="utf-8",
    )
    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "test idea",
            "--run-id",
            "reference-reject",
            "--auto-approve",
        ]
    ) == 0
    run_dir = json.loads(capsys.readouterr().out)["run_dir"]

    exit_code = main(
        [
            "reference-bundle",
            run_dir,
            "--config",
            str(config_file),
            "--output-root",
            str(tmp_path / "references"),
        ]
    )

    assert exit_code == 2
    assert "not evidence_complete" in capsys.readouterr().err
