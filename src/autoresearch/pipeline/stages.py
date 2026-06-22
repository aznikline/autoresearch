from __future__ import annotations

from enum import Enum, IntEnum


class Stage(IntEnum):
    IDEA_INTAKE = 1
    PROBLEM_DECOMPOSE = 2
    LITERATURE_COLLECT = 3
    LITERATURE_SCREEN = 4
    SYNTHESIS = 5
    HYPOTHESIS_GENERATION = 6
    EXPERIMENT_DESIGN = 7
    EXPERIMENT_GENERATION = 8
    EXPERIMENT_LOOP = 9
    RESULT_ANALYSIS_DECISION = 10
    PAPER_DRAFT_REVISION = 11
    FINAL_VERIFICATION_EXPORT = 12

    @property
    def slug(self) -> str:
        return self.name.lower()


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"


STAGE_SEQUENCE: tuple[Stage, ...] = tuple(Stage)

GATE_STAGES: frozenset[Stage] = frozenset(
    {
        Stage.LITERATURE_SCREEN,
        Stage.EXPERIMENT_DESIGN,
        Stage.RESULT_ANALYSIS_DECISION,
        Stage.FINAL_VERIFICATION_EXPORT,
    }
)

ROLLBACK_STAGE: dict[Stage, Stage] = {
    Stage.LITERATURE_SCREEN: Stage.LITERATURE_COLLECT,
    Stage.EXPERIMENT_DESIGN: Stage.HYPOTHESIS_GENERATION,
    Stage.RESULT_ANALYSIS_DECISION: Stage.EXPERIMENT_LOOP,
    Stage.FINAL_VERIFICATION_EXPORT: Stage.PAPER_DRAFT_REVISION,
}


def next_stage(stage: Stage) -> Stage | None:
    index = STAGE_SEQUENCE.index(stage)
    if index + 1 >= len(STAGE_SEQUENCE):
        return None
    return STAGE_SEQUENCE[index + 1]


def stage_from_slug(slug: str) -> Stage:
    normalized = slug.lower().strip().replace("-", "_")
    for stage in Stage:
        if stage.slug == normalized:
            return stage
    raise ValueError(f"unknown stage: {slug}")
