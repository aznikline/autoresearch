from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.backends.local import LocalBackend
from autoresearch.experiments.ledger import read_ledger
from autoresearch.experiments.loop import run_experiment_loop
from autoresearch.experiments.spec import ExperimentSpec
from autoresearch.experiments.workspace import create_workspace


def test_experiment_loop_keeps_improvements_and_discards_regressions(
    tmp_path: Path,
) -> None:
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = tmp_path / "experiment"
    ledger_path = tmp_path / "ledger.jsonl"
    create_workspace(workspace, spec)

    entries = run_experiment_loop(
        spec,
        backend=LocalBackend(),
        workspace=workspace,
        runs_dir=tmp_path / "runs",
        ledger_path=ledger_path,
    )

    assert [entry.decision for entry in entries] == ["keep", "keep", "discard"]
    assert entries[0].metrics_path == "runs/baseline/metrics.json"
    assert read_ledger(ledger_path) == entries
