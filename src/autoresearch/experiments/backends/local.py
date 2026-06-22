from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from autoresearch.experiments.sandbox import SandboxResult
from autoresearch.experiments.spec import TrialSpec
from autoresearch.experiments.validator import validate_experiment_script


@dataclass(frozen=True)
class LocalBackend:
    allowed_imports: tuple[str, ...] = ()

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
        validation = validate_experiment_script(
            script,
            workspace=workspace,
            allowed_imports=self.allowed_imports,
        )
        trial_dir = runs_dir / trial.trial_id
        metrics_path = trial_dir / "metrics.json"
        trial_dir.mkdir(parents=True, exist_ok=True)
        if not validation.ok:
            stderr = "\n".join(validation.issues)
            (trial_dir / "stdout.txt").write_text("", encoding="utf-8")
            (trial_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
            return SandboxResult(
                trial_id=trial.trial_id,
                status="invalid",
                metrics_path=metrics_path,
                stdout="",
                stderr=stderr,
                returncode=1,
            )

        evaluator_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
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
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            (trial_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
            (trial_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
            return SandboxResult(
                trial_id=trial.trial_id,
                status="timeout",
                metrics_path=metrics_path,
                stdout=stdout,
                stderr=stderr,
                returncode=124,
            )
        status = "ok" if completed.returncode == 0 and metrics_path.exists() else "failed"
        stderr = completed.stderr
        if hashlib.sha256(script.read_bytes()).hexdigest() != evaluator_sha256:
            status = "invalid"
            stderr = (stderr + "\nevaluator changed during execution").lstrip("\n")
            evaluator_immutable = False
        else:
            evaluator_immutable = True
        (trial_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (trial_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        return SandboxResult(
            trial_id=trial.trial_id,
            status=status,
            metrics_path=metrics_path,
            stdout=completed.stdout,
            stderr=stderr,
            returncode=completed.returncode,
            evaluator_immutable=evaluator_immutable,
        )
