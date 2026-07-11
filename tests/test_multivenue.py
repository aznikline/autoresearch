from __future__ import annotations

from pathlib import Path

from autoresearch.multivenue.report import (
    MultiVenueReport,
    VenueRanking,
    generate_fit_report,
    write_fit_report,
)
from autoresearch.strategy.registry import VenueStrategyRegistry


def _load_registry() -> VenueStrategyRegistry:
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "autoresearch"
        / "strategy"
        / "profiles"
    )
    return VenueStrategyRegistry.load(root)


class TestMultiVenueReport:
    def test_generates_rankings_for_all_venues(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea="A novel attention mechanism with linear complexity via hierarchical decomposition",
            registry=registry,
        )
        assert len(report.venue_rankings) >= 13
        # Should be sorted by score descending
        scores = [r.overall_score for r in report.venue_rankings]
        assert scores == sorted(scores, reverse=True)

    def test_first_rank_is_best(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea="A memory-efficient cache replacement policy for learned index structures on NVMe SSDs",
            registry=registry,
        )
        assert report.best_venue == report.venue_rankings[0].venue_id
        assert report.venue_rankings[0].rank == 1
        assert report.venue_rankings[1].rank == 2

    def test_different_ideas_rank_differently(self) -> None:
        registry = _load_registry()
        ml_idea = (
            "A novel transformer architecture with hierarchical attention "
            "for efficient long-context language modeling"
        )
        db_idea = (
            "A learned index structure with cache-aware replacement "
            "for OLAP workloads on columnar storage"
        )
        ml_report = generate_fit_report(idea=ml_idea, registry=registry)
        db_report = generate_fit_report(idea=db_idea, registry=registry)
        # Different ideas should have different top venues
        assert ml_report.best_venue != db_report.best_venue or (
            ml_report.best_fit_score != db_report.best_fit_score
        )

    def test_to_markdown_is_readable(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea="Graph neural networks for fraud detection at scale",
            registry=registry,
        )
        md = report.to_markdown()
        assert "# Multi-Venue Fit Report" in md
        assert "## Rankings" in md
        assert "## Per-Venue Details" in md
        assert "| # | Venue |" in md

    def test_to_dict_is_serializable(self) -> None:
        import json

        registry = _load_registry()
        report = generate_fit_report(
            idea="Cross-lingual few-shot NER with language-agnostic representations",
            registry=registry,
        )
        data = report.to_dict()
        json.dumps(data)
        assert data["idea"]
        assert len(data["venue_rankings"]) >= 13

    def test_write_fit_report(self, tmp_path: Path) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea="Efficient distributed training with gradient compression",
            registry=registry,
        )
        path = tmp_path / "fit_report.md"
        write_fit_report(report, path)
        assert path.is_file()
        assert (tmp_path / "fit_report.json").is_file()

    def test_nlp_idea_top_venue_is_acl_or_emnlp(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea=(
                "Cross-lingual transfer learning for low-resource named entity "
                "recognition with typologically informed parameter sharing"
            ),
            registry=registry,
        )
        top_venues = {r.venue_id for r in report.venue_rankings[:3]}
        # NLP ideas should rank ACL/EMNLP/NAACL/CoLM high
        nlp_venues = {"acl", "emnlp", "naacl", "colm", "coling"}
        assert top_venues & nlp_venues

    def test_vision_idea_top_venue_is_cvpr_or_eccv_or_iccv(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea=(
                "A multi-scale vision transformer with deformable attention "
                "for dense prediction tasks including object detection and "
                "semantic segmentation on COCO and ADE20K benchmarks"
            ),
            registry=registry,
        )
        top_venues = {r.venue_id for r in report.venue_rankings[:3]}
        vision_venues = {"cvpr", "eccv", "iccv"}
        assert top_venues & vision_venues, f"Expected vision venues in top 3, got {top_venues}"

    def test_db_idea_with_keywords_ranks_vldb_higher(self) -> None:
        registry = _load_registry()
        report = generate_fit_report(
            idea=(
                "A database system with real implementation, reproducible code "
                "and data, scalable architecture for realistic workloads, "
                "comparison against deployed systems with honest performance "
                "analysis including failure cases on standard benchmarks"
            ),
            registry=registry,
        )
        # With explicit keyword matches, VLDB/SIGMOD should score well
        vldb_ranking = next(
            (r for r in report.venue_rankings if r.venue_id == "vldb"), None
        )
        assert vldb_ranking is not None
        # VLDB should be in top half with explicit keyword matches
        top_half = len(report.venue_rankings) // 2
        assert vldb_ranking.rank <= top_half + 1, (
            f"VLDB ranked {vldb_ranking.rank}, expected top {top_half + 1}"
        )

    def test_venue_ranking_to_dict(self) -> None:
        ranking = VenueRanking(
            rank=1,
            venue_id="neurips",
            display_name="NeurIPS",
            overall_score=0.85,
            ideation_fit=0.8,
            review_score=8,
            contribution_fit=0.9,
            critical_weaknesses=("weak ablation",),
            top_contribution="novel algorithm",
            recommendation="Strong match.",
        )
        data = ranking.to_dict()
        assert data["rank"] == 1
        assert data["venue_id"] == "neurips"
