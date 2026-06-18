from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    abstract: str
    url: str
    source: str
    venue: str = ""
    doi: str = ""

    @property
    def citation_key(self) -> str:
        lead = self.authors[0].split()[-1] if self.authors else "paper"
        year = str(self.year or "nd")
        title_word = next(iter(ordered_tokens(self.title)), "work")
        return f"{slugify(lead)}{year}{slugify(title_word)}"

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["authors"] = list(self.authors)
        data["citation_key"] = self.citation_key
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PaperRecord":
        return cls(
            paper_id=str(data["paper_id"]),
            title=str(data["title"]),
            authors=tuple(str(author) for author in data.get("authors", ())),
            year=int(data["year"]) if data.get("year") is not None else None,
            abstract=str(data.get("abstract", "")),
            url=str(data.get("url", "")),
            source=str(data.get("source", "")),
            venue=str(data.get("venue", "")),
            doi=str(data.get("doi", "")),
        )


@dataclass(frozen=True)
class ScreenedPaper:
    paper: PaperRecord
    score: float
    decision: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "paper": self.paper.to_dict(),
            "score": self.score,
            "decision": self.decision,
            "reason": self.reason,
        }


def write_papers_jsonl(path: Path, papers: Iterable[PaperRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(paper.to_dict(), sort_keys=True) for paper in papers]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_papers_jsonl(path: Path) -> list[PaperRecord]:
    papers: list[PaperRecord] = []
    if not path.exists():
        return papers
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            papers.append(PaperRecord.from_dict(json.loads(line)))
    return papers


def write_screened_jsonl(path: Path, screened: Iterable[ScreenedPaper]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item.to_dict(), sort_keys=True) for item in screened]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_screened_jsonl(path: Path) -> list[ScreenedPaper]:
    screened: list[ScreenedPaper] = []
    if not path.exists():
        return screened
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        screened.append(
            ScreenedPaper(
                paper=PaperRecord.from_dict(data["paper"]),
                score=float(data["score"]),
                decision=str(data["decision"]),
                reason=str(data["reason"]),
            )
        )
    return screened


def tokenize(text: str) -> set[str]:
    return set(ordered_tokens(text))


def ordered_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in _STOPWORDS
    )


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", text.lower())
    return slug or "x"


_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "our",
    "the",
    "this",
    "that",
    "with",
}
