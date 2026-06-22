from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from autoresearch.experiments.backends.base import ExperimentBackend
from autoresearch.experiments.decision import should_keep
from autoresearch.experiments.ledger import LedgerEntry, append_entry
from autoresearch.experiments.metrics import MetricError, read_metric
from autoresearch.experiments.spec import ExperimentSpec


def run_experiment_loop(
    spec: ExperimentSpec,
    *,
    backend: ExperimentBackend,
    workspace: Path,
    runs_dir: Path,
    ledger_path: Path,
) -> list[LedgerEntry]:
    runs_dir.mkdir(parents=True, exist_ok=True)
    if ledger_path.exists():
        ledger_path.unlink()

    best_metric: float | None = None
    entries: list[LedgerEntry] = []
    code_path = workspace / "experiment.py"
    code_sha256 = _sha256(code_path.read_bytes())
    spec_sha256 = _sha256(
        json.dumps(spec.to_dict(), sort_keys=True).encode("utf-8")
    )
    protocol_fingerprint = _sha256(
        json.dumps(
            {
                "code_sha256": code_sha256,
                "metric_key": spec.metric_key,
                "metric_direction": spec.metric_direction,
                "metrics": spec.metrics,
                "time_budget_sec": spec.time_budget_sec,
                "data_split": spec.data_split,
                "evaluation_units": spec.evaluation_units,
                "seeds": spec.seeds,
                "tuning_allowance": spec.tuning_allowance,
                "stopping_rule": spec.stopping_rule,
                "resource_budget": spec.resource_budget,
            },
            sort_keys=True,
        ).encode("utf-8")
    )
    for trial in spec.trials:
        result = backend.run_trial(
            trial,
            workspace=workspace,
            runs_dir=runs_dir,
            timeout_sec=spec.time_budget_sec,
        )
        metric: float | None = None
        decision = "crash"
        reason = result.status
        if result.ok:
            try:
                metric = read_metric(result.metrics_path, spec.metric_key)
            except MetricError as exc:
                reason = str(exc)
                decision = "invalid"
            else:
                keep = should_keep(
                    candidate_metric=metric,
                    best_metric=best_metric,
                    direction=spec.metric_direction,
                )
                decision = "keep" if keep else "discard"
                reason = "improved primary metric" if keep else "did not improve primary metric"
                if keep:
                    best_metric = metric

        entry = LedgerEntry(
            trial_id=trial.trial_id,
            metric=metric,
            status=result.status,
            decision=decision,
            description=trial.description,
            reason=reason,
            metrics_path=_portable_metrics_path(result.metrics_path, ledger_path.parent),
            run_id=trial.trial_id,
            metric_definition=f"{spec.metric_key} ({spec.metric_direction})",
            experiment_spec_sha256=spec_sha256,
            code_sha256=code_sha256,
            config_sha256=_sha256(
                json.dumps(trial.to_dict(), sort_keys=True).encode("utf-8")
            ),
            protocol_fingerprint=protocol_fingerprint,
            environment=f"Python {platform.python_version()} on {platform.platform()}",
            raw_outputs=tuple(
                _portable_metrics_path(path, ledger_path.parent)
                for path in sorted(result.metrics_path.parent.iterdir())
                if path.is_file()
            ),
            evaluator_immutable=result.evaluator_immutable,
        )
        append_entry(ledger_path, entry)
        entries.append(entry)
    return entries


def _portable_metrics_path(metrics_path: Path, base_dir: Path) -> str:
    try:
        return metrics_path.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return metrics_path.as_posix()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
