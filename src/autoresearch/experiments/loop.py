from __future__ import annotations

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
        )
        append_entry(ledger_path, entry)
        entries.append(entry)
    return entries


def _portable_metrics_path(metrics_path: Path, base_dir: Path) -> str:
    try:
        return metrics_path.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return metrics_path.as_posix()
