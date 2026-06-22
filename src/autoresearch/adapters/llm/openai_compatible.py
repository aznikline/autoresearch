from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from autoresearch.adapters.llm.base import (
    LLMBudgetError,
    LLMError,
    LLMResponseError,
    LLMUsage,
    StructuredLLMResponse,
)


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        allowed_hosts: tuple[str, ...],
        api_key_env: str,
        model: str,
        audit_dir: Path,
        max_requests: int,
        auth_mode: str = "bearer_env",
        max_retries: int = 2,
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
        timeout_sec: float = 60.0,
        retry_backoff_sec: float = 0.01,
    ) -> None:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        if parsed.username or parsed.password:
            raise ValueError("LLM base_url must not contain credentials")
        if host not in {item.lower() for item in allowed_hosts}:
            raise ValueError(f"LLM base_url host is not allowlisted: {host}")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("LLM base_url must use HTTPS except for loopback tests")
        if parsed.query or parsed.fragment:
            raise ValueError("LLM base_url must not contain query or fragment")
        if auth_mode not in {"bearer_env", "none"}:
            raise ValueError("LLM auth_mode must be bearer_env or none")
        if auth_mode == "none" and host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("unauthenticated LLM provider is allowed only on loopback")
        api_key = os.environ.get(api_key_env, "").strip() if api_key_env else ""
        if auth_mode == "bearer_env" and not api_key:
            raise LLMError(f"LLM credential environment variable is not set: {api_key_env}")
        if max_requests <= 0:
            raise LLMBudgetError("max_requests must be positive")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._auth_mode = auth_mode
        self._model = model
        self._audit_dir = audit_dir
        self._max_requests = max_requests
        self._max_retries = max_retries
        self._input_cost_per_million = input_cost_per_million
        self._output_cost_per_million = output_cost_per_million
        self._timeout_sec = timeout_sec
        self._retry_backoff_sec = retry_backoff_sec
        audit_path = audit_dir / "llm_calls.jsonl"
        self._request_count = (
            sum(1 for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip())
            if audit_path.exists()
            else 0
        )

    @property
    def request_count(self) -> int:
        return self._request_count

    def complete_json(
        self,
        *,
        stage: str,
        messages: tuple[tuple[str, str], ...],
        required_keys: tuple[str, ...],
    ) -> StructuredLLMResponse:
        payload, elapsed = self._request(messages)
        parsed = self._parse_content(payload, required_keys)
        self._record(stage=stage, messages=messages, payload=payload, elapsed=elapsed)
        if parsed is None:
            repair_messages = messages + (
                ("assistant", _content(payload)),
                (
                    "user",
                    "Return valid JSON only and include these required keys: "
                    + ", ".join(required_keys),
                ),
            )
            payload, elapsed = self._request(repair_messages)
            parsed = self._parse_content(payload, required_keys)
            self._record(
                stage=stage,
                messages=repair_messages,
                payload=payload,
                elapsed=elapsed,
            )
        if parsed is None:
            raise LLMResponseError(
                "provider response was not valid JSON with required keys after one repair"
            )
        usage = _usage(payload)
        return StructuredLLMResponse(
            data=parsed,
            request_id=str(payload.get("id", "")),
            model=str(payload.get("model", self._model)),
            usage=usage,
            cost_usd=(
                usage.prompt_tokens * self._input_cost_per_million
                + usage.completion_tokens * self._output_cost_per_million
            )
            / 1_000_000,
        )

    def _request(
        self,
        messages: tuple[tuple[str, str], ...],
    ) -> tuple[dict[str, Any], float]:
        body = json.dumps(
            {
                "model": self._model,
                "messages": [
                    {"role": role, "content": content} for role, content in messages
                ],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._consume_request_budget()
            headers = {"content-type": "application/json"}
            if self._auth_mode == "bearer_env":
                headers["authorization"] = f"Bearer {self._api_key}"
            request = Request(
                f"{self._base_url}/chat/completions",
                data=body,
                method="POST",
                headers=headers,
            )
            started = time.monotonic()
            try:
                with urlopen(request, timeout=self._timeout_sec) as response:
                    payload = json.loads(response.read())
                if not isinstance(payload, dict):
                    raise LLMResponseError("provider response must be a JSON object")
                return payload, time.monotonic() - started
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 409, 429, 500, 502, 503, 504}:
                    raise LLMError(f"LLM HTTP error {exc.code}") from exc
            except (URLError, TimeoutError) as exc:
                last_error = exc
            except json.JSONDecodeError as exc:
                raise LLMResponseError("provider HTTP response is not JSON") from exc
            if attempt < self._max_retries:
                time.sleep(self._retry_backoff_sec * (2**attempt))
        raise LLMError("LLM request failed after bounded retries") from last_error

    def _consume_request_budget(self) -> None:
        if self._request_count >= self._max_requests:
            raise LLMBudgetError(
                f"request budget exhausted: {self._request_count}/{self._max_requests}"
            )
        self._request_count += 1

    @staticmethod
    def _parse_content(
        payload: dict[str, Any],
        required_keys: tuple[str, ...],
    ) -> dict[str, Any] | None:
        try:
            parsed = json.loads(_content(payload))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None
        if not isinstance(parsed, dict) or any(key not in parsed for key in required_keys):
            return None
        return parsed

    def _record(
        self,
        *,
        stage: str,
        messages: tuple[tuple[str, str], ...],
        payload: dict[str, Any],
        elapsed: float,
    ) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        usage = _usage(payload)
        record = {
            "stage": stage,
            "provider": "openai-compatible",
            "auth_mode": self._auth_mode,
            "request_id": str(payload.get("id", "")),
            "model": str(payload.get("model", self._model)),
            "messages_sha256": _digest(json.dumps(messages, sort_keys=True)),
            "response_sha256": _digest(json.dumps(payload, sort_keys=True)),
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "latency_sec": round(elapsed, 6),
            "request_number": self._request_count,
        }
        with (self._audit_dir / "llm_calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _content(payload: dict[str, Any]) -> str:
    return str(payload["choices"][0]["message"]["content"])


def _usage(payload: dict[str, Any]) -> LLMUsage:
    raw = payload.get("usage", {})
    if not isinstance(raw, dict):
        raw = {}
    prompt = int(raw.get("prompt_tokens", 0))
    completion = int(raw.get("completion_tokens", 0))
    return LLMUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=int(raw.get("total_tokens", prompt + completion)),
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = ["LLMBudgetError", "OpenAICompatibleProvider"]
