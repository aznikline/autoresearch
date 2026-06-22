from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from autoresearch.adapters.llm.openai_compatible import (
    LLMBudgetError,
    OpenAICompatibleProvider,
)


class _Handler(BaseHTTPRequestHandler):
    responses: list[tuple[int, dict[str, object]]] = []
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("authorization"),
                "body": body,
            }
        )
        status, payload = type(self).responses.pop(0)
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def llm_server():
    _Handler.responses = []
    _Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _completion(content: str, *, request_id: str = "req-1") -> dict[str, object]:
    return {
        "id": request_id,
        "model": "test-model-2026",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }


def _provider(
    base_url: str,
    audit_dir: Path,
    monkeypatch,
    *,
    max_requests: int = 3,
) -> OpenAICompatibleProvider:
    monkeypatch.setenv("TEST_LLM_KEY", "super-secret-key")
    return OpenAICompatibleProvider(
        base_url=base_url,
        allowed_hosts=("127.0.0.1",),
        api_key_env="TEST_LLM_KEY",
        model="test-model",
        audit_dir=audit_dir,
        max_requests=max_requests,
        max_retries=2,
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )


def test_provider_returns_structured_response_and_audit_record(
    llm_server: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _Handler.responses = [(200, _completion('{"hypotheses": ["H1", "H2"]}'))]
    provider = _provider(llm_server, tmp_path, monkeypatch)

    response = provider.complete_json(
        stage="hypothesis_generation",
        messages=(("system", "Return JSON."), ("user", "Form hypotheses.")),
        required_keys=("hypotheses",),
    )

    assert response.data == {"hypotheses": ["H1", "H2"]}
    assert response.request_id == "req-1"
    assert response.model == "test-model-2026"
    assert response.usage.total_tokens == 18
    assert response.cost_usd == pytest.approx(0.000025)
    assert _Handler.requests[0]["path"] == "/v1/chat/completions"
    assert _Handler.requests[0]["authorization"] == "Bearer super-secret-key"
    audit = (tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert "super-secret-key" not in audit
    assert "Form hypotheses" not in audit
    assert "messages_sha256" in audit


def test_provider_repairs_one_malformed_structured_response(
    llm_server: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _Handler.responses = [
        (200, _completion("not json", request_id="req-bad")),
        (200, _completion('{"hypotheses": ["H1"]}', request_id="req-fixed")),
    ]
    provider = _provider(llm_server, tmp_path, monkeypatch)

    response = provider.complete_json(
        stage="hypothesis_generation",
        messages=(("user", "Form hypotheses."),),
        required_keys=("hypotheses",),
    )

    assert response.request_id == "req-fixed"
    assert len(_Handler.requests) == 2
    repair_messages = _Handler.requests[1]["body"]["messages"]
    assert "valid JSON" in repair_messages[-1]["content"]


def test_provider_retries_retryable_http_status(
    llm_server: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _Handler.responses = [
        (429, {"error": {"message": "rate limited"}}),
        (200, _completion('{"ok": true}')),
    ]
    provider = _provider(llm_server, tmp_path, monkeypatch)

    response = provider.complete_json(
        stage="synthesis",
        messages=(("user", "Synthesize."),),
        required_keys=("ok",),
    )

    assert response.data["ok"] is True
    assert len(_Handler.requests) == 2


def test_provider_enforces_request_budget_before_network_call(
    llm_server: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _Handler.responses = [(200, _completion('{"ok": true}'))]
    provider = _provider(llm_server, tmp_path, monkeypatch, max_requests=1)
    provider.complete_json(
        stage="synthesis",
        messages=(("user", "First."),),
        required_keys=("ok",),
    )

    with pytest.raises(LLMBudgetError, match="request budget exhausted"):
        provider.complete_json(
            stage="synthesis",
            messages=(("user", "Second."),),
            required_keys=("ok",),
        )

    assert len(_Handler.requests) == 1


def test_provider_rejects_non_allowlisted_or_credential_bearing_url(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TEST_LLM_KEY", "secret")
    with pytest.raises(ValueError, match="allowlisted"):
        OpenAICompatibleProvider(
            base_url="https://metadata.internal/v1",
            allowed_hosts=("api.openai.com",),
            api_key_env="TEST_LLM_KEY",
            model="x",
            audit_dir=tmp_path,
            max_requests=1,
        )


def test_unauthenticated_provider_is_allowed_only_on_loopback(
    llm_server: str,
    tmp_path: Path,
) -> None:
    _Handler.responses = [(200, _completion('{"ok": true}'))]
    provider = OpenAICompatibleProvider(
        base_url=llm_server,
        allowed_hosts=("127.0.0.1",),
        auth_mode="none",
        api_key_env="",
        model="local-model",
        audit_dir=tmp_path,
        max_requests=1,
    )

    response = provider.complete_json(
        stage="smoke",
        messages=(("user", "Return JSON."),),
        required_keys=("ok",),
    )

    assert response.data == {"ok": True}
    assert _Handler.requests[0]["authorization"] is None
    with pytest.raises(ValueError, match="loopback"):
        OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            allowed_hosts=("api.openai.com",),
            auth_mode="none",
            api_key_env="",
            model="x",
            audit_dir=tmp_path,
            max_requests=1,
        )
    with pytest.raises(ValueError, match="credentials"):
        OpenAICompatibleProvider(
            base_url="https://user:pass@api.openai.com/v1",
            allowed_hosts=("api.openai.com",),
            api_key_env="TEST_LLM_KEY",
            model="x",
            audit_dir=tmp_path,
            max_requests=1,
        )
