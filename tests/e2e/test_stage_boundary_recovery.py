from __future__ import annotations

import hashlib
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.pipeline.checkpoint import write_checkpoint
from autoresearch.pipeline.runner import PipelineRunner
from autoresearch.pipeline.stages import STAGE_SEQUENCE, StageStatus


EVIDENCE_PATHS = (
    "stage-09-experiment_loop/ledger.jsonl",
    "stage-12-final_verification_export/paper.tex",
    "stage-12-final_verification_export/references.bib",
    "stage-12-final_verification_export/evidence_graph.json",
)


def test_every_stage_boundary_recovers_to_identical_scientific_evidence(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    result = runner.run(
        topic="test idea",
        run_id="all-boundaries",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])
    baseline = _hashes(run_dir)

    for stage in reversed(STAGE_SEQUENCE):
        write_checkpoint(
            run_dir,
            run_id="all-boundaries",
            stage=stage,
            status=StageStatus.RUNNING,
            message="simulated process interruption",
        )
        recovered = runner.recover(run_dir, auto_approve=True)
        assert recovered["status"] == "done", stage.slug
        assert _hashes(run_dir) == baseline, stage.slug


def _hashes(run_dir: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256((run_dir / relative).read_bytes()).hexdigest()
        for relative in EVIDENCE_PATHS
    }
