from __future__ import annotations

from dataclasses import dataclass

from autoresearch.literature.models import PaperRecord
from autoresearch.literature.sources import LiteratureSource


@dataclass(frozen=True)
class SearchReport:
    query: str
    source_names: tuple[str, ...]
    candidate_count: int

    def to_markdown(self) -> str:
        sources = ", ".join(self.source_names) or "none"
        return (
            "# Literature Search Report\n\n"
            f"- Query: {self.query}\n"
            f"- Sources: {sources}\n"
            f"- Candidates: {self.candidate_count}\n"
        )


def collect_candidates(
    query: str,
    sources: list[LiteratureSource],
    *,
    per_source_limit: int = 10,
) -> tuple[list[PaperRecord], SearchReport]:
    seen: set[str] = set()
    candidates: list[PaperRecord] = []
    for source in sources:
        for paper in source.search(query, limit=per_source_limit):
            key = _dedupe_key(paper)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(paper)
    return candidates, SearchReport(
        query=query,
        source_names=tuple(source.name for source in sources),
        candidate_count=len(candidates),
    )


def _dedupe_key(paper: PaperRecord) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    return f"{paper.paper_id.lower()}:{paper.title.lower()}"
