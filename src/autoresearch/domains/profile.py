from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ProfileError(ValueError):
    """Raised when a domain profile is missing or malformed."""


@dataclass(frozen=True)
class DepthRequirements:
    min_screened_papers: int
    min_baselines: int
    min_evaluation_units: int
    min_seeds: int
    min_ablations: int
    min_verified_metrics: int
    require_confidence_intervals: bool
    require_effect_sizes: bool
    require_compute_reporting: bool
    require_hypothesis_outcomes: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DepthRequirements":
        required = {
            "min_screened_papers",
            "min_baselines",
            "min_evaluation_units",
            "min_seeds",
            "min_ablations",
            "min_verified_metrics",
        }
        missing = sorted(required - data.keys())
        if missing:
            raise ProfileError(f"depth requirements missing: {', '.join(missing)}")
        return cls(
            min_screened_papers=int(data["min_screened_papers"]),
            min_baselines=int(data["min_baselines"]),
            min_evaluation_units=int(data["min_evaluation_units"]),
            min_seeds=int(data["min_seeds"]),
            min_ablations=int(data["min_ablations"]),
            min_verified_metrics=int(data["min_verified_metrics"]),
            require_confidence_intervals=bool(data.get("require_confidence_intervals", True)),
            require_effect_sizes=bool(data.get("require_effect_sizes", True)),
            require_compute_reporting=bool(data.get("require_compute_reporting", True)),
            require_hypothesis_outcomes=bool(data.get("require_hypothesis_outcomes", True)),
        )


@dataclass(frozen=True)
class DomainProfile:
    profile_id: str
    display_name: str
    parent_domain: str
    target_venues: tuple[str, ...]
    experiment_paradigm: str
    focus_areas: tuple[str, ...]
    biases: tuple[str, ...]
    anti_patterns: tuple[str, ...]
    standard_baselines: tuple[str, ...]
    metric_types: tuple[str, ...]
    statistical_tests: tuple[str, ...]
    detector_keywords: tuple[str, ...]
    skill_tags: tuple[str, ...]
    depth_requirements: dict[str, DepthRequirements]
    stage_guidance: dict[str, str]

    def requirements_for(self, depth: str) -> DepthRequirements:
        try:
            return self.depth_requirements[depth]
        except KeyError as exc:
            choices = ", ".join(sorted(self.depth_requirements))
            raise ProfileError(
                f"unknown depth '{depth}' for {self.profile_id}; choose: {choices}"
            ) from exc


def load_profile(profile_id: str, profiles_dir: Path | None = None) -> DomainProfile:
    root = profiles_dir or Path(__file__).resolve().parents[1] / "profiles"
    path = root / f"{profile_id}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ProfileError(f"domain profile not found: {profile_id}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"domain profile must be a mapping: {path}")
    depths = data.get("depth_requirements", {})
    if not isinstance(depths, dict) or not depths:
        raise ProfileError(f"domain profile has no depth_requirements: {path}")
    return DomainProfile(
        profile_id=str(data.get("profile_id") or profile_id),
        display_name=str(data.get("display_name") or profile_id),
        parent_domain=str(data.get("parent_domain") or ""),
        target_venues=tuple(str(item) for item in data.get("target_venues", ())),
        experiment_paradigm=str(data.get("experiment_paradigm") or "comparison"),
        focus_areas=tuple(str(item) for item in data.get("focus_areas", ())),
        biases=tuple(str(item) for item in data.get("biases", ())),
        anti_patterns=tuple(str(item) for item in data.get("anti_patterns", ())),
        standard_baselines=tuple(str(item) for item in data.get("standard_baselines", ())),
        metric_types=tuple(str(item) for item in data.get("metric_types", ())),
        statistical_tests=tuple(str(item) for item in data.get("statistical_tests", ())),
        detector_keywords=tuple(str(item) for item in data.get("detector_keywords", ())),
        skill_tags=tuple(str(item) for item in data.get("skill_tags", ())),
        depth_requirements={
            str(name): DepthRequirements.from_mapping(dict(requirements))
            for name, requirements in depths.items()
        },
        stage_guidance={
            str(stage): str(guidance)
            for stage, guidance in dict(data.get("stage_guidance", {})).items()
        },
    )
