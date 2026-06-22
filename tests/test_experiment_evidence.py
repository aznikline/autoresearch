from __future__ import annotations

import json
from pathlib import Path

from autoresearch.experiments.evidence import observe_experiment_evidence
from autoresearch.experiments.ledger import LedgerEntry


def _entry(loop_dir: Path, trial_id: str, payload: dict[str, object]) -> LedgerEntry:
    metrics = loop_dir / "runs" / trial_id / "metrics.json"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(json.dumps(payload), encoding="utf-8")
    return LedgerEntry(
        trial_id=trial_id,
        metric=float(payload["primary_metric"]),
        status="ok",
        decision="keep",
        description=trial_id,
        reason="recorded",
        metrics_path=metrics.relative_to(loop_dir).as_posix(),
        raw_outputs=(metrics.relative_to(loop_dir).as_posix(),),
    )


def test_observed_evidence_requires_metrics_in_real_outputs(tmp_path: Path) -> None:
    plan = {
        "trials": [
            {"trial_id": "baseline-seed-0"},
            {"trial_id": "baseline-seed-1"},
            {"trial_id": "ablation-seed-0"},
        ],
        "evaluation_units": ["dataset-a", "dataset-b"],
        "seeds": [0, 1],
        "metrics": [
            "primary_metric",
            "ci_low",
            "ci_high",
            "effect_size",
            "runtime_sec",
            "compute_units",
        ],
        "confidence_intervals": True,
        "effect_sizes": True,
        "compute_reporting": True,
    }
    common = {
        "primary_metric": 0.8,
        "ci_low": 0.7,
        "ci_high": 0.9,
        "effect_size": 0.2,
        "runtime_sec": 1.5,
        "compute_units": 1.0,
        "evaluation_units": ["dataset-a", "dataset-b"],
    }
    ledger = [
        _entry(tmp_path, "baseline-seed-0", {**common, "seed": 0}),
        _entry(tmp_path, "baseline-seed-1", {**common, "seed": 1}),
        _entry(tmp_path, "ablation-seed-0", {**common, "seed": 0}),
    ]

    observed = observe_experiment_evidence(plan, ledger=ledger, loop_dir=tmp_path)

    assert observed.baselines == 2
    assert observed.ablations == 1
    assert observed.evaluation_units == 2
    assert observed.seeds == 2
    assert observed.verified_metrics == 6
    assert observed.confidence_intervals
    assert observed.effect_sizes
    assert observed.compute_reporting


def test_declared_but_missing_output_evidence_does_not_count(tmp_path: Path) -> None:
    plan = {
        "trials": [{"trial_id": "baseline-seed-0"}],
        "evaluation_units": ["dataset-a"],
        "seeds": [0, 1],
        "metrics": ["primary_metric", "ci_low", "ci_high", "effect_size"],
        "confidence_intervals": True,
        "effect_sizes": True,
        "compute_reporting": True,
    }
    ledger = [
        _entry(
            tmp_path,
            "baseline-seed-0",
            {"primary_metric": 0.8, "seed": 0, "evaluation_units": ["wrong"]},
        )
    ]

    observed = observe_experiment_evidence(plan, ledger=ledger, loop_dir=tmp_path)

    assert observed.verified_metrics == 1
    assert observed.evaluation_units == 0
    assert observed.seeds == 1
    assert not observed.confidence_intervals
    assert not observed.effect_sizes
    assert not observed.compute_reporting
