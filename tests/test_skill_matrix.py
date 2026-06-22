from __future__ import annotations

from pathlib import Path

from autoresearch.domains.profile import load_profiles
from autoresearch.skills.harness import SkillHarness


PROJECT_SKILLS = Path(__file__).resolve().parents[1] / "skills"
EXPECTED_SKILLS = {
    "foundation-models-llm": "autoresearch-foundation-models-llm",
    "computer-vision": "autoresearch-computer-vision",
    "natural-language-processing": "autoresearch-natural-language-processing",
    "data-management-mining": "autoresearch-data-management-mining",
    "ml-systems-efficiency": "autoresearch-ml-systems",
}


def test_every_profile_has_a_deterministic_project_skill() -> None:
    harness = SkillHarness.from_directories((PROJECT_SKILLS,))

    for profile in load_profiles():
        context = harness.resolve(
            stage="experiment_design",
            topic=" ".join(profile.focus_areas),
            profile=profile,
            depth="top_venue",
        )
        assert len(context.skills) == 1
        assert context.skills[0].profiles == (profile.profile_id,)
        assert context.skills[0].name == EXPECTED_SKILLS[profile.profile_id]
        assert context.skills[0].references["experiment_design"]
