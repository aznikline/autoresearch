from __future__ import annotations

from pathlib import Path
import shutil

from autoresearch.experiments.spec import ExperimentSpec


def create_workspace(
    workspace: Path,
    spec: ExperimentSpec,
    *,
    source_dir: Path | None = None,
    plan_path: Path | None = None,
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    if source_dir is None:
        (workspace / "experiment.py").write_text(_EXPERIMENT_SCRIPT, encoding="utf-8")
        description = (
            "This deterministic workspace is the first local execution backend. "
            "It proves run orchestration and metric capture before domain-specific "
            "experiment generators are added."
        )
    else:
        source = source_dir.resolve()
        if not (source / "experiment.py").is_file():
            raise ValueError("real experiment source requires experiment.py")
        if any(path.is_symlink() for path in source.rglob("*")):
            raise ValueError("real experiment source cannot contain symlinks")
        shutil.copytree(source, workspace, dirs_exist_ok=True)
        description = "This workspace was copied from the configured real experiment source."
    if plan_path is None:
        spec.write_yaml(workspace / "experiment_plan.yaml")
    else:
        shutil.copy2(plan_path, workspace / "experiment_plan.yaml")
    (workspace / "README.md").write_text(
        "# Experiment Workspace\n\n"
        f"Topic: {spec.topic}\n\n"
        f"{description}\n",
        encoding="utf-8",
    )


def write_spec_markdown(path: Path, spec: ExperimentSpec) -> None:
    lines = [
        "# Experiment Spec",
        "",
        f"- Topic: {spec.topic}",
        f"- Metric: {spec.metric_key}",
        f"- Direction: {spec.metric_direction}",
        f"- Time budget seconds: {spec.time_budget_sec}",
        "",
        "## Trials",
    ]
    for trial in spec.trials:
        lines.append(f"- `{trial.trial_id}`: {trial.description}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


_EXPERIMENT_SCRIPT = """\
from __future__ import annotations

import argparse
import json
from pathlib import Path


PARAMS = {
    "baseline": {"regularization": 0.0, "learning_rate": 0.05},
    "regularized": {"regularization": 0.2, "learning_rate": 0.05},
    "overfit": {"regularization": -0.3, "learning_rate": 0.20},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    params = PARAMS[args.trial]
    # Deterministic toy objective: lower is better. The regularized trial wins,
    # while the overfit trial demonstrates discard behavior.
    loss = 1.0 - 0.25 * params["regularization"] + 0.8 * abs(params["learning_rate"] - 0.05)
    if params["regularization"] < 0:
        loss += 0.20

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "primary_metric": round(loss, 6),
                "loss": round(loss, 6),
                "trial_id": args.trial,
                "status": "ok",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
