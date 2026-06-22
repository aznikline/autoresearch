from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, expected: int = 0) -> dict[str, object]:
    completed = subprocess.run(
        ["uv", "run", "autoresearch", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == expected, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


def test_clean_process_auto_and_hitl_operator_paths(config_file: Path) -> None:
    config_arg = str(config_file)
    plan = _run(
        "plan",
        "--config",
        config_arg,
        "--topic",
        "operator workflow",
    )
    assert plan["capability"]["level"] == "contract_supported"
    assert plan["capability"]["blockers"] == ["real integration evidence missing"]

    automatic = _run(
        "run",
        "--config",
        config_arg,
        "--topic",
        "operator workflow",
        "--run-id",
        "subprocess-auto",
        "--auto-approve",
    )
    assert automatic["status"] == "done"
    assert _run("verify", automatic["run_dir"], "--config", config_arg)["ok"] is True

    manual = _run(
        "run",
        "--config",
        config_arg,
        "--topic",
        "operator workflow",
        "--run-id",
        "subprocess-hitl",
    )
    for expected_gate in (
        "literature_screen",
        "experiment_design",
        "result_analysis_decision",
        "final_verification_export",
    ):
        assert manual["checkpoint"]["stage_slug"] == expected_gate
        _run(
            "approve",
            manual["run_dir"],
            "--actor",
            "reviewer",
            "--reason",
            "reviewed",
        )
        manual = _run(
            "resume",
            manual["run_dir"],
            "--config",
            config_arg,
            "--actor",
            "reviewer",
        )
    assert manual["status"] == "done"
    assert _run("export", manual["run_dir"])["submission_ready"] is False
    assert _run("verify", manual["run_dir"], "--config", config_arg)["ok"] is True
