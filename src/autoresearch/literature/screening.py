from __future__ import annotations

from dataclasses import dataclass

from autoresearch.literature.models import PaperRecord, ScreenedPaper, tokenize


@dataclass(frozen=True)
class ScreeningReport:
    topic: str
    kept: int
    rejected: int
    threshold: float

    def to_markdown(self) -> str:
        return (
            "# Literature Screening Report\n\n"
            f"- Topic: {self.topic}\n"
            f"- Threshold: {self.threshold:.2f}\n"
            f"- Kept: {self.kept}\n"
            f"- Rejected: {self.rejected}\n"
        )


def screen_papers(
    papers: list[PaperRecord],
    *,
    topic: str,
    threshold: float = 0.10,
) -> tuple[list[ScreenedPaper], ScreeningReport]:
    topic_tokens = tokenize(topic)
    screened: list[ScreenedPaper] = []
    for paper in papers:
        score = relevance_score(topic_tokens, paper)
        decision = "keep" if score >= threshold else "reject"
        reason = (
            "topic terms overlap title or abstract"
            if decision == "keep"
            else "insufficient topic overlap"
        )
        screened.append(
            ScreenedPaper(
                paper=paper,
                score=round(score, 4),
                decision=decision,
                reason=reason,
            )
        )
    kept = sum(1 for item in screened if item.decision == "keep")
    return screened, ScreeningReport(
        topic=topic,
        kept=kept,
        rejected=len(screened) - kept,
        threshold=threshold,
    )


def relevance_score(topic_tokens: set[str], paper: PaperRecord) -> float:
    if not topic_tokens:
        return 0.0
    paper_tokens = tokenize(f"{paper.title} {paper.abstract} {paper.venue}")
    return len(topic_tokens & paper_tokens) / len(topic_tokens)
