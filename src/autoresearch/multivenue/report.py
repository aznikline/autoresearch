from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.ideation.session import IdeationSession
from autoresearch.strategy.contributions import mine_contributions
from autoresearch.strategy.models import (
    ContributionMining,
    ReviewSimulation,
    VenueStrategy,
)
from autoresearch.strategy.registry import VenueStrategyRegistry
from autoresearch.strategy.reviewer import simulate_review


@dataclass(frozen=True)
class VenueRanking:
    rank: int
    venue_id: str
    display_name: str
    overall_score: float  # 0-1 composite
    ideation_fit: float  # 0-1
    review_score: int  # 1-10
    contribution_fit: float  # 0-1
    critical_weaknesses: tuple[str, ...]
    top_contribution: str
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "venue_id": self.venue_id,
            "display_name": self.display_name,
            "overall_score": self.overall_score,
            "ideation_fit": self.ideation_fit,
            "review_score": self.review_score,
            "contribution_fit": self.contribution_fit,
            "critical_weaknesses": list(self.critical_weaknesses),
            "top_contribution": self.top_contribution,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class MultiVenueReport:
    idea: str
    venue_rankings: tuple[VenueRanking, ...]
    best_venue: str
    best_fit_score: float
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "idea": self.idea,
            "best_venue": self.best_venue,
            "best_fit_score": self.best_fit_score,
            "summary": self.summary,
            "venue_rankings": [r.to_dict() for r in self.venue_rankings],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Multi-Venue Fit Report",
            "",
            f"**Idea:** {self.idea}",
            f"**Best Match:** {self.display_name_for(self.best_venue)} ({self.best_fit_score:.0%} fit)",
            "",
            self.summary,
            "",
            "## Rankings",
            "",
            "| # | Venue | Score | Ideation | Review | Contrib | Critical Issues |",
            "|---|-------|-------|----------|--------|---------|-----------------|",
        ]
        for r in self.venue_rankings:
            critical = ", ".join(r.critical_weaknesses[:2]) or "none"
            if len(r.critical_weaknesses) > 2:
                critical += f" +{len(r.critical_weaknesses) - 2} more"
            lines.append(
                f"| {r.rank} | **{r.display_name}** | {r.overall_score:.0%} | "
                f"{r.ideation_fit:.0%} | {r.review_score}/10 | {r.contribution_fit:.0%} | "
                f"{critical} |"
            )

        lines.extend(["", "## Per-Venue Details", ""])
        for r in self.venue_rankings:
            lines.extend([
                f"### {r.rank}. {r.display_name} ({r.venue_id})",
                f"- **Overall:** {r.overall_score:.0%}",
                f"- **Ideation Fit:** {r.ideation_fit:.0%}",
                f"- **Review Score:** {r.review_score}/10",
                f"- **Contribution Fit:** {r.contribution_fit:.0%}",
                f"- **Top Contribution:** {r.top_contribution}",
                f"- **Recommendation:** {r.recommendation}",
                "",
            ])

        return "\n".join(lines) + "\n"

    def display_name_for(self, venue_id: str) -> str:
        for r in self.venue_rankings:
            if r.venue_id == venue_id:
                return r.display_name
        return venue_id


def generate_fit_report(
    *,
    idea: str,
    registry: VenueStrategyRegistry,
    paper_markdown: str = "",
    ledger: tuple[LedgerEntry, ...] = (),
    claims: tuple[dict[str, object], ...] = (),
    llm_provider: LLMProvider | None = None,
    top_n: int = 17,
) -> MultiVenueReport:
    """Generate a ranked multi-venue fit report.

    Runs ideation, reviewer simulation, and contribution mining across all
    registered venues, then ranks them by composite score. Use this before
    committing to a venue-specific pipeline run.
    """
    rankings: list[VenueRanking] = []

    for strategy in registry.strategies:
        # Ideation
        ideation_report = IdeationSession(strategy, idea=idea).analyze(
            llm_provider=llm_provider,
        )

        # Reviewer simulation (if we have a paper)
        if paper_markdown.strip():
            review = simulate_review(
                paper_markdown=paper_markdown,
                venue_strategy=strategy,
                ledger=ledger,
                llm_provider=llm_provider,
            )
        else:
            review = None

        # Contribution mining (if we have evidence)
        if ledger:
            mining = mine_contributions(
                venue_strategy=strategy,
                ledger=ledger,
                claims=claims,
                llm_provider=llm_provider,
                topic=idea,
            )
        else:
            mining = None

        # Composite score
        ideation_score = ideation_report.overall_fit
        review_score = review.overall_score / 10.0 if review else 0.5
        contribution_score = mining.venue_fit_score if mining else 0.5

        # Weight: ideation 30%, review 35%, contributions 35%
        composite = (
            0.30 * ideation_score
            + 0.35 * review_score
            + 0.35 * contribution_score
        )

        critical_weaknesses = tuple(
            w.claim for w in (review.weaknesses if review else ())
            if w.severity == "critical"
        )

        top_contribution = (
            mining.contributions[0].description
            if mining and mining.contributions
            else "no contributions mined"
        )

        recommendation = _make_recommendation(
            composite=composite,
            critical_count=len(critical_weaknesses),
            venue_name=strategy.display_name,
        )

        rankings.append(
            VenueRanking(
                rank=0,  # assigned after sorting
                venue_id=strategy.venue_id,
                display_name=strategy.display_name,
                overall_score=round(composite, 3),
                ideation_fit=round(ideation_score, 3),
                review_score=review.overall_score if review else 5,
                contribution_fit=round(contribution_score, 3),
                critical_weaknesses=critical_weaknesses,
                top_contribution=top_contribution,
                recommendation=recommendation,
            )
        )

    # Sort by composite score descending
    rankings.sort(key=lambda r: r.overall_score, reverse=True)

    # Assign ranks and take top N
    ranked = tuple(
        VenueRanking(
            rank=i + 1,
            venue_id=r.venue_id,
            display_name=r.display_name,
            overall_score=r.overall_score,
            ideation_fit=r.ideation_fit,
            review_score=r.review_score,
            contribution_fit=r.contribution_fit,
            critical_weaknesses=r.critical_weaknesses,
            top_contribution=r.top_contribution,
            recommendation=r.recommendation,
        )
        for i, r in enumerate(rankings[:top_n])
    )

    best = ranked[0]
    summary = (
        f"**{best.display_name}** is the best match ({best.overall_score:.0%}). "
    )
    if best.critical_weaknesses:
        summary += (
            f"Address {len(best.critical_weaknesses)} critical issues before submission: "
            + "; ".join(best.critical_weaknesses[:3])
            + "."
        )
    else:
        summary += "No critical blockers — proceed with a full pipeline run."

    if len(ranked) > 1:
        runner_up = ranked[1]
        if runner_up.overall_score >= best.overall_score * 0.9:
            summary += (
                f" {runner_up.display_name} is a close second "
                f"({runner_up.overall_score:.0%})."
            )

    return MultiVenueReport(
        idea=idea,
        venue_rankings=ranked,
        best_venue=best.venue_id,
        best_fit_score=best.overall_score,
        summary=summary,
    )


def write_fit_report(report: MultiVenueReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_markdown(), encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _make_recommendation(
    *,
    composite: float,
    critical_count: int,
    venue_name: str,
) -> str:
    if composite >= 0.75 and critical_count == 0:
        return f"Strong match for {venue_name}. Run a full pipeline."
    if composite >= 0.60 and critical_count <= 1:
        return f"Good fit for {venue_name}. Address the critical issue before running."
    if composite >= 0.45:
        return (
            f"Possible fit for {venue_name}. {critical_count} critical issues "
            "need resolution before the idea is venue-ready."
        )
    if composite >= 0.30:
        return (
            f"Weak fit for {venue_name}. Consider reframing the contribution "
            "or targeting a different venue."
        )
    return (
        f"Poor fit for {venue_name}. The idea as stated does not align "
        "with this venue's values. Try a different venue or rethink the angle."
    )
