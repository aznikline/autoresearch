from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.pipeline.verification import verify_run


REQUIRED_PROFILES = (
    "foundation-models-llm",
    "computer-vision",
    "natural-language-processing",
    "data-management-mining",
)
_AUDIT_FIELDS = {
    "profile_id",
    "synthetic",
    "capability",
    "depth",
    "literature_mode",
    "experiment_mode",
    "llm_mode",
    "artifacts",
}
_ARTIFACT_FIELDS = {"path", "sha256"}


class ReferenceBundleError(ValueError):
    """Raised when a run cannot honestly become a real reference bundle."""


@dataclass(frozen=True)
class ReferenceBundleAudit:
    ok: bool
    blockers: tuple[str, ...]
    profiles: tuple[str, ...]


def export_reference_bundle(
    run_dir: str | Path,
    *,
    config: AutoresearchConfig,
    output_root: str | Path,
) -> Path:
    run = Path(run_dir).resolve()
    output_base = Path(output_root).resolve()
    profile = config.research.profile
    if profile not in REQUIRED_PROFILES:
        raise ReferenceBundleError(f"profile is not a required reference domain: {profile}")
    verification = verify_run(run, config=config)
    if verification["ok"] is not True:
        raise ReferenceBundleError(
            "run integrity verification failed: " + "; ".join(verification["issues"])
        )
    alignment = _read_object(run / "alignment.json", "run alignment")
    if alignment.get("profile") != profile:
        raise ReferenceBundleError("run profile does not match config profile")
    if config.research.depth != "top_venue" or alignment.get("depth") != "top_venue":
        raise ReferenceBundleError("reference bundle requires top_venue depth")
    quality = _read_object(
        run / "stage-12-final_verification_export/quality_report.json",
        "quality report",
    )
    if quality.get("evidence_complete") is not True:
        raise ReferenceBundleError("quality report is not evidence_complete")
    literature = alignment.get("literature")
    if not isinstance(literature, dict) or (
        literature.get("mode") != "live" or literature.get("synthetic") is not False
    ):
        raise ReferenceBundleError("reference bundle requires live literature")
    experiment = alignment.get("experiment")
    if not isinstance(experiment, dict) or (
        experiment.get("evidence_mode") != "real"
        or experiment.get("synthetic") is not False
    ):
        raise ReferenceBundleError("reference bundle requires a real experiment")
    llm = alignment.get("llm")
    if profile == "foundation-models-llm" and (
        not isinstance(llm, dict)
        or llm.get("mode") != "live"
        or llm.get("synthetic") is not False
    ):
        raise ReferenceBundleError("LLM reference bundle requires a live LLM provider")

    target = output_base / profile
    try:
        target.relative_to(run)
    except ValueError:
        pass
    else:
        raise ReferenceBundleError("reference output cannot be inside the source run")
    if target.exists():
        raise ReferenceBundleError(f"reference bundle already exists: {target}")
    files = [path for path in run.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    if total_bytes > config.runtime.max_artifact_bytes:
        raise ReferenceBundleError(
            f"reference bundle exceeds artifact budget: {total_bytes} > "
            f"{config.runtime.max_artifact_bytes}"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run, target / "run")
    artifacts = []
    for path in sorted((target / "run").rglob("*")):
        if path.is_file():
            artifacts.append(
                {
                    "path": path.relative_to(target).as_posix(),
                    "sha256": _file_hash(path),
                }
            )
    payload = {
        "profile_id": profile,
        "synthetic": False,
        "capability": "evidence_complete",
        "depth": "top_venue",
        "literature_mode": "live",
        "experiment_mode": "real",
        "llm_mode": "live" if profile == "foundation-models-llm" else "not_applicable",
        "artifacts": artifacts,
    }
    (target / "audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return target


def audit_reference_bundles(root: str | Path) -> ReferenceBundleAudit:
    reference_root = Path(root).resolve()
    blockers: list[str] = []
    profiles: list[str] = []
    seen: set[str] = set()

    for audit_path in sorted(reference_root.glob("*/audit.json")):
        bundle_root = audit_path.parent.resolve()
        try:
            data = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            blockers.append(f"invalid reference bundle {audit_path.parent.name}: {exc}")
            continue
        if not isinstance(data, dict):
            blockers.append(f"reference bundle {audit_path.parent.name} must be an object")
            continue

        profile = data.get("profile_id")
        label = profile if isinstance(profile, str) and profile else audit_path.parent.name
        unknown = sorted(set(data) - _AUDIT_FIELDS)
        missing = sorted(_AUDIT_FIELDS - set(data))
        if unknown:
            blockers.append(f"reference bundle {label} unknown fields: {', '.join(unknown)}")
        if missing:
            blockers.append(f"reference bundle {label} missing fields: {', '.join(missing)}")
        if profile not in REQUIRED_PROFILES:
            blockers.append(f"reference bundle has unsupported profile_id: {profile!r}")
            continue
        profiles.append(profile)
        if profile in seen:
            blockers.append(f"duplicate real reference bundle: {profile}")
        seen.add(profile)
        if data.get("synthetic") is not False:
            blockers.append(f"reference bundle {profile} is synthetic")
        if data.get("capability") != "evidence_complete":
            blockers.append(f"reference bundle {profile} is not evidence_complete")
        if data.get("depth") != "top_venue":
            blockers.append(f"reference bundle {profile} must use top_venue depth")
        if data.get("literature_mode") != "live":
            blockers.append(f"reference bundle {profile} did not use live literature")
        if data.get("experiment_mode") != "real":
            blockers.append(f"reference bundle {profile} did not run real experiments")
        required_llm_mode = "live" if profile == "foundation-models-llm" else "not_applicable"
        if data.get("llm_mode") != required_llm_mode:
            blockers.append(
                f"reference bundle {profile} llm_mode must be {required_llm_mode}"
            )
        blockers.extend(_audit_artifacts(bundle_root, profile, data.get("artifacts")))

    for profile in REQUIRED_PROFILES:
        if profile not in seen:
            blockers.append(f"missing real reference bundle: {profile}")
    return ReferenceBundleAudit(
        ok=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        profiles=tuple(profiles),
    )


def _audit_artifacts(bundle_root: Path, profile: str, raw: object) -> list[str]:
    blockers: list[str] = []
    if not isinstance(raw, list) or not raw:
        return [f"reference bundle {profile} has no artifacts"]
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            blockers.append(f"reference bundle {profile} artifact {index} must be an object")
            continue
        unknown = sorted(set(item) - _ARTIFACT_FIELDS)
        missing = sorted(_ARTIFACT_FIELDS - set(item))
        if unknown:
            blockers.append(
                f"reference bundle {profile} artifact {index} unknown fields: {', '.join(unknown)}"
            )
        if missing:
            blockers.append(
                f"reference bundle {profile} artifact {index} missing fields: {', '.join(missing)}"
            )
        relative = item.get("path")
        if not isinstance(relative, str) or not relative:
            blockers.append(f"reference bundle {profile} artifact {index} has invalid path")
            continue
        if relative in seen:
            blockers.append(f"reference bundle {profile} has duplicate artifact: {relative}")
        seen.add(relative)
        candidate = (bundle_root / relative).resolve()
        try:
            candidate.relative_to(bundle_root)
        except ValueError:
            blockers.append(f"reference bundle {profile} artifact path escapes bundle: {relative}")
            continue
        expected = item.get("sha256")
        actual = _file_hash(candidate)
        if not isinstance(expected, str) or actual != expected:
            blockers.append(f"reference bundle {profile} artifact hash mismatch: {relative}")
    return blockers


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceBundleError(f"{label} is missing or invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ReferenceBundleError(f"{label} must be an object")
    return data
