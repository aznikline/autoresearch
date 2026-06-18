from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from autoresearch.experiments.sandbox import SandboxResult
from autoresearch.experiments.spec import TrialSpec
from autoresearch.experiments.validator import validate_experiment_script


class LocalBackend:
    def run_trial(
        self,
        trial: TrialSpec,
        *,
        workspace: Path,
        runs_dir: Path,
        timeout_sec: int,
    ) -> SandboxResult:
        workspace = workspace.resolve()
        runs_dir = runs_dir.resolve()
        script = workspace / "experiment.py"
        validation = validate_experiment_script(script, workspace=workspace)
        trial_dir = runs_dir / trial.trial_id
        metrics_path = trial_dir / "metrics.json"
        if not validation.ok:
            return SandboxResult(
                trial_id=trial.trial_id,
                status="invalid",
                metrics_path=metrics_path,
                stdout="",
                stderr="\n".join(validation.issues),
                returncode=1,
            )

        trial_dir.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--trial",
                    trial.trial_id,
                    "--output",
                    str(metrics_path),
                ],
                cwd=workspace,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                trial_id=trial.trial_id,
                status="timeout",
                metrics_path=metrics_path,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                returncode=124,
            )
        status = "ok" if completed.returncode == 0 and metrics_path.exists() else "failed"
        return SandboxResult(
            trial_id=trial.trial_id,
            status=status,
            metrics_path=metrics_path,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
