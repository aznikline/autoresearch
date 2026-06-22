from __future__ import annotations

from urllib.parse import urlencode
from xml.etree import ElementTree

from autoresearch.adapters.literature.base import (
    HTTPLiteratureSource,
    SourceSearchResult,
)
from autoresearch.literature.models import PaperRecord


class ArxivSource(HTTPLiteratureSource):
    name = "arxiv"
    official_hosts = frozenset({"export.arxiv.org"})

    def search(self, query: str, *, limit: int = 10) -> SourceSearchResult:
        url = f"{self.base_url}/api/query?{urlencode({'search_query': f'all:{query}', 'max_results': limit})}"
        body, result = self._fetch(url=url, query=query)
        if body is None:
            return result
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            return self._invalid_response(result, exc)
        papers: list[PaperRecord] = []
        for entry in root.findall("atom:entry", namespace):
            raw_id = _text(entry, "atom:id", namespace)
            arxiv_id = raw_id.rsplit("/", 1)[-1]
            if "v" in arxiv_id and arxiv_id.rsplit("v", 1)[-1].isdigit():
                arxiv_id = arxiv_id.rsplit("v", 1)[0]
            published = _text(entry, "atom:published", namespace)
            link = entry.find("atom:link[@rel='alternate']", namespace)
            papers.append(
                PaperRecord(
                    paper_id=f"arxiv:{arxiv_id}",
                    title=_clean(_text(entry, "atom:title", namespace)),
                    authors=tuple(
                        _clean(_text(author, "atom:name", namespace))
                        for author in entry.findall("atom:author", namespace)
                    ),
                    year=int(published[:4]) if published[:4].isdigit() else None,
                    abstract=_clean(_text(entry, "atom:summary", namespace)),
                    url=(link.get("href", "") if link is not None else raw_id),
                    source=self.name,
                )
            )
        return SourceSearchResult(**{**result.__dict__, "papers": tuple(papers)})


def _text(element: ElementTree.Element, path: str, namespace: dict[str, str]) -> str:
    child = element.find(path, namespace)
    return child.text or "" if child is not None else ""


def _clean(value: str) -> str:
    return " ".join(value.split())
