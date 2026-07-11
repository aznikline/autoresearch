from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


class VenueStrategyError(ValueError):
    """Raised when a venue strategy profile is missing or malformed."""


@dataclass(frozen=True)
class VenueStrategy:
    """Reviewer preferences and narrative strategy for a specific venue.

    Extends the existing VenueContract (format/policy) with subjective
    reviewer culture: what they value, what they reject, and how to
    frame contributions to maximize acceptance probability.
    """

    schema_version: int
    venue_id: str
    display_name: str
    reviewer_values: tuple[str, ...]
    common_rejections: tuple[str, ...]
    high_score_indicators: tuple[str, ...]
    narrative_framing: str
    methodology_expectations: str
    contribution_weights: dict[str, float]
    known_biases: tuple[str, ...]
    page_economy: str
    source_path: Path

    @property
    def key(self) -> str:
        return self.venue_id


@dataclass(frozen=True)
class ReviewWeakness:
    claim: str
    severity: str  # critical | major | minor
    suggested_fix: str
    missing_evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewSimulation:
    venue_id: str
    overall_score: int  # 1-10
    confidence: float  # 0-1 how confident we are this matches real review
    strengths: tuple[str, ...]
    weaknesses: tuple[ReviewWeakness, ...]
    suggested_experiments: tuple[str, ...]
    narrative_suggestions: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "venue_id": self.venue_id,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "strengths": list(self.strengths),
            "weaknesses": [w.to_dict() for w in self.weaknesses],
            "suggested_experiments": list(self.suggested_experiments),
            "narrative_suggestions": list(self.narrative_suggestions),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class ScoredContribution:
    description: str
    evidence_run_ids: tuple[str, ...]
    venue_relevance: float  # 0-1
    strength_score: float  # 0-1
    narrative_hook: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ContributionMining:
    venue_id: str
    contributions: tuple[ScoredContribution, ...]
    venue_fit_score: float  # 0-1 overall fit
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "venue_id": self.venue_id,
            "venue_fit_score": self.venue_fit_score,
            "summary": self.summary,
            "contributions": [c.to_dict() for c in self.contributions],
        }


# --- YAML schema constants ---

_ROOT_FIELDS = {
    "schema_version",
    "venue_id",
    "display_name",
    "reviewer_values",
    "common_rejections",
    "high_score_indicators",
    "narrative_framing",
    "methodology_expectations",
    "contribution_weights",
    "known_biases",
    "page_economy",
}
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_venue_strategy(path: Path) -> VenueStrategy:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise VenueStrategyError(f"strategy profile not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise VenueStrategyError(
            f"strategy profile is not valid YAML: {path}"
        ) from exc

    data = _mapping(raw, "venue strategy")
    _reject_unknown(data, _ROOT_FIELDS, "venue strategy")
    _require_fields(data, _ROOT_FIELDS, "venue strategy")

    schema_version = _integer(data["schema_version"], "schema_version")
    if schema_version != 1:
        raise VenueStrategyError(
            f"unsupported strategy schema_version: {schema_version}"
        )
    venue_id = _identifier(data["venue_id"], "venue_id")
    display_name = _text(data["display_name"], "display_name")

    reviewer_values = _string_list(data["reviewer_values"], "reviewer_values")
    common_rejections = _string_list(data["common_rejections"], "common_rejections")
    high_score_indicators = _string_list(
        data["high_score_indicators"], "high_score_indicators"
    )
    narrative_framing = _text(data["narrative_framing"], "narrative_framing")
    methodology_expectations = _text(
        data["methodology_expectations"], "methodology_expectations"
    )
    known_biases = _string_list(data["known_biases"], "known_biases")
    page_economy = _text(data["page_economy"], "page_economy")

    weights_raw = data["contribution_weights"]
    if not isinstance(weights_raw, dict) or not weights_raw:
        raise VenueStrategyError("contribution_weights must be a non-empty mapping")
    contribution_weights: dict[str, float] = {}
    for key, value in weights_raw.items():
        if not isinstance(value, (int, float)):
            raise VenueStrategyError(
                f"contribution_weights.{key} must be a number"
            )
        contribution_weights[str(key)] = float(value)

    return VenueStrategy(
        schema_version=schema_version,
        venue_id=venue_id,
        display_name=display_name,
        reviewer_values=reviewer_values,
        common_rejections=common_rejections,
        high_score_indicators=high_score_indicators,
        narrative_framing=narrative_framing,
        methodology_expectations=methodology_expectations,
        contribution_weights=contribution_weights,
        known_biases=known_biases,
        page_economy=page_economy,
        source_path=path,
    )


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VenueStrategyError(f"{field} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _reject_unknown(
    data: dict[str, Any], allowed: set[str], field: str
) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise VenueStrategyError(
            f"{field} has unknown fields: {', '.join(unknown)}"
        )


def _require_fields(
    data: dict[str, Any], required: set[str], field: str
) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise VenueStrategyError(
            f"{field} missing fields: {', '.join(missing)}"
        )


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise VenueStrategyError(f"{field} must not be empty")
    return text


def _identifier(value: object, field: str) -> str:
    text = _text(value, field)
    if not _ID_PATTERN.fullmatch(text):
        raise VenueStrategyError(
            f"{field} must be a lowercase kebab-case identifier"
        )
    return text


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VenueStrategyError(f"{field} must be an integer")
    return value


def _string_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise VenueStrategyError(f"{field} must be a non-empty list")
    return tuple(str(item).strip() for item in value if str(item).strip())
