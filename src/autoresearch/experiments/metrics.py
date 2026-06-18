from __future__ import annotations

import json
from pathlib import Path


class MetricError(ValueError):
    """Raised when experiment metrics are missing or invalid."""


def read_metric(path: Path, metric_key: str) -> float:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MetricError(f"metrics file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MetricError(f"metrics file is not valid JSON: {path}") from exc

    if metric_key not in data:
        raise MetricError(f"metric '{metric_key}' missing from {path}")
    value = data[metric_key]
    if not isinstance(value, int | float):
        raise MetricError(f"metric '{metric_key}' must be numeric")
    return float(value)
