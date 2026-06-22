from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxResult:
    trial_id: str
    status: str
    metrics_path: Path
    stdout: str
    stderr: str
    returncode: int
    evaluator_immutable: bool = True

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.returncode == 0
