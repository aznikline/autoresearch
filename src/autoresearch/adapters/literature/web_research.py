from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from autoresearch.adapters.literature.base import (
    HTTPLiteratureSource,
    SourceSearchResult,
)
from autoresearch.literature.models import PaperRecord


class WebResearchSource(HTTPLiteratureSource):
    """ReAct-style deep retrieval: LLM expands the query into sub-queries,
    retrieves from OpenAlex (free, no key), then the LLM judges relevance to
    filter out off-topic hits. Inspired by Alibaba DeepResearch's IterResearch
    mode, but lightweight — no model-format binding, no Serper key.

    Uses OpenRouter (OpenAI-compatible) to call a qwen model for the
    query-expansion + relevance-judgment reasoning. Without OPENROUTER_API_KEY
    it degrades to a plain OpenAlex search (no expansion, no filtering).
    """

    name = "web_research"
    official_hosts = frozenset({"api.openalex.org"})

    DEFAULT_MODEL = "qwen3.7-max"
    LLM_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_KEY_ENV = "DASHSCOPE_API_KEY"

    def __init__(self, base_url: str = "https://api.openalex.org", **kwargs) -> None:
        # Bypass the base class URL-validation (we manage our own OpenAlex calls)
        # but keep compatible with the source_type(url) factory in core.py.
        self._base_url = base_url
        self._max_retries = kwargs.get("max_retries", 2)
        self._timeout_sec = kwargs.get("timeout_sec", 30.0)

    def search(self, query: str, *, limit: int = 10) -> SourceSearchResult:
        api_key = os.environ.get(self.LLM_KEY_ENV, "").strip()
        if not api_key:
            # Degrade to plain OpenAlex (still useful, just no deep reasoning)
            return self._openalex_search(query, limit)

        # Step 1: LLM expands the query into 3 sub-queries (ReAct: plan)
        sub_queries = self._expand_query(query, api_key)
        all_queries = [query] + sub_queries

        # Step 2: retrieve from OpenAlex for each sub-query (ReAct: act)
        seen_ids: set[str] = set()
        candidates: list[PaperRecord] = []
        for q in all_queries:
            for paper in self._openalex_papers(q, limit=limit):
                if paper.paper_id not in seen_ids:
                    seen_ids.add(paper.paper_id)
                    candidates.append(paper)

        if not candidates:
            return SourceSearchResult(
                source_name=self.name,
                status="ok",
                papers=(),
                attempts=1,
                raw_sha256="",
            )

        # Step 3: LLM judges relevance, ranks (ReAct: observe + reason)
        kept = self._judge_relevance(query, candidates, limit, api_key)
        return SourceSearchResult(
            source_name=self.name,
            status="ok",
            papers=tuple(kept),
            attempts=len(all_queries),
            raw_sha256="",
        )

    def _expand_query(self, query: str, api_key: str) -> list[str]:
        """Deterministic query expansion (no LLM — that was unstable on qwen3.7-max).

        Splits the query into key terms and generates complementary sub-queries
        targeting method, metric, and domain angles. This is cheaper and more
        reliable than LLM-based expansion, and the LLM is reserved for the
        relevance-judgment step where it adds real value.
        """
        terms = query.lower().split()
        if len(terms) <= 2:
            return []
        # Method angle: focus on the technical terms (nouns)
        method_terms = [t for t in terms if len(t) > 4 and t not in {"under", "than", "from", "with", "the", "than"}]
        # Metric angle: extract metric-like terms
        metric_terms = [t for t in terms if any(k in t for k in ["error", "robust", "shift", "q-error", "degrad"])]
        sub_queries: list[str] = []
        if method_terms:
            sub_queries.append(" ".join(method_terms[:4]))
        if metric_terms:
            sub_queries.append(" ".join(metric_terms))
        # Domain angle: the full query minus stopwords
        sub_queries.append(" ".join(t for t in terms if t not in {"of", "the", "a", "an", "under", "than"}))
        return [q for q in sub_queries if q and q != query.lower()][:3]

    def _judge_relevance(
        self, query: str, candidates: list[PaperRecord], limit: int, api_key: str
    ) -> list[PaperRecord]:
        # Keep it cheap: send titles + first 150 chars of abstract
        paper_list = "\n".join(
            f"{i}. {p.title} | {(p.abstract or '')[:150]}"
            for i, p in enumerate(candidates[:40])
        )
        prompt = (
            f"Research question: {query}\n\nPapers:\n{paper_list}\n\n"
            f"Select ONLY papers directly relevant to the research question — "
            f"reject papers that merely share generic keywords (e.g. 'robust', "
            f"'estimation', 'shift') but are from unrelated domains. Return a JSON "
            f"array of indices (0-based), most relevant first, at most {limit}. "
            f"Fewer is better than including irrelevant ones. No prose."
        )
        resp = self._llm_call(api_key, prompt)
        try:
            indices = json.loads(resp)
            if isinstance(indices, list):
                kept = [candidates[i] for i in indices if isinstance(i, int) and 0 <= i < len(candidates)]
                return kept[:limit]
        except (json.JSONDecodeError, TypeError, IndexError):
            pass
        # Fallback: return first `limit` unranked
        return candidates[:limit]

    def _llm_call(self, api_key: str, prompt: str) -> str:
        body = json.dumps(
            {
                "model": os.environ.get("WEB_RESEARCH_MODEL", self.DEFAULT_MODEL),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
            }
        ).encode("utf-8")
        req = Request(
            f"{self.LLM_BASE}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=30) as r:
                payload = json.loads(r.read())
            return payload["choices"][0]["message"]["content"]
        except Exception:
            return ""

    def _openalex_search(self, query: str, limit: int) -> SourceSearchResult:
        papers = self._openalex_papers(query, limit)
        return SourceSearchResult(
            source_name=self.name,
            status="ok",
            papers=tuple(papers),
            attempts=1,
            raw_sha256="",
        )

    def _openalex_papers(self, query: str, limit: int) -> list[PaperRecord]:
        url = f"https://api.openalex.org/works?{urlencode({'search': query, 'per-page': limit})}"
        req = Request(url, headers={"User-Agent": "autoresearch/0.1 web-research"})
        try:
            with urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        except Exception:
            return []
        papers: list[PaperRecord] = []
        for item in data.get("results", ()):
            raw_id = str(item.get("id", ""))
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            papers.append(
                PaperRecord(
                    paper_id=f"web_research:{raw_id.rsplit('/', 1)[-1]}",
                    title=str(item.get("display_name", "")),
                    authors=tuple(
                        str((a.get("author") or {}).get("display_name", ""))
                        for a in item.get("authorships", ())
                    ),
                    year=int(item["publication_year"]) if item.get("publication_year") else None,
                    abstract=_restore_abstract(item.get("abstract_inverted_index") or {}),
                    url=str(location.get("landing_page_url") or raw_id),
                    source=self.name,
                    venue=str(source.get("display_name") or ""),
                )
            )
        return papers


def _restore_abstract(inverted: dict[str, list[int]]) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for idx in idxs:
            positions.append((idx, word))
    positions.sort()
    return " ".join(w for _, w in positions)
