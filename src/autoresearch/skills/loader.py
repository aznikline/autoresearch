from __future__ import annotations

from pathlib import Path

import yaml

from autoresearch.skills.schema import Skill


class SkillLoadError(ValueError):
    """Raised when a skill cannot satisfy the harness contract."""


def load_skill(skill_dir: Path) -> Skill:
    skill_path = skill_dir / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise SkillLoadError(f"SKILL.md missing YAML frontmatter: {skill_path}")
    header = yaml.safe_load(parts[1]) or {}
    if not isinstance(header, dict):
        raise SkillLoadError(f"invalid SKILL.md frontmatter: {skill_path}")
    name = str(header.get("name", "")).strip()
    description = str(header.get("description", "")).strip()
    if not name or not description:
        raise SkillLoadError(f"skill requires name and description: {skill_path}")

    harness_path = skill_dir / "harness.yaml"
    harness = yaml.safe_load(harness_path.read_text(encoding="utf-8")) or {}
    if not isinstance(harness, dict):
        raise SkillLoadError(f"harness metadata must be a mapping: {harness_path}")

    stage_instructions = _string_mapping(harness.get("stage_instructions", {}))
    references = _reference_mapping(harness.get("references", {}))
    for stage, paths in references.items():
        for relative_path in paths:
            reference_path = (skill_dir / relative_path).resolve()
            if not reference_path.is_relative_to(skill_dir.resolve()):
                raise SkillLoadError(
                    f"skill reference escapes its directory: {relative_path}"
                )
            if not reference_path.is_file():
                raise SkillLoadError(
                    f"missing skill reference for {stage}: {relative_path}"
                )

    return Skill(
        name=name,
        description=description,
        body=parts[2].strip(),
        category=str(harness.get("category", "domain")),
        trigger_keywords=_tuple(harness.get("trigger_keywords", ())),
        applicable_stages=_tuple(harness.get("applicable_stages", ())),
        profiles=_tuple(harness.get("profiles", ())),
        depths=_tuple(harness.get("depths", ())),
        priority=int(harness.get("priority", 5)),
        stage_instructions=stage_instructions,
        references=references,
        source_dir=skill_dir,
    )


def load_skills(directories: tuple[Path, ...]) -> list[Skill]:
    loaded: dict[str, Skill] = {}
    for root in directories:
        if not root.exists():
            continue
        for skill_path in sorted(root.glob("*/SKILL.md")):
            skill = load_skill(skill_path.parent)
            loaded[skill.name] = skill
    return list(loaded.values())


def _tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    raise SkillLoadError(f"expected string or list, got {type(value).__name__}")


def _string_mapping(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SkillLoadError("expected a mapping of stage names to instructions")
    return {str(key): str(item).strip() for key, item in value.items()}


def _reference_mapping(value: object) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SkillLoadError("expected a mapping of stage names to reference lists")
    return {str(stage): _tuple(paths) for stage, paths in value.items()}
