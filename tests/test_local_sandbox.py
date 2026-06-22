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
    assert (result.metrics_path.parent / "stderr.txt").is_file()


def test_local_validator_rejects_dynamic_import_and_code_execution(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="unsafe",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    for index, payload in enumerate(
        (
            "__import__('socket')\n",
            "eval('1 + 1')\n",
            "exec('value = 1')\n",
        )
    ):
        workspace = tmp_path / f"experiment-{index}"
        create_workspace(workspace, spec)
        (workspace / "experiment.py").write_text(payload, encoding="utf-8")

        result = LocalBackend().run_trial(
            spec.trials[0],
            workspace=workspace,
            runs_dir=tmp_path / f"runs-{index}",
            timeout_sec=3,
        )

        assert result.status == "invalid"
        assert "call not allowed" in result.stderr


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


def test_local_backend_rejects_evaluator_mutation(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="machine learning optimization",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = tmp_path / "experiment"
    create_workspace(workspace, spec)
    script = workspace / "experiment.py"
    script.write_text(
        """
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--trial")
parser.add_argument("--output")
args = parser.parse_args()
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps({"primary_metric": 1.0}))
Path(__file__).write_text("# mutated evaluator\\n")
""",
        encoding="utf-8",
    )

    result = LocalBackend().run_trial(
        spec.trials[0],
        workspace=workspace,
        runs_dir=tmp_path / "runs",
        timeout_sec=3,
    )

    assert not result.ok
    assert result.status == "invalid"
    assert not result.evaluator_immutable
    assert "evaluator changed during execution" in result.stderr


def test_local_backend_records_timeout_without_losing_outputs(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="timeout",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=1,
    )
    workspace = tmp_path / "experiment"
    create_workspace(workspace, spec)
    (workspace / "experiment.py").write_text("while True:\n    pass\n", encoding="utf-8")

    result = LocalBackend().run_trial(
        spec.trials[0],
        workspace=workspace,
        runs_dir=tmp_path / "runs",
        timeout_sec=1,
    )

    assert result.status == "timeout"
    assert result.returncode == 124
    assert (result.metrics_path.parent / "stdout.txt").is_file()
    assert (result.metrics_path.parent / "stderr.txt").is_file()


def test_real_workspace_copies_operator_experiment_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    script = source / "experiment.py"
    script.write_text(
        "from pathlib import Path\nPath('source-marker').write_text('real')\n",
        encoding="utf-8",
    )
    spec = ExperimentSpec.default(
        topic="real experiment",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )

    workspace = tmp_path / "workspace"
    create_workspace(workspace, spec, source_dir=source)

    assert (workspace / "experiment.py").read_text(encoding="utf-8") == script.read_text(
        encoding="utf-8"
    )
    assert "deterministic workspace" not in (workspace / "README.md").read_text(
        encoding="utf-8"
    )


def test_local_backend_uses_explicit_import_allowlist(tmp_path: Path) -> None:
    spec = ExperimentSpec.default(
        topic="allowed dependency",
        metric_key="primary_metric",
        metric_direction="minimize",
        time_budget_sec=3,
    )
    workspace = tmp_path / "experiment"
    create_workspace(workspace, spec)
    (workspace / "experiment.py").write_text("import math\n", encoding="utf-8")

    rejected = LocalBackend().run_trial(
        spec.trials[0], workspace=workspace, runs_dir=tmp_path / "rejected", timeout_sec=3
    )
    allowed = LocalBackend(allowed_imports=("math",)).run_trial(
        spec.trials[0], workspace=workspace, runs_dir=tmp_path / "allowed", timeout_sec=3
    )

    assert rejected.status == "invalid"
    assert "import not allowed: math" in rejected.stderr
    assert allowed.status == "failed"
    assert "import not allowed" not in allowed.stderr
