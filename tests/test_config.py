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


def test_write_example_config_does_not_embed_secret(tmp_path: Path) -> None:
    path = write_example_config(tmp_path / "config.yaml")
    text = path.read_text(encoding="utf-8")

    assert "api_key_env" in text
    assert "sk-" not in text
