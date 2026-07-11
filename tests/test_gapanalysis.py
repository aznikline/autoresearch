from __future__ import annotations

from pathlib import Path

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.gapanalysis.report import (
    ActionItem,
    GapReport,
    analyze_gap,
    write_gap_report,
)
from autoresearch.strategy.models import (
    ReviewSimulation,
    ReviewWeakness,
    load_venue_strategy,
)


def _make_review(score: int = 5, weaknesses: tuple[ReviewWeakness, ...] = ()) -> ReviewSimulation:
    return ReviewSimulation(
        venue_id="neurips",
        overall_score=score,
        confidence=0.5,
        strengths=("clear idea",),
        weaknesses=weaknesses or (
            ReviewWeakness(
                claim="ablations",
                severity="critical",
                suggested_fix="Add ablation experiments.",
                missing_evidence=("ablation_table",),
            ),
            ReviewWeakness(
                claim="only 3 trials",
                severity="major",
                suggested_fix="Run at least 5 trials.",
            ),
        ),
        suggested_experiments=(),
        narrative_suggestions=(),
        summary="Test review.",
    )


def _ledger(num_trials: int = 3) -> tuple[LedgerEntry, ...]:
    return tuple(
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
            code_sha256="a" * 64,
            protocol_fingerprint="b" * 64,
        )
        for i in range(num_trials)
    )


class TestGapAnalysis:
    def test_analyzes_critical_weakness(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "neurips.yaml")
        review = _make_review(
            score=5,
            weaknesses=(
                ReviewWeakness(
                    claim="ablations",
                    severity="critical",
                    suggested_fix="Add ablation experiments.",
                ),
            ),
        )
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(3),
            target_score=8,
        )
        assert report.current_score == 5
        assert report.target_score == 8
        assert report.gap == 3
        assert len(report.action_items) >= 1
        # Should have an action for the critical weakness
        ablation_actions = [a for a in report.action_items if "ablation" in a.description.lower()]
        assert len(ablation_actions) >= 1
        assert ablation_actions[0].estimated_score_gain >= 2

    def test_zero_gap_when_score_above_target(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "icml.yaml")
        review = _make_review(score=9)
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(5),
            target_score=8,
        )
        assert report.gap == 0
        # Action items still generated (improvement opportunities) but minimal path is empty
        assert len(report.minimal_path) == 0

    def test_minimal_path_exists(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "vldb.yaml")
        review = _make_review(
            score=4,
            weaknesses=(
                ReviewWeakness(
                    claim="ablations",
                    severity="critical",
                    suggested_fix="Add ablation experiments.",
                ),
                ReviewWeakness(
                    claim="systems contribution",
                    severity="critical",
                    suggested_fix="Describe system architecture.",
                ),
                ReviewWeakness(
                    claim="only 2 trials",
                    severity="major",
                    suggested_fix="Run at least 5 trials.",
                ),
            ),
        )
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(2),
            target_score=7,
        )
        assert len(report.minimal_path) > 0
        assert report.estimated_final_score >= report.current_score

    def test_to_markdown_readable(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "acl.yaml")
        review = _make_review(score=6)
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(4),
        )
        md = report.to_markdown()
        assert "# Gap Analysis: ACL" in md
        assert "Action Items" in md
        assert "Minimal Path" in md

    def test_to_dict_serializable(self) -> None:
        import json

        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "cvpr.yaml")
        review = _make_review(score=7)
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(5),
        )
        data = report.to_dict()
        json.dumps(data)

    def test_write_gap_report(self, tmp_path: Path) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "kdd.yaml")
        review = _make_review(score=5)
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(3),
        )
        path = tmp_path / "gap_report.md"
        write_gap_report(report, path)
        assert path.is_file()
        assert (tmp_path / "gap_report.json").is_file()

    def test_seed_count_triggers_methodology_action(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autoresearch"
            / "strategy"
            / "profiles"
        )
        strategy = load_venue_strategy(root / "mlsys.yaml")
        review = _make_review(score=5)
        report = analyze_gap(
            review=review,
            venue_strategy=strategy,
            ledger=_ledger(2),  # only 2 trials
        )
        seed_actions = [a for a in report.action_items if "trial" in a.description.lower()]
        assert len(seed_actions) >= 1

    def test_action_item_to_dict(self) -> None:
        item = ActionItem(
            priority=1,
            category="experiment",
            description="Add ablation experiments",
            current_state="No ablations",
            target_state="Ablation table with 5 components",
            estimated_score_gain=3,
            effort="medium",
            stage_to_rerun="experiment_loop",
            concrete_steps=("Design ablation", "Run experiments", "Report results"),
        )
        data = item.to_dict()
        assert data["priority"] == 1
        assert data["category"] == "experiment"
