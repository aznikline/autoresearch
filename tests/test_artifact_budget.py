from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.runner import PipelineRunner


def test_artifact_budget_overrun_pauses_before_next_stage(
    config: AutoresearchConfig,
) -> None:
    constrained = replace(
        config,
        runtime=replace(config.runtime, max_artifact_bytes=1),
    )

    result = PipelineRunner(constrained).run(
        topic="test idea",
        run_id="artifact-budget",
        auto_approve=True,
    )

    assert result["status"] == "paused"
    assert result["checkpoint"]["pause_kind"] == "artifact_budget"
    assert result["checkpoint"]["allowed_actions"] == ["cancel"]
    assert result["stages_completed"] == 1
    checkpoint = read_checkpoint(Path(result["run_dir"]))
    assert checkpoint == result["checkpoint"]
