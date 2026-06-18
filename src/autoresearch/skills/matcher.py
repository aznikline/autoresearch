from __future__ import annotations

import re

from autoresearch.skills.schema import Skill


def match_skills(
    skills: list[Skill],
    *,
    stage: str,
    context: str,
    profile_id: str,
    depth: str,
    top_k: int,
) -> list[Skill]:
    context_tokens = _tokens(context)
    scored: list[tuple[float, Skill]] = []
    for skill in skills:
        if skill.applicable_stages and stage not in skill.applicable_stages:
            continue
        if skill.profiles and profile_id not in skill.profiles:
            continue
        if skill.depths and depth not in skill.depths:
            continue

        score = 0.0
        if profile_id in skill.profiles:
            score += 2.0
        if depth in skill.depths:
            score += 1.0
        for keyword in skill.trigger_keywords:
            if _tokens(keyword) & context_tokens:
                score += 0.5
        score += max(0.0, (10 - skill.priority) / 20.0)
        if score > 0:
            scored.append((score, skill))

    scored.sort(key=lambda item: (-item[0], item[1].priority, item[1].name))
    return [skill for _, skill in scored[:top_k]]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", text.lower()))
