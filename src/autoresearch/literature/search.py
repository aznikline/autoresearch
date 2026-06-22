from __future__ import annotations

from dataclasses import dataclass

from autoresearch.adapters.literature.base import SourceSearchResult
from autoresearch.literature.models import PaperRecord
from autoresearch.literature.sources import LiteratureSource


@dataclass(frozen=True)
class QueryRound:
    query: str
    candidate_count: int
    new_candidates: int
    status: str


@dataclass(frozen=True)
class SearchReport:
    query: str
    source_names: tuple[str, ...]
    candidate_count: int
    source_results: tuple[SourceSearchResult, ...] = ()
    status: str = "ok"
    synthetic: bool = False
    query_rounds: tuple[QueryRound, ...] = ()
    saturated: bool = False
    saturation_max_new_ratio: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "source_names": list(self.source_names),
            "candidate_count": self.candidate_count,
            "status": self.status,
            "synthetic": self.synthetic,
            "saturated": self.saturated,
            "saturation_max_new_ratio": self.saturation_max_new_ratio,
            "query_rounds": [
                {
                    "query": round_.query,
                    "candidate_count": round_.candidate_count,
                    "new_candidates": round_.new_candidates,
                    "status": round_.status,
                }
                for round_ in self.query_rounds
            ],
            "source_results": [
                {
                    "source_name": result.source_name,
                    "status": result.status,
                    "synthetic": result.synthetic,
                    "attempts": result.attempts,
                    "raw_sha256": result.raw_sha256,
                    "error": result.error,
                    "paper_count": len(result.papers),
                }
                for result in self.source_results
            ],
        }

    def to_markdown(self) -> str:
        sources = ", ".join(self.source_names) or "none"
        source_status = "\n".join(
            f"- {result.source_name}: {result.status}"
            for result in self.source_results
        )
        return (
            "# Literature Search Report\n\n"
            f"- Query: {self.query}\n"
            f"- Sources: {sources}\n"
            f"- Candidates: {self.candidate_count}\n"
            f"- Status: {self.status}\n"
            f"- Synthetic: {str(self.synthetic).lower()}\n"
            f"- Saturated: {str(self.saturated).lower()}\n"
            + (f"\n## Source Status\n\n{source_status}\n" if source_status else "")
        )


def collect_candidates(
    query: str,
    sources: list[LiteratureSource],
    *,
    per_source_limit: int = 10,
) -> tuple[list[PaperRecord], SearchReport]:
    seen: set[str] = set()
    candidates: list[PaperRecord] = []
    source_results: list[SourceSearchResult] = []
    for source in sources:
        raw_result = source.search(query, limit=per_source_limit)
        if isinstance(raw_result, SourceSearchResult):
            result = raw_result
            papers = result.papers
        else:
            papers = tuple(raw_result)
            result = SourceSearchResult(
                source_name=source.name,
                status="ok",
                papers=papers,
                synthetic=source.name == "seed",
            )
        source_results.append(result)
        for paper in papers:
            key = _dedupe_key(paper)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(paper)
    return candidates, SearchReport(
        query=query,
        source_names=tuple(source.name for source in sources),
        candidate_count=len(candidates),
        source_results=tuple(source_results),
        status=(
            "degraded"
            if any(result.status != "ok" for result in source_results)
            else "ok"
        ),
        synthetic=bool(source_results) and all(
            result.synthetic for result in source_results
        ),
    )


def collect_query_plan(
    queries: tuple[str, ...],
    sources: list[LiteratureSource],
    *,
    per_source_limit: int = 10,
    saturation_patience: int = 2,
    saturation_max_new_ratio: float = 0.0,
) -> tuple[list[PaperRecord], SearchReport]:
    if not queries:
        raise ValueError("literature query plan must contain at least one query")
    normalized_queries = tuple(" ".join(query.lower().split()) for query in queries)
    if len(normalized_queries) != len(set(normalized_queries)):
        raise ValueError("literature query plan contains duplicate normalized queries")
    if saturation_patience <= 0:
        raise ValueError("saturation_patience must be positive")
    if not 0.0 <= saturation_max_new_ratio <= 1.0:
        raise ValueError("saturation_max_new_ratio must be between 0 and 1")
    seen: set[str] = set()
    candidates: list[PaperRecord] = []
    rounds: list[QueryRound] = []
    source_results: list[SourceSearchResult] = []
    reports: list[SearchReport] = []
    for query in queries:
        round_candidates, report = collect_candidates(
            query,
            sources,
            per_source_limit=per_source_limit,
        )
        reports.append(report)
        source_results.extend(report.source_results)
        new_count = 0
        for paper in round_candidates:
            key = _dedupe_key(paper)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(paper)
            new_count += 1
        rounds.append(
            QueryRound(
                query=query,
                candidate_count=len(round_candidates),
                new_candidates=new_count,
                status=report.status,
            )
        )
    saturated = len(rounds) >= saturation_patience and all(
        (
            round_.new_candidates / round_.candidate_count
            if round_.candidate_count
            else 0.0
        )
        <= saturation_max_new_ratio
        for round_ in rounds[-saturation_patience:]
    )
    return candidates, SearchReport(
        query=" | ".join(queries),
        source_names=tuple(source.name for source in sources),
        candidate_count=len(candidates),
        source_results=tuple(source_results),
        status=(
            "degraded"
            if any(report.status != "ok" for report in reports)
            else "ok"
        ),
        synthetic=bool(reports) and all(report.synthetic for report in reports),
        query_rounds=tuple(rounds),
        saturated=saturated,
        saturation_max_new_ratio=saturation_max_new_ratio,
    )


def _dedupe_key(paper: PaperRecord) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    return f"{paper.paper_id.lower()}:{paper.title.lower()}"
