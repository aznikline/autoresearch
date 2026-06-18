from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from autoresearch.domains.profile import DomainProfile
from autoresearch.skills.loader import load_skills
from autoresearch.skills.matcher import match_skills
from autoresearch.skills.schema import Skill


@dataclass(frozen=True)
class SkillContext:
    stage: str
    profile_id: str
    depth: str
    skills: tuple[Skill, ...]
    rendered: str


class SkillHarness:
    def __init__(self, skills: list[Skill], *, max_per_stage: int = 3) -> None:
        self._skills = skills
        self._max_per_stage = max_per_stage

    @classmethod
    def from_directories(
        cls,
        directories: tuple[Path, ...],
        *,
        max_per_stage: int = 3,
    ) -> "SkillHarness":
        return cls(load_skills(directories), max_per_stage=max_per_stage)

    @classmethod
    def disabled(cls) -> "SkillHarness":
        return cls([])

    def resolve(
        self,
        *,
        stage: str,
        topic: str,
        profile: DomainProfile,
        depth: str,
    ) -> SkillContext:
        context = " ".join((topic, profile.display_name, *profile.focus_areas, *profile.skill_tags))
        matched = match_skills(
            self._skills,
            stage=stage,
            context=context,
            profile_id=profile.profile_id,
            depth=depth,
            top_k=self._max_per_stage,
        )
        rendered = self._render(stage=stage, profile=profile, depth=depth, skills=matched)
        return SkillContext(
            stage=stage,
            profile_id=profile.profile_id,
            depth=depth,
            skills=tuple(matched),
            rendered=rendered,
        )

    def write_stage_context(self, stage_path: Path, context: SkillContext) -> None:
        stage_path.mkdir(parents=True, exist_ok=True)
        (stage_path / "skill_context.md").write_text(context.rendered, encoding="utf-8")
        (stage_path / "skills_applied.json").write_text(
            json.dumps(
                {
                    "stage": context.stage,
                    "profile_id": context.profile_id,
                    "depth": context.depth,
                    "skills": [
                        skill.to_summary(stage=context.stage) for skill in context.skills
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _render(
        *,
        stage: str,
        profile: DomainProfile,
        depth: str,
        skills: list[Skill],
    ) -> str:
        lines = [
            "# Stage Skill Context",
            "",
            f"- Stage: `{stage}`",
            f"- Domain profile: `{profile.profile_id}` ({profile.display_name})",
            f"- Research depth: `{depth}`",
        ]
        guidance = profile.stage_guidance.get(stage)
        if guidance:
            lines.extend(["", "## Domain Guidance", "", guidance])
        if skills:
            lines.extend(["", "## Matched Skills"])
            for skill in skills:
                lines.extend(["", f"### {skill.name}", "", skill.body])
                instruction = skill.stage_instructions.get(stage)
                if instruction:
                    lines.extend(["", "#### Stage Instruction", "", instruction])
                for relative_path in skill.references.get(stage, ()):
                    reference_path = skill.source_dir / relative_path
                    lines.extend(
                        [
                            "",
                            f"#### Reference: `{relative_path}`",
                            "",
                            reference_path.read_text(encoding="utf-8").strip(),
                        ]
                    )
        else:
            lines.extend(["", "## Matched Skills", "", "No project skill matched this stage."])
        return "\n".join(lines).rstrip() + "\n"
