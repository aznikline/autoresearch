from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from autoresearch.literature.models import PaperRecord


@dataclass(frozen=True)
class SourceSearchResult:
    source_name: str
    status: str
    papers: tuple[PaperRecord, ...]
    synthetic: bool = False
    attempts: int = 1
    raw_sha256: str = ""
    error: str = ""


class HTTPLiteratureSource:
    name = ""
    official_hosts: frozenset[str] = frozenset()

    def __init__(
        self,
        *,
        base_url: str,
        cache_dir: str | Path,
        max_retries: int = 2,
        timeout_sec: float = 30.0,
    ) -> None:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        loopback = host in {"127.0.0.1", "localhost", "::1"}
        if host not in self.official_hosts and not loopback:
            raise ValueError(
                f"{self.name} base_url must use an official host or loopback test server"
            )
        if parsed.username or parsed.password:
            raise ValueError(f"{self.name} base_url must not contain credentials")
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError(f"{self.name} base_url must use HTTPS")
        if parsed.query or parsed.fragment:
            raise ValueError(f"{self.name} base_url must not contain query or fragment")
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.max_retries = max_retries
        self.timeout_sec = timeout_sec

    def _fetch(self, *, url: str, query: str) -> tuple[bytes | None, SourceSearchResult]:
        attempts = 0
        body = b""
        error = ""
        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                request = Request(
                    url,
                    headers={
                        "Accept": "application/json, application/atom+xml",
                        "User-Agent": "autoresearch/0.1 literature-audit",
                    },
                )
                with urlopen(request, timeout=self.timeout_sec) as response:
                    body = response.read()
                raw_sha256 = self._record(
                    body=body,
                    query=query,
                    url=url,
                    status="ok",
                    attempts=attempts,
                    error="",
                )
                return body, SourceSearchResult(
                    source_name=self.name,
                    status="ok",
                    papers=(),
                    attempts=attempts,
                    raw_sha256=raw_sha256,
                )
            except HTTPError as exc:
                body = exc.read()
                error = f"HTTP {exc.code}: {exc.reason}"
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except URLError as exc:
                error = f"network error: {exc.reason}"
            except TimeoutError as exc:
                error = f"network timeout: {exc}"
            if attempt < self.max_retries:
                time.sleep(min(0.05 * (2**attempt), 0.2))

        raw_sha256 = self._record(
            body=body,
            query=query,
            url=url,
            status="degraded",
            attempts=attempts,
            error=error,
        )
        return None, SourceSearchResult(
            source_name=self.name,
            status="degraded",
            papers=(),
            attempts=attempts,
            raw_sha256=raw_sha256,
            error=error,
        )

    def _invalid_response(
        self,
        result: SourceSearchResult,
        exc: Exception,
    ) -> SourceSearchResult:
        return replace(
            result,
            status="degraded",
            papers=(),
            error=f"invalid response: {type(exc).__name__}: {exc}",
        )

    def _record(
        self,
        *,
        body: bytes,
        query: str,
        url: str,
        status: str,
        attempts: int,
        error: str,
    ) -> str:
        digest = hashlib.sha256(body).hexdigest() if body else ""
        if body:
            raw_dir = self.cache_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{digest}.bin"
            if not raw_path.exists():
                raw_path.write_bytes(body)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "source": self.name,
            "query": query,
            "url": url,
            "status": status,
            "attempts": attempts,
            "raw_sha256": digest,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "error": error,
        }
        with (self.cache_dir / "requests.jsonl").open("a", encoding="utf-8") as audit:
            audit.write(json.dumps(event, sort_keys=True) + "\n")
        return digest
