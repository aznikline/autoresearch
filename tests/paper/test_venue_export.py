from __future__ import annotations

from datetime import date
from pathlib import Path

from autoresearch.paper.venue import assess_venue_export
from autoresearch.venues.schema import (
    OfficialSource,
    VenueContract,
    VenuePolicy,
    VenueStatus,
    VenueTemplate,
)


def _contract(*, status: VenueStatus = VenueStatus.VERIFIED) -> VenueContract:
    return VenueContract(
        schema_version=1,
        venue_id="testconf",
        display_name="TestConf",
        year=2026,
        track="main",
        status=status,
        compatible_profiles=("ml-systems-efficiency",),
        official_sources=(
            OfficialSource("https://example.test/rules", date(2026, 1, 1), "a" * 64),
        ),
        template=VenueTemplate("testconf-2026", "https://example.test/template", "b" * 64),
        policy=VenuePolicy(
            anonymity="double_blind",
            page_limit=9,
            supplement_allowed=True,
            checklist_required=True,
            checklist_delivery="paper",
            ethics_required=True,
            limitations_required=True,
            artifact_policy="required",
            required_sections=(),
        ),
        valid_until=date(2026, 12, 31),
        source_path=Path("test.yaml"),
    )


def test_verified_materialized_bundle_with_required_sections_passes() -> None:
    result = assess_venue_export(
        _contract(),
        paper_markdown=(
            "# Anonymous Paper\n\n## Ethics\nReviewed.\n\n"
            "## Limitations\nScoped.\n\n## Artifact Checklist\nIncluded.\n"
        ),
        template_materialized=True,
        on=date(2026, 6, 1),
    )

    assert result.ok, result.blockers


def test_draft_or_unmaterialized_contract_fails_closed() -> None:
    result = assess_venue_export(
        _contract(status=VenueStatus.DRAFT),
        paper_markdown="# Paper\n",
        template_materialized=False,
        on=date(2026, 6, 1),
    )

    assert not result.ok
    assert "contract_not_current_verified" in result.blockers
    assert "template_not_materialized" in result.blockers
    assert "missing_ethics_section" in result.blockers
    assert "missing_limitations_section" in result.blockers
    assert "missing_artifact_checklist" in result.blockers


def test_double_blind_bundle_rejects_author_identity() -> None:
    result = assess_venue_export(
        _contract(),
        paper_markdown=(
            "# Paper\n\nAuthors: Ada Researcher\n\n## Ethics\nOk.\n\n"
            "## Limitations\nOk.\n\n## Artifact Checklist\nOk.\n"
        ),
        template_materialized=True,
        on=date(2026, 6, 1),
    )

    assert "anonymity_violation" in result.blockers


def test_exact_required_section_title_is_enforced() -> None:
    base = _contract()
    contract = VenueContract(
        **{
            **base.__dict__,
            "policy": VenuePolicy(
                **{**base.policy.__dict__, "required_sections": ("Impact Statement",)}
            ),
        }
    )

    result = assess_venue_export(
        contract,
        paper_markdown=(
            "# Paper\n\n## Ethics\nOk.\n\n## Limitations\nOk.\n\n"
            "## Artifact Checklist\nOk.\n"
        ),
        template_materialized=True,
        on=date(2026, 6, 1),
    )

    assert "missing_required_section:impact statement" in result.blockers
