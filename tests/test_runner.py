from __future__ import annotations

from pathlib import Path
import json
from dataclasses import replace

from autoresearch.config import AutoresearchConfig
from autoresearch.experiments.ledger import read_ledger
from autoresearch.experiments.spec import ExperimentSpec
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
    assert result["checkpoint"]["expected_artifacts"] == ["candidates.jsonl"]
    assert result["checkpoint"]["allowed_actions"] == ["approve", "reject"]
    assert "literature_screen" in result["checkpoint"]["context_summary"]


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

    alignment = json.loads((run_dir / "alignment.json").read_text())
    report = (
        run_dir / "stage-03-literature_collect" / "search_report.md"
    ).read_text()
    assert alignment["literature"]["mode"] == "synthetic"
    assert alignment["literature"]["synthetic"] is True
    assert "Synthetic: true" in report
    quality = json.loads(
        (
            run_dir / "stage-12-final_verification_export" / "quality_report.json"
        ).read_text()
    )
    assert any(
        check["requirement"] == "literature_retrieval_integrity"
        and not check["passed"]
        for check in quality["checks"]
    )
    protocol_validation = json.loads(
        (
            run_dir / "stage-07-experiment_design" / "protocol_validation.json"
        ).read_text()
    )
    assert protocol_validation["plugin_id"] == "ml-systems-efficiency"
    assert protocol_validation["ok"] is False
    assert any(
        check["requirement"] == "domain_protocol_valid" and not check["passed"]
        for check in quality["checks"]
    )
    evidence_graph = json.loads(
        (
            run_dir / "stage-12-final_verification_export" / "evidence_graph.json"
        ).read_text()
    )
    governance = json.loads(
        (
            run_dir / "stage-12-final_verification_export" / "governance_report.json"
        ).read_text()
    )
    assert evidence_graph["validation"]["ok"] is True
    graph_kinds = {node["kind"] for node in evidence_graph["nodes"]}
    assert {
        "literature",
        "citation",
        "raw_output",
        "metric",
        "numeric_claim",
        "prose_claim",
    } <= graph_kinds
    paper_evidence = json.loads(
        (
            run_dir / "stage-12-final_verification_export" / "paper_evidence.json"
        ).read_text()
    )
    assert paper_evidence["verification"]["ok"] is True
    assert paper_evidence["blocks"]
    assert governance["ok"] is False
    venue_export = json.loads(
        (
            run_dir / "stage-12-final_verification_export" / "venue_export.json"
        ).read_text()
    )
    assert venue_export["ok"] is False
    assert "contract_not_current_verified" not in venue_export["blockers"]
    assert "template_not_materialized" in venue_export["blockers"]
    assert any(
        check["requirement"] == "asset_governance_valid" and not check["passed"]
        for check in quality["checks"]
    )
    assert any(
        check["requirement"] == "venue_export_valid" and not check["passed"]
        for check in quality["checks"]
    )


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


def test_runner_validates_configured_complete_domain_protocol(
    config: AutoresearchConfig,
) -> None:
    protocol = {
        "confirmatory": True,
        "hypotheses": ["h1", "h2"],
        "primary_metrics": ["quality"],
        "exclusions": ["corrupt input"],
        "evaluator_hash": "a" * 64,
        "stopping_rule": "fixed budget",
        "resource_budget": "matched",
        "seeds": [1, 2, 3],
        "uncertainty": "bootstrap confidence interval",
        "dataset_version": "dataset-v1",
        "split_hash": "b" * 64,
        "model_checkpoint": "model-v1",
        "matched_resource_budgets": True,
        "immutable_evaluator": True,
        "quality_metrics": ["accuracy"],
        "efficiency_metrics": ["latency", "memory", "compute"],
        "baseline_tuning_policy": "same budget",
    }
    configured = replace(
        config,
        experiment=replace(config.experiment, protocol=protocol),
    )

    result = PipelineRunner(configured).run(
        topic="test idea",
        run_id="domain-protocol-run",
        auto_approve=True,
    )

    validation = json.loads(
        (
            Path(result["run_dir"])
            / "stage-07-experiment_design"
            / "protocol_validation.json"
        ).read_text()
    )
    assert validation["ok"] is True


def test_runner_uses_configured_asset_registry(
    config: AutoresearchConfig,
    tmp_path: Path,
) -> None:
    assets = tmp_path / "assets.yaml"
    assets.write_text(
        """
schema_version: 1
assets:
  - asset_id: dataset-1
    kind: dataset
    source_url: https://example.test/dataset
    sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    license_id: Apache-2.0
    privacy_status: public-non-sensitive
    split_hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    governance_approval: ""
    consent_basis: ""
""",
        encoding="utf-8",
    )
    configured = replace(
        config,
        governance=replace(config.governance, assets_file=str(assets)),
    )

    result = PipelineRunner(configured).run(
        topic="test idea",
        run_id="governed-assets-run",
        auto_approve=True,
    )

    report = json.loads(
        (
            Path(result["run_dir"])
            / "stage-12-final_verification_export"
            / "governance_report.json"
        ).read_text()
    )
    assert report["ok"] is True
    assert report["assets"] == ["dataset-1"]


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
    bundle = json.loads((final_dir / "bundle_index.json").read_text())
    assert set(
        ("evidence_graph.json", "governance_report.json", "venue_export.json")
    ) <= set(bundle["files"])
    assert any(
        check["requirement"] == "evaluation_units" and not check["passed"]
        for check in quality["checks"]
    )
    assert "\\section{Results}" in paper
    assert "@misc{" in bib


def test_runner_executes_real_workspace_and_removes_scaffold_claims(
    config: AutoresearchConfig,
    tmp_path: Path,
) -> None:
    source = tmp_path / "real-workspace"
    source.mkdir()
    (source / "experiment.py").write_text(
        """from __future__ import annotations
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--trial", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
values = {"baseline": 1.0, "regularized": 0.9, "overfit": 1.2}
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"primary_metric": values[args.trial], "loss": values[args.trial]}))
""",
        encoding="utf-8",
    )
    plan = ExperimentSpec.default(
        topic="real local evidence",
        metric_key=config.experiment.metric_key,
        metric_direction=config.experiment.metric_direction,
        time_budget_sec=config.experiment.time_budget_sec,
    )
    plan.write_yaml(source / "experiment_plan.yaml")
    configured = replace(
        config,
        experiment=replace(
            config.experiment,
            evidence_mode="real",
            workspace_source=str(source),
        ),
    )

    result = PipelineRunner(configured).run(
        topic="real local evidence",
        run_id="real-workspace-run",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])
    paper = (
        run_dir / "stage-11-paper_draft_revision" / "paper_revised.md"
    ).read_text(encoding="utf-8")
    copied_script = (
        run_dir / "stage-08-experiment_generation" / "experiment" / "experiment.py"
    )

    assert result["status"] == "done"
    assert result["alignment"]["experiment"]["synthetic"] is False
    assert copied_script.read_text(encoding="utf-8") == (
        source / "experiment.py"
    ).read_text(encoding="utf-8")
    assert "deterministic scaffold" not in paper
    assert "domain-specific experiments" not in paper
