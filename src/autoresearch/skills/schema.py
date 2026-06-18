from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    category: str
    trigger_keywords: tuple[str, ...]
    applicable_stages: tuple[str, ...]
    profiles: tuple[str, ...]
    depths: tuple[str, ...]
    priority: int
    stage_instructions: dict[str, str]
    references: dict[str, tuple[str, ...]]
    source_dir: Path

    def to_summary(self, *, stage: str | None = None) -> dict[str, object]:
        reference_files = self.references.get(stage, ()) if stage else ()
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "applicable_stages": list(self.applicable_stages),
            "profiles": list(self.profiles),
            "depths": list(self.depths),
            "priority": self.priority,
            "stage_instruction": self.stage_instructions.get(stage, "") if stage else "",
            "references": list(reference_files),
            "source_dir": self.source_dir.as_posix(),
        }
