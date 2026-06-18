from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autoresearch.experiments.sandbox import SandboxResult
from autoresearch.experiments.spec import TrialSpec


class ExperimentBackend(Protocol):
    def run_trial(
        self,
        trial: TrialSpec,
        *,
        workspace: Path,
        runs_dir: Path,
        timeout_sec: int,
    ) -> SandboxResult:
        """Run one trial and return execution evidence."""
