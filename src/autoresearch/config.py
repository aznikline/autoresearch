from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class ProjectConfig:
    name: str


UNWAIVABLE_REQUIREMENTS = frozenset(
    {
        "citation_integrity",
        "immutable_evaluation",
        "protocol_parity",
        "artifact_provenance",
    }
)
WAIVABLE_THRESHOLD_REQUIREMENTS = frozenset(
    {
        "screened_papers",
        "baselines",
        "evaluation_units",
        "seeds",
        "ablations",
        "verified_metrics",
        "confidence_intervals",
        "effect_sizes",
        "compute_reporting",
        "hypothesis_outcomes",
    }
)


@dataclass(frozen=True)
class ThresholdWaiver:
    requirement: str
    affected_claim: str
    reason: str
    alternative_test: str


@dataclass(frozen=True)
class ResearchConfig:
    topic: str = ""
    quality_threshold: float = 4.0
    profile: str = "ml-systems-efficiency"
    depth: str = "top_venue"
    target_venues: tuple[str, ...] = ("NeurIPS", "ICML", "ICLR", "MLSys")
    primary_claim_type: str = "empirical efficiency"
    threshold_waivers: tuple[ThresholdWaiver, ...] = ()
    venue_id: str = "mlsys"
    venue_year: int | str = "latest_available"
    venue_track: str = "main"


@dataclass(frozen=True)
class RuntimeConfig:
    artifacts_root: str = "artifacts"
    max_iterations: int = 3
    max_artifact_bytes: int = 1_000_000_000


@dataclass(frozen=True)
class LLMConfig:
    mode: str = "synthetic"
    provider: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    allowed_hosts: tuple[str, ...] = ("api.openai.com",)
    auth_mode: str = "bearer_env"
    api_key_env: str = "OPENAI_API_KEY"
    primary_model: str = "gpt-4.1"
    max_requests: int = 20
    max_retries: int = 2
    timeout_sec: float = 60.0
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0


@dataclass(frozen=True)
class LiteratureConfig:
    mode: str = "synthetic"
    sources: tuple[str, ...] = ("seed",)
    per_source_limit: int = 10
    max_retries: int = 2
    timeout_sec: float = 30.0
    queries: tuple[str, ...] = ()
    saturation_patience: int = 2
    saturation_max_new_ratio: float = 0.0
    arxiv_base_url: str = "https://export.arxiv.org"
    openalex_base_url: str = "https://api.openalex.org"
    crossref_base_url: str = "https://api.crossref.org"


@dataclass(frozen=True)
class GovernanceConfig:
    assets_file: str = ""


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = "local"
    evidence_mode: str = "synthetic"
    workspace_source: str = ""
    allowed_imports: tuple[str, ...] = ()
    code_trust: str = "trusted_generated"
    time_budget_sec: int = 300
    metric_key: str = "primary_metric"
    metric_direction: str = "minimize"
    total_compute_budget: str = "local CPU within the per-trial time budget"
    protocol: dict[str, Any] = field(default_factory=dict)


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
    literature: LiteratureConfig = field(default_factory=LiteratureConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
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
        evidence_mode = str(
            experiment_data.get("evidence_mode", ExperimentConfig().evidence_mode)
        ).strip()
        if evidence_mode not in {"synthetic", "real"}:
            raise ConfigError("experiment.evidence_mode must be synthetic or real")
        workspace_source = str(experiment_data.get("workspace_source", "")).strip()
        imports_raw = experiment_data.get("allowed_imports", ())
        if not isinstance(imports_raw, list | tuple) or any(
            not isinstance(item, str) or not item.strip().isidentifier()
            for item in imports_raw
        ):
            raise ConfigError("experiment.allowed_imports must be a list of module names")
        allowed_imports = tuple(item.strip() for item in imports_raw)
        if len(allowed_imports) != len(set(allowed_imports)):
            raise ConfigError("experiment.allowed_imports contains duplicates")
        code_trust = str(
            experiment_data.get("code_trust", ExperimentConfig().code_trust)
        ).strip()
        if code_trust not in {"trusted_generated", "untrusted"}:
            raise ConfigError(
                "experiment.code_trust must be trusted_generated or untrusted"
            )
        protocol_raw = experiment_data.get("protocol", {})
        if not isinstance(protocol_raw, dict):
            raise ConfigError("experiment.protocol must be a mapping")
        protocol = {str(key): value for key, value in protocol_raw.items()}
        reserved_protocol_fields = {
            "topic",
            "trials",
            "metric_key",
            "metric_direction",
            "time_budget_sec",
        }
        forbidden = sorted(set(protocol) & reserved_protocol_fields)
        if forbidden:
            raise ConfigError(
                "experiment.protocol cannot override execution fields: "
                + ", ".join(forbidden)
            )

        hitl_data = _section(data, "hitl")
        required_stages = tuple(str(s) for s in hitl_data.get("required_stages", ()))
        research_data = _section(data, "research")
        target_venues = tuple(str(v) for v in research_data.get("target_venues", ()))
        threshold_waivers = _parse_threshold_waivers(
            research_data.get("threshold_waivers", ())
        )
        depth = str(research_data.get("depth", "top_venue")).strip()
        if depth not in {"exploratory", "publication", "top_venue"}:
            raise ConfigError("research.depth must be exploratory, publication, or top_venue")
        primary_claim_type = str(
            research_data.get("primary_claim_type", ResearchConfig().primary_claim_type)
        ).strip()
        if not primary_claim_type:
            raise ConfigError("research.primary_claim_type is required")
        venue_id = str(research_data.get("venue_id", ResearchConfig().venue_id)).strip()
        venue_track = str(
            research_data.get("venue_track", ResearchConfig().venue_track)
        ).strip()
        venue_year_raw = research_data.get("venue_year", ResearchConfig().venue_year)
        if isinstance(venue_year_raw, bool) or not isinstance(venue_year_raw, int | str):
            raise ConfigError(
                "research.venue_year must be an integer, latest_available, or latest_verified"
            )
        venue_year: int | str
        if isinstance(venue_year_raw, int):
            venue_year = venue_year_raw
        else:
            venue_year = venue_year_raw.strip()
            if venue_year not in {"latest_available", "latest_verified"}:
                raise ConfigError(
                    "research.venue_year must be an integer, latest_available, or latest_verified"
                )
        if not venue_id or not venue_track:
            raise ConfigError("research.venue_id and research.venue_track are required")
        skills_data = _section(data, "skills")
        skill_directories = tuple(str(d) for d in skills_data.get("directories", ()))
        llm_data = _section(data, "llm")
        llm_mode = str(llm_data.get("mode", LLMConfig().mode)).strip()
        if llm_mode not in {"synthetic", "live"}:
            raise ConfigError("llm.mode must be synthetic or live")
        auth_mode = str(llm_data.get("auth_mode", LLMConfig().auth_mode)).strip()
        if auth_mode not in {"bearer_env", "none"}:
            raise ConfigError("llm.auth_mode must be bearer_env or none")
        max_requests = int(llm_data.get("max_requests", LLMConfig().max_requests))
        if max_requests <= 0:
            raise ConfigError("llm.max_requests must be positive")
        allowed_hosts_raw = llm_data.get("allowed_hosts", LLMConfig().allowed_hosts)
        if not isinstance(allowed_hosts_raw, (list, tuple)):
            raise ConfigError("llm.allowed_hosts must be a non-empty list")
        allowed_hosts = tuple(
            str(host).strip().lower() for host in allowed_hosts_raw
        )
        if not allowed_hosts or any(not host for host in allowed_hosts):
            raise ConfigError("llm.allowed_hosts must be a non-empty list")
        llm_base_url = str(llm_data.get("base_url", LLMConfig().base_url)).strip()
        llm_host = (urlparse(llm_base_url).hostname or "").lower()
        if auth_mode == "none" and llm_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ConfigError("llm.auth_mode none is allowed only for loopback providers")
        literature_data = _section(data, "literature")
        governance_data = _section(data, "governance")
        assets_file = str(
            governance_data.get("assets_file", GovernanceConfig().assets_file)
        ).strip()
        literature_mode = str(
            literature_data.get("mode", LiteratureConfig().mode)
        ).strip()
        if literature_mode not in {"synthetic", "live"}:
            raise ConfigError("literature.mode must be synthetic or live")
        default_sources = LiteratureConfig().sources
        sources = tuple(str(source).strip() for source in literature_data.get("sources", default_sources))
        allowed_sources = {"seed"} if literature_mode == "synthetic" else {
            "arxiv",
            "openalex",
            "crossref",
        }
        if not sources or any(source not in allowed_sources for source in sources):
            raise ConfigError(
                f"literature.sources must be non-empty and valid for {literature_mode} mode"
            )
        per_source_limit = int(
            literature_data.get("per_source_limit", LiteratureConfig().per_source_limit)
        )
        max_retries = int(
            literature_data.get("max_retries", LiteratureConfig().max_retries)
        )
        timeout_sec = float(
            literature_data.get("timeout_sec", LiteratureConfig().timeout_sec)
        )
        if per_source_limit <= 0:
            raise ConfigError("literature.per_source_limit must be positive")
        if max_retries < 0:
            raise ConfigError("literature.max_retries cannot be negative")
        if timeout_sec <= 0:
            raise ConfigError("literature.timeout_sec must be positive")
        queries_raw = literature_data.get("queries", LiteratureConfig().queries)
        if not isinstance(queries_raw, (list, tuple)):
            raise ConfigError("literature.queries must be a list")
        queries = tuple(" ".join(str(query).split()) for query in queries_raw)
        if any(not query for query in queries):
            raise ConfigError("literature.queries must not contain empty queries")
        normalized_queries = tuple(query.lower() for query in queries)
        if len(normalized_queries) != len(set(normalized_queries)):
            raise ConfigError("literature.queries contains duplicate normalized queries")
        saturation_patience = int(
            literature_data.get(
                "saturation_patience", LiteratureConfig().saturation_patience
            )
        )
        if saturation_patience <= 0:
            raise ConfigError("literature.saturation_patience must be positive")
        saturation_max_new_ratio = float(
            literature_data.get(
                "saturation_max_new_ratio",
                LiteratureConfig().saturation_max_new_ratio,
            )
        )
        if not 0.0 <= saturation_max_new_ratio <= 1.0:
            raise ConfigError(
                "literature.saturation_max_new_ratio must be between 0 and 1"
            )
        runtime_data = _section(data, "runtime")
        max_artifact_bytes = int(
            runtime_data.get(
                "max_artifact_bytes", RuntimeConfig().max_artifact_bytes
            )
        )
        if max_artifact_bytes <= 0:
            raise ConfigError("runtime.max_artifact_bytes must be positive")

        return cls(
            project=ProjectConfig(name=project_name),
            research=ResearchConfig(
                **{
                    **_filtered(research_data, ResearchConfig),
                    "depth": depth,
                    "target_venues": target_venues or ResearchConfig().target_venues,
                    "primary_claim_type": primary_claim_type,
                    "threshold_waivers": threshold_waivers,
                    "venue_id": venue_id,
                    "venue_year": venue_year,
                    "venue_track": venue_track,
                }
            ),
            runtime=RuntimeConfig(
                **{
                    **_filtered(runtime_data, RuntimeConfig),
                    "max_artifact_bytes": max_artifact_bytes,
                }
            ),
            llm=LLMConfig(
                **{
                    **_filtered(llm_data, LLMConfig),
                    "mode": llm_mode,
                    "auth_mode": auth_mode,
                    "max_requests": max_requests,
                    "allowed_hosts": allowed_hosts,
                }
            ),
            literature=LiteratureConfig(
                **{
                    **_filtered(literature_data, LiteratureConfig),
                    "mode": literature_mode,
                    "sources": sources,
                    "per_source_limit": per_source_limit,
                    "max_retries": max_retries,
                    "timeout_sec": timeout_sec,
                    "queries": queries,
                    "saturation_patience": saturation_patience,
                    "saturation_max_new_ratio": saturation_max_new_ratio,
                }
            ),
            governance=GovernanceConfig(assets_file=assets_file),
            experiment=ExperimentConfig(
                **{
                    **_filtered(experiment_data, ExperimentConfig),
                    "mode": mode,
                    "evidence_mode": evidence_mode,
                    "workspace_source": workspace_source,
                    "allowed_imports": allowed_imports,
                    "code_trust": code_trust,
                    "metric_direction": metric_direction,
                    "protocol": protocol,
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
                "primary_claim_type": self.research.primary_claim_type,
                "threshold_waivers": [
                    {
                        "requirement": waiver.requirement,
                        "affected_claim": waiver.affected_claim,
                        "reason": waiver.reason,
                        "alternative_test": waiver.alternative_test,
                    }
                    for waiver in self.research.threshold_waivers
                ],
                "venue_id": self.research.venue_id,
                "venue_year": self.research.venue_year,
                "venue_track": self.research.venue_track,
            },
            "runtime": {
                "artifacts_root": self.runtime.artifacts_root,
                "max_iterations": self.runtime.max_iterations,
                "max_artifact_bytes": self.runtime.max_artifact_bytes,
            },
            "llm": {
                "mode": self.llm.mode,
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "allowed_hosts": list(self.llm.allowed_hosts),
                "auth_mode": self.llm.auth_mode,
                "api_key_env": self.llm.api_key_env,
                "primary_model": self.llm.primary_model,
                "max_requests": self.llm.max_requests,
                "max_retries": self.llm.max_retries,
                "timeout_sec": self.llm.timeout_sec,
                "input_cost_per_million": self.llm.input_cost_per_million,
                "output_cost_per_million": self.llm.output_cost_per_million,
            },
            "literature": {
                "mode": self.literature.mode,
                "sources": list(self.literature.sources),
                "per_source_limit": self.literature.per_source_limit,
                "max_retries": self.literature.max_retries,
                "timeout_sec": self.literature.timeout_sec,
                "queries": list(self.literature.queries),
                "saturation_patience": self.literature.saturation_patience,
                "saturation_max_new_ratio": self.literature.saturation_max_new_ratio,
                "arxiv_base_url": self.literature.arxiv_base_url,
                "openalex_base_url": self.literature.openalex_base_url,
                "crossref_base_url": self.literature.crossref_base_url,
            },
            "governance": {
                "assets_file": self.governance.assets_file,
            },
            "experiment": {
                "mode": self.experiment.mode,
                "evidence_mode": self.experiment.evidence_mode,
                "workspace_source": self.experiment.workspace_source,
                "allowed_imports": list(self.experiment.allowed_imports),
                "code_trust": self.experiment.code_trust,
                "time_budget_sec": self.experiment.time_budget_sec,
                "metric_key": self.experiment.metric_key,
                "metric_direction": self.experiment.metric_direction,
                "total_compute_budget": self.experiment.total_compute_budget,
                "protocol": self.experiment.protocol,
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


def _parse_threshold_waivers(value: object) -> tuple[ThresholdWaiver, ...]:
    if value is None or value == ():
        return ()
    if not isinstance(value, list):
        raise ConfigError("research.threshold_waivers must be a list")
    waivers: list[ThresholdWaiver] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ConfigError(f"research.threshold_waivers[{index}] must be a mapping")
        fields = {
            name: str(item.get(name, "")).strip()
            for name in ("requirement", "affected_claim", "reason", "alternative_test")
        }
        if fields["requirement"] in UNWAIVABLE_REQUIREMENTS:
            raise ConfigError(f"{fields['requirement']} cannot be waived")
        if fields["requirement"] not in WAIVABLE_THRESHOLD_REQUIREMENTS:
            raise ConfigError(
                f"unknown threshold requirement: {fields['requirement']}"
            )
        missing = [name for name, text in fields.items() if not text]
        if missing:
            raise ConfigError(
                f"research.threshold_waivers[{index}] missing: {', '.join(missing)}"
            )
        waivers.append(ThresholdWaiver(**fields))
    return tuple(waivers)
