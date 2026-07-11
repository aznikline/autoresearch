from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.revision.loop import (
    RevisionLoop,
    RevisionResult,
    RevisionStep,
    run_revision_loop,
    write_revision_report,
)
from autoresearch.strategy.models import load_venue_strategy


def _strategy() -> "VenueStrategy":
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "autoresearch"
        / "strategy"
        / "profiles"
    )
    return load_venue_strategy(root / "neurips.yaml")


class TestRevisionLoop:
    def test_runs_on_completed_run(self) -> None:
        """The revision loop should run without errors on a completed pipeline run."""
        run_dir = (
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "run-20260711-103808"
        )
        if not run_dir.is_dir():
            pytest.skip("run directory not available")

        strategy = _strategy()
        result = run_revision_loop(
            run_dir,
            venue_strategy=strategy,
            target_score=8,
            max_iterations=3,
        )
        assert isinstance(result, RevisionResult)
        assert result.venue_id == "neurips"
        assert result.initial_score >= 1
        assert result.final_score >= result.initial_score
        assert result.iterations >= 0

    def test_no_iterations_when_score_above_target(self) -> None:
        run_dir = (
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "run-20260711-103808"
        )
        if not run_dir.is_dir():
            pytest.skip("run directory not available")

        strategy = _strategy()
        result = run_revision_loop(
            run_dir,
            venue_strategy=strategy,
            target_score=1,  # impossibly low target
            max_iterations=3,
        )
        assert result.iterations == 0

    def test_max_iterations_respected(self) -> None:
        run_dir = (
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "run-20260711-103808"
        )
        if not run_dir.is_dir():
            pytest.skip("run directory not available")

        strategy = _strategy()
        result = run_revision_loop(
            run_dir,
            venue_strategy=strategy,
            target_score=10,
            max_iterations=2,
        )
        assert result.iterations <= 2

    def test_to_markdown_readable(self) -> None:
        result = RevisionResult(
            venue_id="neurips",
            initial_score=4,
            final_score=7,
            target_score=8,
            iterations=2,
            steps=(
                RevisionStep(
                    iteration=1,
                    action_description="Add ablation experiments",
                    stage_modified="experiment_loop",
                    score_before=4,
                    score_after=6,
                    fix_applied="Added ablation placeholder section",
                    success=True,
                ),
                RevisionStep(
                    iteration=2,
                    action_description="Increase trials from 3 to 5",
                    stage_modified="experiment_loop",
                    score_before=6,
                    score_after=7,
                    fix_applied="Increased trials from 3 to 5",
                    success=True,
                ),
            ),
            converged=False,
            summary="Stopped at 7/10 after 2 fixes.",
        )
        md = result.to_markdown()
        assert "# Revision Loop Results" in md
        assert "4/10 → 7/10" in md
        assert "2" in md  # iterations

    def test_to_dict_serializable(self) -> None:
        import json

        result = RevisionResult(
            venue_id="icml",
            initial_score=5,
            final_score=8,
            target_score=8,
            iterations=3,
            steps=(
                RevisionStep(
                    iteration=1,
                    action_description="Fix ablation",
                    stage_modified="experiment_loop",
                    score_before=5,
                    score_after=7,
                    fix_applied="Added ablation section",
                    success=True,
                ),
            ),
            converged=True,
            summary="Reached 8/10 after 1 fix.",
        )
        data = result.to_dict()
        json.dumps(data)

    def test_write_revision_report(self, tmp_path: Path) -> None:
        result = RevisionResult(
            venue_id="vldb",
            initial_score=3,
            final_score=6,
            target_score=8,
            iterations=2,
            steps=(),
            converged=False,
            summary="Test.",
        )
        path = tmp_path / "revision.md"
        write_revision_report(result, path)
        assert path.is_file()
        assert (tmp_path / "revision.json").is_file()

    def test_revision_step_to_dict(self) -> None:
        step = RevisionStep(
            iteration=1,
            action_description="Increase trials",
            stage_modified="experiment_loop",
            score_before=5,
            score_after=7,
            fix_applied="Added 2 trials",
            success=True,
        )
        data = step.to_dict()
        assert data["iteration"] == 1
        assert data["success"] is True
