from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from autoresearch.adapters.llm.base import LLMProvider, TextLLMResponse
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.knowledge.cards import KnowledgeCard


SYSTEM_PROMPT = (
    "You are a research paper writer producing venue-grade prose for a research "
    "submission. Rewrite the given template section into polished academic prose. "
    "Rules you MUST obey: (1) Keep every numeric value identical to the ledger values "
    "provided — do not round, invent, or alter any number. (2) Do not introduce claims, "
    "datasets, baselines, or results absent from the ledger and citations provided. "
    "(3) Do not claim novelty, correctness, or venue readiness from your own judgment; "
    "frame contributions only as what the experimental evidence shows. (4) Preserve the "
    "section heading. (5) Output only the section markdown, no preamble."
)

SECTION_HEADINGS = (
    "## Abstract",
    "## Introduction",
    "## Related Work",
    "## Method",
    "## Experiments",
    "## Results",
    "## Limitations",
    "## Conclusion",
)


@dataclass(frozen=True)
class ProseContext:
    topic: str
    ledger: tuple[LedgerEntry, ...]
    cards: tuple[KnowledgeCard, ...]
    decision_text: str


def rewrite_paper_to_prose(
    *,
    template_draft: str,
    context: ProseContext,
    provider: LLMProvider,
    stage: str = "paper_prose",
) -> str:
    """Rewrite a template draft into venue-grade prose, section by section.

    Each recognized section heading triggers one LLM call that rewrites that section's
    body using the ledger and citation cards as grounded evidence. Sections not in
    SECTION_HEADINGS (e.g. the title line) are passed through unchanged.
    """
    sections = _split_sections(template_draft)
    rewritten: list[str] = []
    ledger_digest = _ledger_digest(context.ledger)
    cards_digest = _cards_digest(context.cards)
    for heading, body in sections:
        if heading in SECTION_HEADINGS:
            user_prompt = _section_prompt(
                heading=heading,
                body=body,
                topic=context.topic,
                ledger_digest=ledger_digest,
                cards_digest=cards_digest,
                decision_text=context.decision_text,
            )
            section_stage = f"{stage}:{heading.lstrip('# ').lower().replace(' ', '_')}"
            response = _call_with_retry(
                provider,
                stage=section_stage,
                messages=(
                    ("system", SYSTEM_PROMPT),
                    ("user", user_prompt),
                ),
            )
            if response is not None:
                rewritten.append(_ensure_heading(response.text.strip(), heading))
            else:
                # Per-section fail-soft: keep the template body for THIS section only
                # and continue, so one bad LLM call never sinks the whole paper.
                logging.getLogger("autoresearch.paper.prose").warning(
                    "prose rewrite failed for %s after retries; keeping template body",
                    heading,
                )
                rewritten.append(
                    (heading + "\n" + body).rstrip() if body else heading
                )
        else:
            rewritten.append((heading + "\n" + body).rstrip() if heading else body)
    return "\n\n".join(part for part in rewritten if part is not None and part.strip() != "")


def _call_with_retry(
    provider: LLMProvider,
    *,
    stage: str,
    messages: tuple[tuple[str, str], ...],
    retries: int = 3,
    backoff_sec: float = 1.0,
) -> TextLLMResponse | None:
    """Call complete_text with bounded retries; return None on final failure.

    One section's transient failure (timeout, bad response, network) must not
    cascade to abandoning the whole paper. The caller keeps the template body
    for the failed section and continues.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return provider.complete_text(stage=stage, messages=messages)
        except Exception as exc:  # noqa: BLE001 — bounded retry, fail-soft per section
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff_sec * (2**attempt))
    logging.getLogger("autoresearch.paper.prose").warning(
        "complete_text failed for %s after %d retries: %s", stage, retries, last_exc
    )
    return None


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs.

    A heading is a line starting with '##'. Text before the first heading
    (e.g. the '# Title' line) is returned with an empty heading.
    """
    lines = markdown.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_body: list[str] = []
    flushed_title = False
    for line in lines:
        if line.startswith("## "):
            if current_heading or current_body or not flushed_title:
                sections.append((current_heading, "\n".join(current_body).strip()))
            current_heading = line
            current_body = []
        elif line.startswith("# ") and not sections and not current_heading:
            sections.append((line, ""))
            flushed_title = True
        else:
            current_body.append(line)
    sections.append((current_heading, "\n".join(current_body).strip()))
    return sections


def _section_prompt(
    *,
    heading: str,
    body: str,
    topic: str,
    ledger_digest: str,
    cards_digest: str,
    decision_text: str,
) -> str:
    return (
        f"Topic: {topic}\n\n"
        f"Section to rewrite: {heading}\n\n"
        f"Template section content (rewrite this):\n{body or '(empty — write this section from scratch using the evidence below)'}\n\n"
        f"Verified experiment ledger (use ONLY these numbers):\n{ledger_digest}\n\n"
        f"Screened citations (cite only these):\n{cards_digest}\n\n"
        f"Result analysis decision:\n{decision_text.strip()}\n\n"
        f"Rewrite the section as venue-grade prose under the heading {heading}."
    )


def _ledger_digest(ledger: tuple[LedgerEntry, ...]) -> str:
    """Build a compact digest of verified trial metrics for the LLM prompt.

    Capped to keep the per-section prompt small enough for the model to respond
    within the provider timeout. The full per-trial numbers are already present
    in the template draft body (which the LLM also sees and rewrites), so the
    digest only needs to attest which numbers are ledger-verified; the prose
    writer lifts specifics from the template body, not from this digest.
    """
    if not ledger:
        return "(no verified trials)"
    # Keep the first 12 entries (spanning all estimator families given the
    # trial ordering) plus a count of the remainder.
    capped = ledger[:12]
    lines = []
    for entry in capped:
        parts = [f"primary_metric={entry.metric}"]
        for key, value in entry.extra_metrics.items():
            parts.append(f"{key}={value}")
        lines.append(
            f"- {entry.trial_id}: {', '.join(parts)}, "
            f"decision={entry.decision}, status={entry.status}"
        )
    if len(ledger) > len(capped):
        lines.append(f"- (and {len(ledger) - len(capped)} more verified trials in the template body below)")
    return "\n".join(lines)


def _cards_digest(cards: tuple[KnowledgeCard, ...]) -> str:
    if not cards:
        return "(no screened citations)"
    # Cap the digest to keep each LLM section prompt small enough for the model
    # to respond within the provider timeout. The full citation list is still
    # available to the export stage (references.bib); the prose writer only
    # needs a representative subset to cite from.
    capped = cards[:25]
    lines = [f"- {card.title} [@{card.citation_key}]" for card in capped]
    if len(cards) > len(capped):
        lines.append(f"- (and {len(cards) - len(capped)} more screened citations available)")
    return "\n".join(lines)


def _ensure_heading(text: str, heading: str) -> str:
    """Guarantee the rewritten section starts with the expected heading."""
    stripped = text.lstrip()
    if stripped.startswith(heading):
        return text
    return f"{heading}\n\n{stripped}"


__all__ = ["ProseContext", "rewrite_paper_to_prose", "SECTION_HEADINGS"]
