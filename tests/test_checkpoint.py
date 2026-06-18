from __future__ import annotations

from pathlib import Path

from autoresearch.pipeline.checkpoint import read_checkpoint, write_checkpoint
from autoresearch.pipeline.stages import Stage, StageStatus


def test_write_and_read_checkpoint(tmp_path: Path) -> None:
    checkpoint = write_checkpoint(
        tmp_path,
        run_id="run-1",
        stage=Stage.EXPERIMENT_DESIGN,
        status=StageStatus.PAUSED,
        message="approval required",
    )

    assert checkpoint["stage_slug"] == "experiment_design"
    assert read_checkpoint(tmp_path) == checkpoint


def test_corrupt_checkpoint_returns_failure_payload(tmp_path: Path) -> None:
    (tmp_path / "checkpoint.json").write_text("{", encoding="utf-8")

    checkpoint = read_checkpoint(tmp_path)

    assert checkpoint is not None
    assert checkpoint["status"] == "failed"
