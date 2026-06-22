from __future__ import annotations

import json
from urllib.parse import urlencode

from autoresearch.adapters.literature.base import (
    HTTPLiteratureSource,
    SourceSearchResult,
)
from autoresearch.literature.models import PaperRecord


class OpenAlexSource(HTTPLiteratureSource):
    name = "openalex"
    official_hosts = frozenset({"api.openalex.org"})

    def search(self, query: str, *, limit: int = 10) -> SourceSearchResult:
        url = f"{self.base_url}/works?{urlencode({'search': query, 'per-page': limit})}"
        body, result = self._fetch(url=url, query=query)
        if body is None:
            return result
        try:
            papers = tuple(_paper(item) for item in json.loads(body).get("results", ()))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return self._invalid_response(result, exc)
        return SourceSearchResult(**{**result.__dict__, "papers": papers})


def _paper(item: dict[str, object]) -> PaperRecord:
    raw_id = str(item.get("id", ""))
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    doi = str(item.get("doi") or "").removeprefix("https://doi.org/")
    return PaperRecord(
        paper_id=f"openalex:{raw_id.rsplit('/', 1)[-1]}",
        title=str(item.get("display_name", "")),
        authors=tuple(
            str((authorship.get("author") or {}).get("display_name", ""))
            for authorship in item.get("authorships", ())
        ),
        year=int(item["publication_year"]) if item.get("publication_year") else None,
        abstract=_restore_abstract(item.get("abstract_inverted_index") or {}),
        url=str(location.get("landing_page_url") or raw_id),
        source="openalex",
        venue=str(source.get("display_name") or ""),
        doi=doi,
    )


def _restore_abstract(index: dict[str, list[int]]) -> str:
    positioned = ((position, word) for word, positions in index.items() for position in positions)
    return " ".join(word for _, word in sorted(positioned))
