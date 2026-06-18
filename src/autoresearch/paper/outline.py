from __future__ import annotations

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.knowledge.cards import KnowledgeCard


def build_outline(
    *,
    topic: str,
    cards: list[KnowledgeCard],
    ledger: list[LedgerEntry],
) -> str:
    best = _best_kept(ledger)
    lines = [
        "# Paper Outline",
        "",
        f"Working title: Evidence-Grounded Study of {topic}",
        "",
        "## Abstract",
        "- State the research question, evidence source, best metric, and limitation.",
        "",
        "## Introduction",
        "- Motivate the topic and why the experiment is narrow but reproducible.",
        "",
        "## Related Work",
    ]
    for card in cards:
        lines.append(f"- Discuss {card.title} [@{card.citation_key}].")
    lines.extend(
        [
            "",
            "## Method",
            "- Describe the deterministic local experiment and trial variants.",
            "",
            "## Experiments",
            "- Report every trial in the ledger and the keep/discard decision.",
            "",
            "## Results",
            f"- Best kept trial: {best.trial_id if best else 'none'}.",
            "",
            "## Limitations",
            "- Clarify that this is a local scaffold until domain experiments replace the toy task.",
            "",
            "## Conclusion",
            "- Summarize what the evidence supports and what must be improved next.",
        ]
    )
    return "\n".join(lines) + "\n"


def _best_kept(ledger: list[LedgerEntry]) -> LedgerEntry | None:
    kept = [entry for entry in ledger if entry.decision == "keep" and entry.metric is not None]
    return kept[-1] if kept else None
