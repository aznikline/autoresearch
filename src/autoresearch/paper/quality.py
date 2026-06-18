from __future__ import annotations

from dataclasses import asdict, dataclass

from autoresearch.domains.profile import DomainProfile
from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification


@dataclass(frozen=True)
class ResearchEvidence:
    screened_papers: int = 0
    baselines: int = 0
    evaluation_units: int = 0
    seeds: int = 0
    ablations: int = 0
    verified_metrics: int = 0
    confidence_intervals: bool = False
    effect_sizes: bool = False
    compute_reporting: bool = False
    hypothesis_outcomes: bool = False


@dataclass(frozen=True)
class QualityCheck:
    requirement: str
    required: int | bool
    observed: int | bool
    passed: bool


@dataclass(frozen=True)
class QualityAssessment:
    score: float
    threshold: float
    submission_ready: bool
    profile_id: str
    depth: str
    checks: tuple[QualityCheck, ...]
    blocking_issues: tuple[str, ...]
    strengths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_venue_readiness(
    markdown: str,
    *,
    citation_verification: CitationVerification,
    claim_verification: ClaimVerification,
    profile: DomainProfile,
    depth: str,
    evidence: ResearchEvidence,
    threshold: float = 4.0,
) -> QualityAssessment:
    """Assess readiness from verified artifacts and the selected depth rubric."""

    requirements = profile.requirements_for(depth)
    checks = (
        _minimum("screened_papers", requirements.min_screened_papers, evidence.screened_papers),
        _minimum("baselines", requirements.min_baselines, evidence.baselines),
        _minimum(
            "evaluation_units",
            requirements.min_evaluation_units,
            evidence.evaluation_units,
        ),
        _minimum("seeds", requirements.min_seeds, evidence.seeds),
        _minimum("ablations", requirements.min_ablations, evidence.ablations),
        _minimum(
            "verified_metrics",
            requirements.min_verified_metrics,
            evidence.verified_metrics,
        ),
        _required(
            "confidence_intervals",
            requirements.require_confidence_intervals,
            evidence.confidence_intervals,
        ),
        _required("effect_sizes", requirements.require_effect_sizes, evidence.effect_sizes),
        _required(
            "compute_reporting",
            requirements.require_compute_reporting,
            evidence.compute_reporting,
        ),
        _required(
            "hypothesis_outcomes",
            requirements.require_hypothesis_outcomes,
            evidence.hypothesis_outcomes,
        ),
    )

    issues: list[str] = []
    strengths: list[str] = []
    if citation_verification.ok:
        strengths.append("All citations resolve to the screened bibliography.")
    else:
        issues.append("Unsupported citations remain in the paper.")
    if claim_verification.ok:
        strengths.append("All numeric claims resolve to experiment ledger values.")
    else:
        issues.append("Unsupported numeric claims remain in the paper.")

    for check in checks:
        if check.passed:
            strengths.append(f"Depth requirement passed: {check.requirement}.")
        else:
            issues.append(
                f"Depth requirement failed: {check.requirement} "
                f"requires {check.required!r}, observed {check.observed!r}."
            )

    lowered = markdown.lower()
    scaffold_markers = (
        "deterministic scaffold",
        "toy experiment",
        "not yet a top-conference submission",
        "domain-specific experiments",
    )
    if any(marker in lowered for marker in scaffold_markers):
        issues.append("Paper self-identifies as scaffold-level rather than venue-ready science.")

    score = round(max(1.0, 5.0 - min(4.0, 0.35 * len(issues))), 2)
    if not citation_verification.ok or not claim_verification.ok:
        score = min(score, 2.0)
    submission_ready = score >= threshold and not issues
    return QualityAssessment(
        score=score,
        threshold=threshold,
        submission_ready=submission_ready,
        profile_id=profile.profile_id,
        depth=depth,
        checks=checks,
        blocking_issues=tuple(issues),
        strengths=tuple(strengths),
    )


def _minimum(requirement: str, required: int, observed: int) -> QualityCheck:
    return QualityCheck(requirement, required, observed, observed >= required)


def _required(requirement: str, required: bool, observed: bool) -> QualityCheck:
    return QualityCheck(requirement, required, observed, not required or observed)
