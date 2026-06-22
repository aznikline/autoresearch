from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class VenueContractError(ValueError):
    """Raised when a venue contract is missing, malformed, or unusable."""


class VenueStatus(str, Enum):
    DRAFT = "draft"
    VERIFIED = "verified"
    STALE = "stale"
    RETIRED = "retired"


@dataclass(frozen=True)
class OfficialSource:
    url: str
    retrieved_at: date | None
    sha256: str | None


@dataclass(frozen=True)
class VenueTemplate:
    identity: str
    source_url: str
    sha256: str | None


@dataclass(frozen=True)
class VenuePolicy:
    anonymity: str
    page_limit: int | None
    supplement_allowed: bool | None
    checklist_required: bool | None
    checklist_delivery: str
    ethics_required: bool | None
    limitations_required: bool | None
    artifact_policy: str
    required_sections: tuple[str, ...]

    def is_resolved(self) -> bool:
        return (
            self.anonymity != "unknown"
            and self.artifact_policy != "unknown"
            and self.checklist_delivery != "unknown"
            and all(
                value is not None
                for value in (
                    self.supplement_allowed,
                    self.checklist_required,
                    self.ethics_required,
                    self.limitations_required,
                )
            )
        )


@dataclass(frozen=True)
class VenueContract:
    schema_version: int
    venue_id: str
    display_name: str
    year: int
    track: str
    status: VenueStatus
    compatible_profiles: tuple[str, ...]
    official_sources: tuple[OfficialSource, ...]
    template: VenueTemplate
    policy: VenuePolicy
    valid_until: date | None
    source_path: Path

    @property
    def key(self) -> tuple[str, int, str]:
        return (self.venue_id, self.year, self.track)

    def compatible_with(self, profile_id: str) -> bool:
        return profile_id in self.compatible_profiles

    def is_verified(self, *, on: date) -> bool:
        return (
            self.status is VenueStatus.VERIFIED
            and self.valid_until is not None
            and on <= self.valid_until
        )


_ROOT_FIELDS = {
    "schema_version",
    "venue_id",
    "display_name",
    "year",
    "track",
    "status",
    "compatible_profiles",
    "official_sources",
    "template",
    "policy",
    "valid_until",
}
_SOURCE_FIELDS = {"url", "retrieved_at", "sha256"}
_TEMPLATE_FIELDS = {"identity", "source_url", "sha256"}
_POLICY_FIELDS = {
    "anonymity",
    "page_limit",
    "supplement_allowed",
    "checklist_required",
    "checklist_delivery",
    "ethics_required",
    "limitations_required",
    "artifact_policy",
    "required_sections",
}
_ANONYMITY = {"double_blind", "single_blind", "open", "none", "unknown"}
_ARTIFACT_POLICIES = {"none", "optional", "encouraged", "required", "unknown"}
_CHECKLIST_DELIVERY = {"paper", "submission_form", "none", "unknown"}
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def load_venue_contract(path: Path) -> VenueContract:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise VenueContractError(f"venue contract not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise VenueContractError(f"venue contract is not valid YAML: {path}") from exc
    data = _mapping(raw, "venue contract")
    _reject_unknown(data, _ROOT_FIELDS, "venue contract")
    _require_fields(data, _ROOT_FIELDS, "venue contract")

    schema_version = _integer(data["schema_version"], "schema_version")
    if schema_version != 1:
        raise VenueContractError(f"unsupported venue schema_version: {schema_version}")
    venue_id = _identifier(data["venue_id"], "venue_id")
    track = _identifier(data["track"], "track")
    display_name = _text(data["display_name"], "display_name")
    year = _integer(data["year"], "year")
    if not 2000 <= year <= 2100:
        raise VenueContractError("year must be between 2000 and 2100")
    try:
        status = VenueStatus(_text(data["status"], "status"))
    except ValueError as exc:
        choices = ", ".join(item.value for item in VenueStatus)
        raise VenueContractError(f"status must be one of: {choices}") from exc

    profiles_raw = data["compatible_profiles"]
    if not isinstance(profiles_raw, list) or not profiles_raw:
        raise VenueContractError("compatible_profiles must be a non-empty list")
    profiles = tuple(_identifier(item, "compatible_profiles item") for item in profiles_raw)
    if len(profiles) != len(set(profiles)):
        raise VenueContractError("compatible_profiles contains duplicates")

    sources_raw = data["official_sources"]
    if not isinstance(sources_raw, list) or not sources_raw:
        raise VenueContractError("official_sources must be a non-empty list")
    sources = tuple(_source(item, index) for index, item in enumerate(sources_raw))
    template = _template(data["template"])
    policy = _policy(data["policy"])
    valid_until = _optional_date(data["valid_until"], "valid_until")
    if status is VenueStatus.VERIFIED and (
        valid_until is None
        or template.sha256 is None
        or any(source.retrieved_at is None or source.sha256 is None for source in sources)
    ):
        raise VenueContractError(
            "verified contract requires source retrieval dates, source/template hashes, "
            "and valid_until"
        )
    if status is VenueStatus.VERIFIED and not policy.is_resolved():
        raise VenueContractError("verified contract requires resolved policy fields")
    return VenueContract(
        schema_version=schema_version,
        venue_id=venue_id,
        display_name=display_name,
        year=year,
        track=track,
        status=status,
        compatible_profiles=profiles,
        official_sources=sources,
        template=template,
        policy=policy,
        valid_until=valid_until,
        source_path=path,
    )


def _source(value: object, index: int) -> OfficialSource:
    data = _mapping(value, f"official_sources[{index}]")
    _reject_unknown(data, _SOURCE_FIELDS, f"official_sources[{index}]")
    _require_fields(data, _SOURCE_FIELDS, f"official_sources[{index}]")
    return OfficialSource(
        url=_https_url(data["url"], f"official_sources[{index}].url"),
        retrieved_at=_optional_date(
            data["retrieved_at"], f"official_sources[{index}].retrieved_at"
        ),
        sha256=_optional_sha256(data["sha256"], f"official_sources[{index}].sha256"),
    )


def _template(value: object) -> VenueTemplate:
    data = _mapping(value, "template")
    _reject_unknown(data, _TEMPLATE_FIELDS, "template")
    _require_fields(data, _TEMPLATE_FIELDS, "template")
    return VenueTemplate(
        identity=_text(data["identity"], "template.identity"),
        source_url=_https_url(data["source_url"], "template.source_url"),
        sha256=_optional_sha256(data["sha256"], "template.sha256"),
    )


def _policy(value: object) -> VenuePolicy:
    data = _mapping(value, "policy")
    _reject_unknown(data, _POLICY_FIELDS, "policy")
    _require_fields(data, _POLICY_FIELDS, "policy")
    anonymity = _text(data["anonymity"], "policy.anonymity")
    if anonymity not in _ANONYMITY:
        raise VenueContractError(
            f"policy.anonymity must be one of: {', '.join(sorted(_ANONYMITY))}"
        )
    page_limit_raw = data["page_limit"]
    page_limit = None if page_limit_raw is None else _integer(page_limit_raw, "policy.page_limit")
    if page_limit is not None and page_limit <= 0:
        raise VenueContractError("policy.page_limit must be positive or null")
    artifact_policy = _text(data["artifact_policy"], "policy.artifact_policy")
    if artifact_policy not in _ARTIFACT_POLICIES:
        raise VenueContractError(
            "policy.artifact_policy must be one of: "
            + ", ".join(sorted(_ARTIFACT_POLICIES))
        )
    checklist_delivery = _text(
        data["checklist_delivery"], "policy.checklist_delivery"
    )
    if checklist_delivery not in _CHECKLIST_DELIVERY:
        raise VenueContractError(
            "policy.checklist_delivery must be one of: "
            + ", ".join(sorted(_CHECKLIST_DELIVERY))
        )
    checklist_required = _optional_boolean(
        data["checklist_required"], "policy.checklist_required"
    )
    if checklist_required is True and checklist_delivery == "none":
        raise VenueContractError("required checklist cannot use delivery none")
    if checklist_required is False and checklist_delivery not in {"none", "unknown"}:
        raise VenueContractError("non-required checklist must use delivery none")
    sections_raw = data["required_sections"]
    if not isinstance(sections_raw, list):
        raise VenueContractError("policy.required_sections must be a list")
    required_sections = tuple(
        _text(item, "policy.required_sections item") for item in sections_raw
    )
    if len(required_sections) != len(
        {item.casefold() for item in required_sections}
    ):
        raise VenueContractError("policy.required_sections contains duplicates")
    return VenuePolicy(
        anonymity=anonymity,
        page_limit=page_limit,
        supplement_allowed=_optional_boolean(
            data["supplement_allowed"], "policy.supplement_allowed"
        ),
        checklist_required=checklist_required,
        checklist_delivery=checklist_delivery,
        ethics_required=_optional_boolean(data["ethics_required"], "policy.ethics_required"),
        limitations_required=_optional_boolean(
            data["limitations_required"], "policy.limitations_required"
        ),
        artifact_policy=artifact_policy,
        required_sections=required_sections,
    )


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VenueContractError(f"{field} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _reject_unknown(data: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise VenueContractError(f"{field} has unknown fields: {', '.join(unknown)}")


def _require_fields(data: dict[str, Any], required: set[str], field: str) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise VenueContractError(f"{field} missing fields: {', '.join(missing)}")


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise VenueContractError(f"{field} must not be empty")
    return text


def _identifier(value: object, field: str) -> str:
    text = _text(value, field)
    if not _ID_PATTERN.fullmatch(text):
        raise VenueContractError(f"{field} must be a lowercase kebab-case identifier")
    return text


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VenueContractError(f"{field} must be an integer")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise VenueContractError(f"{field} must be a boolean")
    return value


def _optional_boolean(value: object, field: str) -> bool | None:
    return None if value is None else _boolean(value, field)


def _date(value: object, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise VenueContractError(f"{field} must be an ISO date") from exc


def _optional_date(value: object, field: str) -> date | None:
    return None if value is None else _date(value, field)


def _sha256(value: object, field: str) -> str:
    text = _text(value, field)
    if not _SHA256_PATTERN.fullmatch(text):
        raise VenueContractError(f"{field} must be a lowercase SHA-256 hex digest")
    return text


def _optional_sha256(value: object, field: str) -> str | None:
    return None if value is None else _sha256(value, field)


def _https_url(value: object, field: str) -> str:
    text = _text(value, field)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc:
        raise VenueContractError(f"{field} must be an HTTPS URL")
    return text
