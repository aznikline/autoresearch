from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urlencode

from autoresearch.adapters.literature.base import (
    HTTPLiteratureSource,
    SourceSearchResult,
)
from autoresearch.literature.models import PaperRecord


class CrossrefSource(HTTPLiteratureSource):
    name = "crossref"
    official_hosts = frozenset({"api.crossref.org"})

    def search(self, query: str, *, limit: int = 10) -> SourceSearchResult:
        url = f"{self.base_url}/works?{urlencode({'query': query, 'rows': limit})}"
        body, result = self._fetch(url=url, query=query)
        if body is None:
            return result
        try:
            items = json.loads(body).get("message", {}).get("items", ())
            papers = tuple(_paper(item) for item in items)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return self._invalid_response(result, exc)
        return SourceSearchResult(**{**result.__dict__, "papers": papers})


def _paper(item: dict[str, object]) -> PaperRecord:
    doi = str(item.get("DOI") or "")
    date_parts = (item.get("published") or {}).get("date-parts") or []
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    return PaperRecord(
        paper_id=f"doi:{doi.lower()}",
        title=_first(item.get("title")),
        authors=tuple(
            " ".join(filter(None, (str(author.get("given", "")), str(author.get("family", "")))))
            for author in item.get("author", ())
        ),
        year=int(year) if year is not None else None,
        abstract=_strip_markup(str(item.get("abstract") or "")),
        url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
        source="crossref",
        venue=_first(item.get("container-title")),
        doi=doi,
    )


def _first(value: object) -> str:
    return str(value[0]) if isinstance(value, list) and value else ""


def _strip_markup(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())
