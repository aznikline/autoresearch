from __future__ import annotations

from autoresearch.literature.screening import screen_papers
from autoresearch.literature.sources import seed_source


def test_screen_papers_keeps_topic_relevant_records() -> None:
    papers = seed_source().search("machine learning optimization")
    screened, report = screen_papers(
        papers,
        topic="machine learning optimization",
        threshold=0.1,
    )

    kept = [item for item in screened if item.decision == "keep"]
    assert kept
    assert report.kept == len(kept)
    assert all(item.score >= 0.1 for item in kept)


def test_screen_papers_rejects_unrelated_topic() -> None:
    papers = seed_source().search("machine learning optimization")
    screened, report = screen_papers(
        papers,
        topic="marine geology sediments",
        threshold=0.1,
    )

    assert all(item.decision == "reject" for item in screened)
    assert report.kept == 0
