from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.spec import ExperimentSpec


def test_experiment_spec_round_trips_yaml(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    path = tmp_path / "experiment_plan.yaml"

    spec.write_yaml(path)

    loaded = ExperimentSpec.from_yaml(path)
    assert loaded == spec
    assert loaded.trials[0].trial_id == "baseline"
