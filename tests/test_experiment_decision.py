from __future__ import annotations

import pytest

from autoresearch.experiments.decision import should_keep


def test_should_keep_baseline() -> None:
    assert should_keep(candidate_metric=1.0, best_metric=None, direction="minimize")


def test_should_keep_minimize_improvement_only() -> None:
    assert should_keep(candidate_metric=0.9, best_metric=1.0, direction="minimize")
    assert not should_keep(candidate_metric=1.1, best_metric=1.0, direction="minimize")


def test_should_keep_maximize_improvement_only() -> None:
    assert should_keep(candidate_metric=1.1, best_metric=1.0, direction="maximize")
    assert not should_keep(candidate_metric=0.9, best_metric=1.0, direction="maximize")


def test_should_keep_rejects_unknown_direction() -> None:
    with pytest.raises(ValueError, match="unknown metric direction"):
        should_keep(candidate_metric=1.0, best_metric=1.0, direction="sideways")
