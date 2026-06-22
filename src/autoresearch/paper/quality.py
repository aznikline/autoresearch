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
    literature_gap_records: bool = False
    literature_retrieval_integrity: bool = False
    domain_protocol_valid: bool = False
    evidence_graph_valid: bool = False
    asset_governance_valid: bool = False
    venue_export_valid: bool = False
    empirical_claim_links: bool = False
    preregistered_confirmatory_spec: bool = False
    immutable_evaluation: bool = False
    protocol_parity: bool = False
    failed_runs_accounted: bool = False
    limitations: bool = False
    artifact_manifest: bool = False
    artifact_provenance: bool = False
    competing_hypotheses: bool = False


@dataclass(frozen=True)
class QualityCheck:
    requirement: str
    required: int | bool
    observed: int | bool
    passed: bool
    blocking_reason: str = ""


@dataclass(frozen=True)
class QualityAssessment:
    score: float
    threshold: float
    evidence_complete: bool
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
        _required("citation_integrity", True, citation_verification.ok),
        _required("numeric_claim_integrity", True, claim_verification.ok),
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
        _required("literature_gap_records", True, evidence.literature_gap_records),
        _required(
            "literature_retrieval_integrity",
            True,
            evidence.literature_retrieval_integrity,
        ),
        _required("domain_protocol_valid", True, evidence.domain_protocol_valid),
        _required("evidence_graph_valid", True, evidence.evidence_graph_valid),
        _required("asset_governance_valid", True, evidence.asset_governance_valid),
        _required("venue_export_valid", True, evidence.venue_export_valid),
        _required("empirical_claim_links", True, evidence.empirical_claim_links),
        _required(
            "preregistered_confirmatory_spec",
            True,
            evidence.preregistered_confirmatory_spec,
        ),
        _required("immutable_evaluation", True, evidence.immutable_evaluation),
        _required("protocol_parity", True, evidence.protocol_parity),
        _required("failed_runs_accounted", True, evidence.failed_runs_accounted),
        _required("limitations", True, evidence.limitations),
        _required("artifact_manifest", True, evidence.artifact_manifest),
        _required("artifact_provenance", True, evidence.artifact_provenance),
        _required("competing_hypotheses", depth == "top_venue", evidence.competing_hypotheses),
    )

    issues: list[str] = []
    science_issues: list[str] = []
    strengths: list[str] = []
    if citation_verification.ok:
        strengths.append("All citations resolve to the screened bibliography.")
    else:
        message = "Unsupported citations remain in the paper."
        issues.append(message)
        science_issues.append(message)
    if claim_verification.ok:
        strengths.append("All numeric claims resolve to experiment ledger values.")
    else:
        message = "Unsupported numeric claims remain in the paper."
        issues.append(message)
        science_issues.append(message)

    for check in checks:
        if check.passed:
            strengths.append(f"Depth requirement passed: {check.requirement}.")
        else:
            message = (
                f"Depth requirement failed: {check.requirement} "
                f"requires {check.required!r}, observed {check.observed!r}."
            )
            issues.append(message)
            if check.requirement != "venue_export_valid":
                science_issues.append(message)

    lowered = markdown.lower()
    scaffold_markers = (
        "deterministic scaffold",
        "toy experiment",
        "not yet a top-conference submission",
        "domain-specific experiments",
    )
    if any(marker in lowered for marker in scaffold_markers):
        message = "Paper self-identifies as scaffold-level rather than venue-ready science."
        issues.append(message)
        science_issues.append(message)

    score = round(max(1.0, 5.0 - min(4.0, 0.35 * len(issues))), 2)
    if not citation_verification.ok or not claim_verification.ok:
        score = min(score, 2.0)
    evidence_complete = not science_issues
    submission_ready = evidence_complete and score >= threshold and not issues
    return QualityAssessment(
        score=score,
        threshold=threshold,
        evidence_complete=evidence_complete,
        submission_ready=submission_ready,
        profile_id=profile.profile_id,
        depth=depth,
        checks=checks,
        blocking_issues=tuple(issues),
        strengths=tuple(strengths),
    )


def _minimum(requirement: str, required: int, observed: int) -> QualityCheck:
    passed = observed >= required
    reason = "" if passed else f"requires at least {required}, observed {observed}"
    return QualityCheck(requirement, required, observed, passed, reason)


def _required(requirement: str, required: bool, observed: bool) -> QualityCheck:
    passed = not required or observed
    reason = "" if passed else f"required {requirement} evidence is missing"
    return QualityCheck(requirement, required, observed, passed, reason)
