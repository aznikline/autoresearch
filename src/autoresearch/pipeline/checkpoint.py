from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch.pipeline.stages import Stage, StageStatus


CHECKPOINT_FILE = "checkpoint.json"


def write_checkpoint(
    run_dir: Path,
    *,
    run_id: str,
    stage: Stage,
    status: StageStatus,
    message: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint: dict[str, Any] = {
        "run_id": run_id,
        "stage": int(stage),
        "stage_name": stage.name,
        "stage_slug": stage.slug,
        "status": status.value,
        "message": message,
    }
    if details:
        checkpoint.update(details)
    fd, tmp_name = tempfile.mkstemp(
        dir=run_dir, prefix="checkpoint-", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(checkpoint, handle, indent=2)
        Path(tmp_name).replace(run_dir / CHECKPOINT_FILE)
        event = {
            **checkpoint,
            "recorded_at": datetime.now(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
        }
        with (run_dir / "checkpoint_events.jsonl").open(
            "a", encoding="utf-8"
        ) as history:
            history.write(json.dumps(event, sort_keys=True) + "\n")
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return checkpoint


def read_checkpoint(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / CHECKPOINT_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": StageStatus.FAILED.value,
            "message": "checkpoint is not valid JSON",
        }
