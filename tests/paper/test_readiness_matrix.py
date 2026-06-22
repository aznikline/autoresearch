from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from autoresearch.domains.profile import load_profiles
from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification
from autoresearch.paper.quality import ResearchEvidence, assess_venue_readiness
from autoresearch.paper.venue import assess_venue_export
from autoresearch.venues.schema import (
    OfficialSource,
    VenueContract,
    VenuePolicy,
    VenueStatus,
    VenueTemplate,
)


STRONG_PAPER = """# Anonymous Study

## Ethics
Reviewed.

## Limitations
Scoped to the measured evidence.

## Artifact Checklist
All evidence artifacts are linked.
"""


def _contract(venue_id: str, profile_id: str) -> VenueContract:
    return VenueContract(
        schema_version=1,
        venue_id=venue_id,
        display_name=venue_id.upper(),
        year=2026,
        track="main",
        status=VenueStatus.VERIFIED,
        compatible_profiles=(profile_id,),
        official_sources=(
            OfficialSource("https://example.test/rules", date(2026, 1, 1), "a" * 64),
        ),
        template=VenueTemplate(
            f"{venue_id}-2026-main",
            "https://example.test/template",
            "b" * 64,
        ),
        policy=VenuePolicy(
            anonymity="double_blind",
            page_limit=20,
            supplement_allowed=True,
            checklist_required=True,
            checklist_delivery="paper",
            ethics_required=True,
            limitations_required=True,
            artifact_policy="required",
            required_sections=(),
        ),
        valid_until=date(2026, 12, 31),
        source_path=Path(f"{venue_id}.yaml"),
    )


def _evidence(**overrides: object) -> ResearchEvidence:
    values = {
        "screened_papers": 100,
        "baselines": 100,
        "evaluation_units": 100,
        "seeds": 100,
        "ablations": 100,
        "verified_metrics": 100,
        "confidence_intervals": True,
        "effect_sizes": True,
        "compute_reporting": True,
        "hypothesis_outcomes": True,
        "literature_gap_records": True,
        "literature_retrieval_integrity": True,
        "domain_protocol_valid": True,
        "evidence_graph_valid": True,
        "asset_governance_valid": True,
        "venue_export_valid": True,
        "empirical_claim_links": True,
        "preregistered_confirmatory_spec": True,
        "immutable_evaluation": True,
        "protocol_parity": True,
        "failed_runs_accounted": True,
        "limitations": True,
        "artifact_manifest": True,
        "artifact_provenance": True,
        "competing_hypotheses": True,
    }
    values.update(overrides)
    return ResearchEvidence(**values)


def test_every_compatible_profile_venue_pair_requires_composed_readiness() -> None:
    for profile in load_profiles():
        for venue_id in profile.compatible_venue_ids:
            venue = assess_venue_export(
                _contract(venue_id, profile.profile_id),
                paper_markdown=STRONG_PAPER,
                template_materialized=True,
                on=date(2026, 6, 19),
            )
            assert venue.ok, (profile.profile_id, venue_id, venue.blockers)
            quality = assess_venue_readiness(
                STRONG_PAPER,
                citation_verification=CitationVerification(True, (), (), ()),
                claim_verification=ClaimVerification(True, (), (), ()),
                profile=profile,
                depth="top_venue",
                evidence=_evidence(venue_export_valid=venue.ok),
            )
            assert quality.submission_ready, (
                profile.profile_id,
                venue_id,
                quality.blocking_issues,
            )


@pytest.mark.parametrize(
    ("citation_ok", "domain_ok", "venue_ok", "failed_requirement"),
    [
        (False, True, True, "citation_integrity"),
        (True, False, True, "domain_protocol_valid"),
        (True, True, False, "venue_export_valid"),
    ],
)
def test_global_domain_and_venue_failures_each_block_submission(
    citation_ok: bool,
    domain_ok: bool,
    venue_ok: bool,
    failed_requirement: str,
) -> None:
    profile = load_profiles()[0]
    quality = assess_venue_readiness(
        STRONG_PAPER,
        citation_verification=CitationVerification(citation_ok, (), (), (() if citation_ok else ("x",))),
        claim_verification=ClaimVerification(True, (), (), ()),
        profile=profile,
        depth="top_venue",
        evidence=_evidence(
            domain_protocol_valid=domain_ok,
            venue_export_valid=venue_ok,
        ),
    )

    assert not quality.submission_ready
    by_name = {check.requirement: check for check in quality.checks}
    assert by_name[failed_requirement].passed is False
