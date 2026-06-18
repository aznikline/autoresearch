from __future__ import annotations

from pathlib import Path

from autoresearch.knowledge.cards import (
    cards_from_screened,
    read_cards_jsonl,
    write_cards_jsonl,
)
from autoresearch.literature.screening import screen_papers
from autoresearch.literature.sources import seed_source


def test_cards_from_screened_preserve_citation_keys() -> None:
    papers = seed_source().search("language model scaling")
    screened, _ = screen_papers(
        papers,
        topic="language model scaling",
        threshold=0.1,
    )

    cards = cards_from_screened(screened)

    assert cards
    assert all(card.citation_key for card in cards)
    assert all(card.source_url.startswith("https://") for card in cards)


def test_cards_round_trip_jsonl(tmp_path: Path) -> None:
    papers = seed_source().search("attention sequence model")
    screened, _ = screen_papers(
        papers,
        topic="attention sequence model",
        threshold=0.1,
    )
    cards = cards_from_screened(screened)
    path = tmp_path / "cards.jsonl"

    write_cards_jsonl(path, cards)

    assert read_cards_jsonl(path) == cards
