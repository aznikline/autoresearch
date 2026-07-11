from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.strategy.models import VenueStrategy


@dataclass(frozen=True)
class VenueProseOutput:
    venue_id: str
    venue_display_name: str
    abstract: str
    introduction: str
    related_work_positioning: str
    conclusion: str
    full_paper: str
    changes_summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_markdown(self) -> str:
        return (
            f"# Venue-Aware Prose: {self.venue_display_name}\n\n"
            f"{self.changes_summary}\n\n"
            f"## Abstract\n\n{self.abstract}\n\n"
            f"## Introduction\n\n{self.introduction}\n\n"
            f"## Related Work Positioning\n\n{self.related_work_positioning}\n\n"
            f"## Conclusion\n\n{self.conclusion}\n\n"
            f"---\n\n## Full Paper\n\n{self.full_paper}\n"
        )


class VenueProseGenerator:
    """Rewrite key paper sections to match venue-specific narrative expectations.

    The same experimental results framed differently:
    - NeurIPS: "We discover a novel mechanism that explains..."
    - VLDB: "We build a system that achieves... through the following design decisions..."
    - ACL: "We show that language exhibits... which enables..."
    """

    def __init__(
        self,
        venue_strategy: VenueStrategy,
        *,
        paper_markdown: str,
        ledger: tuple[LedgerEntry, ...] = (),
        topic: str = "",
    ) -> None:
        self.venue_strategy = venue_strategy
        self.paper = paper_markdown
        self.ledger = ledger
        self.topic = topic

    def generate(
        self,
        *,
        llm_provider: LLMProvider | None = None,
    ) -> VenueProseOutput:
        if llm_provider is not None:
            try:
                return self._llm_generate(llm_provider)
            except Exception:
                import logging

                logging.getLogger("autoresearch.prose").warning(
                    "LLM prose generation failed; falling back to rule-based"
                )
        return self._rule_based_generate()

    def _llm_generate(self, llm_provider: LLMProvider) -> VenueProseOutput:
        strategy = self.venue_strategy
        response = llm_provider.complete_json(
            stage="venue_prose",
            messages=(
                ("system", self._prose_prompt()),
                ("user", f"Rewrite this paper for {strategy.display_name}:\n\n{self.paper[:15000]}"),
            ),
            required_keys=(
                "abstract",
                "introduction",
                "related_work_positioning",
                "conclusion",
                "full_paper",
                "changes_summary",
            ),
        )
        data = response.data
        return VenueProseOutput(
            venue_id=strategy.venue_id,
            venue_display_name=strategy.display_name,
            abstract=str(data.get("abstract", "")),
            introduction=str(data.get("introduction", "")),
            related_work_positioning=str(data.get("related_work_positioning", "")),
            conclusion=str(data.get("conclusion", "")),
            full_paper=str(data.get("full_paper", self.paper)),
            changes_summary=str(data.get("changes_summary", "LLM-generated venue-aware prose.")),
        )

    def _rule_based_generate(self) -> VenueProseOutput:
        """Rule-based prose adaptation using venue strategy heuristics."""
        strategy = self.venue_strategy
        current_sections = _parse_sections(self.paper)

        # Generate venue-appropriate abstract
        abstract = self._generate_abstract(current_sections)

        # Generate venue-appropriate introduction
        introduction = self._generate_introduction(current_sections)

        # Generate related work positioning
        related_work = self._generate_related_work(current_sections)

        # Generate conclusion
        conclusion = self._generate_conclusion(current_sections)

        # Assemble full paper with venue-appropriate section ordering
        full_paper = self._assemble_paper(
            abstract=abstract,
            introduction=introduction,
            sections=current_sections,
            related_work=related_work,
            conclusion=conclusion,
        )

        changes = [
            f"Abstract rewritten for {strategy.display_name} framing",
            f"Introduction aligned with {strategy.display_name} narrative strategy",
            f"Related work positioned for {strategy.display_name} reviewer expectations",
            f"Conclusion addresses {strategy.display_name} scope/limitations expectations",
        ]

        return VenueProseOutput(
            venue_id=strategy.venue_id,
            venue_display_name=strategy.display_name,
            abstract=abstract,
            introduction=introduction,
            related_work_positioning=related_work,
            conclusion=conclusion,
            full_paper=full_paper,
            changes_summary="\n".join(f"- {c}" for c in changes),
        )

    def _generate_abstract(self, sections: dict[str, str]) -> str:
        strategy = self.venue_strategy
        venue_id = strategy.venue_id
        best_metric = self._best_metric_text()

        templates = {
            "neurips": (
                f"We present a novel approach to {self.topic or 'the research problem'}. "
                f"Our key insight is that [mechanism] enables [capability], which prior "
                f"methods cannot achieve because [fundamental limitation]. "
                f"Through rigorous experiments with {best_metric}, we demonstrate "
                f"that our method [result]. Ablation studies isolate the contribution "
                f"of each component, and we discuss limitations and broader impact."
            ),
            "icml": (
                f"We propose a new method for {self.topic or 'the learning problem'} "
                f"with formal guarantees. Our approach achieves {best_metric} while "
                f"providing [theoretical property]. We prove that [theorem sketch] "
                f"and validate empirically across [domains]. Statistical significance "
                f"tests confirm that improvements are not due to variance."
            ),
            "iclr": (
                f"We investigate what representations emerge when [training paradigm] "
                f"is applied to {self.topic or 'the learning problem'}. Our analysis "
                f"reveals that [representation property], which explains why prior "
                f"methods [behavior]. We validate this understanding through "
                f"controlled experiments achieving {best_metric}."
            ),
            "vldb": (
                f"We build and evaluate a system for {self.topic or 'data management'}. "
                f"Our design addresses [practical challenge] through [architectural "
                f"decision], achieving {best_metric}. We compare against [baselines] "
                f"on standard benchmarks and discuss engineering trade-offs. "
                f"Code and data are available for reproduction."
            ),
            "sigmod": (
                f"We present a data management system that advances {self.topic or 'query processing'}. "
                f"Our approach introduces [technique] which achieves {best_metric} "
                f"on standard benchmarks while maintaining [property]. We provide "
                f"a formal analysis of [property] and validate with reproducible experiments."
            ),
            "acl": (
                f"We study {self.topic or 'a linguistic phenomenon'} through "
                f"[computational approach]. Our findings reveal that [linguistic insight], "
                f"which challenges the assumption that [prior belief]. "
                f"Experiments across [languages/domains] achieve {best_metric}, "
                f"and analysis shows [generalization property]. We release code, "
                f"data, and models to facilitate reproduction."
            ),
            "cvpr": (
                f"We introduce a novel visual approach for {self.topic or 'computer vision'}. "
                f"Our method achieves {best_metric} through [architectural innovation] "
                f"that enables [visual capability]. Qualitative results demonstrate "
                f"[visual property], and thorough ablation identifies [key component] "
                f"as the primary driver of improvement. Code and pretrained models are released."
            ),
        }

        abstract = templates.get(
            venue_id,
            f"We present work on {self.topic or 'the research problem'}, "
            f"achieving {best_metric}. Our approach addresses [gap] through [method]. "
            f"We validate with experiments and discuss limitations.",
        )

        return abstract

    def _generate_introduction(self, sections: dict[str, str]) -> str:
        strategy = self.venue_strategy
        narrative = strategy.narrative_framing

        existing_intro = sections.get("introduction", "")
        if existing_intro:
            first_paragraph = existing_intro.split("\n\n")[0] if existing_intro else ""
        else:
            first_paragraph = f"## Introduction\n\nWe address {self.topic or 'an important research problem'}."

        venue_intro_guidance = {
            "neurips": (
                "\n\n*[NeurIPS framing: Lead with the insight or mechanism. "
                "Answer: what did we discover about how learning works?]*\n\n"
            ),
            "icml": (
                "\n\n*[ICML framing: Start with the learning problem. "
                "State the gap in current methods precisely. Signal that "
                "theory accompanies experiments.]*\n\n"
            ),
            "vldb": (
                "\n\n*[VLDB framing: Lead with the problem the system solves. "
                "Explain why existing systems fall short. Preview the architecture "
                "and design trade-offs.]*\n\n"
            ),
            "acl": (
                "\n\n*[ACL framing: Frame as advancing NLP — what do we now "
                "understand about language that we didn't before? Accessible "
                "to any ACL reviewer, not just your subarea.]*\n\n"
            ),
        }

        guidance = venue_intro_guidance.get(
            strategy.venue_id,
            f"\n\n*[{strategy.display_name} framing: {narrative[:200]}]*\n\n",
        )

        return first_paragraph + guidance + (
            f"This work addresses a gap in the current understanding of "
            f"{self.topic or 'the problem domain'}. Our contribution is "
            f"[contribution type]. The remainder of this paper is organized "
            f"as follows: Section 2 reviews related work, Section 3 describes "
            f"our approach, Section 4 presents experimental results, and "
            f"Section 5 concludes with limitations and future directions."
        )

    def _generate_related_work(self, sections: dict[str, str]) -> str:
        strategy = self.venue_strategy
        existing = sections.get("related work", sections.get("related_work", ""))

        venue_rw_guidance = {
            "neurips": "Position the gap — not just list prior art. What does prior work miss that you address?",
            "icml": "Connect to formal results where possible. Differentiate from most similar prior work explicitly.",
            "vldb": "Compare against deployed or widely-used systems. What do real users do today?",
            "acl": "Cover the last 2 years of ACL/EMNLP/NAACL. Acknowledge that LLM-based methods are a moving target.",
            "cvpr": "Include very recent arxiv preprints. The field moves fast — missing a 3-month-old baseline is a rejection risk.",
        }

        guidance = venue_rw_guidance.get(
            strategy.venue_id,
            f"Review prior work relevant to {self.topic or 'this area'}.",
        )

        if existing:
            return existing + f"\n\n*[{strategy.display_name} related work strategy: {guidance}]*\n"
        return (
            f"## Related Work\n\n"
            f"Prior work in {self.topic or 'this area'} falls into several categories. "
            f"[Category 1] addresses [aspect] but does not [limitation]. "
            f"[Category 2] provides [capability] at the cost of [trade-off]. "
            f"Our work bridges these approaches by [contribution].\n\n"
            f"*[{strategy.display_name} positioning: {guidance}]*\n"
        )

    def _generate_conclusion(self, sections: dict[str, str]) -> str:
        strategy = self.venue_strategy
        best_metric = self._best_metric_text()

        existing = sections.get("conclusion", "")
        if existing:
            base = existing
        else:
            base = (
                f"## Conclusion\n\n"
                f"We have presented work on {self.topic or 'the research problem'}, "
                f"achieving {best_metric}."
            )

        venue_conclusion = {
            "neurips": (
                f"\n\nOur results suggest that [mechanism] is a promising direction. "
                f"However, this work is limited to [scope]. Future work should "
                f"investigate [extension] and validate on [broader context]. "
                f"We have released code and data to facilitate reproduction "
                f"and extension by the community."
            ),
            "icml": (
                f"\n\nOur theoretical and empirical results establish that [finding]. "
                f"Limitations include [assumption] and [scope]. An important open "
                f"question is whether [generalization]. We believe this work opens "
                f"several directions for future investigation."
            ),
            "vldb": (
                f"\n\nWe have built and evaluated a system that addresses [problem]. "
                f"The key engineering insight is [trade-off]. Our system is available "
                f"as open-source software. Limitations include [scale/domain], "
                f"and we are actively working on [next steps]."
            ),
            "acl": (
                f"\n\nThis work demonstrates that [linguistic finding]. We acknowledge "
                f"that our study is limited to [languages/domains]. Future work should "
                f"extend to [understudied languages/phenomena]. We release all code, "
                f"data, and models to support reproducibility and further research."
            ),
        }

        extra = venue_conclusion.get(
            strategy.venue_id,
            f"\n\nThis work contributes to {self.topic or 'the field'} by [contribution]. "
            f"Limitations include [scope]. Future work includes [directions].",
        )

        return base + extra

    def _assemble_paper(
        self,
        *,
        abstract: str,
        introduction: str,
        sections: dict[str, str],
        related_work: str,
        conclusion: str,
    ) -> str:
        strategy = self.venue_strategy
        venue_id = strategy.venue_id

        # Venue-specific section ordering
        if venue_id in {"icml", "neurips"}:
            order = ["introduction", "related work", "method", "experiments", "conclusion"]
        elif venue_id in {"vldb", "sigmod", "icde"}:
            order = ["introduction", "system_overview", "architecture", "experiments", "related work", "conclusion"]
        else:
            order = ["introduction", "related work", "method", "experiments", "conclusion"]

        parts: list[str] = [f"# {self.topic or 'Research Paper'}\n"]

        if abstract:
            parts.append(f"## Abstract\n\n{abstract}\n")

        for section_key in order:
            if section_key == "introduction":
                parts.append(introduction)
            elif section_key == "related work" or section_key == "related_work":
                parts.append(related_work)
            elif section_key == "conclusion":
                parts.append(conclusion)
            elif section_key in sections:
                parts.append(f"## {section_key.replace('_', ' ').title()}\n\n{sections[section_key]}")
            elif section_key == "method":
                method = sections.get("method", sections.get("approach", sections.get("methodology", "")))
                if method:
                    parts.append(f"## Method\n\n{method}")
                else:
                    parts.append(f"## Method\n\nWe describe our approach to {self.topic or 'the problem'}.\n")
            elif section_key == "experiments":
                exp = sections.get("experiments", sections.get("results", sections.get("evaluation", "")))
                if exp:
                    parts.append(f"## Experiments\n\n{exp}")
                else:
                    parts.append(f"## Experiments\n\nExperimental results support our claims.\n")
            elif section_key in {"system_overview", "architecture"}:
                parts.append(f"## {section_key.replace('_', ' ').title()}\n\n[System description placeholder]\n")

        parts.append(f"\n## Acknowledgments\n\nWe thank the anonymous reviewers for their feedback.\n")

        return "\n\n".join(parts)

    def _best_metric_text(self) -> str:
        kept = [e for e in self.ledger if e.decision == "keep" and e.metric is not None]
        if kept:
            best = kept[-1]
            return f"{best.metric} {best.metric_definition}"
        return "competitive performance"

    def _prose_prompt(self) -> str:
        strategy = self.venue_strategy
        return (
            f"You are an expert scientific writer adapting a paper for {strategy.display_name}.\n\n"
            f"## {strategy.display_name} Narrative Strategy:\n{strategy.narrative_framing}\n\n"
            f"## What {strategy.display_name} reviewers value:\n"
            + "\n".join(f"- {v}" for v in strategy.reviewer_values)
            + "\n\n"
            f"## Common reasons for rejection:\n"
            + "\n".join(f"- {r}" for r in strategy.common_rejections)
            + "\n\n"
            "Rewrite the paper's abstract, introduction, related work positioning, "
            "and conclusion to maximize acceptance probability at this venue. "
            "Return JSON with: abstract, introduction, related_work_positioning, "
            "conclusion, full_paper (complete rewritten paper), changes_summary. "
            "Preserve all experimental results and claims — only change the framing, "
            "emphasis, and narrative structure. Be specific to this venue."
        )


def generate_venue_prose(
    *,
    venue_strategy: VenueStrategy,
    paper_markdown: str,
    ledger: tuple[LedgerEntry, ...] = (),
    topic: str = "",
    llm_provider: LLMProvider | None = None,
) -> VenueProseOutput:
    generator = VenueProseGenerator(
        venue_strategy,
        paper_markdown=paper_markdown,
        ledger=ledger,
        topic=topic,
    )
    return generator.generate(llm_provider=llm_provider)


def write_prose_output(output: VenueProseOutput, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output.to_markdown(), encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(output.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _parse_sections(markdown: str) -> dict[str, str]:
    """Parse markdown into sections keyed by normalized heading."""
    sections: dict[str, str] = {}
    current_heading = "preamble"
    current_content: list[str] = []

    for line in markdown.split("\n"):
        if line.startswith("## "):
            if current_content:
                sections[_normalize_heading(current_heading)] = "\n".join(current_content).strip()
            current_heading = line[3:].strip()
            current_content = [line]
        else:
            current_content.append(line)

    if current_content:
        sections[_normalize_heading(current_heading)] = "\n".join(current_content).strip()

    return sections


def _normalize_heading(heading: str) -> str:
    return heading.lower().replace(" ", "_").replace("-", "_").replace(".", "")
