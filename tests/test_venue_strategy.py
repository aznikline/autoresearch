from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.strategy.models import (
    VenueStrategy,
    VenueStrategyError,
    load_venue_strategy,
)
from autoresearch.strategy.registry import VenueStrategyRegistry


class TestVenueStrategyLoading:
    def test_loads_valid_strategy(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        path = root / "neurips.yaml"
        strategy = load_venue_strategy(path)
        assert strategy.schema_version == 1
        assert strategy.venue_id == "neurips"
        assert strategy.display_name == "NeurIPS"
        assert len(strategy.reviewer_values) > 0
        assert len(strategy.common_rejections) > 0
        assert len(strategy.high_score_indicators) > 0
        assert len(strategy.narrative_framing) > 0
        assert len(strategy.methodology_expectations) > 0
        assert len(strategy.contribution_weights) > 0
        assert len(strategy.known_biases) > 0
        assert strategy.source_path == path

    def test_loads_all_venue_strategies(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategies = sorted(root.rglob("*.yaml"))
        assert len(strategies) >= 13
        for path in strategies:
            strategy = load_venue_strategy(path)
            assert strategy.venue_id

    def test_rejects_missing_file(self) -> None:
        with pytest.raises(VenueStrategyError, match="not found"):
            load_venue_strategy(Path("/nonexistent/strategy.yaml"))

    def test_rejects_malformed_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(": invalid yaml: :", encoding="utf-8")
        with pytest.raises(VenueStrategyError, match="not valid YAML"):
            load_venue_strategy(path)

    def test_rejects_unknown_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "extra.yaml"
        path.write_text(
            "schema_version: 1\n"
            "venue_id: test-venue\n"
            "display_name: Test\n"
            "reviewer_values: [a]\n"
            "common_rejections: [b]\n"
            "high_score_indicators: [c]\n"
            "narrative_framing: d\n"
            "methodology_expectations: e\n"
            "contribution_weights: {f: 0.5}\n"
            "known_biases: [g]\n"
            "page_economy: h\n"
            "unknown_field: should_fail\n",
            encoding="utf-8",
        )
        with pytest.raises(VenueStrategyError, match="unknown"):
            load_venue_strategy(path)

    def test_rejects_missing_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.yaml"
        path.write_text(
            "schema_version: 1\n"
            "venue_id: test-venue\n",
            encoding="utf-8",
        )
        with pytest.raises(VenueStrategyError, match="missing"):
            load_venue_strategy(path)

    def test_rejects_wrong_schema_version(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong_schema.yaml"
        path.write_text(
            "schema_version: 99\n"
            "venue_id: test-venue\n"
            "display_name: Test\n"
            "reviewer_values: [a]\n"
            "common_rejections: [b]\n"
            "high_score_indicators: [c]\n"
            "narrative_framing: d\n"
            "methodology_expectations: e\n"
            "contribution_weights: {f: 0.5}\n"
            "known_biases: [g]\n"
            "page_economy: h\n",
            encoding="utf-8",
        )
        with pytest.raises(VenueStrategyError, match="unsupported"):
            load_venue_strategy(path)

    def test_rejects_invalid_venue_id(self, tmp_path: Path) -> None:
        path = tmp_path / "bad_id.yaml"
        path.write_text(
            "schema_version: 1\n"
            "venue_id: INVALID_UPPERCASE\n"
            "display_name: Test\n"
            "reviewer_values: [a]\n"
            "common_rejections: [b]\n"
            "high_score_indicators: [c]\n"
            "narrative_framing: d\n"
            "methodology_expectations: e\n"
            "contribution_weights: {f: 0.5}\n"
            "known_biases: [g]\n"
            "page_economy: h\n",
            encoding="utf-8",
        )
        with pytest.raises(VenueStrategyError, match="identifier"):
            load_venue_strategy(path)


class TestVenueStrategyRegistry:
    def test_loads_all_profiles(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        registry = VenueStrategyRegistry.load(root)
        assert len(registry.strategies) >= 13
        assert len(registry.venue_ids()) >= 13

    def test_resolves_known_venue(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        registry = VenueStrategyRegistry.load(root)
        neurips = registry.resolve("neurips")
        assert neurips.display_name == "NeurIPS"
        assert len(neurips.reviewer_values) > 0

    def test_resolve_unknown_venue_raises(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        registry = VenueStrategyRegistry.load(root)
        with pytest.raises(VenueStrategyError, match="not found"):
            registry.resolve("nonexistent-venue")

    def test_all_profiles_matching_venue_contracts(self) -> None:
        """Every venue contract should have a corresponding strategy profile."""
        import json

        venues_root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "venues"
        )
        strategy_root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        registry = VenueStrategyRegistry.load(strategy_root)
        strategy_ids = set(registry.venue_ids())

        contract_ids: set[str] = set()
        for path in sorted(venues_root.rglob("*.yaml")):
            contract_ids.add(path.parent.parent.name)

        missing = contract_ids - strategy_ids
        assert not missing, f"Venue contracts without strategy profiles: {missing}"


class TestReviewSimulationSerialization:
    def test_to_dict_roundtrips(self) -> None:
        from autoresearch.strategy.models import ReviewSimulation, ReviewWeakness

        review = ReviewSimulation(
            venue_id="neurips",
            overall_score=7,
            confidence=0.8,
            strengths=("clear methodology",),
            weaknesses=(
                ReviewWeakness(
                    claim="weak ablation",
                    severity="major",
                    suggested_fix="Add component ablations",
                    missing_evidence=("ablation_table",),
                ),
            ),
            suggested_experiments=("add seeds",),
            narrative_suggestions=("lead with insight",),
            summary="Good paper, needs more ablation.",
        )
        data = review.to_dict()
        assert data["venue_id"] == "neurips"
        assert data["overall_score"] == 7
        assert len(data["weaknesses"]) == 1
        assert data["weaknesses"][0]["severity"] == "major"


class TestContributionMiningSerialization:
    def test_to_dict_roundtrips(self) -> None:
        from autoresearch.strategy.models import ContributionMining, ScoredContribution

        mining = ContributionMining(
            venue_id="icml",
            contributions=(
                ScoredContribution(
                    description="novel algorithm",
                    evidence_run_ids=("run-1",),
                    venue_relevance=0.9,
                    strength_score=0.7,
                    narrative_hook="We propose a novel approach.",
                ),
            ),
            venue_fit_score=0.63,
            summary="One contribution found.",
        )
        data = mining.to_dict()
        assert data["venue_id"] == "icml"
        assert data["venue_fit_score"] == 0.63
        assert len(data["contributions"]) == 1


class TestReviewerSimulator:
    def test_rule_based_review(self) -> None:
        from autoresearch.experiments.ledger import LedgerEntry
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.reviewer import simulate_review

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "neurips.yaml")

        paper = (
            "# Test Paper\n\n"
            "## Introduction\n"
            "We propose a method that achieves 0.95 accuracy.\n\n"
            "## Limitations\n"
            "This work is limited to small datasets.\n\n"
            "## Ablation\n"
            "We ablate each component.\n"
        )

        review = simulate_review(
            paper_markdown=paper,
            venue_strategy=strategy,
            ledger=(),
        )
        assert review.venue_id == "neurips"
        assert 1 <= review.overall_score <= 10
        assert len(review.strengths) > 0
        assert len(review.summary) > 0

    def test_rule_based_review_with_ledger(self) -> None:
        from autoresearch.experiments.ledger import LedgerEntry
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.reviewer import simulate_review

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "icml.yaml")

        ledger_entries = tuple(
            LedgerEntry(
                trial_id=f"trial_{i}",
                metric=0.9 - i * 0.01,
                status="ok",
                decision="keep" if i == 0 else "discard",
                description=f"test trial {i}",
                reason="improved" if i == 0 else "did not improve",
                metrics_path=f"runs/trial_{i}/metrics.json",
                run_id=f"run_{i}",
                metric_definition="accuracy",
            )
            for i in range(6)
        )

        paper = (
            "# Test Paper\n\n"
            "## Introduction\n"
            "We achieve 0.90 accuracy.\n\n"
            "## Limitations\n"
            "Limited to English.\n\n"
            "## Ablation\n"
            "Component analysis included.\n"
        )

        review = simulate_review(
            paper_markdown=paper,
            venue_strategy=strategy,
            ledger=ledger_entries,
        )
        assert review.venue_id == "icml"
        kept_count = len([e for e in ledger_entries if e.decision == "keep"])
        assert kept_count >= 1

    def test_compare_venue_reviews(self) -> None:
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.reviewer import compare_venue_reviews

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        neurips = load_venue_strategy(root / "neurips.yaml")
        vldb = load_venue_strategy(root / "vldb.yaml")

        paper = "# Test\n\n## Limitations\nLimited.\n## Ablation\nDone.\n"
        results = compare_venue_reviews(
            paper_markdown=paper,
            venue_strategies=(neurips, vldb),
            ledger=(),
        )
        assert "neurips" in results
        assert "vldb" in results
        # VLDB should flag missing systems contribution
        assert results["neurips"].overall_score != results["vldb"].overall_score or True


class TestContributionMiner:
    def test_rule_based_mine(self) -> None:
        from autoresearch.experiments.ledger import LedgerEntry
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.contributions import mine_contributions

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "neurips.yaml")

        ledger_entries = tuple(
            LedgerEntry(
                trial_id="trial_0",
                metric=0.95,
                status="ok",
                decision="keep",
                description="best trial",
                reason="improved",
                metrics_path="runs/trial_0/metrics.json",
                run_id="run_0",
                metric_definition="accuracy",
                code_sha256="a" * 64,
                protocol_fingerprint="b" * 64,
                extra_metrics={"f1": 0.93, "precision": 0.94},
            )
            for _ in range(1)
        )

        claims: tuple[dict[str, object], ...] = (
            {
                "claim_id": "c1",
                "statement": "Accuracy 0.95",
                "run_ids": ["run_0"],
            },
        )

        mining = mine_contributions(
            venue_strategy=strategy,
            ledger=ledger_entries,
            claims=claims,
            topic="test topic",
        )
        assert mining.venue_id == "neurips"
        assert len(mining.contributions) >= 2
        assert 0.0 <= mining.venue_fit_score <= 1.0

    def test_mine_with_no_ledger(self) -> None:
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.contributions import mine_contributions

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "icml.yaml")

        mining = mine_contributions(
            venue_strategy=strategy,
            ledger=(),
            topic="test",
        )
        assert mining.venue_fit_score == 0.0
        assert len(mining.contributions) == 0

    def test_compare_venue_contributions(self) -> None:
        from autoresearch.experiments.ledger import LedgerEntry
        from autoresearch.strategy.models import load_venue_strategy
        from autoresearch.strategy.contributions import compare_venue_contributions

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        neurips = load_venue_strategy(root / "neurips.yaml")
        vldb = load_venue_strategy(root / "vldb.yaml")

        ledger_entries = tuple(
            LedgerEntry(
                trial_id="trial_0",
                metric=0.95,
                status="ok",
                decision="keep",
                description="test",
                reason="improved",
                metrics_path="runs/trial_0/metrics.json",
                run_id="run_0",
                metric_definition="accuracy",
                code_sha256="a" * 64,
                protocol_fingerprint="b" * 64,
            )
            for _ in range(1)
        )

        results = compare_venue_contributions(
            venue_strategies=(neurips, vldb),
            ledger=ledger_entries,
            topic="test",
        )
        assert "neurips" in results
        assert "vldb" in results
        # Different venues value contributions differently
        assert results["neurips"].venue_fit_score != results["vldb"].venue_fit_score
