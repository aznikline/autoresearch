from __future__ import annotations


def should_keep(
    *,
    candidate_metric: float,
    best_metric: float | None,
    direction: str,
) -> bool:
    if best_metric is None:
        return True
    if direction == "minimize":
        return candidate_metric < best_metric
    if direction == "maximize":
        return candidate_metric > best_metric
    raise ValueError(f"unknown metric direction: {direction}")
