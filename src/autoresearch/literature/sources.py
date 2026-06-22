from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from autoresearch.adapters.literature.base import SourceSearchResult
from autoresearch.literature.models import PaperRecord, tokenize


class LiteratureSource(Protocol):
    name: str

    def search(
        self, query: str, *, limit: int = 10
    ) -> list[PaperRecord] | SourceSearchResult:
        """Return normalized paper records for a query."""


@dataclass(frozen=True)
class InMemorySource:
    name: str
    papers: tuple[PaperRecord, ...]

    def search(self, query: str, *, limit: int = 10) -> list[PaperRecord]:
        query_tokens = tokenize(query)
        scored: list[tuple[int, PaperRecord]] = []
        for paper in self.papers:
            haystack = tokenize(f"{paper.title} {paper.abstract}")
            overlap = len(query_tokens & haystack)
            if overlap:
                scored.append((overlap, paper))
        scored.sort(key=lambda item: (-item[0], item[1].title))
        return [paper for _, paper in scored[:limit]]


def seed_source() -> InMemorySource:
    """Small built-in corpus for offline smoke tests and first-run scaffolding."""

    return InMemorySource(
        name="seed",
        papers=(
            PaperRecord(
                paper_id="seed:attention-is-all-you-need",
                title="Attention Is All You Need",
                authors=("Ashish Vaswani", "Noam Shazeer", "Niki Parmar"),
                year=2017,
                abstract=(
                    "Introduces the Transformer architecture using attention "
                    "mechanisms for sequence transduction and empirical machine "
                    "learning benchmarks."
                ),
                url="https://arxiv.org/abs/1706.03762",
                source="seed",
                venue="NeurIPS",
            ),
            PaperRecord(
                paper_id="seed:adam",
                title="Adam: A Method for Stochastic Optimization",
                authors=("Diederik Kingma", "Jimmy Ba"),
                year=2015,
                abstract=(
                    "Presents an adaptive optimization method for stochastic "
                    "gradient-based training of machine learning models."
                ),
                url="https://arxiv.org/abs/1412.6980",
                source="seed",
                venue="ICLR",
            ),
            PaperRecord(
                paper_id="seed:scaling-laws",
                title="Scaling Laws for Neural Language Models",
                authors=("Jared Kaplan", "Sam McCandlish", "Tom Henighan"),
                year=2020,
                abstract=(
                    "Studies empirical scaling laws for language model loss as a "
                    "function of compute, dataset size, and model parameters."
                ),
                url="https://arxiv.org/abs/2001.08361",
                source="seed",
            ),
            PaperRecord(
                paper_id="seed:deep-residual-learning",
                title="Deep Residual Learning for Image Recognition",
                authors=("Kaiming He", "Xiangyu Zhang", "Shaoqing Ren"),
                year=2016,
                abstract=(
                    "Shows residual connections enable optimization of very deep "
                    "neural networks for image recognition experiments."
                ),
                url="https://arxiv.org/abs/1512.03385",
                source="seed",
                venue="CVPR",
            ),
        ),
    )
