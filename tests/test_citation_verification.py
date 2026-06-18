from __future__ import annotations

from autoresearch.literature.screening import screen_papers
from autoresearch.literature.sources import seed_source
from autoresearch.paper.citations import build_bibtex, verify_citations


def test_verify_citations_accepts_screened_keys() -> None:
    screened, _ = screen_papers(
        seed_source().search("machine learning optimization"),
        topic="machine learning optimization",
    )
    key = screened[0].paper.citation_key

    result = verify_citations(f"Related work [@{key}].", screened)

    assert result.ok
    assert key in result.supported_keys


def test_verify_citations_rejects_unsupported_keys() -> None:
    screened, _ = screen_papers(
        seed_source().search("machine learning optimization"),
        topic="machine learning optimization",
    )

    result = verify_citations("Unsupported claim [@fake2026paper].", screened)

    assert not result.ok
    assert result.unsupported_keys == ("fake2026paper",)


def test_build_bibtex_contains_screened_paper_keys() -> None:
    screened, _ = screen_papers(
        seed_source().search("machine learning optimization"),
        topic="machine learning optimization",
    )

    bibtex = build_bibtex(screened)

    assert "@misc{" in bibtex
    assert screened[0].paper.citation_key in bibtex
