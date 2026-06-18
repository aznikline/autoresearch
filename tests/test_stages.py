from __future__ import annotations

from autoresearch.pipeline.stages import (
    GATE_STAGES,
    STAGE_SEQUENCE,
    Stage,
    next_stage,
    stage_from_slug,
)


def test_stage_sequence_is_ordered() -> None:
    assert STAGE_SEQUENCE[0] is Stage.IDEA_INTAKE
    assert STAGE_SEQUENCE[-1] is Stage.FINAL_VERIFICATION_EXPORT
    assert next_stage(Stage.IDEA_INTAKE) is Stage.PROBLEM_DECOMPOSE
    assert next_stage(Stage.FINAL_VERIFICATION_EXPORT) is None


def test_stage_slug_lookup_accepts_hyphens() -> None:
    assert stage_from_slug("experiment-design") is Stage.EXPERIMENT_DESIGN


def test_gate_stages_cover_high_leverage_reviews() -> None:
    assert Stage.LITERATURE_SCREEN in GATE_STAGES
    assert Stage.EXPERIMENT_DESIGN in GATE_STAGES
    assert Stage.RESULT_ANALYSIS_DECISION in GATE_STAGES
    assert Stage.FINAL_VERIFICATION_EXPORT in GATE_STAGES
