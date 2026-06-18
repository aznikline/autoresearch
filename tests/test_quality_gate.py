from __future__ import annotations

from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification
from autoresearch.domains.profile import load_profile
from autoresearch.paper.quality import ResearchEvidence, assess_venue_readiness


def test_quality_gate_blocks_scaffold_paper_even_when_artifacts_verify() -> None:
    assessment = assess_venue_readiness(
        "This is not yet a top-conference submission. The current experiment is a deterministic scaffold.",
        citation_verification=CitationVerification(
            True,
            ("a", "b"),
            ("a", "b"),
            (),
        ),
        claim_verification=ClaimVerification(True, (1.0, 0.9), (1.0, 0.9), ()),
        profile=load_profile("ml-systems-efficiency"),
        depth="exploratory",
        evidence=ResearchEvidence(
            screened_papers=8,
            baselines=1,
            evaluation_units=1,
            seeds=1,
            ablations=1,
            verified_metrics=2,
            compute_reporting=True,
            hypothesis_outcomes=True,
        ),
    )

    assert not assessment.submission_ready
    assert any("scaffold-level" in issue for issue in assessment.blocking_issues)


def test_quality_gate_can_pass_strong_artifact_profile() -> None:
    assessment = assess_venue_readiness(
        "We present a novel contribution that outperform prior baselines with a state of the art result.",
        citation_verification=CitationVerification(
            True,
            tuple(f"k{i}" for i in range(8)),
            tuple(f"k{i}" for i in range(8)),
            (),
        ),
        claim_verification=ClaimVerification(
            True,
            (1.0, 0.9, 0.8, 0.7),
            (1.0, 0.9, 0.8, 0.7),
            (),
        ),
        profile=load_profile("ml-systems-efficiency"),
        depth="top_venue",
        evidence=ResearchEvidence(
            screened_papers=25,
            baselines=4,
            evaluation_units=3,
            seeds=5,
            ablations=3,
            verified_metrics=8,
            confidence_intervals=True,
            effect_sizes=True,
            compute_reporting=True,
            hypothesis_outcomes=True,
        ),
    )

    assert assessment.submission_ready
    assert assessment.score >= assessment.threshold
    assert all(check.passed for check in assessment.checks)
