from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.experiments.metrics import MetricError, read_metric


def test_read_metric_returns_numeric_value(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text('{"primary_metric": 0.91}', encoding="utf-8")

    assert read_metric(path, "primary_metric") == 0.91


def test_read_metric_rejects_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text('{"loss": 0.91}', encoding="utf-8")

    with pytest.raises(MetricError, match="missing"):
        read_metric(path, "primary_metric")


def test_read_metric_rejects_non_numeric_value(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text('{"primary_metric": "bad"}', encoding="utf-8")

    with pytest.raises(MetricError, match="numeric"):
        read_metric(path, "primary_metric")
