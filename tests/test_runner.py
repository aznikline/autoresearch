from __future__ import annotations

from pathlib import Path
import json

from autoresearch.config import AutoresearchConfig
from autoresearch.experiments.ledger import read_ledger
from autoresearch.knowledge.cards import read_cards_jsonl
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.stages import STAGE_SEQUENCE, Stage
from autoresearch.pipeline.runner import PipelineRunner


def test_runner_pauses_at_first_gate_without_auto_approve(
    config: AutoresearchConfig,
) -> None:
    result = PipelineRunner(config).run(topic="test idea", run_id="paused-run")

    assert result["status"] == "paused"
    assert result["checkpoint"]["stage_slug"] == "literature_screen"
    assert result["stages_completed"] == 3


def test_runner_auto_approve_writes_contract_outputs(
    config: AutoresearchConfig,
) -> None:
    result = PipelineRunner(config).run(
        topic="test idea",
        run_id="complete-run",
        auto_approve=True,
    )

    assert result["status"] == "done"
    run_dir = Path(result["run_dir"])
    checkpoint = read_checkpoint(run_dir)
    assert checkpoint is not None
    assert checkpoint["stage_slug"] == "final_verification_export"

    for stage in STAGE_SEQUENCE:
        stage_dir = run_dir / f"stage-{int(stage):02d}-{stage.slug}"
        for output in contract_for(stage).output_files:
            output_path = stage_dir / output
            if output.endswith("/"):
                assert output_path.is_dir()
            else:
                assert output_path.is_file()


def test_runner_rejects_empty_topic(config: AutoresearchConfig) -> None:
    result = PipelineRunner(config).run(topic=" ")

    assert result["status"] == "failed"
    assert "topic is required" in result["message"]


def test_runner_writes_grounded_literature_artifacts(
    config: AutoresearchConfig,
) -> None:
    result = PipelineRunner(config).run(
        topic="machine learning optimization",
        run_id="literature-run",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])

    candidates = (
        run_dir / "stage-03-literature_collect" / "candidates.jsonl"
    ).read_text(encoding="utf-8")
    shortlist = (
        run_dir / "stage-04-literature_screen" / "shortlist.jsonl"
    ).read_text(encoding="utf-8")
    cards = read_cards_jsonl(
        run_dir / "stage-05-synthesis" / "knowledge_cards.jsonl"
    )

    assert "Adam: A Method for Stochastic Optimization" in candidates
    assert "decision" in shortlist
    assert cards


def test_runner_executes_local_experiment_loop(
    config: AutoresearchConfig,
) -> None:
    result = PipelineRunner(config).run(
        topic="machine learning optimization",
        run_id="experiment-run",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])

    ledger = read_ledger(run_dir / "stage-09-experiment_loop" / "ledger.jsonl")
    decision = (
        run_dir / "stage-10-result_analysis_decision" / "decision.md"
    ).read_text(encoding="utf-8")

    assert [entry.decision for entry in ledger] == ["keep", "keep", "discard"]
    assert "Decision: PROCEED" in decision


def test_runner_exports_verified_paper_bundle(
    config: AutoresearchConfig,
) -> None:
    result = PipelineRunner(config).run(
        topic="machine learning optimization",
        run_id="paper-run",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])
    final_dir = run_dir / "stage-12-final_verification_export"

    report = json.loads((final_dir / "verification_report.json").read_text())
    quality = json.loads((final_dir / "quality_report.json").read_text())
    paper = (final_dir / "paper.tex").read_text(encoding="utf-8")
    bib = (final_dir / "references.bib").read_text(encoding="utf-8")

    assert report["artifact_verification_ok"] is True
    assert report["submission_ready"] is False
    assert report["citations"]["unsupported_keys"] == []
    assert report["numeric_claims"]["unsupported_numbers"] == []
    assert quality["submission_ready"] is False
    assert quality["blocking_issues"]
    assert quality["profile_id"] == "ml-systems-efficiency"
    assert quality["depth"] == "top_venue"
    assert any(
        check["requirement"] == "evaluation_units" and not check["passed"]
        for check in quality["checks"]
    )
    assert "\\section{Results}" in paper
    assert "@misc{" in bib
