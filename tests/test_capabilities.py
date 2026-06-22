from __future__ import annotations

import pytest
from pathlib import Path

from autoresearch.capabilities import CapabilityError, CapabilityLevel, assess_capability


def test_pipeline_completion_does_not_imply_evidence_complete() -> None:
    assessment = assess_capability(
        contract_supported=True,
        integration_validated=False,
        evidence_complete=False,
        submission_ready=False,
        blockers=("real provider smoke evidence missing",),
    )

    assert assessment.level is CapabilityLevel.CONTRACT_SUPPORTED
    assert assessment.blockers == ("real provider smoke evidence missing",)


def test_capability_advances_only_through_contiguous_levels() -> None:
    assessment = assess_capability(
        contract_supported=True,
        integration_validated=True,
        evidence_complete=True,
        submission_ready=False,
        blockers=("venue checklist failed",),
    )

    assert assessment.level is CapabilityLevel.EVIDENCE_COMPLETE


def test_submission_ready_cannot_bypass_lower_capabilities() -> None:
    with pytest.raises(CapabilityError, match="requires evidence_complete"):
        assess_capability(
            contract_supported=True,
            integration_validated=True,
            evidence_complete=False,
            submission_ready=True,
        )


def test_unsupported_capability_requires_a_blocker() -> None:
    with pytest.raises(CapabilityError, match="blocker"):
        assess_capability(
            contract_supported=False,
            integration_validated=False,
            evidence_complete=False,
            submission_ready=False,
        )


def test_readme_documents_all_levels_and_no_completion_shortcut() -> None:
    readme = (
        Path(__file__).resolve().parents[1] / "README.md"
    ).read_text(encoding="utf-8")

    for level in (
        "unsupported",
        "contract_supported",
        "integration_validated",
        "evidence_complete",
        "submission_ready",
    ):
        assert f"`{level}`" in readme
    assert "does not advance the capability level" in readme
    assert "autoresearch capabilities" in readme
