from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
project:
  name: "test-project"
research:
  topic: "test idea"
runtime:
  artifacts_root: "{artifacts}"
experiment:
  mode: "local"
  metric_direction: "minimize"
""".format(artifacts=(tmp_path / "artifacts").as_posix()),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def config(config_file: Path) -> AutoresearchConfig:
    from autoresearch.config import load_config

    return load_config(config_file)
