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


def read_all_numeric_metrics(path: Path) -> dict[str, float]:
    """Read every top-level numeric field from a metrics.json file.

    Returns a mapping of metric name to float value, including the primary
    metric. Non-numeric and nested values are skipped. This lets the claim
    verifier attest multi-metric findings (degradation ratios, correlations,
    CI bounds, etc.), not just the single primary_metric.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MetricError(f"metrics file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MetricError(f"metrics file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise MetricError(f"metrics file must be a JSON object: {path}")
    return {
        key: float(value)
        for key, value in data.items()
        if isinstance(value, int | float)
    }
