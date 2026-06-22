from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from autoresearch.adapters.literature.arxiv import ArxivSource
from autoresearch.adapters.literature.crossref import CrossrefSource
from autoresearch.adapters.literature.openalex import OpenAlexSource
from autoresearch.literature.search import collect_candidates


ARXIV_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/2401.00001v2</id>
    <title>Auditable Research Agents</title>
    <summary>Evidence-backed autonomous research.</summary>
    <published>2024-01-02T00:00:00Z</published>
    <author><name>Ada Researcher</name></author>
    <link rel="alternate" href="https://arxiv.org/abs/2401.00001v2" />
  </entry>
</feed>"""

OPENALEX_RESPONSE = json.dumps(
    {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "Auditable Research Agents",
                "publication_year": 2024,
                "authorships": [
                    {"author": {"display_name": "Ada Researcher"}}
                ],
                "abstract_inverted_index": {
                    "Evidence-backed": [0],
                    "autonomous": [1],
                    "research.": [2],
                },
                "doi": "https://doi.org/10.1000/example",
                "primary_location": {
                    "landing_page_url": "https://example.test/paper",
                    "source": {"display_name": "TestConf"},
                },
            }
        ]
    }
).encode()

CROSSREF_RESPONSE = json.dumps(
    {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/example",
                    "title": ["Auditable Research Agents"],
                    "abstract": "<jats:p>Evidence-backed autonomous research.</jats:p>",
                    "author": [{"given": "Ada", "family": "Researcher"}],
                    "published": {"date-parts": [[2024, 1, 2]]},
                    "URL": "https://doi.org/10.1000/example",
                    "container-title": ["TestConf"],
                }
            ]
        }
    }
).encode()


class _FixtureServer:
    def __init__(self, responses: dict[str, list[tuple[int, bytes, str]]]) -> None:
        self.responses = responses
        self.requests: list[str] = []

        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = self.path.split("?", 1)[0]
                owner.requests.append(self.path)
                queue = owner.responses[path]
                status, body, content_type = queue.pop(0) if len(queue) > 1 else queue[0]
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.thread.join()


@pytest.mark.parametrize(
    ("source_type", "path", "body", "content_type", "expected_id"),
    [
        (ArxivSource, "/api/query", ARXIV_RESPONSE, "application/atom+xml", "arxiv:2401.00001"),
        (OpenAlexSource, "/works", OPENALEX_RESPONSE, "application/json", "openalex:W123"),
        (CrossrefSource, "/works", CROSSREF_RESPONSE, "application/json", "doi:10.1000/example"),
    ],
)
def test_live_sources_normalize_and_cache_raw_responses(
    tmp_path: Path,
    source_type: type,
    path: str,
    body: bytes,
    content_type: str,
    expected_id: str,
) -> None:
    with _FixtureServer({path: [(200, body, content_type)]}) as base_url:
        source = source_type(base_url=base_url, cache_dir=tmp_path)
        result = source.search("research agents", limit=3)

    assert result.status == "ok"
    assert result.synthetic is False
    assert result.papers[0].paper_id == expected_id
    assert result.papers[0].title == "Auditable Research Agents"
    assert result.papers[0].authors == ("Ada Researcher",)
    assert result.raw_sha256
    assert (tmp_path / "raw" / f"{result.raw_sha256}.bin").read_bytes() == body
    audit = json.loads((tmp_path / "requests.jsonl").read_text().splitlines()[0])
    assert audit["source"] == result.source_name
    assert audit["query"] == "research agents"
    assert audit["raw_sha256"] == result.raw_sha256
    assert audit["retrieved_at"].endswith("Z")


def test_retryable_failure_is_bounded_and_reported_as_degraded(tmp_path: Path) -> None:
    responses = {
        "/works": [
            (429, b'{"error":"rate limited"}', "application/json"),
            (503, b'{"error":"unavailable"}', "application/json"),
        ]
    }
    server = _FixtureServer(responses)
    with server as base_url:
        result = OpenAlexSource(
            base_url=base_url,
            cache_dir=tmp_path,
            max_retries=1,
        ).search("research agents")

    assert result.status == "degraded"
    assert result.papers == ()
    assert result.attempts == 2
    assert "HTTP 503" in result.error
    assert len(server.requests) == 2


def test_socket_read_timeout_is_bounded_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def timeout(*args: object, **kwargs: object) -> object:
        raise TimeoutError("read timed out")

    monkeypatch.setattr("autoresearch.adapters.literature.base.urlopen", timeout)
    result = CrossrefSource(
        base_url="https://api.crossref.org",
        cache_dir=tmp_path,
        max_retries=1,
    ).search("sentiment classification")

    assert result.status == "degraded"
    assert result.attempts == 2
    assert result.error == "network timeout: read timed out"
    event = json.loads((tmp_path / "requests.jsonl").read_text().splitlines()[0])
    assert event["status"] == "degraded"


def test_malformed_success_response_is_cached_and_marked_degraded(tmp_path: Path) -> None:
    body = b"{not-json"
    with _FixtureServer({"/works": [(200, body, "application/json")]}) as base_url:
        result = OpenAlexSource(base_url=base_url, cache_dir=tmp_path).search("agents")

    assert result.status == "degraded"
    assert result.papers == ()
    assert "invalid response" in result.error
    assert (tmp_path / "raw" / f"{result.raw_sha256}.bin").read_bytes() == body


def test_multi_source_collection_preserves_partial_success_and_provenance(
    tmp_path: Path,
) -> None:
    responses = {
        "/api/query": [(200, ARXIV_RESPONSE, "application/atom+xml")],
        "/works": [(503, b"unavailable", "text/plain")],
    }
    with _FixtureServer(responses) as base_url:
        papers, report = collect_candidates(
            "research agents",
            [
                ArxivSource(base_url=base_url, cache_dir=tmp_path / "arxiv"),
                OpenAlexSource(
                    base_url=base_url,
                    cache_dir=tmp_path / "openalex",
                    max_retries=0,
                ),
            ],
        )

    assert [paper.paper_id for paper in papers] == ["arxiv:2401.00001"]
    assert report.status == "degraded"
    assert report.synthetic is False
    assert report.source_results[0].status == "ok"
    assert report.source_results[1].status == "degraded"
    assert "openalex: degraded" in report.to_markdown()


def test_literature_source_rejects_nonofficial_network_target(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="official host"):
        OpenAlexSource(
            base_url="https://metadata.internal",
            cache_dir=tmp_path,
        )
