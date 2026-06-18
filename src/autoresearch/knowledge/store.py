from __future__ import annotations

from pathlib import Path

from autoresearch.knowledge.cards import KnowledgeCard, read_cards_jsonl, write_cards_jsonl


class KnowledgeStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def cards_path(self) -> Path:
        return self.root / "knowledge_cards.jsonl"

    def write_cards(self, cards: list[KnowledgeCard]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        write_cards_jsonl(self.cards_path, cards)

    def read_cards(self) -> list[KnowledgeCard]:
        return read_cards_jsonl(self.cards_path)
