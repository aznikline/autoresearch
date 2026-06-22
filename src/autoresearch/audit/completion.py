from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from autoresearch.audit.reference import audit_reference_bundles
from autoresearch.audit.venues import audit_venue_materials


REQUIREMENT_IDS = tuple(f"MD-{index:03d}" for index in range(1, 16))
_PROVIDER_IDENTITY_REQUIRED = frozenset({"MD-004", "MD-013"})
_ATTESTATION_REQUIRED_FIELDS = {
    "requirement_id",
    "status",
    "synthetic",
    "credentialed",
    "spec_sha256",
    "plan_sha256",
    "artifacts",
}
_ATTESTATION_FIELDS = _ATTESTATION_REQUIRED_FIELDS | {"local_model_attested"}
_ARTIFACT_FIELDS = {"path", "sha256"}


@dataclass(frozen=True)
class RequirementAudit:
    requirement_id: str
    passed: bool
    blockers: tuple[str, ...]
    artifacts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "passed": self.passed,
            "blockers": list(self.blockers),
            "artifacts": list(self.artifacts),
        }


@dataclass(frozen=True)
class CompletionAudit:
    complete: bool
    spec_sha256: str
    plan_sha256: str
    requirements: dict[str, RequirementAudit]

    @property
    def blocked_requirements(self) -> tuple[str, ...]:
        return tuple(
            requirement_id
            for requirement_id, result in self.requirements.items()
            if not result.passed
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "spec_sha256": self.spec_sha256,
            "plan_sha256": self.plan_sha256,
            "blocked_requirements": list(self.blocked_requirements),
            "requirements": {
                key: value.to_dict() for key, value in self.requirements.items()
            },
        }


def audit_repository(root: str | Path) -> CompletionAudit:
    repository = Path(root).resolve()
    spec_path = repository / "docs/specs/multidomain-top-venue-autoresearch.md"
    plan_path = repository / "docs/plans/2026-06-18-002-feat-multidomain-top-venue-autoresearch-plan.md"
    spec_sha256 = _file_hash(spec_path)
    plan_sha256 = _file_hash(plan_path)
    static = _static_blockers(repository)
    requirements: dict[str, RequirementAudit] = {}
    for requirement_id in REQUIREMENT_IDS:
        blockers = list(static.get(requirement_id, ()))
        artifacts: tuple[str, ...] = ()
        attestation_path = (
            repository / "docs" / "audits" / "evidence" / f"{requirement_id}.json"
        )
        if not attestation_path.is_file():
            blockers.append("current direct attestation is missing")
        else:
            attestation_blockers, artifacts = _validate_attestation(
                repository,
                requirement_id,
                attestation_path,
                spec_sha256=spec_sha256,
                plan_sha256=plan_sha256,
            )
            blockers.extend(attestation_blockers)
        requirements[requirement_id] = RequirementAudit(
            requirement_id=requirement_id,
            passed=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            artifacts=artifacts,
        )
    return CompletionAudit(
        complete=all(result.passed for result in requirements.values()),
        spec_sha256=spec_sha256,
        plan_sha256=plan_sha256,
        requirements=requirements,
    )


def _validate_attestation(
    root: Path,
    requirement_id: str,
    path: Path,
    spec_sha256: str,
    plan_sha256: str,
) -> tuple[list[str], tuple[str, ...]]:
    blockers: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid attestation: {exc}"], ()
    if not isinstance(data, dict):
        return ["attestation must be an object"], ()
    unknown = sorted(set(data) - _ATTESTATION_FIELDS)
    if unknown:
        blockers.append("attestation unknown fields: " + ", ".join(unknown))
    missing = sorted(_ATTESTATION_REQUIRED_FIELDS - set(data))
    if missing:
        blockers.append("attestation missing fields: " + ", ".join(missing))
    if data.get("requirement_id") != requirement_id:
        blockers.append("attestation requirement_id mismatch")
    if data.get("status") != "passed":
        blockers.append("attestation status is not passed")
    if data.get("spec_sha256") != spec_sha256:
        blockers.append("attestation spec hash mismatch")
    if data.get("plan_sha256") != plan_sha256:
        blockers.append("attestation plan hash mismatch")
    if data.get("synthetic") is True:
        blockers.append("synthetic evidence is not accepted")
    if not isinstance(data.get("synthetic"), bool):
        blockers.append("attestation synthetic must be a boolean")
    if not isinstance(data.get("credentialed"), bool):
        blockers.append("attestation credentialed must be a boolean")
    if (
        requirement_id in _PROVIDER_IDENTITY_REQUIRED
        and data.get("credentialed") is not True
        and data.get("local_model_attested") is not True
    ):
        blockers.append(
            "authenticated remote or digest-attested local provider evidence is required"
        )
    raw_artifacts = data.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        blockers.append("attestation artifacts are missing")
        return blockers, ()
    artifact_paths: list[str] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(raw_artifacts):
        if not isinstance(item, dict):
            blockers.append(f"artifact {index} must be an object")
            continue
        artifact_unknown = sorted(set(item) - _ARTIFACT_FIELDS)
        if artifact_unknown:
            blockers.append(
                f"artifact {index} unknown fields: {', '.join(artifact_unknown)}"
            )
        relative = str(item.get("path", ""))
        if relative in seen_paths:
            blockers.append(f"duplicate artifact path: {relative}")
        seen_paths.add(relative)
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            blockers.append(f"artifact path escapes repository: {relative}")
            continue
        artifact_paths.append(relative)
        expected = str(item.get("sha256", ""))
        actual = _file_hash(candidate)
        if not actual or actual != expected:
            blockers.append(f"artifact hash mismatch: {relative}")
    return blockers, tuple(artifact_paths)


def _static_blockers(root: Path) -> dict[str, tuple[str, ...]]:
    blockers: dict[str, tuple[str, ...]] = {}
    profiles = list((root / "src/autoresearch/profiles").glob("*.yaml"))
    if len(profiles) != 5:
        blockers["MD-001"] = (f"expected 5 profiles, found {len(profiles)}",)
    venue_paths = list((root / "src/autoresearch/venues").glob("*/*/*.yaml"))
    venue_materials = audit_venue_materials(root)
    if len(venue_paths) != 17 or not venue_materials.source_ok:
        blockers["MD-002"] = (
            f"venue registry has {len(venue_paths)} contracts",
            *venue_materials.source_blockers,
        )
    if not venue_materials.template_ok:
        blockers["MD-009"] = venue_materials.template_blockers
    reference_audit = audit_reference_bundles(root / "docs/audits/reference-runs")
    if not reference_audit.ok:
        blockers["MD-013"] = reference_audit.blockers
    return blockers


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
