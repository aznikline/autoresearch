from __future__ import annotations

from autoresearch.literature.search import collect_query_plan
from autoresearch.literature.sources import seed_source


def test_query_plan_records_rounds_and_requires_consecutive_zero_new_results() -> None:
    papers, report = collect_query_plan(
        (
            "machine learning optimization",
            "optimization machine learning",
            "learning optimization machine",
        ),
        [seed_source()],
        saturation_patience=2,
    )

    assert papers
    assert [round_.new_candidates for round_ in report.query_rounds] == [len(papers), 0, 0]
    assert report.saturated is True
    assert report.synthetic is True
    assert report.to_dict()["query_rounds"][0]["query"] == "machine learning optimization"


def test_query_plan_rejects_duplicate_normalized_queries() -> None:
    import pytest

    with pytest.raises(ValueError, match="duplicate"):
        collect_query_plan(
            ("machine learning", "  machine   learning  "),
            [seed_source()],
        )


def test_query_plan_does_not_claim_saturation_from_one_query() -> None:
    _, report = collect_query_plan(
        ("attention sequence model",),
        [seed_source()],
        saturation_patience=2,
    )

    assert report.saturated is False


def test_query_plan_supports_explicit_marginal_gain_ratio() -> None:
    _, report = collect_query_plan(
        (
            "machine learning optimization",
            "optimization machine learning",
            "learning optimization machine",
        ),
        [seed_source()],
        saturation_patience=2,
        saturation_max_new_ratio=0.1,
    )

    assert report.saturated is True
    assert report.to_dict()["saturation_max_new_ratio"] == 0.1
