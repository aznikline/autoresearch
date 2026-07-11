from __future__ import annotations

import json
import re
from pathlib import Path

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.strategy.models import (
    ReviewSimulation,
    ReviewWeakness,
    VenueStrategy,
)


def simulate_review(
    *,
    paper_markdown: str,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    llm_provider: LLMProvider | None = None,
    prior_reviews: str = "",
) -> ReviewSimulation:
    """Simulate a venue-specific review of a paper draft.

    Uses venue strategy profiles to generate structured feedback that
    mimics what real reviewers at this venue would flag. When an LLM
    provider is available, it generates richer, venue-aware critique.
    Without one, falls back to deterministic rule-based simulation
    using the venue strategy and evidence ledger.
    """
    if llm_provider is not None:
        return _llm_review(
            paper_markdown=paper_markdown,
            venue_strategy=venue_strategy,
            ledger=ledger,
            llm_provider=llm_provider,
            prior_reviews=prior_reviews,
        )
    return _rule_based_review(
        paper_markdown=paper_markdown,
        venue_strategy=venue_strategy,
        ledger=ledger,
    )


def _llm_review(
    *,
    paper_markdown: str,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
    llm_provider: LLMProvider,
    prior_reviews: str,
) -> ReviewSimulation:
    ledger_summary = _ledger_summary(ledger)
    prompt = _build_reviewer_prompt(
        venue_strategy=venue_strategy,
        paper_markdown=paper_markdown,
        ledger_summary=ledger_summary,
        prior_reviews=prior_reviews,
    )
    try:
        response = llm_provider.complete_json(
            stage="reviewer_simulation",
            messages=(
                ("system", prompt),
                (
                    "user",
                    f"Review this paper as a {venue_strategy.display_name} reviewer.",
                ),
            ),
            required_keys=(
                "overall_score",
                "confidence",
                "strengths",
                "weaknesses",
                "suggested_experiments",
                "narrative_suggestions",
                "summary",
            ),
        )
        data = response.data
        weaknesses = tuple(
            ReviewWeakness(
                claim=str(w.get("claim", "")),
                severity=_normalize_severity(str(w.get("severity", "minor"))),
                suggested_fix=str(w.get("suggested_fix", "")),
                missing_evidence=tuple(
                    str(e)
                    for e in w.get("missing_evidence", ())
                    if str(e).strip()
                ),
            )
            for w in data.get("weaknesses", ())
            if isinstance(w, dict) and str(w.get("claim", "")).strip()
        )
        return ReviewSimulation(
            venue_id=venue_strategy.venue_id,
            overall_score=max(1, min(10, int(data.get("overall_score", 5)))),
            confidence=min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
            strengths=tuple(
                str(s)
                for s in data.get("strengths", ())
                if str(s).strip()
            ),
            weaknesses=weaknesses,
            suggested_experiments=tuple(
                str(e)
                for e in data.get("suggested_experiments", ())
                if str(e).strip()
            ),
            narrative_suggestions=tuple(
                str(n)
                for n in data.get("narrative_suggestions", ())
                if str(n).strip()
            ),
            summary=str(data.get("summary", "No summary provided.")),
        )
    except Exception:
        import logging

        logging.getLogger("autoresearch.strategy.reviewer").warning(
            "LLM reviewer simulation failed; falling back to rule-based"
        )
    return _rule_based_review(
        paper_markdown=paper_markdown,
        venue_strategy=venue_strategy,
        ledger=ledger,
    )


def _rule_based_review(
    *,
    paper_markdown: str,
    venue_strategy: VenueStrategy,
    ledger: tuple[LedgerEntry, ...],
) -> ReviewSimulation:
    """Deterministic review using venue strategy heuristics and ledger data."""
    strengths: list[str] = []
    weaknesses: list[ReviewWeakness] = []
    suggestions: list[str] = []
    narrative: list[str] = []

    # Structural checks
    if "limitations" not in paper_markdown.lower():
        weaknesses.append(
            ReviewWeakness(
                claim="limitations",
                severity="major",
                suggested_fix="Add a dedicated Limitations section with at least 3 concrete limitations.",
                missing_evidence=("limitations_section",),
            )
        )

    if "ablation" not in paper_markdown.lower():
        weaknesses.append(
            ReviewWeakness(
                claim="ablations",
                severity="critical",
                suggested_fix="Add ablation experiments isolating each proposed component's contribution.",
                missing_evidence=("ablation_results",),
            )
        )

    # Venue-specific checks
    if venue_strategy.venue_id in {"icml", "neurips"} and not re.search(
        r"\\begin\{(theorem|proof|lemma|proposition)\}", paper_markdown
    ):
        suggestions.append(
            "Consider adding a formal theorem or proof sketch — "
            f"{venue_strategy.display_name} reviewers expect theoretical grounding."
        )

    if venue_strategy.venue_id in {"vldb", "sigmod", "icde"} and not re.search(
        r"(system|architecture|implementation|deployment)",
        paper_markdown,
        re.IGNORECASE,
    ):
        weaknesses.append(
            ReviewWeakness(
                claim="systems contribution",
                severity="critical",
                suggested_fix=(
                    "Describe the system architecture with a diagram and "
                    "discuss engineering trade-offs."
                ),
                missing_evidence=("system_description", "architecture_diagram"),
            )
        )

    # Narrative suggestions from venue strategy
    narrative.append(
        f"{venue_strategy.display_name} narrative strategy: "
        f"{venue_strategy.narrative_framing[:200]}"
    )

    # Evidence checks from ledger
    kept = [e for e in ledger if e.decision == "keep" and e.metric is not None]
    if kept:
        best = kept[-1]
        strengths.append(
            f"Best experimental result: {best.metric} "
            f"(trial {best.trial_id}, metric: {best.metric_definition})"
        )
    else:
        weaknesses.append(
            ReviewWeakness(
                claim="experimental evidence",
                severity="critical",
                suggested_fix=(
                    "Run experiments with at least one kept result in the ledger."
                ),
                missing_evidence=("kept_ledger_entry",),
            )
        )

    # Seed count check
    seed_count = len({e.trial_id for e in ledger})
    if seed_count < 5:
        weaknesses.append(
            ReviewWeakness(
                claim=f"only {seed_count} trial(s) in ledger",
                severity="major",
                suggested_fix=(
                    f"Run at least 5 trials with different random seeds. "
                    f"{venue_strategy.display_name} expects multiple seeds."
                ),
                missing_evidence=("multi_seed_results",),
            )
        )

    # Extra metrics check
    entries_with_extra = [e for e in kept if e.extra_metrics]
    if not entries_with_extra and kept:
        suggestions.append(
            "Report confidence intervals or effect sizes — "
            f"{venue_strategy.display_name} reviewers value statistical rigor."
        )

    # Compute score heuristically
    critical_count = sum(1 for w in weaknesses if w.severity == "critical")
    major_count = sum(1 for w in weaknesses if w.severity == "major")
    minor_count = sum(1 for w in weaknesses if w.severity == "minor")
    score = max(1, 10 - critical_count * 3 - major_count * 2 - minor_count)
    confidence = 0.3 + 0.05 * len(kept)  # more evidence = more confident

    return ReviewSimulation(
        venue_id=venue_strategy.venue_id,
        overall_score=score,
        confidence=min(1.0, confidence),
        strengths=tuple(strengths) if strengths else ("no strengths identified",),
        weaknesses=tuple(weaknesses),
        suggested_experiments=tuple(suggestions),
        narrative_suggestions=tuple(narrative),
        summary=(
            f"Rule-based {venue_strategy.display_name} review: "
            f"score {score}/10, {len(weaknesses)} weaknesses "
            f"({critical_count} critical, {major_count} major)."
        ),
    )


def compare_venue_reviews(
    *,
    paper_markdown: str,
    venue_strategies: tuple[VenueStrategy, ...],
    ledger: tuple[LedgerEntry, ...],
    llm_provider: LLMProvider | None = None,
) -> dict[str, ReviewSimulation]:
    """Simulate reviews across multiple venues for direct comparison."""
    results: dict[str, ReviewSimulation] = {}
    for strategy in venue_strategies:
        results[strategy.venue_id] = simulate_review(
            paper_markdown=paper_markdown,
            venue_strategy=strategy,
            ledger=ledger,
            llm_provider=llm_provider,
        )
    return results


def write_review_report(
    review: ReviewSimulation,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(review.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _build_reviewer_prompt(
    *,
    venue_strategy: VenueStrategy,
    paper_markdown: str,
    ledger_summary: str,
    prior_reviews: str,
) -> str:
    return (
        f"You are a reviewer for {venue_strategy.display_name}.\n\n"
        f"## What {venue_strategy.display_name} reviewers value (ordered):\n"
        + "\n".join(
            f"- {value}" for value in venue_strategy.reviewer_values
        )
        + "\n\n"
        f"## Common rejection reasons at {venue_strategy.display_name}:\n"
        + "\n".join(
            f"- {reason}" for reason in venue_strategy.common_rejections
        )
        + "\n\n"
        f"## High-score indicators:\n"
        + "\n".join(
            f"- {indicator}" for indicator in venue_strategy.high_score_indicators
        )
        + "\n\n"
        f"## Methodology expectations:\n"
        f"{venue_strategy.methodology_expectations}\n\n"
        f"## Known reviewer biases:\n"
        + "\n".join(
            f"- {bias}" for bias in venue_strategy.known_biases
        )
        + "\n\n"
        + (f"## Prior reviews to consider:\n{prior_reviews}\n\n" if prior_reviews else "")
        + "## Paper to review:\n\n"
        + paper_markdown[:12000]
        + "\n\n"
        "## Evidence ledger summary:\n"
        + ledger_summary
        + "\n\n"
        "Return JSON with: overall_score (int 1-10), confidence (float 0-1), "
        "strengths (string array), weaknesses (array of {claim, severity, "
        "suggested_fix, missing_evidence[]}), suggested_experiments (string array), "
        "narrative_suggestions (string array), summary (string). "
        "Be honest and critical — this is a real review simulation, not encouragement."
    )


def _ledger_summary(ledger: tuple[LedgerEntry, ...]) -> str:
    if not ledger:
        return "No experiments recorded."
    lines = [f"Total trials: {len(ledger)}"]
    kept = [e for e in ledger if e.decision == "keep" and e.metric is not None]
    lines.append(f"Kept trials: {len(kept)}")
    if kept:
        best = kept[-1]
        lines.append(f"Best metric: {best.metric} ({best.metric_definition})")
        lines.append(f"Best trial: {best.trial_id}")
    for entry in ledger:
        lines.append(
            f"  [{entry.decision}] {entry.trial_id}: "
            f"metric={entry.metric}, status={entry.status}"
        )
    return "\n".join(lines)


def _normalize_severity(raw: str) -> str:
    raw_lower = raw.strip().lower()
    if raw_lower in {"critical"}:
        return "critical"
    if raw_lower in {"major", "high"}:
        return "major"
    return "minor"
