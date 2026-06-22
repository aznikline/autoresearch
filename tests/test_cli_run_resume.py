from __future__ import annotations

import json
from pathlib import Path

from autoresearch.cli import main


def _payload(capsys) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_cli_manual_gate_flow_reaches_export(config_file: Path, capsys) -> None:
    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "A tiny empirical ML idea",
            "--run-id",
            "manual-cli-run",
        ]
    ) == 0
    result = _payload(capsys)
    run_dir = Path(str(result["run_dir"]))

    for expected_stage in (
        "literature_screen",
        "experiment_design",
        "result_analysis_decision",
        "final_verification_export",
    ):
        assert result["status"] == "paused"
        assert result["checkpoint"]["stage_slug"] == expected_stage
        assert main(["approve", str(run_dir), "--reason", "reviewed"]) == 0
        approval = _payload(capsys)
        assert approval["decision"] == "approve"
        assert main(["resume", str(run_dir), "--config", str(config_file)]) == 0
        result = _payload(capsys)

    assert result["status"] == "done"
    assert main(["export", str(run_dir)]) == 0
    exported = _payload(capsys)
    assert exported["status"] == "ready"
    assert "paper.tex" in exported["files"]
    assert "evidence_graph.json" in exported["files"]
    assert "governance_report.json" in exported["files"]
    assert "venue_export.json" in exported["files"]
    assert exported["submission_ready"] is False


def test_cli_reject_requires_reason(config_file: Path, capsys) -> None:
    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "A tiny empirical ML idea",
            "--run-id",
            "reject-cli-run",
        ]
    ) == 0
    run_dir = Path(str(_payload(capsys)["run_dir"]))

    exit_code = main(["reject", str(run_dir)])

    assert exit_code == 2
    assert "reason is required" in capsys.readouterr().err


def test_cli_actor_bound_approval_and_cancel(config_file: Path, capsys) -> None:
    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "test idea",
            "--run-id",
            "actor-cli-run",
        ]
    ) == 0
    run_dir = str(_payload(capsys)["run_dir"])

    assert main(
        ["approve", run_dir, "--reason", "reviewed", "--actor", "alice"]
    ) == 0
    _payload(capsys)
    assert main(
        ["resume", run_dir, "--config", str(config_file), "--actor", "bob"]
    ) == 2
    assert "decision actor" in capsys.readouterr().err
    assert main(
        ["cancel", run_dir, "--actor", "alice", "--reason", "budget revoked"]
    ) == 0
    cancelled = _payload(capsys)
    assert cancelled["status"] == "cancelled"
