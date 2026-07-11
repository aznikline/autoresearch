from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.strategy.models import (
    ContributionMining,
    ReviewSimulation,
    ReviewWeakness,
    VenueStrategy,
)


@dataclass(frozen=True)
class ActionItem:
    priority: int  # 1 = do first
    category: str  # experiment | narrative | evidence | methodology
    description: str
    current_state: str
    target_state: str
    estimated_score_gain: int  # points gained (1-10 scale)
    effort: str  # low | medium | high
    stage_to_rerun: str  # which pipeline stage to re-execute
    concrete_steps: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GapReport:
    venue_id: str
    venue_display_name: str
    current_score: int  # 1-10
    target_score: int  # 1-10
    gap: int  # target - current
    action_items: tuple[ActionItem, ...]
    minimal_path: tuple[int, ...]  # priority numbers of items in shortest path
    estimated_final_score: int
    estimated_effort: str  # low | medium | high | very_high
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "venue_id": self.venue_id,
            "venue_display_name": self.venue_display_name,
            "current_score": self.current_score,
            "target_score": self.target_score,
            "gap": self.gap,
            "estimated_final_score": self.estimated_final_score,
            "estimated_effort": self.estimated_effort,
            "summary": self.summary,
            "action_items": [a.to_dict() for a in self.action_items],
            "minimal_path": list(self.minimal_path),
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Gap Analysis: {self.venue_display_name}",
            "",
            f"**Current Score:** {self.current_score}/10",
            f"**Target Score:** {self.target_score}/10",
            f"**Gap:** {self.gap} points",
            f"**Estimated Effort:** {self.estimated_effort}",
            "",
            self.summary,
            "",
            "## Action Items (priority order)",
            "",
            "| # | Category | Action | Gain | Effort | Rerun Stage |",
            "|---|----------|--------|------|--------|-------------|",
        ]
        for item in self.action_items:
            lines.append(
                f"| {item.priority} | {item.category} | {item.description[:60]}... | "
                f"+{item.estimated_score_gain} | {item.effort} | {item.stage_to_rerun} |"
            )

        lines.extend(["", "## Detailed Action Plan", ""])
        for item in self.action_items:
            in_path = "⭐" if item.priority in self.minimal_path else "  "
            lines.extend([
                f"### {in_path} {item.priority}. {item.description}",
                f"- **Category:** {item.category}",
                f"- **Current:** {item.current_state}",
                f"- **Target:** {item.target_state}",
                f"- **Score Gain:** +{item.estimated_score_gain} points",
                f"- **Effort:** {item.effort}",
                f"- **Rerun Stage:** `{item.stage_to_rerun}`",
                "",
                "**Concrete Steps:**",
            ])
            for step in item.concrete_steps:
                lines.append(f"  1. {step}")
            lines.append("")

        lines.extend([
            "## Minimal Path to Target",
            "",
            f"Complete items marked with ⭐ above ({len(self.minimal_path)} actions) "
            f"to reach estimated score of {self.estimated_final_score}/10.",
            "",
        ])
        return "\n".join(lines) + "\n"


def analyze_gap(
    *,
    review: ReviewSimulation,
    mining: ContributionMining | None = None,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...] = (),
    llm_provider: LLMProvider | None = None,
    target_score: int = 8,
) -> GapReport:
    """Analyze the gap between current review score and target, producing
    a ranked, actionable plan to close it.
    """
    if llm_provider is not None:
        try:
            return _llm_analyze(
                review=review,
                mining=mining,
                venue_strategy=venue_strategy,
                ledger=ledger,
                llm_provider=llm_provider,
                target_score=target_score,
            )
        except Exception:
            import logging

            logging.getLogger("autoresearch.gapanalysis").warning(
                "LLM gap analysis failed; falling back to rule-based"
            )
    return _rule_based_analyze(
        review=review,
        mining=mining,
        venue_strategy=venue_strategy,
        ledger=ledger,
        target_score=target_score,
    )


def _rule_based_analyze(
    *,
    review: ReviewSimulation,
    mining: ContributionMining | None,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    target_score: int,
) -> GapReport:
    current = review.overall_score
    gap = max(0, target_score - current)
    actions: list[ActionItem] = []
    priority = 0

    # 1. Critical weaknesses → experiment actions
    for w in review.weaknesses:
        if w.severity != "critical":
            continue
        priority += 1
        actions.append(_weakness_to_action(w, priority, venue_strategy))

    # 2. Seed/trial count → methodology action
    seed_count = len({e.trial_id for e in ledger})
    if seed_count < 5:
        priority += 1
        actions.append(
            ActionItem(
                priority=priority,
                category="methodology",
                description=f"Increase trials from {seed_count} to at least 5",
                current_state=f"{seed_count} trial(s) in ledger",
                target_state="5+ trials with different random seeds",
                estimated_score_gain=min(2, max(1, (5 - seed_count))),
                effort="low" if seed_count >= 3 else "medium",
                stage_to_rerun="experiment_loop",
                concrete_steps=(
                    f"Add {5 - seed_count} more trial configs with different seeds",
                    "Re-run experiment loop stage",
                    "Verify all trials appear in ledger with distinct trial_ids",
                ),
            )
        )

    # 3. Missing extra metrics → evidence action
    kept = [e for e in ledger if e.decision == "keep" and e.metric is not None]
    if kept and not any(e.extra_metrics for e in kept):
        priority += 1
        actions.append(
            ActionItem(
                priority=priority,
                category="evidence",
                description="Report confidence intervals and effect sizes",
                current_state="Only primary metric reported",
                target_state="Primary metric + CI + effect size for each trial",
                estimated_score_gain=1,
                effort="low",
                stage_to_rerun="experiment_loop",
                concrete_steps=(
                    "Modify experiment.py to output 95% CI in metrics.json",
                    "Add effect_size field to metrics output",
                    "Re-run experiment loop with updated evaluator",
                ),
            )
        )

    # 4. Major weaknesses → narrative/evidence actions
    for w in review.weaknesses:
        if w.severity != "major":
            continue
        priority += 1
        actions.append(_weakness_to_action(w, priority, venue_strategy))

    # 5. Venue-specific gaps
    priority += 1
    actions.append(
        ActionItem(
            priority=priority,
            category="narrative",
            description=f"Align paper narrative with {venue_strategy.display_name} expectations",
            current_state="Generic template-based prose",
            target_state=f"Venue-aware narrative: {venue_strategy.narrative_framing[:100]}...",
            estimated_score_gain=1,
            effort="medium",
            stage_to_rerun="paper_draft_revision",
            concrete_steps=(
                f"Rewrite introduction to match {venue_strategy.display_name} framing",
                "Add venue-appropriate related work positioning",
                "Align conclusion with venue expectation for limitations/scope",
            ),
        )
    )

    # 6. Contribution strengthening
    if mining and mining.contributions:
        weak_contributions = [
            c for c in mining.contributions if c.strength_score < 0.6
        ]
        if weak_contributions:
            priority += 1
            actions.append(
                ActionItem(
                    priority=priority,
                    category="evidence",
                    description=f"Strengthen {len(weak_contributions)} weak contribution(s)",
                    current_state=f"Contributions with strength < 0.6: {[c.description[:50] for c in weak_contributions]}",
                    target_state="All contributions with strength >= 0.7",
                    estimated_score_gain=min(2, len(weak_contributions)),
                    effort="high",
                    stage_to_rerun="experiment_loop",
                    concrete_steps=(
                        "Add supporting experiments for the weakest contribution",
                        "Strengthen evidence links in ledger for each claim",
                        "Re-run contribution mining to verify improvement",
                    ),
                )
            )

    if not actions:
        return GapReport(
            venue_id=venue_strategy.venue_id,
            venue_display_name=venue_strategy.display_name,
            current_score=current,
            target_score=target_score,
            gap=0,
            action_items=(),
            minimal_path=(),
            estimated_final_score=current,
            estimated_effort="low",
            summary="No gap to close — current score already meets or exceeds target.",
        )

    # Compute minimal path: greedy by score gain/effort
    effort_weight = {"low": 0.5, "medium": 1.0, "high": 2.0}
    scored_actions = sorted(
        actions,
        key=lambda a: a.estimated_score_gain / effort_weight.get(a.effort, 1.0),
        reverse=True,
    )
    cumulative = current
    minimal: list[int] = []
    for action in scored_actions:
        if cumulative >= target_score:
            break
        cumulative += action.estimated_score_gain
        minimal.append(action.priority)

    total_effort = sum(
        effort_weight.get(a.effort, 1.0) for a in actions if a.priority in minimal
    )
    estimated_effort = (
        "low" if total_effort <= 1 else
        "medium" if total_effort <= 3 else
        "high" if total_effort <= 6 else
        "very_high"
    )

    return GapReport(
        venue_id=venue_strategy.venue_id,
        venue_display_name=venue_strategy.display_name,
        current_score=current,
        target_score=target_score,
        gap=gap,
        action_items=tuple(sorted(actions, key=lambda a: a.priority)),
        minimal_path=tuple(minimal),
        estimated_final_score=min(10, cumulative),
        estimated_effort=estimated_effort,
        summary=(
            f"Close the {gap}-point gap from {current}/10 to {target_score}/10 "
            f"by completing {len(minimal)} prioritized actions "
            f"(out of {len(actions)} total identified). "
            f"Estimated effort: {estimated_effort}."
        ),
    )


def _llm_analyze(
    *,
    review: ReviewSimulation,
    mining: ContributionMining | None,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    llm_provider: LLMProvider,
    target_score: int,
) -> GapReport:
    response = llm_provider.complete_json(
        stage="gap_analysis",
        messages=(
            ("system", _gap_prompt(venue_strategy, target_score)),
            (
                "user",
                json.dumps({
                    "current_review": review.to_dict(),
                    "contributions": mining.to_dict() if mining else None,
                    "ledger_summary": [
                        {
                            "trial_id": e.trial_id,
                            "metric": e.metric,
                            "decision": e.decision,
                        }
                        for e in ledger
                    ],
                }, indent=2),
            ),
        ),
        required_keys=("action_items", "estimated_final_score", "estimated_effort", "summary"),
    )
    data = response.data
    actions = tuple(
        ActionItem(
            priority=i + 1,
            category=str(a.get("category", "evidence")),
            description=str(a.get("description", "")),
            current_state=str(a.get("current_state", "")),
            target_state=str(a.get("target_state", "")),
            estimated_score_gain=max(1, min(5, int(a.get("estimated_score_gain", 1)))),
            effort=_normalize_effort(str(a.get("effort", "medium"))),
            stage_to_rerun=str(a.get("stage_to_rerun", "experiment_loop")),
            concrete_steps=tuple(
                str(s) for s in a.get("concrete_steps", ()) if str(s).strip()
            ),
        )
        for i, a in enumerate(data.get("action_items", ()))
        if isinstance(a, dict) and str(a.get("description", "")).strip()
    )
    if not actions:
        return _rule_based_analyze(
            review=review,
            mining=mining,
            venue_strategy=venue_strategy,
            ledger=ledger,
            target_score=target_score,
        )
    # Simple greedy minimal path
    cumulative = review.overall_score
    minimal: list[int] = []
    for a in sorted(actions, key=lambda a: a.estimated_score_gain, reverse=True):
        if cumulative >= target_score:
            break
        cumulative += a.estimated_score_gain
        minimal.append(a.priority)
    return GapReport(
        venue_id=venue_strategy.venue_id,
        venue_display_name=venue_strategy.display_name,
        current_score=review.overall_score,
        target_score=target_score,
        gap=max(0, target_score - review.overall_score),
        action_items=actions,
        minimal_path=tuple(minimal),
        estimated_final_score=min(10, cumulative),
        estimated_effort=str(data.get("estimated_effort", "medium")),
        summary=str(data.get("summary", "No summary provided.")),
    )


def write_gap_report(report: GapReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_markdown(), encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _weakness_to_action(
    w: ReviewWeakness,
    priority: int,
    venue_strategy: VenueStrategy,
) -> ActionItem:
    category = "experiment" if "ablation" in w.claim.lower() or "seed" in w.claim.lower() or "trial" in w.claim.lower() else "narrative"
    if "system" in w.claim.lower() or "architecture" in w.claim.lower():
        category = "evidence"
    return ActionItem(
        priority=priority,
        category=category,
        description=f"Fix: {w.claim[:80]}",
        current_state=w.claim,
        target_state=w.suggested_fix,
        estimated_score_gain=3 if w.severity == "critical" else 2,
        effort="medium" if w.severity == "critical" else "low",
        stage_to_rerun=_rerun_stage_for(w.claim),
        concrete_steps=(
            w.suggested_fix,
            f"Verify against {venue_strategy.display_name} methodology expectations",
        ),
    )


def _rerun_stage_for(claim: str) -> str:
    claim_lower = claim.lower()
    if any(t in claim_lower for t in ("ablation", "seed", "trial", "experiment")):
        return "experiment_loop"
    if any(t in claim_lower for t in ("system", "architecture", "implementation")):
        return "experiment_generation"
    if any(t in claim_lower for t in ("prose", "narrative", "writing", "claim")):
        return "paper_draft_revision"
    return "paper_draft_revision"


def _gap_prompt(venue_strategy: VenueStrategy, target_score: int) -> str:
    return (
        f"You are a research advisor helping to close the gap between a paper's "
        f"current state and acceptance at {venue_strategy.display_name}.\n\n"
        f"## {venue_strategy.display_name} values:\n"
        + "\n".join(f"- {v}" for v in venue_strategy.reviewer_values)
        + "\n\n"
        f"## Common rejections:\n"
        + "\n".join(f"- {r}" for r in venue_strategy.common_rejections)
        + "\n\n"
        f"Given the current review, contributions, and evidence, produce a gap "
        f"analysis to reach a score of {target_score}/10. Return JSON with:\n"
        "- action_items: array of {category, description, current_state, target_state, "
        "estimated_score_gain (int 1-5), effort (low|medium|high), stage_to_rerun, "
        "concrete_steps[]}\n"
        "- estimated_final_score: int\n"
        "- estimated_effort: string\n"
        "- summary: string\n\n"
        "Order actions by impact/cost ratio. Be specific and actionable — "
        "vague advice wastes the author's time."
    )


def _normalize_effort(raw: str) -> str:
    raw_lower = raw.strip().lower()
    if raw_lower in {"high", "very_high"}:
        return "high"
    if raw_lower in {"medium", "moderate"}:
        return "medium"
    return "low"
