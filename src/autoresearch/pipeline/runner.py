from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch.config import AutoresearchConfig
from autoresearch.domains.profile import load_profile
from autoresearch.pipeline.checkpoint import write_checkpoint
from autoresearch.pipeline.executor import StageResult, execute_stage
from autoresearch.pipeline.stages import GATE_STAGES, STAGE_SEQUENCE, StageStatus
from autoresearch.skills.harness import SkillHarness


class PipelineRunner:
    def __init__(self, config: AutoresearchConfig) -> None:
        self.config = config
        self.profile = load_profile(config.research.profile)
        self.skill_harness = (
            SkillHarness.from_directories(
                tuple(Path(path).expanduser() for path in config.skills.directories),
                max_per_stage=config.skills.max_per_stage,
            )
            if config.skills.enabled
            else SkillHarness.disabled()
        )

    def run(
        self,
        *,
        topic: str,
        run_id: str | None = None,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        resolved_topic = topic.strip()
        if not resolved_topic:
            return {
                "status": StageStatus.FAILED.value,
                "message": "research topic is required",
            }

        active_run_id = run_id or _new_run_id()
        run_dir = Path(self.config.runtime.artifacts_root) / active_run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        results: list[StageResult] = []
        for stage in STAGE_SEQUENCE:
            if stage in GATE_STAGES and not auto_approve:
                checkpoint = write_checkpoint(
                    run_dir,
                    run_id=active_run_id,
                    stage=stage,
                    status=StageStatus.PAUSED,
                    message=f"approval required before {stage.slug}",
                )
                return {
                    "run_id": active_run_id,
                    "run_dir": str(run_dir),
                    "status": StageStatus.PAUSED.value,
                    "checkpoint": checkpoint,
                    "stages_completed": len(results),
                }

            write_checkpoint(
                run_dir,
                run_id=active_run_id,
                stage=stage,
                status=StageStatus.RUNNING,
                message=f"running {stage.slug}",
            )
            result = execute_stage(
                stage,
                run_dir=run_dir,
                config=self.config,
                topic=resolved_topic,
                profile=self.profile,
                skill_harness=self.skill_harness,
            )
            results.append(result)
            write_checkpoint(
                run_dir,
                run_id=active_run_id,
                stage=stage,
                status=result.status,
                message=result.message,
            )
            if result.status is StageStatus.FAILED:
                return {
                    "run_id": active_run_id,
                    "run_dir": str(run_dir),
                    "status": StageStatus.FAILED.value,
                    "failed_stage": stage.slug,
                    "message": result.message,
                    "stages_completed": len(
                        [item for item in results if item.status is StageStatus.DONE]
                    ),
                }

        return {
            "run_id": active_run_id,
            "run_dir": str(run_dir),
            "status": StageStatus.DONE.value,
            "stages_completed": len(results),
        }


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
