from __future__ import annotations

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.knowledge.cards import KnowledgeCard


def draft_paper(
    *,
    topic: str,
    cards: list[KnowledgeCard],
    ledger: list[LedgerEntry],
    decision_text: str,
) -> str:
    best = _best_kept(ledger)
    citation_sentence = _related_work_sentence(cards)
    result_sentence = (
        f"The best kept trial was `{best.trial_id}` with primary metric {best.metric}."
        if best
        else "No valid trial produced a verified metric."
    )
    trial_lines = [
        f"- `{entry.trial_id}`: metric={entry.metric}, decision={entry.decision}, status={entry.status}."
        for entry in ledger
    ]
    return "\n".join(
        [
            f"# Evidence-Grounded Study of {topic}",
            "",
            "## Abstract",
            f"We study {topic} with a local, auditable experiment pipeline. {result_sentence}",
            "",
            "## Introduction",
            "The goal is to convert a research idea into a paper candidate without losing provenance.",
            "This draft only reports evidence that exists in the run artifacts.",
            "",
            "## Related Work",
            citation_sentence,
            "",
            "## Method",
            "The current method uses a deterministic local experiment workspace with configured trials.",
            "Each trial writes structured metrics, and the pipeline keeps only metric improvements.",
            "",
            "## Experiments",
            *trial_lines,
            "",
            "## Results",
            result_sentence,
            decision_text.strip(),
            "",
            "## Limitations",
            "This is not yet a top-conference submission. The current experiment is a deterministic scaffold, so domain-specific experiments and stronger novelty analysis are still required.",
            "",
            "## Conclusion",
            "The workflow now links literature, experiment metrics, and paper text through auditable artifacts.",
            "",
        ]
    )


def _related_work_sentence(cards: list[KnowledgeCard]) -> str:
    if not cards:
        return "No screened literature is available yet."
    cited = ", ".join(f"{card.title} [@{card.citation_key}]" for card in cards)
    return f"The screened literature includes {cited}."


def _best_kept(ledger: list[LedgerEntry]) -> LedgerEntry | None:
    kept = [entry for entry in ledger if entry.decision == "keep" and entry.metric is not None]
    return kept[-1] if kept else None
