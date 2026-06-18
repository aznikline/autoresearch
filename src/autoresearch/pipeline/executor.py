from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.domains.profile import DomainProfile
from autoresearch.pipeline.artifacts import artifact_exists, stage_dir
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.stage_impls.core import execute_placeholder_stage
from autoresearch.pipeline.stages import Stage, StageStatus
from autoresearch.skills.harness import SkillHarness


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    status: StageStatus
    artifacts: tuple[str, ...]
    message: str = ""


def execute_stage(
    stage: Stage,
    *,
    run_dir: Path,
    config: AutoresearchConfig,
    topic: str,
    profile: DomainProfile,
    skill_harness: SkillHarness,
) -> StageResult:
    stage_path = stage_dir(run_dir, stage)
    stage_path.mkdir(parents=True, exist_ok=True)
    skill_context = skill_harness.resolve(
        stage=stage.slug,
        topic=topic,
        profile=profile,
        depth=config.research.depth,
    )
    skill_harness.write_stage_context(stage_path, skill_context)
    execute_placeholder_stage(
        stage,
        stage_path=stage_path,
        run_dir=run_dir,
        config=config,
        topic=topic,
    )

    contract = contract_for(stage)
    missing = [
        output
        for output in contract.output_files
        if not artifact_exists(run_dir, stage, output)
    ]
    if missing:
        return StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            artifacts=tuple(contract.output_files),
            message=f"missing required outputs: {', '.join(missing)}",
        )
    return StageResult(
        stage=stage,
        status=StageStatus.DONE,
        artifacts=tuple(contract.output_files),
        message=contract.definition_of_done,
    )
