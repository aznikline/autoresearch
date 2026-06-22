from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoresearch.pipeline.stages import Stage


def stage_dir(run_dir: Path, stage: Stage) -> Path:
    return run_dir / f"stage-{int(stage):02d}-{stage.slug}"


def artifact_exists(run_dir: Path, stage: Stage, relative_path: str) -> bool:
    path = stage_dir(run_dir, stage) / relative_path
    if relative_path.endswith("/"):
        return path.is_dir()
    return path.is_file()


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
