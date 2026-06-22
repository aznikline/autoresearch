from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from autoresearch.venues.schema import VenueContract


@dataclass(frozen=True)
class VenueExportAssessment:
    ok: bool
    venue_id: str
    year: int
    track: str
    template_identity: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "venue_id": self.venue_id,
            "year": self.year,
            "track": self.track,
            "template_identity": self.template_identity,
            "blockers": list(self.blockers),
        }


def assess_venue_export(
    contract: VenueContract,
    *,
    paper_markdown: str,
    template_materialized: bool,
    on: date,
) -> VenueExportAssessment:
    blockers: list[str] = []
    if not contract.is_verified(on=on):
        blockers.append("contract_not_current_verified")
    if not template_materialized:
        blockers.append("template_not_materialized")
    lowered = paper_markdown.lower()
    if contract.policy.ethics_required is True and not _has_section(lowered, "ethics"):
        blockers.append("missing_ethics_section")
    if contract.policy.limitations_required is True and not _has_section(
        lowered, "limitations"
    ):
        blockers.append("missing_limitations_section")
    if (
        contract.policy.checklist_required is True
        and contract.policy.checklist_delivery == "paper"
        and not (
        _has_section(lowered, "artifact checklist")
        or _has_section(lowered, "checklist")
        )
    ):
        blockers.append("missing_artifact_checklist")
    if contract.policy.artifact_policy == "required" and "artifact" not in lowered:
        blockers.append("missing_required_artifact_statement")
    for section in contract.policy.required_sections:
        if not _has_section(lowered, section.casefold()):
            blockers.append(f"missing_required_section:{section.casefold()}")
    if contract.policy.anonymity == "double_blind" and re.search(
        r"(?im)^\s*(authors?|affiliations?|acknowledg(?:e)?ments?)\s*:",
        paper_markdown,
    ):
        blockers.append("anonymity_violation")
    return VenueExportAssessment(
        ok=not blockers,
        venue_id=contract.venue_id,
        year=contract.year,
        track=contract.track,
        template_identity=contract.template.identity,
        blockers=tuple(blockers),
    )


def _has_section(lowered_markdown: str, title: str) -> bool:
    return bool(re.search(rf"(?m)^##+\s+{re.escape(title)}\s*$", lowered_markdown))
