from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.config import ConfigError, load_config, write_example_config


def test_load_config_resolves_defaults(config_file: Path) -> None:
    config = load_config(config_file)

    assert config.project.name == "test-project"
    assert config.research.topic == "test idea"
    assert config.llm.api_key_env == "OPENAI_API_KEY"
    assert config.experiment.metric_direction == "minimize"
    assert "result_analysis_decision" in config.hitl.required_stages
    assert config.research.venue_id == "mlsys"
    assert config.research.venue_year == "latest_available"
    assert config.research.venue_track == "main"
    assert config.llm.mode == "synthetic"
    assert config.llm.max_requests == 20
    assert config.experiment.protocol == {}
    assert config.experiment.evidence_mode == "synthetic"
    assert config.experiment.workspace_source == ""
    assert config.experiment.allowed_imports == ()
    assert config.governance.assets_file == ""


def test_load_config_rejects_missing_project_name(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("project: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="project.name is required"):
        load_config(path)


def test_load_config_rejects_invalid_experiment_mode(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
project:
  name: x
experiment:
  mode: simulated
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="experiment.mode"):
        load_config(path)


def test_config_rejects_unknown_experiment_evidence_mode() -> None:
    from autoresearch.config import AutoresearchConfig

    with pytest.raises(ConfigError, match="evidence_mode"):
        AutoresearchConfig.from_mapping(
            {"project": {"name": "x"}, "experiment": {"evidence_mode": "maybe"}}
        )


def test_runner_rejects_unimplemented_or_untrusted_local_execution(
    config_file: Path,
) -> None:
    from dataclasses import replace

    from autoresearch.config import load_config
    from autoresearch.pipeline.runner import PipelineRunner

    config = load_config(config_file)
    with pytest.raises(ConfigError, match="backend is not implemented"):
        PipelineRunner(replace(config, experiment=replace(config.experiment, mode="docker")))
    with pytest.raises(ConfigError, match="untrusted code requires"):
        PipelineRunner(
            replace(
                config,
                experiment=replace(config.experiment, code_trust="untrusted"),
            )
        )


def test_runner_requires_real_experiment_workspace(config_file: Path) -> None:
    from dataclasses import replace

    from autoresearch.config import load_config
    from autoresearch.pipeline.runner import PipelineRunner

    config = load_config(config_file)
    real = replace(
        config,
        experiment=replace(config.experiment, evidence_mode="real"),
    )

    with pytest.raises(ConfigError, match="workspace_source"):
        PipelineRunner(real)


def test_config_accepts_explicit_experiment_import_allowlist() -> None:
    from autoresearch.config import AutoresearchConfig

    config = AutoresearchConfig.from_mapping(
        {
            "project": {"name": "x"},
            "experiment": {"allowed_imports": ["numpy", "sklearn"]},
        }
    )

    assert config.experiment.allowed_imports == ("numpy", "sklearn")


def test_config_rejects_unknown_code_trust() -> None:
    from autoresearch.config import AutoresearchConfig

    with pytest.raises(ConfigError, match="code_trust"):
        AutoresearchConfig.from_mapping(
            {"project": {"name": "x"}, "experiment": {"code_trust": "hopeful"}}
        )


def test_live_local_llm_can_use_none_auth_but_remote_cannot() -> None:
    from autoresearch.config import AutoresearchConfig

    local = AutoresearchConfig.from_mapping(
        {
            "project": {"name": "x"},
            "llm": {
                "mode": "live",
                "base_url": "http://127.0.0.1:11434/v1",
                "allowed_hosts": ["127.0.0.1"],
                "auth_mode": "none",
            },
        }
    )
    assert local.llm.auth_mode == "none"

    with pytest.raises(ConfigError, match="loopback"):
        AutoresearchConfig.from_mapping(
            {
                "project": {"name": "x"},
                "llm": {
                    "mode": "live",
                    "base_url": "https://api.openai.com/v1",
                    "auth_mode": "none",
                },
            }
        )


def test_write_example_config_does_not_embed_secret(tmp_path: Path) -> None:
    path = write_example_config(tmp_path / "config.yaml")
    text = path.read_text(encoding="utf-8")

    assert "api_key_env" in text
    assert "sk-" not in text


def test_config_accepts_domain_protocol_mapping() -> None:
    from autoresearch.config import AutoresearchConfig

    config = AutoresearchConfig.from_mapping(
        {
            "project": {"name": "x"},
            "experiment": {"protocol": {"model_checkpoint": "model-v1"}},
        }
    )

    assert config.experiment.protocol == {"model_checkpoint": "model-v1"}


@pytest.mark.parametrize("protocol", [[], "bad", {"trials": []}, {"topic": "override"}])
def test_config_rejects_invalid_or_execution_overriding_protocol(protocol: object) -> None:
    from autoresearch.config import AutoresearchConfig

    with pytest.raises(ConfigError, match="experiment.protocol"):
        AutoresearchConfig.from_mapping(
            {"project": {"name": "x"}, "experiment": {"protocol": protocol}}
        )
