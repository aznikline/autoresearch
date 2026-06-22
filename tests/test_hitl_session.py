from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig
from autoresearch.hitl.session import HITLError, read_decisions, record_decision
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.runner import PipelineRunner


def test_approved_run_resumes_through_every_gate(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="manual-run")
    run_dir = Path(result["run_dir"])

    for expected_stage in (
        "literature_screen",
        "experiment_design",
        "result_analysis_decision",
        "final_verification_export",
    ):
        assert result["status"] == "paused"
        assert result["checkpoint"]["stage_slug"] == expected_stage
        record_decision(run_dir, decision="approve", reason="reviewed")
        result = runner.resume(run_dir)

    assert result["status"] == "done"
    assert result["stages_completed"] == 12
    checkpoint = read_checkpoint(run_dir)
    assert checkpoint is not None
    assert checkpoint["status"] == "done"
    assert [item["decision"] for item in read_decisions(run_dir)].count("approve") == 4
    assert [item["decision"] for item in read_decisions(run_dir)].count("consumed") == 4


def test_resume_requires_a_decision_for_paused_gate(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="no-decision-run")

    with pytest.raises(HITLError, match="approve or reject"):
        runner.resume(Path(result["run_dir"]))


def test_rejection_rolls_back_and_pauses_at_same_gate(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="rejected-run")
    run_dir = Path(result["run_dir"])
    record_decision(run_dir, decision="approve", reason="literature reviewed")
    result = runner.resume(run_dir)
    assert result["checkpoint"]["stage_slug"] == "experiment_design"

    record_decision(run_dir, decision="reject", reason="hypotheses need revision")
    result = runner.resume(run_dir)

    assert result["status"] == "paused"
    assert result["checkpoint"]["stage_slug"] == "experiment_design"
    assert result["checkpoint"]["message"] == "approval required before experiment_design"


def test_decision_requires_a_paused_gate(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="done-run", auto_approve=True)

    with pytest.raises(HITLError, match="not paused"):
        record_decision(Path(result["run_dir"]), decision="approve", reason="late")


def test_resume_rejects_changed_run_config(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="config-change-run")
    run_dir = Path(result["run_dir"])
    record_decision(run_dir, decision="approve", reason="reviewed")
    changed_config = replace(
        config,
        experiment=replace(config.experiment, time_budget_sec=999),
    )

    with pytest.raises(HITLError, match="config does not match"):
        PipelineRunner(changed_config).resume(run_dir)


def test_approval_is_actor_bound_and_artifact_bound(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="bound-approval")
    run_dir = Path(result["run_dir"])
    decision = record_decision(
        run_dir,
        decision="approve",
        reason="reviewed",
        actor="alice",
    )

    assert decision["actor"] == "alice"
    assert len(decision["review_artifacts_sha256"]) == 64
    assert len(decision["config_fingerprint"]) == 64
    with pytest.raises(HITLError, match="decision actor"):
        runner.resume(run_dir, actor="bob")

    candidate = run_dir / "stage-03-literature_collect" / "candidates.jsonl"
    candidate.write_text(candidate.read_text() + "{}\n", encoding="utf-8")
    with pytest.raises(HITLError, match="reviewed artifacts changed"):
        runner.resume(run_dir, actor="alice")


def test_rejection_preserves_reviewed_artifacts_before_rollback(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="preserved-rejection")
    run_dir = Path(result["run_dir"])
    original = (
        run_dir / "stage-03-literature_collect" / "candidates.jsonl"
    ).read_bytes()
    record_decision(
        run_dir,
        decision="reject",
        reason="scope incomplete",
        actor="reviewer",
    )

    runner.resume(run_dir, actor="reviewer")

    snapshots = list(
        (run_dir / "rejected_artifacts").glob(
            "*/stage-03-literature_collect/candidates.jsonl"
        )
    )
    assert len(snapshots) == 1
    assert snapshots[0].read_bytes() == original


def test_resume_rejects_decision_copied_from_another_run(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="decision-target")
    run_dir = Path(result["run_dir"])
    record_decision(run_dir, decision="approve", reason="reviewed")
    decision_path = run_dir / "decisions.jsonl"
    decision = json.loads(decision_path.read_text().splitlines()[0])
    decision["run_id"] = "another-run"
    decision_path.write_text(json.dumps(decision) + "\n", encoding="utf-8")

    with pytest.raises(HITLError, match="decision run"):
        runner.resume(run_dir)
