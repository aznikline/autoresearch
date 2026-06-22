from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig
from autoresearch.hitl.session import HITLError
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.runner import PipelineRunner


def test_paused_run_can_be_cancelled_with_audited_reason(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    result = runner.run(topic="test idea", run_id="cancelled-run")
    run_dir = Path(result["run_dir"])

    cancelled = runner.cancel(run_dir, actor="operator", reason="budget revoked")

    assert cancelled["status"] == "cancelled"
    checkpoint = read_checkpoint(run_dir)
    assert checkpoint is not None
    assert checkpoint["actor"] == "operator"
    assert checkpoint["reason"] == "budget revoked"
    with pytest.raises(HITLError, match="not recoverable"):
        runner.recover(run_dir)


def test_cancellation_requires_actor_and_reason(config: AutoresearchConfig) -> None:
    result = PipelineRunner(config).run(topic="test idea", run_id="bad-cancel")
    run_dir = Path(result["run_dir"])

    with pytest.raises(HITLError, match="actor and reason"):
        PipelineRunner(config).cancel(run_dir, actor="", reason="")
