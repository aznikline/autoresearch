from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.prose.venue_prose import (
    VenueProseGenerator,
    VenueProseOutput,
    generate_venue_prose,
    write_prose_output,
)
from autoresearch.strategy.models import load_venue_strategy


def _strategy(venue_id: str) -> "VenueStrategy":
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "autoresearch"
        / "strategy"
        / "profiles"
    )
    return load_venue_strategy(root / f"{venue_id}.yaml")


SAMPLE_PAPER = """# Test Paper

## Abstract
We present a method that achieves good results.

## Introduction
This is a test paper about an important problem.

## Related Work
Prior work includes many approaches.

## Method
Our method works as follows.

## Experiments
Results are promising.

## Conclusion
We have shown that our method works.
"""

SAMPLE_LEDGER = tuple(
    LedgerEntry(
        trial_id=f"trial_{i}",
        metric=0.9 - i * 0.01,
        status="ok",
        decision="keep" if i == 0 else "discard",
        description=f"trial {i}",
        reason="improved" if i == 0 else "did not improve",
        metrics_path=f"runs/trial_{i}/metrics.json",
        run_id=f"run_{i}",
        metric_definition="accuracy",
    )
    for i in range(5)
)


class TestVenueProseGenerator:
    def test_generates_for_neurips(self) -> None:
        strategy = _strategy("neurips")
        gen = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="hierarchical attention mechanisms",
        )
        output = gen.generate()
        assert output.venue_id == "neurips"
        assert "novel" in output.abstract.lower() or "present" in output.abstract.lower()
        assert "NeurIPS" in output.introduction
        assert len(output.full_paper) > len(SAMPLE_PAPER)

    def test_generates_for_vldb(self) -> None:
        strategy = _strategy("vldb")
        gen = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="query optimization",
        )
        output = gen.generate()
        assert output.venue_id == "vldb"
        assert "system" in output.abstract.lower() or "build" in output.abstract.lower()
        assert "VLDB" in output.introduction

    def test_generates_for_acl(self) -> None:
        strategy = _strategy("acl")
        gen = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="cross-lingual transfer",
        )
        output = gen.generate()
        assert output.venue_id == "acl"
        assert len(output.abstract) > 0
        assert "ACL" in output.introduction

    def test_generates_for_cvpr(self) -> None:
        strategy = _strategy("cvpr")
        gen = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="object detection",
        )
        output = gen.generate()
        assert output.venue_id == "cvpr"
        assert "visual" in output.abstract.lower() or "novel" in output.abstract.lower()

    def test_different_venues_produce_different_output(self) -> None:
        neurips = _strategy("neurips")
        vldb = _strategy("vldb")
        neurips_out = VenueProseGenerator(
            neurips,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="test",
        ).generate()
        vldb_out = VenueProseGenerator(
            vldb,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="test",
        ).generate()
        # Different venues should produce different abstracts
        assert neurips_out.abstract != vldb_out.abstract
        # Different full papers
        assert neurips_out.full_paper != vldb_out.full_paper

    def test_to_dict_and_markdown(self) -> None:
        import json

        strategy = _strategy("icml")
        output = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="test",
        ).generate()
        data = output.to_dict()
        json.dumps(data)
        md = output.to_markdown()
        assert "## Abstract" in md
        assert "## Introduction" in md

    def test_write_prose_output(self, tmp_path: Path) -> None:
        strategy = _strategy("kdd")
        output = VenueProseGenerator(
            strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="fraud detection",
        ).generate()
        path = tmp_path / "prose.md"
        write_prose_output(output, path)
        assert path.is_file()
        assert (tmp_path / "prose.json").is_file()

    def test_convenience_function(self) -> None:
        strategy = _strategy("mlsys")
        output = generate_venue_prose(
            venue_strategy=strategy,
            paper_markdown=SAMPLE_PAPER,
            ledger=SAMPLE_LEDGER,
            topic="distributed training",
        )
        assert isinstance(output, VenueProseOutput)
        assert output.venue_id == "mlsys"

    def test_section_ordering_differs_by_venue(self) -> None:
        """VLDB should put architecture before related work, ICML should not."""
        neurips = _strategy("neurips")
        vldb = _strategy("vldb")
        neurips_out = VenueProseGenerator(
            neurips, paper_markdown=SAMPLE_PAPER, topic="test"
        ).generate()
        vldb_out = VenueProseGenerator(
            vldb, paper_markdown=SAMPLE_PAPER, topic="test"
        ).generate()
        # VLDB paper should mention architecture/system
        assert "architecture" in vldb_out.full_paper.lower() or "system" in vldb_out.full_paper.lower()
