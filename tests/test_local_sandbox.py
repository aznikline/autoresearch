from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.backends.local import LocalBackend
from autoresearch.experiments.metrics import read_metric
from autoresearch.experiments.spec import ExperimentSpec
from autoresearch.experiments.workspace import create_workspace


def test_local_backend_runs_fixture_experiment(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = tmp_path / "experiment"
    create_workspace(workspace, spec)

    result = LocalBackend().run_trial(
        spec.trials[0],
        workspace=workspace,
        runs_dir=tmp_path / "runs",
        timeout_sec=3,
    )

    assert result.ok
    assert read_metric(result.metrics_path, "primary_metric") == 1.0


def test_local_backend_reports_invalid_script(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = tmp_path / "experiment"
    create_workspace(workspace, spec)
    (workspace / "experiment.py").write_text("import socket\n", encoding="utf-8")

    result = LocalBackend().run_trial(
        spec.trials[0],
        workspace=workspace,
        runs_dir=tmp_path / "runs",
        timeout_sec=3,
    )

    assert not result.ok
    assert result.status == "invalid"


def test_local_backend_handles_relative_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = Path("relative-experiment")
    create_workspace(workspace, spec)

    result = LocalBackend().run_trial(
        spec.trials[0],
        workspace=workspace,
        runs_dir=Path("relative-runs"),
        timeout_sec=3,
    )

    assert result.ok
    assert result.metrics_path.exists()
