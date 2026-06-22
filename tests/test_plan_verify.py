from __future__ import annotations

import json
from pathlib import Path

from autoresearch.cli import main
from autoresearch.config import AutoresearchConfig
from autoresearch.pipeline.runner import PipelineRunner
from autoresearch.pipeline.verification import verify_run


def test_plan_is_side_effect_free_and_reports_gates(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)

    plan = runner.plan(topic="test idea")

    assert plan["topic"] == "test idea"
    assert plan["capability"]["level"] == "contract_supported"
    assert plan["capability"]["blockers"] == ["real integration evidence missing"]
    assert plan["stages"][0]["slug"] == "idea_intake"
    assert {item["slug"] for item in plan["stages"] if item["approval_gate"]} == {
        "literature_screen",
        "experiment_design",
        "result_analysis_decision",
        "final_verification_export",
    }
    assert not Path(config.runtime.artifacts_root).exists()


def test_verify_run_detects_export_tampering(config: AutoresearchConfig) -> None:
    result = PipelineRunner(config).run(
        topic="test idea", run_id="verify-run", auto_approve=True
    )
    run_dir = Path(result["run_dir"])

    assert verify_run(run_dir, config=config)["ok"] is True
    paper = run_dir / "stage-12-final_verification_export" / "paper.tex"
    paper.write_text(paper.read_text() + "% tampered\n", encoding="utf-8")

    verification = verify_run(run_dir, config=config)
    assert verification["ok"] is False
    assert any("hash mismatch" in issue for issue in verification["issues"])


def test_cli_plan_and_verify(config_file: Path, capsys) -> None:
    assert main(
        ["plan", "--config", str(config_file), "--topic", "test idea"]
    ) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["capability"]["level"] == "contract_supported"

    assert main(
        [
            "run",
            "--config",
            str(config_file),
            "--topic",
            "test idea",
            "--run-id",
            "cli-verify",
            "--auto-approve",
        ]
    ) == 0
    run_dir = json.loads(capsys.readouterr().out)["run_dir"]
    assert main(["verify", run_dir, "--config", str(config_file)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
