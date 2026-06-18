from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class ProjectConfig:
    name: str


@dataclass(frozen=True)
class ResearchConfig:
    topic: str = ""
    quality_threshold: float = 4.0
    profile: str = "ml-systems-efficiency"
    depth: str = "top_venue"
    target_venues: tuple[str, ...] = ("NeurIPS", "ICML", "ICLR", "MLSys")


@dataclass(frozen=True)
class RuntimeConfig:
    artifacts_root: str = "artifacts"
    max_iterations: int = 3


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    primary_model: str = "gpt-4.1"


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = "local"
    time_budget_sec: int = 300
    metric_key: str = "primary_metric"
    metric_direction: str = "minimize"


@dataclass(frozen=True)
class HITLConfig:
    mode: str = "gate-only"
    required_stages: tuple[str, ...] = field(
        default_factory=lambda: (
            "literature_screen",
            "experiment_design",
            "result_analysis_decision",
            "final_verification_export",
        )
    )


@dataclass(frozen=True)
class SkillsConfig:
    enabled: bool = True
    directories: tuple[str, ...] = ("skills",)
    max_per_stage: int = 3


@dataclass(frozen=True)
class AutoresearchConfig:
    project: ProjectConfig
    research: ResearchConfig = field(default_factory=ResearchConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    hitl: HITLConfig = field(default_factory=HITLConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AutoresearchConfig":
        if not isinstance(data, dict):
            raise ConfigError("config must be a mapping")
        project_data = _section(data, "project", required=True)
        project_name = str(project_data.get("name", "")).strip()
        if not project_name:
            raise ConfigError("project.name is required")

        experiment_data = _section(data, "experiment")
        metric_direction = str(
            experiment_data.get("metric_direction", "minimize")
        ).strip()
        if metric_direction not in {"minimize", "maximize"}:
            raise ConfigError("experiment.metric_direction must be minimize or maximize")
        mode = str(experiment_data.get("mode", "local")).strip()
        if mode not in {"local", "docker", "ssh"}:
            raise ConfigError("experiment.mode must be local, docker, or ssh")

        hitl_data = _section(data, "hitl")
        required_stages = tuple(str(s) for s in hitl_data.get("required_stages", ()))
        research_data = _section(data, "research")
        target_venues = tuple(str(v) for v in research_data.get("target_venues", ()))
        depth = str(research_data.get("depth", "top_venue")).strip()
        if depth not in {"exploratory", "publication", "top_venue"}:
            raise ConfigError("research.depth must be exploratory, publication, or top_venue")
        skills_data = _section(data, "skills")
        skill_directories = tuple(str(d) for d in skills_data.get("directories", ()))

        return cls(
            project=ProjectConfig(name=project_name),
            research=ResearchConfig(
                **{
                    **_filtered(research_data, ResearchConfig),
                    "depth": depth,
                    "target_venues": target_venues or ResearchConfig().target_venues,
                }
            ),
            runtime=RuntimeConfig(**_filtered(_section(data, "runtime"), RuntimeConfig)),
            llm=LLMConfig(**_filtered(_section(data, "llm"), LLMConfig)),
            experiment=ExperimentConfig(
                **{
                    **_filtered(experiment_data, ExperimentConfig),
                    "mode": mode,
                    "metric_direction": metric_direction,
                }
            ),
            hitl=HITLConfig(
                **{
                    **_filtered(hitl_data, HITLConfig),
                    "required_stages": required_stages or HITLConfig().required_stages,
                }
            ),
            skills=SkillsConfig(
                **{
                    **_filtered(skills_data, SkillsConfig),
                    "directories": skill_directories or SkillsConfig().directories,
                }
            ),
        )

    def redacted_dict(self) -> dict[str, Any]:
        return {
            "project": {"name": self.project.name},
            "research": {
                "topic": self.research.topic,
                "quality_threshold": self.research.quality_threshold,
                "profile": self.research.profile,
                "depth": self.research.depth,
                "target_venues": list(self.research.target_venues),
            },
            "runtime": {
                "artifacts_root": self.runtime.artifacts_root,
                "max_iterations": self.runtime.max_iterations,
            },
            "llm": {
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "api_key_env": self.llm.api_key_env,
                "primary_model": self.llm.primary_model,
            },
            "experiment": {
                "mode": self.experiment.mode,
                "time_budget_sec": self.experiment.time_budget_sec,
                "metric_key": self.experiment.metric_key,
                "metric_direction": self.experiment.metric_direction,
            },
            "hitl": {
                "mode": self.hitl.mode,
                "required_stages": list(self.hitl.required_stages),
            },
            "skills": {
                "enabled": self.skills.enabled,
                "directories": list(self.skills.directories),
                "max_per_stage": self.skills.max_per_stage,
            },
        }


def load_config(path: str | Path) -> AutoresearchConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"config file is not valid YAML: {config_path}") from exc
    return AutoresearchConfig.from_mapping(raw)


def write_example_config(path: str | Path) -> Path:
    target = Path(path)
    source = Path(__file__).resolve().parents[2] / "config" / "autoresearch.example.yaml"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _section(data: dict[str, Any], key: str, *, required: bool = False) -> dict[str, Any]:
    value = data.get(key, {})
    if required and not isinstance(value, dict):
        raise ConfigError(f"{key} section is required")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value


def _filtered(data: dict[str, Any], config_type: type) -> dict[str, Any]:
    allowed = set(config_type.__dataclass_fields__)
    return {key: value for key, value in data.items() if key in allowed}
