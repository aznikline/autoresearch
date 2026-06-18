from __future__ import annotations

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.knowledge.cards import cards_from_screened
from autoresearch.literature.screening import screen_papers
from autoresearch.literature.sources import seed_source
from autoresearch.paper.draft import draft_paper
from autoresearch.paper.outline import build_outline
from autoresearch.paper.review import REQUIRED_SECTIONS


def test_outline_and_draft_include_required_sections() -> None:
    papers = seed_source().search("machine learning optimization")
    screened, _ = screen_papers(papers, topic="machine learning optimization")
    cards = cards_from_screened(screened)
    ledger = [
        LedgerEntry("baseline", 1.0, "ok", "keep", "baseline", "first", "runs/baseline/metrics.json"),
        LedgerEntry("regularized", 0.95, "ok", "keep", "regularized", "better", "runs/regularized/metrics.json"),
    ]

    outline = build_outline(topic="machine learning optimization", cards=cards, ledger=ledger)
    draft = draft_paper(
        topic="machine learning optimization",
        cards=cards,
        ledger=ledger,
        decision_text="Decision: PROCEED",
    )

    assert "Working title" in outline
    for section in REQUIRED_SECTIONS:
        assert section in draft
    assert "0.95" in draft
    assert "[@" in draft
