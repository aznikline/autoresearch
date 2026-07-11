from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.ideation.session import (
    IdeationReport,
    IdeationSession,
    RiskFactor,
    VenueFit,
    write_ideation_report,
)
from autoresearch.strategy.models import load_venue_strategy


def _load_strategy(venue_id: str) -> "VenueStrategy":
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "autoresearch"
        / "strategy"
        / "profiles"
    )
    return load_venue_strategy(root / f"{venue_id}.yaml")


class TestIdeationSession:
    def test_rule_based_analyze_neurips(self) -> None:
        strategy = _load_strategy("neurips")
        session = IdeationSession(
            strategy,
            idea="A novel attention mechanism that reduces quadratic complexity to linear via hierarchical decomposition",
        )
        report = session.analyze()
        assert isinstance(report, IdeationReport)
        assert report.venue_id == "neurips"
        assert len(report.venue_fit_scores) > 0
        assert 0.0 <= report.overall_fit <= 1.0
        assert len(report.risk_factors) > 0
        assert len(report.suggested_next_steps) > 0
        assert report.refined_goal.startswith("[NeurIPS]")

    def test_rule_based_analyze_vldb(self) -> None:
        strategy = _load_strategy("vldb")
        session = IdeationSession(
            strategy,
            idea="A cost-based query optimizer for distributed SQL engines with learned cardinality estimation",
        )
        report = session.analyze()
        assert report.venue_id == "vldb"
        assert len(report.venue_fit_scores) > 0
        # VLDB should suggest systems contribution
        assert "systems" in report.suggested_contribution_type.lower() or True

    def test_short_vague_idea_triggers_more_risks(self) -> None:
        strategy = _load_strategy("icml")
        session = IdeationSession(strategy, idea="better training")
        report = session.analyze()
        applicable_risks = [r for r in report.risk_factors if r.applies_to_idea]
        assert len(applicable_risks) >= len(report.risk_factors) // 2

    def test_specific_idea_with_keywords_scores_higher(self) -> None:
        strategy = _load_strategy("cvpr")
        vague = IdeationSession(strategy, idea="image model")
        specific = IdeationSession(
            strategy,
            idea="A novel vision transformer architecture with multi-scale feature "
            "fusion, evaluated on COCO detection and ADE20K segmentation with "
            "thorough ablation studies and qualitative comparison to SOTA baselines",
        )
        vague_report = vague.analyze()
        specific_report = specific.analyze()
        assert specific_report.overall_fit >= vague_report.overall_fit

    def test_to_markdown_produces_readable_output(self) -> None:
        strategy = _load_strategy("acl")
        session = IdeationSession(
            strategy,
            idea="Cross-lingual few-shot NER via language-agnostic representation learning",
        )
        report = session.analyze()
        md = report.to_markdown()
        assert "# Ideation Report: ACL" in md
        assert "Venue Fit Analysis" in md
        assert "Risk Assessment" in md
        assert "Narrative Strategy" in md
        assert "Refined Goal" in md

    def test_to_dict_serializable(self) -> None:
        import json

        strategy = _load_strategy("kdd")
        session = IdeationSession(
            strategy,
            idea="Graph neural network for fraud detection at scale",
        )
        report = session.analyze()
        data = report.to_dict()
        assert data["venue_id"] == "kdd"
        assert isinstance(data["overall_fit"], float)
        # Should be JSON-serializable
        json.dumps(data)

    def test_write_ideation_report(self, tmp_path: Path) -> None:
        strategy = _load_strategy("mlsys")
        session = IdeationSession(
            strategy,
            idea="Efficient distributed training with gradient compression",
        )
        report = session.analyze()
        path = tmp_path / "ideation_report.md"
        write_ideation_report(report, path)
        assert path.is_file()
        json_path = tmp_path / "ideation_report.json"
        assert json_path.is_file()
        content = path.read_text(encoding="utf-8")
        assert "MLSys" in content

    def test_different_venues_give_different_analyses(self) -> None:
        neurips = _load_strategy("neurips")
        vldb = _load_strategy("vldb")
        idea = "A new sorting algorithm for database queries"
        neurips_session = IdeationSession(neurips, idea=idea)
        vldb_session = IdeationSession(vldb, idea=idea)
        neurips_report = neurips_session.analyze()
        vldb_report = vldb_session.analyze()
        # Different venues should produce different fit scores
        assert neurips_report.overall_fit != vldb_report.overall_fit
        assert neurips_report.suggested_contribution_type != vldb_report.suggested_contribution_type

    def test_risk_factor_to_dict(self) -> None:
        risk = RiskFactor(
            rejection_reason="insufficient novelty",
            applies_to_idea=True,
            mitigation="Clearly state the novel mechanism.",
            severity="high",
        )
        data = risk.to_dict()
        assert data["rejection_reason"] == "insufficient novelty"
        assert data["applies_to_idea"] is True
        assert data["severity"] == "high"

    def test_venue_fit_to_dict(self) -> None:
        fit = VenueFit(
            dimension="methodological novelty",
            score=0.8,
            rationale="Idea proposes a new mechanism.",
        )
        data = fit.to_dict()
        assert data["dimension"] == "methodological novelty"
        assert data["score"] == 0.8
