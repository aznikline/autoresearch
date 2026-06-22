from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.stages import GATE_STAGES, Stage, StageStatus


DECISIONS_FILE = "decisions.jsonl"


class HITLError(ValueError):
    """Raised when a gate decision or resume transition is invalid."""


def record_decision(
    run_dir: Path,
    *,
    decision: str,
    reason: str,
    actor: str = "operator",
) -> dict[str, Any]:
    checkpoint = read_checkpoint(run_dir)
    if checkpoint is None:
        raise HITLError(f"run checkpoint not found: {run_dir}")
    if checkpoint.get("status") != StageStatus.PAUSED.value:
        raise HITLError("run is not paused at a gate")
    try:
        stage = Stage(int(checkpoint["stage"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HITLError("paused checkpoint has an invalid stage") from exc
    if stage not in GATE_STAGES:
        raise HITLError(f"stage is not an approval gate: {stage.slug}")
    normalized = decision.strip().lower()
    if normalized not in {"approve", "reject"}:
        raise HITLError("decision must be approve or reject")
    normalized_reason = reason.strip()
    normalized_actor = actor.strip()
    if not normalized_actor:
        raise HITLError("decision actor is required")
    if normalized == "reject" and not normalized_reason:
        raise HITLError("reason is required when rejecting a gate")
    if pending_decision(run_dir, stage) is not None:
        raise HITLError(f"a decision already exists for {stage.slug}; resume the run")
    alignment = _read_alignment(run_dir)
    record = {
        "run_id": str(checkpoint["run_id"]),
        "stage": int(stage),
        "stage_slug": stage.slug,
        "decision": normalized,
        "reason": normalized_reason,
        "actor": normalized_actor,
        "config_fingerprint": str(alignment.get("config_fingerprint", "")),
        "profile": str(alignment.get("profile", "")),
        "venue_contract": alignment.get("venue_contract", {}),
        "review_artifacts_sha256": review_artifacts_digest(run_dir, stage),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_record(run_dir, record)
    return record


def pending_decision(run_dir: Path, stage: Stage) -> dict[str, Any] | None:
    for record in reversed(read_decisions(run_dir)):
        if int(record.get("stage", -1)) != int(stage):
            continue
        if record.get("decision") == "consumed":
            return None
        if record.get("decision") in {"approve", "reject"}:
            return record
    return None


def consume_decision(run_dir: Path, decision: dict[str, Any]) -> dict[str, Any]:
    record = {
        "run_id": decision["run_id"],
        "stage": decision["stage"],
        "stage_slug": decision["stage_slug"],
        "decision": "consumed",
        "source_decision": decision["decision"],
        "actor": decision.get("actor", ""),
        "review_artifacts_sha256": decision.get("review_artifacts_sha256", ""),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_record(run_dir, record)
    return record


def read_decisions(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / DECISIONS_FILE
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HITLError(
                f"decision log is invalid JSON at line {line_number}: {path}"
            ) from exc
        if not isinstance(record, dict):
            raise HITLError(f"decision log entry is not an object at line {line_number}")
        records.append(record)
    return records


def _append_record(run_dir: Path, record: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / DECISIONS_FILE).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def review_artifacts_digest(run_dir: Path, gate_stage: Stage) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    for stage_dir in run_dir.glob("stage-*"):
        if not stage_dir.is_dir() or _stage_number(stage_dir.name) >= int(gate_stage):
            continue
        files.extend(path for path in stage_dir.rglob("*") if path.is_file())
    for path in sorted(files):
        relative = path.relative_to(run_dir).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _stage_number(directory_name: str) -> int:
    try:
        return int(directory_name.split("-", 2)[1])
    except (IndexError, ValueError):
        return 10_000


def _read_alignment(run_dir: Path) -> dict[str, Any]:
    try:
        data = json.loads((run_dir / "alignment.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HITLError("run alignment is missing or invalid") from exc
    if not isinstance(data, dict):
        raise HITLError("run alignment is missing or invalid")
    return data
