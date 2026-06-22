from __future__ import annotations

import json
import hashlib
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch.config import AutoresearchConfig, ConfigError
from autoresearch.capabilities import CapabilityAssessment, assess_capability
from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.adapters.llm.openai_compatible import OpenAICompatibleProvider
from autoresearch.domains.profile import load_profile
from autoresearch.hitl.session import (
    HITLError,
    consume_decision,
    pending_decision,
    review_artifacts_digest,
)
from autoresearch.memory.store import MemoryStore
from autoresearch.pipeline.checkpoint import read_checkpoint, write_checkpoint
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.executor import StageResult, execute_stage
from autoresearch.pipeline.stages import (
    GATE_STAGES,
    ROLLBACK_STAGE,
    STAGE_SEQUENCE,
    Stage,
    StageStatus,
)
from autoresearch.skills.harness import SkillHarness
from autoresearch.venues.registry import VenueRegistry
from autoresearch.venues.schema import VenueContract, VenueContractError


class PipelineRunner:
    def __init__(self, config: AutoresearchConfig) -> None:
        self.config = config
        if config.experiment.mode != "local":
            raise ConfigError(
                f"experiment backend is not implemented: {config.experiment.mode}"
            )
        if config.experiment.code_trust == "untrusted":
            raise ConfigError(
                "untrusted code requires a container or equivalent isolation backend"
            )
        if config.experiment.evidence_mode == "real":
            source = Path(config.experiment.workspace_source).expanduser()
            if not config.experiment.workspace_source or not source.is_dir():
                raise ConfigError(
                    "experiment.workspace_source must be an existing directory "
                    "for real evidence mode"
                )
            if not (source / "experiment.py").is_file():
                raise ConfigError("experiment.workspace_source requires experiment.py")
            if any(path.is_symlink() for path in source.rglob("*")):
                raise ConfigError("experiment.workspace_source cannot contain symlinks")
        if config.llm.mode == "live":
            if config.llm.provider != "openai-compatible":
                raise ConfigError(f"unsupported live LLM provider: {config.llm.provider}")
            if (
                config.llm.auth_mode == "bearer_env"
                and not os.environ.get(config.llm.api_key_env, "").strip()
            ):
                raise ConfigError(
                    "LLM credential environment variable is not set: "
                    f"{config.llm.api_key_env}"
                )
        self.profile = load_profile(config.research.profile)
        self.skill_harness = (
            SkillHarness.from_directories(
                tuple(Path(path).expanduser() for path in config.skills.directories),
                max_per_stage=config.skills.max_per_stage,
            )
            if config.skills.enabled
            else SkillHarness.disabled()
        )
        if config.skills.enabled and not self.skill_harness.supports(
            profile_id=self.profile.profile_id,
            depth=config.research.depth,
        ):
            raise ConfigError(
                f"no compatible project skill for profile={self.profile.profile_id} "
                f"depth={config.research.depth}"
            )
        registry = VenueRegistry.load(Path(__file__).resolve().parents[1] / "venues")
        try:
            if config.research.venue_year == "latest_verified":
                self.venue_contract = registry.resolve(
                    config.research.venue_id,
                    year="latest_verified",
                    track=config.research.venue_track,
                    profile_id=self.profile.profile_id,
                    on=date.today(),
                )
            else:
                self.venue_contract = registry.select(
                    config.research.venue_id,
                    year=config.research.venue_year,
                    track=config.research.venue_track,
                    profile_id=self.profile.profile_id,
                )
        except VenueContractError as exc:
            raise ConfigError(str(exc)) from exc
        self.capability = _contract_capability(self.venue_contract)
        project_slug = "".join(
            character if character.isalnum() or character in "-_" else "-"
            for character in config.project.name.lower()
        ).strip("-") or "project"
        self.memory_store = MemoryStore(
            Path(config.runtime.artifacts_root) / "_memory" / f"{project_slug}.jsonl"
        )

    def run(
        self,
        *,
        topic: str,
        run_id: str | None = None,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        resolved_topic = topic.strip()
        if not resolved_topic:
            return {
                "status": StageStatus.FAILED.value,
                "message": "research topic is required",
            }

        active_run_id = run_id or _new_run_id()
        run_dir = Path(self.config.runtime.artifacts_root) / active_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        alignment = self._alignment_summary(resolved_topic)
        (run_dir / "alignment.json").write_text(
            json.dumps(alignment, indent=2),
            encoding="utf-8",
        )

        return self._execute_from(
            run_dir=run_dir,
            run_id=active_run_id,
            topic=resolved_topic,
            start_stage=STAGE_SEQUENCE[0],
            auto_approve=auto_approve,
        )

    def plan(self, *, topic: str) -> dict[str, Any]:
        resolved_topic = topic.strip()
        if not resolved_topic:
            raise ConfigError("research topic is required")
        alignment = self._alignment_summary(resolved_topic)
        return {
            "topic": resolved_topic,
            "profile": self.profile.profile_id,
            "venue_contract": alignment["venue_contract"],
            "capability": alignment["capability"],
            "stages": [
                {
                    "number": int(stage),
                    "slug": stage.slug,
                    "approval_gate": stage in GATE_STAGES,
                    "outputs": list(contract_for(stage).output_files),
                }
                for stage in STAGE_SEQUENCE
            ],
        }

    def resume(self, run_dir: Path, *, actor: str = "operator") -> dict[str, Any]:
        checkpoint = read_checkpoint(run_dir)
        if checkpoint is None:
            raise HITLError(f"run checkpoint not found: {run_dir}")
        if checkpoint.get("status") != StageStatus.PAUSED.value:
            raise HITLError("run is not paused; only paused runs can be resumed")
        try:
            gate_stage = Stage(int(checkpoint["stage"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise HITLError("paused checkpoint has an invalid stage") from exc
        if gate_stage not in GATE_STAGES:
            raise HITLError(f"paused stage is not an approval gate: {gate_stage.slug}")
        decision = pending_decision(run_dir, gate_stage)
        if decision is None:
            raise HITLError(
                f"approve or reject {gate_stage.slug} before resuming the run"
            )
        if decision.get("actor") != actor.strip():
            raise HITLError("decision actor does not match resume actor")
        if decision.get("run_id") != str(checkpoint.get("run_id", "")):
            raise HITLError("decision run does not match checkpoint run")
        alignment = _read_alignment(run_dir)
        if alignment.get("config_fingerprint") != self._config_fingerprint():
            raise HITLError(
                "resume config does not match the config used to create this run"
            )
        if decision.get("config_fingerprint") != alignment.get("config_fingerprint"):
            raise HITLError("gate decision config fingerprint does not match alignment")
        if decision.get("profile") != alignment.get("profile"):
            raise HITLError("gate decision profile does not match alignment")
        if decision.get("venue_contract") != alignment.get("venue_contract"):
            raise HITLError("gate decision venue contract does not match alignment")
        if decision.get("review_artifacts_sha256") != review_artifacts_digest(
            run_dir, gate_stage
        ):
            raise HITLError("reviewed artifacts changed after the gate decision")
        start_stage = (
            gate_stage
            if decision["decision"] == "approve"
            else ROLLBACK_STAGE[gate_stage]
        )
        approved_stage = gate_stage if decision["decision"] == "approve" else None
        if decision["decision"] == "reject":
            _preserve_rejected_artifacts(
                run_dir,
                stage=start_stage,
                decision=decision,
            )
            self.memory_store.append_human_lesson(
                project=self.config.project.name,
                run_id=str(checkpoint["run_id"]),
                stage=gate_stage.slug,
                lesson=str(decision["reason"]),
                topic=str(alignment["topic"]),
                evidence_ref=(
                    "sha256:" + str(decision["review_artifacts_sha256"])
                ),
            )
        consume_decision(run_dir, decision)
        return self._execute_from(
            run_dir=run_dir,
            run_id=str(checkpoint["run_id"]),
            topic=str(alignment["topic"]),
            start_stage=start_stage,
            approved_stage=approved_stage,
        )

    def cancel(
        self,
        run_dir: Path,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        return cancel_run(run_dir, actor=actor, reason=reason)

    def recover(
        self,
        run_dir: Path,
        *,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        checkpoint = read_checkpoint(run_dir)
        if checkpoint is None:
            raise HITLError(f"run checkpoint not found: {run_dir}")
        status = checkpoint.get("status")
        if status not in {StageStatus.RUNNING.value, StageStatus.FAILED.value}:
            raise HITLError(
                f"run is not recoverable from status {status!r}; "
                "use resume for paused approval gates"
            )
        try:
            stage = Stage(int(checkpoint["stage"]))
            run_id = str(checkpoint["run_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HITLError("recoverable checkpoint has invalid stage or run ID") from exc
        alignment = _read_alignment(run_dir)
        if alignment.get("config_fingerprint") != self._config_fingerprint():
            raise HITLError(
                "recover config does not match the config used to create this run"
            )
        return self._execute_from(
            run_dir=run_dir,
            run_id=run_id,
            topic=str(alignment["topic"]),
            start_stage=stage,
            auto_approve=auto_approve,
        )

    def _execute_from(
        self,
        *,
        run_dir: Path,
        run_id: str,
        topic: str,
        start_stage: Stage,
        auto_approve: bool = False,
        approved_stage: Stage | None = None,
    ) -> dict[str, Any]:
        alignment = _read_alignment(run_dir)
        start_index = STAGE_SEQUENCE.index(start_stage)
        llm_provider = self._llm_provider(run_dir)
        prior_lessons = self.memory_store.render(topic=topic)

        results: list[StageResult] = []
        for stage in STAGE_SEQUENCE[start_index:]:
            if (
                stage in GATE_STAGES
                and not auto_approve
                and stage is not approved_stage
            ):
                checkpoint = write_checkpoint(
                    run_dir,
                    run_id=run_id,
                    stage=stage,
                    status=StageStatus.PAUSED,
                    message=f"approval required before {stage.slug}",
                    details={
                        "context_summary": (
                            f"Review declared inputs before running {stage.slug}."
                        ),
                        "expected_artifacts": list(contract_for(stage).input_files),
                        "allowed_actions": ["approve", "reject"],
                    },
                )
                return {
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": StageStatus.PAUSED.value,
                    "checkpoint": checkpoint,
                    "stages_completed": int(stage) - 1,
                    "alignment": alignment,
                }

            write_checkpoint(
                run_dir,
                run_id=run_id,
                stage=stage,
                status=StageStatus.RUNNING,
                message=f"running {stage.slug}",
            )
            result = execute_stage(
                stage,
                run_dir=run_dir,
                config=self.config,
                topic=topic,
                profile=self.profile,
                skill_harness=self.skill_harness,
                llm_provider=llm_provider,
                venue_guidance=(
                    f"Venue contract {self.venue_contract.venue_id}/"
                    f"{self.venue_contract.year}/{self.venue_contract.track} is "
                    f"{self.venue_contract.status.value}. It cannot certify readiness."
                ),
                venue_contract=self.venue_contract,
                prior_lessons=prior_lessons,
            )
            results.append(result)
            artifact_bytes = _artifact_bytes(run_dir)
            if artifact_bytes > self.config.runtime.max_artifact_bytes:
                message = (
                    "artifact budget exhausted: "
                    f"{artifact_bytes}/{self.config.runtime.max_artifact_bytes} bytes"
                )
                self.memory_store.append_event(
                    project=self.config.project.name,
                    run_id=run_id,
                    stage=stage.slug,
                    lesson=message,
                    topic=topic,
                    source="budget_pause",
                    evidence_ref=f"checkpoint:{run_id}:{stage.slug}",
                )
                checkpoint = write_checkpoint(
                    run_dir,
                    run_id=run_id,
                    stage=stage,
                    status=StageStatus.PAUSED,
                    message=message,
                    details={
                        "pause_kind": "artifact_budget",
                        "observed_bytes": artifact_bytes,
                        "max_artifact_bytes": self.config.runtime.max_artifact_bytes,
                        "allowed_actions": ["cancel"],
                    },
                )
                return {
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": StageStatus.PAUSED.value,
                    "checkpoint": checkpoint,
                    "stages_completed": int(stage),
                    "alignment": alignment,
                }
            if (
                stage is Stage.FINAL_VERIFICATION_EXPORT
                and result.status is StageStatus.DONE
            ):
                quality_path = (
                    run_dir
                    / "stage-12-final_verification_export"
                    / "quality_report.json"
                )
                quality = json.loads(quality_path.read_text(encoding="utf-8"))
                if quality.get("submission_ready") is not True:
                    blocker_count = len(quality.get("blocking_issues", ()))
                    self.memory_store.append_event(
                        project=self.config.project.name,
                        run_id=run_id,
                        stage=stage.slug,
                        lesson=(
                            "submission readiness blocked by "
                            f"{blocker_count} verifier issues"
                        ),
                        topic=topic,
                        source="verifier_failure",
                        evidence_ref=(
                            "sha256:" + hashlib.sha256(quality_path.read_bytes()).hexdigest()
                        ),
                    )
            write_checkpoint(
                run_dir,
                run_id=run_id,
                stage=stage,
                status=result.status,
                message=result.message,
            )
            if result.status is StageStatus.FAILED:
                self.memory_store.append_event(
                    project=self.config.project.name,
                    run_id=run_id,
                    stage=stage.slug,
                    lesson=result.message or "stage failed",
                    topic=topic,
                    source="stage_failure",
                    evidence_ref=f"checkpoint:{run_id}:{stage.slug}",
                )
                return {
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": StageStatus.FAILED.value,
                    "failed_stage": stage.slug,
                    "message": result.message,
                    "stages_completed": int(stage) - 1,
                    "alignment": alignment,
                }

        return {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": StageStatus.DONE.value,
            "stages_completed": len(STAGE_SEQUENCE),
            "alignment": alignment,
        }

    def _alignment_summary(self, topic: str) -> dict[str, Any]:
        return {
            "topic": topic,
            "profile": self.profile.profile_id,
            "depth": self.config.research.depth,
            "target_venue_family": list(self.config.research.target_venues),
            "primary_claim_type": self.config.research.primary_claim_type,
            "resource_budget": {
                "time_budget_sec": self.config.experiment.time_budget_sec,
                "max_iterations": self.config.runtime.max_iterations,
                "total_compute_budget": self.config.experiment.total_compute_budget,
            },
            "threshold_waivers": [
                {
                    "requirement": waiver.requirement,
                    "affected_claim": waiver.affected_claim,
                    "reason": waiver.reason,
                    "alternative_test": waiver.alternative_test,
                }
                for waiver in self.config.research.threshold_waivers
            ],
            "config_fingerprint": self._config_fingerprint(),
            "venue_contract": {
                "venue_id": self.venue_contract.venue_id,
                "display_name": self.venue_contract.display_name,
                "year": self.venue_contract.year,
                "track": self.venue_contract.track,
                "status": self.venue_contract.status.value,
                "source_path": self.venue_contract.source_path.as_posix(),
            },
            "capability": {
                "level": self.capability.level.name.lower(),
                "blockers": list(self.capability.blockers),
            },
            "llm": {
                "mode": self.config.llm.mode,
                "provider": self.config.llm.provider,
                "model": self.config.llm.primary_model,
                "synthetic": self.config.llm.mode == "synthetic",
            },
            "literature": {
                "mode": self.config.literature.mode,
                "sources": list(self.config.literature.sources),
                "synthetic": self.config.literature.mode == "synthetic",
            },
            "experiment": {
                "mode": self.config.experiment.mode,
                "evidence_mode": self.config.experiment.evidence_mode,
                "synthetic": self.config.experiment.evidence_mode == "synthetic",
                "workspace_source": self.config.experiment.workspace_source,
                "allowed_imports": list(self.config.experiment.allowed_imports),
            },
            "memory": {
                "human_lesson_count": len(self.memory_store.read()),
            },
        }

    def _config_fingerprint(self) -> str:
        payload = json.dumps(
            self.config.redacted_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _llm_provider(self, run_dir: Path) -> LLMProvider | None:
        if self.config.llm.mode == "synthetic":
            return None
        if self.config.llm.provider != "openai-compatible":
            raise ConfigError(f"unsupported live LLM provider: {self.config.llm.provider}")
        return OpenAICompatibleProvider(
            base_url=self.config.llm.base_url,
            allowed_hosts=self.config.llm.allowed_hosts,
            api_key_env=self.config.llm.api_key_env,
            model=self.config.llm.primary_model,
            audit_dir=run_dir / "llm",
            max_requests=self.config.llm.max_requests,
            auth_mode=self.config.llm.auth_mode,
            max_retries=self.config.llm.max_retries,
            input_cost_per_million=self.config.llm.input_cost_per_million,
            output_cost_per_million=self.config.llm.output_cost_per_million,
            timeout_sec=self.config.llm.timeout_sec,
        )


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")


def _read_alignment(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "alignment.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HITLError(f"run alignment not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HITLError(f"run alignment is not valid JSON: {path}") from exc
    if not isinstance(data, dict) or not str(data.get("topic", "")).strip():
        raise HITLError(f"run alignment does not contain a topic: {path}")
    return data


def _contract_capability(contract: VenueContract) -> CapabilityAssessment:
    verified = contract.is_verified(on=date.today())
    blockers = () if verified else (
        f"venue contract {contract.venue_id}/{contract.year}/{contract.track} "
        f"is {contract.status.value}, not current verified",
    )
    return assess_capability(
        contract_supported=verified,
        integration_validated=False,
        evidence_complete=False,
        submission_ready=False,
        blockers=blockers or ("real integration evidence missing",),
    )


def cancel_run(run_dir: Path, *, actor: str, reason: str) -> dict[str, Any]:
    normalized_actor = actor.strip()
    normalized_reason = reason.strip()
    if not normalized_actor or not normalized_reason:
        raise HITLError("cancellation actor and reason are required")
    checkpoint = read_checkpoint(run_dir)
    if checkpoint is None:
        raise HITLError(f"run checkpoint not found: {run_dir}")
    if checkpoint.get("status") in {
        StageStatus.DONE.value,
        StageStatus.CANCELLED.value,
    }:
        raise HITLError(f"run cannot be cancelled from {checkpoint.get('status')}")
    try:
        stage = Stage(int(checkpoint["stage"]))
        run_id = str(checkpoint["run_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HITLError("checkpoint has invalid stage or run ID") from exc
    cancelled = write_checkpoint(
        run_dir,
        run_id=run_id,
        stage=stage,
        status=StageStatus.CANCELLED,
        message="run cancelled",
        details={"actor": normalized_actor, "reason": normalized_reason},
    )
    return {"run_id": run_id, "run_dir": str(run_dir), **cancelled}


def _preserve_rejected_artifacts(
    run_dir: Path,
    *,
    stage: Stage,
    decision: dict[str, Any],
) -> None:
    source = run_dir / f"stage-{int(stage):02d}-{stage.slug}"
    if not source.is_dir():
        return
    recorded_at = str(decision.get("recorded_at", "unknown")).replace(":", "-")
    destination = run_dir / "rejected_artifacts" / recorded_at / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=False)


def _artifact_bytes(run_dir: Path) -> int:
    return sum(path.stat().st_size for path in run_dir.rglob("*") if path.is_file())
