from __future__ import annotations

import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig, ConfigError
from autoresearch.pipeline.runner import PipelineRunner


class _LiveHandler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self) -> None:  # noqa: N802
        type(self).calls += 1
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)
        hypotheses = [
            {
                "hypothesis_id": "H-live-1",
                "statement": "The intervention improves the frozen metric.",
                "expected_direction": "improve",
                "disconfirming_evidence": "No matched improvement.",
                "competes_with": "H-live-2",
            },
            {
                "hypothesis_id": "H-live-2",
                "statement": "The effect is explained by variance.",
                "expected_direction": "no material change",
                "disconfirming_evidence": "A repeated matched effect.",
                "competes_with": "H-live-1",
            },
        ]
        payload = {
            "id": "live-request-1",
            "model": "live-test-model",
            "choices": [
                {"message": {"content": json.dumps({"hypotheses": hypotheses})}}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_live_provider_drives_hypothesis_stage(
    config: AutoresearchConfig,
    monkeypatch,
) -> None:
    _LiveHandler.calls = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("LIVE_TEST_KEY", "do-not-persist")
    live_config = replace(
        config,
        llm=replace(
            config.llm,
            mode="live",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            allowed_hosts=("127.0.0.1",),
            api_key_env="LIVE_TEST_KEY",
            primary_model="live-test-model",
            max_requests=3,
        ),
    )
    try:
        result = PipelineRunner(live_config).run(
            topic="test live hypothesis generation",
            run_id="live-reasoning-run",
            auto_approve=True,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result["status"] == "done"
    run_dir = Path(result["run_dir"])
    hypotheses = json.loads(
        (run_dir / "stage-06-hypothesis_generation/hypotheses.json").read_text(
            encoding="utf-8"
        )
    )
    assert hypotheses[0]["hypothesis_id"] == "H-live-1"
    # 3 calls: hypothesis + reviewer simulation + contribution mining
    assert _LiveHandler.calls == 3
    audit = (run_dir / "llm/llm_calls.jsonl").read_text(encoding="utf-8")
    assert "do-not-persist" not in audit
    assert all(
        b"do-not-persist" not in path.read_bytes()
        for path in run_dir.rglob("*")
        if path.is_file()
    )
    alignment = json.loads((run_dir / "alignment.json").read_text(encoding="utf-8"))
    assert alignment["llm"]["mode"] == "live"


def test_live_mode_fails_before_run_when_credential_is_missing(
    config: AutoresearchConfig,
    monkeypatch,
) -> None:
    monkeypatch.delenv("MISSING_LLM_KEY", raising=False)
    live_config = replace(
        config,
        llm=replace(
            config.llm,
            mode="live",
            api_key_env="MISSING_LLM_KEY",
        ),
    )

    with pytest.raises(ConfigError, match="credential environment variable"):
        PipelineRunner(live_config)
