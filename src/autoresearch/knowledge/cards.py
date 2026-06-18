from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from autoresearch.literature.models import PaperRecord, ScreenedPaper


@dataclass(frozen=True)
class KnowledgeCard:
    citation_key: str
    paper_id: str
    title: str
    source_url: str
    claim: str
    method: str
    limitation: str
    evidence_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def cards_from_screened(screened: list[ScreenedPaper]) -> list[KnowledgeCard]:
    return [
        card_from_paper(item.paper)
        for item in screened
        if item.decision == "keep"
    ]


def card_from_paper(paper: PaperRecord) -> KnowledgeCard:
    abstract = paper.abstract.strip()
    claim = abstract.split(".")[0].strip() if abstract else paper.title
    return KnowledgeCard(
        citation_key=paper.citation_key,
        paper_id=paper.paper_id,
        title=paper.title,
        source_url=paper.url,
        claim=claim,
        method=_method_hint(abstract),
        limitation="Not yet assessed; requires full-paper review.",
        evidence_source=paper.source,
    )


def write_cards_jsonl(path: Path, cards: list[KnowledgeCard]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(card.to_dict(), sort_keys=True) for card in cards]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_cards_jsonl(path: Path) -> list[KnowledgeCard]:
    cards: list[KnowledgeCard] = []
    if not path.exists():
        return cards
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cards.append(KnowledgeCard(**json.loads(line)))
    return cards


def _method_hint(abstract: str) -> str:
    lowered = abstract.lower()
    if "experiment" in lowered or "empirical" in lowered:
        return "Empirical evaluation"
    if "introduces" in lowered or "presents" in lowered:
        return "Method proposal"
    if "studies" in lowered:
        return "Analysis study"
    return "Unknown from abstract"
