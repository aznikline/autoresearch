from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.adapters.llm.base import LLMError, LLMProvider
from autoresearch.domains.profile import DomainProfile
from autoresearch.pipeline.artifacts import artifact_exists, stage_dir
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.stage_impls.core import execute_placeholder_stage
from autoresearch.pipeline.stages import Stage, StageStatus
from autoresearch.skills.harness import SkillHarness
from autoresearch.strategy.models import VenueStrategy
from autoresearch.venues.schema import VenueContract


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
    llm_provider: LLMProvider | None = None,
    venue_guidance: str = "",
    venue_contract: VenueContract | None = None,
    venue_strategy: VenueStrategy | None = None,
    prior_lessons: str = "",
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
    try:
        execute_placeholder_stage(
            stage,
            stage_path=stage_path,
            run_dir=run_dir,
            config=config,
            topic=topic,
            llm_provider=llm_provider,
            prompt_context=skill_context.rendered,
            venue_guidance=venue_guidance,
            venue_contract=venue_contract,
            venue_strategy=venue_strategy,
            prior_lessons=prior_lessons,
        )
    except (LLMError, ValueError) as exc:
        return StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            artifacts=(),
            message=str(exc),
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
