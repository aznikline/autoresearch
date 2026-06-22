from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from autoresearch.venues.registry import VenueRegistry
from autoresearch.venues.schema import VenueStatus


_MANIFEST_FIELDS = {"venue_id", "year", "track", "sources", "template"}
_SOURCE_FIELDS = {"url", "path", "sha256"}
_TEMPLATE_FIELDS = {"identity", "source_url", "path", "sha256"}


@dataclass(frozen=True)
class VenueMaterialAudit:
    source_blockers: tuple[str, ...]
    template_blockers: tuple[str, ...]

    @property
    def source_ok(self) -> bool:
        return not self.source_blockers

    @property
    def template_ok(self) -> bool:
        return not self.template_blockers


def audit_venue_materials(root: str | Path) -> VenueMaterialAudit:
    repository = Path(root).resolve()
    registry = VenueRegistry.load(repository / "src/autoresearch/venues")
    source_blockers: list[str] = []
    template_blockers: list[str] = []
    for contract in registry.contracts:
        label = f"{contract.venue_id}/{contract.year}/{contract.track}"
        if contract.status is not VenueStatus.VERIFIED:
            source_blockers.append(f"venue contract {label} is not verified")
            template_blockers.append(f"venue contract {label} is not verified")
            continue
        manifest_root = (
            repository
            / "docs/audits/venue-sources"
            / contract.venue_id
            / str(contract.year)
            / contract.track
        ).resolve()
        manifest_path = manifest_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            message = f"venue material manifest {label} is missing or invalid: {exc}"
            source_blockers.append(message)
            template_blockers.append(message)
            continue
        if not isinstance(manifest, dict):
            message = f"venue material manifest {label} must be an object"
            source_blockers.append(message)
            template_blockers.append(message)
            continue
        unknown = sorted(set(manifest) - _MANIFEST_FIELDS)
        missing = sorted(_MANIFEST_FIELDS - set(manifest))
        if unknown or missing:
            detail = []
            if unknown:
                detail.append("unknown fields: " + ", ".join(unknown))
            if missing:
                detail.append("missing fields: " + ", ".join(missing))
            message = f"venue material manifest {label} " + "; ".join(detail)
            source_blockers.append(message)
            template_blockers.append(message)
        if (
            manifest.get("venue_id"),
            manifest.get("year"),
            manifest.get("track"),
        ) != contract.key:
            message = f"venue material manifest identity mismatch: {label}"
            source_blockers.append(message)
            template_blockers.append(message)
        source_blockers.extend(
            _audit_sources(manifest_root, label, manifest.get("sources"), contract)
        )
        template_blockers.extend(
            _audit_template(repository, label, manifest.get("template"), contract)
        )
    return VenueMaterialAudit(
        source_blockers=tuple(dict.fromkeys(source_blockers)),
        template_blockers=tuple(dict.fromkeys(template_blockers)),
    )


def _audit_sources(manifest_root: Path, label: str, raw: object, contract: object) -> list[str]:
    blockers: list[str] = []
    if not isinstance(raw, list) or not raw:
        return [f"venue material manifest {label} has no source snapshots"]
    expected = [(item.url, item.sha256) for item in contract.official_sources]
    actual: list[tuple[object, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            blockers.append(f"venue source {label}[{index}] must be an object")
            continue
        unknown = sorted(set(item) - _SOURCE_FIELDS)
        missing = sorted(_SOURCE_FIELDS - set(item))
        if unknown or missing:
            blockers.append(f"venue source {label}[{index}] has invalid fields")
        actual.append((item.get("url"), item.get("sha256")))
        relative = item.get("path")
        if not isinstance(relative, str) or not relative:
            blockers.append(f"venue source {label}[{index}] has invalid path")
            continue
        candidate = (manifest_root / relative).resolve()
        try:
            candidate.relative_to(manifest_root)
        except ValueError:
            blockers.append(f"venue source {label}[{index}] path escapes manifest directory")
            continue
        if _file_hash(candidate) != item.get("sha256"):
            blockers.append(f"venue source hash mismatch: {label}[{index}]")
    if actual != expected:
        blockers.append(f"venue source contract mismatch: {label}")
    return blockers


def _audit_template(repository: Path, label: str, raw: object, contract: object) -> list[str]:
    if not isinstance(raw, dict):
        return [f"venue template {label} must be an object"]
    blockers: list[str] = []
    unknown = sorted(set(raw) - _TEMPLATE_FIELDS)
    missing = sorted(_TEMPLATE_FIELDS - set(raw))
    if unknown or missing:
        blockers.append(f"venue template {label} has invalid fields")
    if (
        raw.get("identity"),
        raw.get("source_url"),
        raw.get("sha256"),
    ) != (
        contract.template.identity,
        contract.template.source_url,
        contract.template.sha256,
    ):
        blockers.append(f"venue template contract mismatch: {label}")
    relative = raw.get("path")
    if not isinstance(relative, str) or not relative:
        blockers.append(f"venue template path is invalid: {label}")
        return blockers
    candidate = (repository / relative).resolve()
    allowed_root = (
        repository / "src/autoresearch/templates" / contract.venue_id / str(contract.year)
    ).resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        blockers.append(f"venue template path escapes registered directory: {label}")
        return blockers
    if _file_hash(candidate) != raw.get("sha256"):
        blockers.append(f"venue template hash mismatch: {label}")
    return blockers


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
