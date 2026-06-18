from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrialSpec:
    trial_id: str
    description: str
    parameters: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrialSpec":
        return cls(
            trial_id=str(data["trial_id"]),
            description=str(data.get("description", "")),
            parameters={
                str(key): float(value)
                for key, value in dict(data.get("parameters", {})).items()
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class ExperimentSpec:
    topic: str
    metric_key: str
    metric_direction: str
    time_budget_sec: int
    trials: tuple[TrialSpec, ...]

    @classmethod
    def default(
        cls,
        *,
        topic: str,
        metric_key: str,
        metric_direction: str,
        time_budget_sec: int,
    ) -> "ExperimentSpec":
        return cls(
            topic=topic,
            metric_key=metric_key,
            metric_direction=metric_direction,
            time_budget_sec=time_budget_sec,
            trials=(
                TrialSpec(
                    trial_id="baseline",
                    description="Baseline deterministic toy experiment.",
                    parameters={"regularization": 0.0, "learning_rate": 0.05},
                ),
                TrialSpec(
                    trial_id="regularized",
                    description="Add light regularization to improve the toy loss.",
                    parameters={"regularization": 0.2, "learning_rate": 0.05},
                ),
                TrialSpec(
                    trial_id="overfit",
                    description="Use an intentionally worse setting.",
                    parameters={"regularization": -0.3, "learning_rate": 0.20},
                ),
            ),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "ExperimentSpec":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            topic=str(data["topic"]),
            metric_key=str(data["metric_key"]),
            metric_direction=str(data["metric_direction"]),
            time_budget_sec=int(data["time_budget_sec"]),
            trials=tuple(TrialSpec.from_dict(item) for item in data.get("trials", ())),
        )

    def write_yaml(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "metric_key": self.metric_key,
            "metric_direction": self.metric_direction,
            "time_budget_sec": self.time_budget_sec,
            "trials": [trial.to_dict() for trial in self.trials],
        }
