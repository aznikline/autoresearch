from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.strategy.models import VenueStrategy


@dataclass(frozen=True)
class RiskFactor:
    rejection_reason: str
    applies_to_idea: bool
    mitigation: str
    severity: str = "medium"  # low | medium | high

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VenueFit:
    dimension: str
    score: float  # 0-1
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IdeationReport:
    venue_id: str
    venue_display_name: str
    idea: str
    venue_fit_scores: tuple[VenueFit, ...]
    overall_fit: float  # 0-1
    suggested_contribution_type: str
    contribution_rationale: str
    risk_factors: tuple[RiskFactor, ...]
    expected_evidence_bar: str
    narrative_strategy: str
    suggested_next_steps: tuple[str, ...]
    refined_goal: str

    def to_dict(self) -> dict[str, object]:
        return {
            "venue_id": self.venue_id,
            "venue_display_name": self.venue_display_name,
            "idea": self.idea,
            "overall_fit": self.overall_fit,
            "suggested_contribution_type": self.suggested_contribution_type,
            "contribution_rationale": self.contribution_rationale,
            "venue_fit_scores": [f.to_dict() for f in self.venue_fit_scores],
            "risk_factors": [r.to_dict() for r in self.risk_factors],
            "expected_evidence_bar": self.expected_evidence_bar,
            "narrative_strategy": self.narrative_strategy,
            "suggested_next_steps": list(self.suggested_next_steps),
            "refined_goal": self.refined_goal,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Ideation Report: {self.venue_display_name}",
            "",
            f"**Idea:** {self.idea}",
            f"**Overall Venue Fit:** {self.overall_fit:.0%}",
            f"**Suggested Contribution Type:** {self.suggested_contribution_type}",
            "",
            "## Venue Fit Analysis",
        ]
        for fit in self.venue_fit_scores:
            lines.append(f"- **{fit.dimension}**: {fit.score:.0%} — {fit.rationale}")

        lines.extend([
            "",
            f"## Contribution Strategy\n\n{self.contribution_rationale}",
            "",
            "## Risk Assessment",
        ])
        for risk in self.risk_factors:
            status = "⚠️ APPLIES" if risk.applies_to_idea else "✅ Mitigated"
            lines.append(
                f"- **[{risk.severity.upper()}]** {risk.rejection_reason} — {status}"
            )
            if risk.applies_to_idea:
                lines.append(f"  - Mitigation: {risk.mitigation}")

        lines.extend([
            "",
            f"## Expected Evidence Bar\n\n{self.expected_evidence_bar}",
            "",
            f"## Narrative Strategy\n\n{self.narrative_strategy}",
            "",
            "## Suggested Next Steps",
        ])
        for i, step in enumerate(self.suggested_next_steps, 1):
            lines.append(f"{i}. {step}")

        lines.extend([
            "",
            f"## Refined Goal\n\n{self.refined_goal}",
        ])
        return "\n".join(lines) + "\n"


class IdeationSession:
    """Analyze a research idea against venue strategy before running the pipeline.

    Gives you a venue-fit report before you invest in the full 12-stage run.
    """

    def __init__(
        self,
        venue_strategy: VenueStrategy,
        *,
        idea: str,
    ) -> None:
        self.venue_strategy = venue_strategy
        self.idea = idea.strip()

    def analyze(
        self,
        *,
        llm_provider: LLMProvider | None = None,
    ) -> IdeationReport:
        if llm_provider is not None:
            try:
                return self._llm_analyze(llm_provider)
            except Exception:
                import logging

                logging.getLogger("autoresearch.ideation").warning(
                    "LLM ideation failed; falling back to rule-based"
                )
        return self._rule_based_analyze()

    def _llm_analyze(self, llm_provider: LLMProvider) -> IdeationReport:
        response = llm_provider.complete_json(
            stage="ideation",
            messages=(
                ("system", self._ideation_prompt()),
                ("user", f"Research idea: {self.idea}"),
            ),
            required_keys=(
                "venue_fit_scores",
                "overall_fit",
                "suggested_contribution_type",
                "contribution_rationale",
                "risk_factors",
                "expected_evidence_bar",
                "narrative_strategy",
                "suggested_next_steps",
                "refined_goal",
            ),
        )
        data = response.data
        fit_scores = tuple(
            VenueFit(
                dimension=str(f.get("dimension", "")),
                score=min(1.0, max(0.0, float(f.get("score", 0.5)))),
                rationale=str(f.get("rationale", "")),
            )
            for f in data.get("venue_fit_scores", ())
            if isinstance(f, dict) and str(f.get("dimension", "")).strip()
        )
        risk_factors = tuple(
            RiskFactor(
                rejection_reason=str(r.get("rejection_reason", "")),
                applies_to_idea=bool(r.get("applies_to_idea", True)),
                mitigation=str(r.get("mitigation", "")),
                severity=_normalize_severity(str(r.get("severity", "medium"))),
            )
            for r in data.get("risk_factors", ())
            if isinstance(r, dict) and str(r.get("rejection_reason", "")).strip()
        )
        return IdeationReport(
            venue_id=self.venue_strategy.venue_id,
            venue_display_name=self.venue_strategy.display_name,
            idea=self.idea,
            venue_fit_scores=fit_scores,
            overall_fit=min(1.0, max(0.0, float(data.get("overall_fit", 0.5)))),
            suggested_contribution_type=str(
                data.get("suggested_contribution_type", "empirical")
            ),
            contribution_rationale=str(
                data.get("contribution_rationale", "No rationale provided.")
            ),
            risk_factors=risk_factors,
            expected_evidence_bar=str(
                data.get("expected_evidence_bar", "Standard venue expectations apply.")
            ),
            narrative_strategy=str(
                data.get("narrative_strategy", self.venue_strategy.narrative_framing)
            ),
            suggested_next_steps=tuple(
                str(s)
                for s in data.get("suggested_next_steps", ())
                if str(s).strip()
            ),
            refined_goal=str(data.get("refined_goal", self.idea)),
        )

    def _rule_based_analyze(self) -> IdeationReport:
        """Rule-based ideation analysis using venue strategy heuristics."""
        strategy = self.venue_strategy

        # Score venue fit against each reviewer value
        fit_scores: list[VenueFit] = []
        for value in strategy.reviewer_values:
            relevance_keywords = _extract_keywords(value)
            idea_lower = self.idea.lower()
            hits = sum(
                1 for kw in relevance_keywords if kw.lower() in idea_lower
            )
            score = min(1.0, 0.3 + hits * 0.2)
            fit_scores.append(
                VenueFit(
                    dimension=value,
                    score=score,
                    rationale=(
                        f"Idea {'mentions' if hits > 0 else 'does not explicitly mention'} "
                        f"concepts related to this value."
                    ),
                )
            )

        overall_fit = (
            sum(f.score for f in fit_scores) / len(fit_scores)
            if fit_scores
            else 0.5
        )

        # Risk assessment: check each common rejection reason
        risks: list[RiskFactor] = []
        for rejection in strategy.common_rejections:
            rejection_lower = rejection.lower()
            idea_lower = self.idea.lower()
            # Check if the idea might trigger this rejection
            keywords = _extract_keywords(rejection)
            risk_applies = not any(
                kw.lower() in idea_lower for kw in keywords
            ) and "no " not in rejection_lower

            # Simpler heuristic: if idea is short/vague, more risks apply
            if len(self.idea.split()) < 20:
                risk_applies = True

            risks.append(
                RiskFactor(
                    rejection_reason=rejection,
                    applies_to_idea=risk_applies,
                    mitigation=(
                        _generate_mitigation(rejection, strategy)
                        if risk_applies
                        else "N/A — idea appears to address this."
                    ),
                    severity=_rejection_severity(rejection),
                )
            )

        # Contribution type suggestion from venue weights
        best_contribution = max(
            strategy.contribution_weights.items(),
            key=lambda item: item[1],
        )
        contribution_type = best_contribution[0].replace("_", " ")

        # Build the report
        return IdeationReport(
            venue_id=strategy.venue_id,
            venue_display_name=strategy.display_name,
            idea=self.idea,
            venue_fit_scores=tuple(fit_scores),
            overall_fit=round(overall_fit, 2),
            suggested_contribution_type=contribution_type,
            contribution_rationale=(
                f"{strategy.display_name} weights '{best_contribution[0]}' "
                f"at {best_contribution[1]:.0%} — structure your contribution "
                f"around this dimension. {strategy.narrative_framing[:200]}"
            ),
            risk_factors=tuple(risks),
            expected_evidence_bar=strategy.methodology_expectations,
            narrative_strategy=strategy.narrative_framing,
            suggested_next_steps=(
                "Draft a one-paragraph contribution statement targeting "
                f"'{best_contribution[0].replace('_', ' ')}' as the primary dimension.",
                f"Review the {len(risks)} risk factors above and address "
                "at least the HIGH severity ones before running the pipeline.",
                "Identify 3-5 strong baselines that this venue's reviewers "
                "would expect to see in the related work.",
                f"Run `autoresearch plan` with this venue to see the full "
                "stage plan before committing to a full run.",
            ),
            refined_goal=(
                f"[{strategy.display_name}] {self.idea} — "
                f"contribution type: {contribution_type}"
            ),
        )

    def _ideation_prompt(self) -> str:
        strategy = self.venue_strategy
        return (
            f"You are a senior researcher helping to refine a research idea "
            f"for submission to {strategy.display_name}.\n\n"
            f"## What {strategy.display_name} reviewers value (ordered):\n"
            + "\n".join(f"- {v}" for v in strategy.reviewer_values)
            + "\n\n"
            f"## Common rejection reasons at {strategy.display_name}:\n"
            + "\n".join(f"- {r}" for r in strategy.common_rejections)
            + "\n\n"
            f"## High-score indicators:\n"
            + "\n".join(f"- {i}" for i in strategy.high_score_indicators)
            + "\n\n"
            f"## Methodology expectations:\n{strategy.methodology_expectations}\n\n"
            f"## Narrative strategy:\n{strategy.narrative_framing}\n\n"
            "Given the research idea, return a JSON object with:\n"
            "- venue_fit_scores: array of {dimension, score (0-1), rationale}\n"
            "- overall_fit: float 0-1\n"
            "- suggested_contribution_type: string\n"
            "- contribution_rationale: string\n"
            "- risk_factors: array of {rejection_reason, applies_to_idea (bool), "
            "mitigation, severity (low|medium|high)}\n"
            "- expected_evidence_bar: string\n"
            "- narrative_strategy: string\n"
            "- suggested_next_steps: string array\n"
            "- refined_goal: one sentence restating the idea for this venue\n\n"
            "Be honest. If the idea is a poor fit, say so with low scores "
            "and concrete reasons. Over-optimistic feedback wastes the author's time."
        )


def write_ideation_report(report: IdeationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_markdown(), encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a reviewer value or rejection reason."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "of", "in", "to", "for", "with", "on", "at", "by", "from",
        "and", "or", "not", "but", "if", "than", "that", "this",
        "as", "it", "its", "no", "any", "all", "each", "every",
        "over", "under", "about", "into", "through", "during",
        "without", "within", "should", "would", "could",
    }
    words = text.lower().replace(",", " ").replace("-", " ").split()
    return [w for w in words if w not in stop_words and len(w) > 3]


def _generate_mitigation(rejection: str, strategy: VenueStrategy) -> str:
    """Generate a concrete mitigation for a rejection risk."""
    rejection_lower = rejection.lower()
    if "novelty" in rejection_lower or "incremental" in rejection_lower:
        return (
            "Clearly state the novel mechanism in the abstract and introduction. "
            "Differentiate from the 3 most similar prior works explicitly."
        )
    if "baseline" in rejection_lower or "comparison" in rejection_lower:
        return (
            "Identify and implement at least 3 strong recent baselines. "
            "Document your tuning budget for each baseline equally."
        )
    if "ablation" in rejection_lower:
        return (
            "Design ablation experiments that isolate each proposed component. "
            "Report results in a dedicated ablation table or figure."
        )
    if "overclaim" in rejection_lower:
        return (
            "Add a Limitations section. Use qualifying language: 'suggests' "
            "not 'proves', 'on this benchmark' not 'in general'."
        )
    if "seed" in rejection_lower or "statistical" in rejection_lower:
        return (
            f"Run at least 5 random seeds. Report mean ± std or 95% CI. "
            f"{strategy.display_name} expects this."
        )
    if "system" in rejection_lower or "implementation" in rejection_lower:
        return (
            "Build and evaluate a real implementation. Describe the system "
            "architecture with a diagram and discuss engineering trade-offs."
        )
    if "reproduc" in rejection_lower:
        return (
            "Release code, data, and experiment configurations. Provide a "
            "reproduction script or Dockerfile."
        )
    if "theory" in rejection_lower or "formal" in rejection_lower:
        return (
            "Add a theorem, proof sketch, or formal analysis section. "
            "Even a brief formal treatment signals rigor to this venue."
        )
    if "scale" in rejection_lower or "realistic" in rejection_lower:
        return (
            "Run experiments at production scale. Report data volumes, "
            "hardware specs, and runtime. Microbenchmarks alone are insufficient."
        )
    return (
        "Address this risk explicitly in the introduction or discussion. "
        "Acknowledge the limitation and explain your approach to mitigating it."
    )


def _rejection_severity(rejection: str) -> str:
    rejection_lower = rejection.lower()
    high_triggers = {"novelty", "incremental", "missing", "no "}
    if any(t in rejection_lower for t in high_triggers):
        return "high"
    medium_triggers = {"weak", "insufficient", "overclaim", "sloppy"}
    if any(t in rejection_lower for t in medium_triggers):
        return "medium"
    return "low"


def _normalize_severity(raw: str) -> str:
    raw_lower = raw.strip().lower()
    if raw_lower in {"high", "critical"}:
        return "high"
    if raw_lower in {"medium", "major"}:
        return "medium"
    return "low"
