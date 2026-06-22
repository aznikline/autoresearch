from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib

import pytest

from autoresearch.config import AutoresearchConfig
from autoresearch.experiments.ledger import read_ledger
from autoresearch.hitl.session import HITLError
from autoresearch.pipeline.checkpoint import write_checkpoint
from autoresearch.pipeline.runner import PipelineRunner
from autoresearch.pipeline.stages import Stage, StageStatus


def test_recover_interrupted_stage_is_idempotent(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    completed = runner.run(topic="test idea", run_id="recover-run", auto_approve=True)
    run_dir = Path(completed["run_dir"])
    ledger_path = run_dir / "stage-09-experiment_loop" / "ledger.jsonl"
    assert len(read_ledger(ledger_path)) == 3
    before = {
        entry.trial_id: (
            entry.experiment_spec_sha256,
            entry.code_sha256,
            entry.config_sha256,
            hashlib.sha256(
                (ledger_path.parent / entry.metrics_path).read_bytes()
            ).hexdigest(),
        )
        for entry in read_ledger(ledger_path)
    }
    write_checkpoint(
        run_dir,
        run_id="recover-run",
        stage=Stage.EXPERIMENT_LOOP,
        status=StageStatus.RUNNING,
        message="simulated interruption",
    )

    recovered = runner.recover(run_dir, auto_approve=True)

    assert recovered["status"] == "done"
    assert len(read_ledger(ledger_path)) == 3
    after = {
        entry.trial_id: (
            entry.experiment_spec_sha256,
            entry.code_sha256,
            entry.config_sha256,
            hashlib.sha256(
                (ledger_path.parent / entry.metrics_path).read_bytes()
            ).hexdigest(),
        )
        for entry in read_ledger(ledger_path)
    }
    assert after == before
    events = (run_dir / "checkpoint_events.jsonl").read_text().splitlines()
    assert len(events) > 1


def test_recover_rejects_completed_run(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    completed = runner.run(topic="test idea", run_id="done-recovery", auto_approve=True)

    with pytest.raises(HITLError, match="not recoverable"):
        runner.recover(Path(completed["run_dir"]))


def test_recover_rejects_changed_config(config: AutoresearchConfig) -> None:
    runner = PipelineRunner(config)
    completed = runner.run(topic="test idea", run_id="changed-recovery", auto_approve=True)
    run_dir = Path(completed["run_dir"])
    write_checkpoint(
        run_dir,
        run_id="changed-recovery",
        stage=Stage.SYNTHESIS,
        status=StageStatus.FAILED,
    )
    changed = replace(config, runtime=replace(config.runtime, max_iterations=99))

    with pytest.raises(HITLError, match="config does not match"):
        PipelineRunner(changed).recover(run_dir)


def test_recover_corrupt_checkpoint_is_actionable(config: AutoresearchConfig) -> None:
    result = PipelineRunner(config).run(topic="test idea", run_id="corrupt-recovery")
    run_dir = Path(result["run_dir"])
    (run_dir / "checkpoint.json").write_text("{", encoding="utf-8")

    with pytest.raises(HITLError, match="invalid stage or run ID"):
        PipelineRunner(config).recover(run_dir)
