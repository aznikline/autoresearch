from __future__ import annotations

from autoresearch.literature.search import collect_candidates
from autoresearch.literature.sources import seed_source


def test_seed_source_returns_relevant_machine_learning_papers() -> None:
    results = seed_source().search("empirical machine learning optimization")

    assert results
    assert any("Optimization" in paper.title for paper in results)


def test_collect_candidates_deduplicates_across_sources() -> None:
    source = seed_source()
    candidates, report = collect_candidates(
        "machine learning optimization",
        [source, source],
    )

    assert len(candidates) == len({paper.paper_id for paper in candidates})
    assert report.candidate_count == len(candidates)
    assert report.source_names == ("seed", "seed")


def test_citation_keys_are_deterministic() -> None:
    paper = seed_source().search("attention sequence model")[0]

    assert paper.citation_key == paper.citation_key
    assert paper.citation_key
