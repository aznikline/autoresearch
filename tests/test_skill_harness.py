from __future__ import annotations

import json
from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig
from autoresearch.domains.profile import load_profile
from autoresearch.pipeline.runner import PipelineRunner
from autoresearch.skills.harness import SkillHarness
from autoresearch.skills.loader import SkillLoadError, load_skill


PROJECT_SKILLS = Path(__file__).resolve().parents[1] / "skills"


def test_project_skill_loads_stage_specific_references() -> None:
    skill = load_skill(PROJECT_SKILLS / "autoresearch-ml-systems")

    assert skill.profiles == ("ml-systems-efficiency",)
    assert skill.priority == 1
    assert skill.references["hypothesis_generation"] == (
        "references/methodology.md",
    )


def test_harness_renders_only_references_for_active_stage() -> None:
    harness = SkillHarness.from_directories((PROJECT_SKILLS,))
    context = harness.resolve(
        stage="hypothesis_generation",
        topic="fixed compute optimizer behavior",
        profile=load_profile("ml-systems-efficiency"),
        depth="top_venue",
    )

    assert [skill.name for skill in context.skills] == ["autoresearch-ml-systems"]
    assert "ML Systems Methodology" in context.rendered
    assert "Submission Readiness Rubric" not in context.rendered
    assert "competing falsifiable hypotheses" in context.rendered


def test_loader_rejects_reference_outside_skill_directory(tmp_path: Path) -> None:
    skill_dir = tmp_path / "unsafe-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: unsafe-skill\ndescription: unsafe test skill\n---\nBody\n",
        encoding="utf-8",
    )
    (skill_dir / "harness.yaml").write_text(
        "references:\n  experiment_design:\n    - ../secret.md\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillLoadError, match="escapes its directory"):
        load_skill(skill_dir)


def test_runner_records_applied_skill_context(config: AutoresearchConfig) -> None:
    result = PipelineRunner(config).run(
        topic="fixed compute optimizer behavior",
        run_id="skill-run",
        auto_approve=True,
    )
    stage_path = Path(result["run_dir"]) / "stage-07-experiment_design"
    applied = json.loads((stage_path / "skills_applied.json").read_text())
    rendered = (stage_path / "skill_context.md").read_text(encoding="utf-8")

    assert applied["profile_id"] == "ml-systems-efficiency"
    assert applied["depth"] == "top_venue"
    assert [skill["name"] for skill in applied["skills"]] == [
        "autoresearch-ml-systems"
    ]
    assert applied["skills"][0]["references"] == [
        "references/methodology.md",
        "references/readiness-rubric.md",
    ]
    assert "Submission Readiness Rubric" in rendered
