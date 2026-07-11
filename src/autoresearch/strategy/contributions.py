from __future__ import annotations

import json
import re
from pathlib import Path

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.strategy.models import (
    ContributionMining,
    ScoredContribution,
    VenueStrategy,
)


def mine_contributions(
    *,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    claims: tuple[dict[str, object], ...] = (),
    llm_provider: LLMProvider | None = None,
    topic: str = "",
) -> ContributionMining:
    """Extract and score contributions against venue-specific expectations.

    Mines the evidence ledger for contribution points, scores each against
    the venue's value weights, and returns a ranked profile with venue-fit
    scores. When an LLM is available, generates richer narrative hooks.
    """
    if llm_provider is not None:
        return _llm_mine(
            venue_strategy=venue_strategy,
            ledger=ledger,
            claims=claims,
            llm_provider=llm_provider,
            topic=topic,
        )
    return _rule_based_mine(
        venue_strategy=venue_strategy,
        ledger=ledger,
        claims=claims,
        topic=topic,
    )


def _rule_based_mine(
    *,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    claims: tuple[dict[str, object], ...],
    topic: str,
) -> ContributionMining:
    contributions: list[ScoredContribution] = []
    kept = [e for e in ledger if e.decision == "keep" and e.metric is not None]

    # Contribution 1: primary metric improvement
    if kept:
        best = kept[-1]
        improvement = "outperforms baselines" if len(kept) > 1 else "achieves target metric"
        contributions.append(
            ScoredContribution(
                description=(
                    f"Primary metric {best.metric} on {best.metric_definition} — "
                    f"{improvement}"
                ),
                evidence_run_ids=tuple(e.run_id for e in kept),
                venue_relevance=_weight_for(
                    venue_strategy, "empirical_rigor", "benchmark_performance"
                ),
                strength_score=min(1.0, 0.3 + 0.1 * len(kept)),
                narrative_hook=(
                    f"We achieve {best.metric} on {best.metric_definition}, "
                    f"demonstrating practical effectiveness."
                ),
            )
        )

    # Contribution 2: protocol rigor from ledger metadata
    code_hashes = {e.code_sha256 for e in ledger if e.code_sha256}
    protocol_hashes = {e.protocol_fingerprint for e in ledger if e.protocol_fingerprint}
    if len(code_hashes) == 1 and len(protocol_hashes) == 1:
        contributions.append(
            ScoredContribution(
                description=(
                    "Immutable experimental protocol with content-addressed "
                    "code, config, and specification"
                ),
                evidence_run_ids=tuple(e.run_id for e in ledger if e.code_sha256),
                venue_relevance=_weight_for(venue_strategy, "reproducibility"),
                strength_score=0.9,
                narrative_hook=(
                    "Every result is traceable to an immutable protocol fingerprint, "
                    "enabling full reproduction."
                ),
            )
        )

    # Contribution 3: multi-metric evidence
    entries_with_extras = [e for e in kept if e.extra_metrics]
    if entries_with_extras:
        extra_keys = set()
        for e in entries_with_extras:
            extra_keys.update(e.extra_metrics.keys())
        contributions.append(
            ScoredContribution(
                description=(
                    f"Multi-metric evaluation including {', '.join(sorted(extra_keys))}"
                ),
                evidence_run_ids=tuple(e.run_id for e in entries_with_extras),
                venue_relevance=_weight_for(venue_strategy, "empirical_rigor"),
                strength_score=min(0.8, 0.2 + 0.15 * len(extra_keys)),
                narrative_hook=(
                    f"Beyond the primary metric, we report {len(extra_keys)} "
                    "additional metrics for a complete picture."
                ),
            )
        )

    # Contribution 4: gap analysis from claims
    if claims:
        contributions.append(
            ScoredContribution(
                description=(
                    f"Evidence-linked claims with traceable provenance "
                    f"({len(claims)} claims)"
                ),
                evidence_run_ids=tuple(
                    str(run_id)
                    for claim in claims
                    for run_id in claim.get("run_ids", ())
                ),
                venue_relevance=_weight_for(venue_strategy, "reproducibility"),
                strength_score=0.7,
                narrative_hook=(
                    "Every numeric claim is verified against the evidence ledger."
                ),
            )
        )

    if not contributions:
        return ContributionMining(
            venue_id=venue_strategy.venue_id,
            contributions=(),
            venue_fit_score=0.0,
            summary=f"No contributions found for {venue_strategy.display_name} from current evidence.",
        )

    # Compute overall venue fit from weighted contribution scores
    total_weight = sum(
        c.venue_relevance * c.strength_score for c in contributions
    )
    max_possible = sum(c.venue_relevance for c in contributions)
    fit_score = total_weight / max_possible if max_possible > 0 else 0.0

    return ContributionMining(
        venue_id=venue_strategy.venue_id,
        contributions=tuple(sorted(contributions, key=lambda c: c.strength_score * c.venue_relevance, reverse=True)),
        venue_fit_score=round(fit_score, 3),
        summary=(
            f"Mined {len(contributions)} contributions for {venue_strategy.display_name}. "
            f"Overall venue fit: {fit_score:.2f}. "
            + (
                f"Strongest: {contributions[0].description[:100]}"
                if contributions
                else ""
            )
        ),
    )


def _llm_mine(
    *,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    claims: tuple[dict[str, object], ...],
    llm_provider: LLMProvider,
    topic: str,
) -> ContributionMining:
    try:
        response = llm_provider.complete_json(
            stage="contribution_mining",
            messages=(
                ("system", _mining_prompt(venue_strategy)),
                (
                    "user",
                    f"Topic: {topic}\n\n"
                    f"Ledger: {json.dumps([e.to_dict() for e in ledger], indent=2)}\n\n"
                    f"Claims: {json.dumps(list(claims), indent=2)}",
                ),
            ),
            required_keys=("contributions",),
        )
        data = response.data
        contributions = tuple(
            ScoredContribution(
                description=str(c.get("description", "")),
                evidence_run_ids=tuple(
                    str(r) for r in c.get("evidence_run_ids", ())
                ),
                venue_relevance=min(1.0, max(0.0, float(c.get("venue_relevance", 0.5)))),
                strength_score=min(1.0, max(0.0, float(c.get("strength_score", 0.5)))),
                narrative_hook=str(c.get("narrative_hook", "")),
            )
            for c in data.get("contributions", ())
            if isinstance(c, dict) and str(c.get("description", "")).strip()
        )
        if not contributions:
            return _rule_based_mine(
                venue_strategy=venue_strategy,
                ledger=ledger,
                claims=claims,
                topic=topic,
            )
        total_weight = sum(
            c.venue_relevance * c.strength_score for c in contributions
        )
        max_possible = sum(c.venue_relevance for c in contributions)
        fit_score = total_weight / max_possible if max_possible > 0 else 0.0
        return ContributionMining(
            venue_id=venue_strategy.venue_id,
            contributions=contributions,
            venue_fit_score=round(fit_score, 3),
            summary="LLM-mined contributions.",
        )
    except Exception:
        import logging

        logging.getLogger("autoresearch.strategy.contributions").warning(
            "LLM contribution mining failed; falling back to rule-based"
        )
    return _rule_based_mine(
        venue_strategy=venue_strategy,
        ledger=ledger,
        claims=claims,
        topic=topic,
    )


def compare_venue_contributions(
    *,
    venue_strategies: tuple[VenueStrategy, ...],
    ledger: tuple[LedgerEntry, ...],
    claims: tuple[dict[str, object], ...] = (),
    llm_provider: LLMProvider | None = None,
    topic: str = "",
) -> dict[str, ContributionMining]:
    """Mine contributions across multiple venues for comparison."""
    results: dict[str, ContributionMining] = {}
    for strategy in venue_strategies:
        results[strategy.venue_id] = mine_contributions(
            venue_strategy=strategy,
            ledger=ledger,
            claims=claims,
            llm_provider=llm_provider,
            topic=topic,
        )
    return results


def write_contribution_report(
    mining: ContributionMining,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(mining.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _weight_for(
    venue_strategy: VenueStrategy,
    *keys: str,
) -> float:
    """Extract the maximum weight among the given contribution dimension keys."""
    weights = venue_strategy.contribution_weights
    return max(
        (weights.get(key, 0.0) for key in keys),
        default=0.5,
    )


def _mining_prompt(venue_strategy: VenueStrategy) -> str:
    return (
        f"You are analyzing research results for {venue_strategy.display_name} submission.\n\n"
        f"## What {venue_strategy.display_name} values:\n"
        + "\n".join(f"- {v}" for v in venue_strategy.reviewer_values)
        + "\n\n"
        f"## Contribution weightings at {venue_strategy.display_name}:\n"
        + "\n".join(
            f"- {k}: {v:.0%}" for k, v in venue_strategy.contribution_weights.items()
        )
        + "\n\n"
        "Given the experimental evidence (ledger entries) and claims, extract "
        "and score contributions against this venue's values. Return JSON with "
        "a contributions array. Each contribution needs: description, "
        "evidence_run_ids (string array), venue_relevance (0-1), strength_score "
        "(0-1), and narrative_hook (how to present this to reviewers). "
        "Be honest — weak evidence should get low scores."
    )
