from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from autoresearch.experiments.ledger import LedgerEntry


@dataclass(frozen=True)
class ObservedExperimentEvidence:
    baselines: int
    ablations: int
    evaluation_units: int
    seeds: int
    verified_metrics: int
    confidence_intervals: bool
    effect_sizes: bool
    compute_reporting: bool


def observe_experiment_evidence(
    plan: dict[str, object],
    *,
    ledger: list[LedgerEntry],
    loop_dir: Path,
) -> ObservedExperimentEvidence:
    successful = [
        entry for entry in ledger if entry.status == "ok" and entry.metric is not None
    ]
    payloads = [
        payload
        for entry in successful
        if (payload := _read_metrics(loop_dir, entry.metrics_path)) is not None
    ]
    declared_metrics = {
        str(item) for item in plan.get("metrics", ()) if str(item).strip()
    }
    verified = {
        metric
        for metric in declared_metrics
        if payloads and all(_finite_number(payload.get(metric)) for payload in payloads)
    }
    declared_units = {
        str(item) for item in plan.get("evaluation_units", ()) if str(item).strip()
    }
    units_verified = bool(payloads) and bool(declared_units) and all(
        isinstance(payload.get("evaluation_units"), list)
        and {str(item) for item in payload["evaluation_units"]} == declared_units
        for payload in payloads
    )
    declared_seeds = {
        int(item)
        for item in plan.get("seeds", ())
        if isinstance(item, int) and not isinstance(item, bool)
    }
    observed_seeds = {
        int(payload["seed"])
        for payload in payloads
        if isinstance(payload.get("seed"), int | float)
        and not isinstance(payload.get("seed"), bool)
        and float(payload["seed"]).is_integer()
    }
    return ObservedExperimentEvidence(
        baselines=sum(1 for entry in successful if "baseline" in entry.trial_id.lower()),
        ablations=sum(1 for entry in successful if "baseline" not in entry.trial_id.lower()),
        evaluation_units=len(declared_units) if units_verified else 0,
        seeds=len(declared_seeds & observed_seeds),
        verified_metrics=len(verified),
        confidence_intervals=(
            plan.get("confidence_intervals") is True
            and {"ci_low", "ci_high"} <= verified
        ),
        effect_sizes=(
            plan.get("effect_sizes") is True and "effect_size" in verified
        ),
        compute_reporting=(
            plan.get("compute_reporting") is True
            and {"runtime_sec", "compute_units"} <= verified
        ),
    )


def _read_metrics(loop_dir: Path, relative: str) -> dict[str, object] | None:
    candidate = (loop_dir / relative).resolve()
    try:
        candidate.relative_to(loop_dir.resolve())
    except ValueError:
        return None
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
