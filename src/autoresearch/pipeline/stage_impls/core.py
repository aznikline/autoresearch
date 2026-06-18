from __future__ import annotations

import json
from pathlib import Path

import yaml

from autoresearch.config import AutoresearchConfig
from autoresearch.domains.profile import load_profile
from autoresearch.experiments.backends.local import LocalBackend
from autoresearch.experiments.ledger import read_ledger
from autoresearch.experiments.loop import run_experiment_loop
from autoresearch.experiments.spec import ExperimentSpec
from autoresearch.experiments.workspace import create_workspace, write_spec_markdown
from autoresearch.knowledge.cards import (
    cards_from_screened,
    read_cards_jsonl,
    write_cards_jsonl,
)
from autoresearch.literature.models import (
    read_papers_jsonl,
    read_screened_jsonl,
    write_papers_jsonl,
    write_screened_jsonl,
)
from autoresearch.literature.screening import screen_papers
from autoresearch.literature.search import collect_candidates
from autoresearch.literature.sources import seed_source
from autoresearch.paper.citations import build_bibtex, verify_citations
from autoresearch.paper.claims import verify_numeric_claims
from autoresearch.paper.draft import draft_paper
from autoresearch.paper.export import export_bundle
from autoresearch.paper.outline import build_outline
from autoresearch.paper.quality import ResearchEvidence, assess_venue_readiness
from autoresearch.paper.review import review_draft
from autoresearch.paper.revision import revise_paper
from autoresearch.pipeline.artifacts import stage_dir, write_json
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.stages import Stage


def execute_placeholder_stage(
    stage: Stage,
    *,
    stage_path: Path,
    run_dir: Path,
    config: AutoresearchConfig,
    topic: str,
) -> None:
    """Write minimal contract artifacts for the current pipeline spine.

    These artifacts are placeholders by design. They make the orchestration,
    checkpoint, and contract layers executable while later units replace each
    stage body with real literature, experiment, and paper-generation logic.
    """

    if stage is Stage.LITERATURE_COLLECT:
        _execute_literature_collect(stage_path=stage_path, topic=topic)
        return
    if stage is Stage.LITERATURE_SCREEN:
        _execute_literature_screen(stage_path=stage_path, run_dir=run_dir, topic=topic)
        return
    if stage is Stage.SYNTHESIS:
        _execute_synthesis(stage_path=stage_path, run_dir=run_dir, topic=topic)
        return
    if stage is Stage.EXPERIMENT_DESIGN:
        _execute_experiment_design(stage_path=stage_path, config=config, topic=topic)
        return
    if stage is Stage.EXPERIMENT_GENERATION:
        _execute_experiment_generation(stage_path=stage_path, run_dir=run_dir)
        return
    if stage is Stage.EXPERIMENT_LOOP:
        _execute_experiment_loop(stage_path=stage_path, run_dir=run_dir)
        return
    if stage is Stage.RESULT_ANALYSIS_DECISION:
        _execute_result_analysis_decision(stage_path=stage_path, run_dir=run_dir)
        return
    if stage is Stage.PAPER_DRAFT_REVISION:
        _execute_paper_draft_revision(stage_path=stage_path, run_dir=run_dir, topic=topic)
        return
    if stage is Stage.FINAL_VERIFICATION_EXPORT:
        _execute_final_verification_export(
            stage_path=stage_path,
            run_dir=run_dir,
            config=config,
        )
        return

    contract = contract_for(stage)
    for output in contract.output_files:
        output_path = stage_path / output
        if output.endswith("/"):
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "README.md").write_text(
                f"# {stage.slug}\n\nPlaceholder workspace for {topic}.\n",
                encoding="utf-8",
            )
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_placeholder(output_path, stage=stage, config=config, topic=topic)


def _write_placeholder(
    path: Path,
    *,
    stage: Stage,
    config: AutoresearchConfig,
    topic: str,
) -> None:
    if path.suffix == ".json":
        write_json(
            path,
            {
                "stage": stage.slug,
                "topic": topic,
                "project": config.project.name,
                "placeholder": True,
            },
        )
        return
    if path.suffix == ".jsonl":
        path.write_text(
            json.dumps(
                {
                    "stage": stage.slug,
                    "topic": topic,
                    "placeholder": True,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return
    if path.suffix in {".yaml", ".yml"}:
        path.write_text(
            yaml.safe_dump(
                {
                    "stage": stage.slug,
                    "topic": topic,
                    "metric_key": config.experiment.metric_key,
                    "metric_direction": config.experiment.metric_direction,
                    "placeholder": True,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return
    if path.suffix == ".bib":
        path.write_text("% Placeholder BibTeX; real citations land in Unit 7.\n", encoding="utf-8")
        return
    if path.suffix == ".tex":
        path.write_text(
            "\\documentclass{article}\n\\begin{document}\nPlaceholder paper.\n\\end{document}\n",
            encoding="utf-8",
        )
        return
    path.write_text(
        f"# {stage.slug}\n\nTopic: {topic}\n\nPlaceholder artifact.\n",
        encoding="utf-8",
    )


def _execute_literature_collect(*, stage_path: Path, topic: str) -> None:
    candidates, report = collect_candidates(
        topic,
        [seed_source()],
        per_source_limit=10,
    )
    write_papers_jsonl(stage_path / "candidates.jsonl", candidates)
    (stage_path / "search_report.md").write_text(report.to_markdown(), encoding="utf-8")


def _execute_literature_screen(
    *,
    stage_path: Path,
    run_dir: Path,
    topic: str,
) -> None:
    candidates_path = stage_dir(run_dir, Stage.LITERATURE_COLLECT) / "candidates.jsonl"
    candidates = read_papers_jsonl(candidates_path)
    screened, report = screen_papers(candidates, topic=topic)
    kept = [item for item in screened if item.decision == "keep"]
    write_screened_jsonl(stage_path / "shortlist.jsonl", kept)
    (stage_path / "screening_report.md").write_text(
        report.to_markdown(),
        encoding="utf-8",
    )


def _execute_synthesis(*, stage_path: Path, run_dir: Path, topic: str) -> None:
    shortlist_path = stage_dir(run_dir, Stage.LITERATURE_SCREEN) / "shortlist.jsonl"
    screened = read_screened_jsonl(shortlist_path)
    cards = cards_from_screened(screened)
    write_cards_jsonl(stage_path / "knowledge_cards.jsonl", cards)
    lines = [
        "# Synthesis",
        "",
        f"Topic: {topic}",
        "",
        "## Grounded Starting Points",
    ]
    if not cards:
        lines.append("- No relevant seed literature passed screening.")
    else:
        for card in cards:
            lines.append(f"- `{card.citation_key}`: {card.claim}")
    (stage_path / "synthesis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _execute_experiment_design(
    *,
    stage_path: Path,
    config: AutoresearchConfig,
    topic: str,
) -> None:
    spec = ExperimentSpec.default(
        topic=topic,
        metric_key=config.experiment.metric_key,
        metric_direction=config.experiment.metric_direction,
        time_budget_sec=config.experiment.time_budget_sec,
    )
    spec.write_yaml(stage_path / "experiment_plan.yaml")


def _execute_experiment_generation(*, stage_path: Path, run_dir: Path) -> None:
    plan_path = stage_dir(run_dir, Stage.EXPERIMENT_DESIGN) / "experiment_plan.yaml"
    spec = ExperimentSpec.from_yaml(plan_path)
    workspace = stage_path / "experiment"
    create_workspace(workspace, spec)
    write_spec_markdown(stage_path / "experiment_spec.md", spec)


def _execute_experiment_loop(*, stage_path: Path, run_dir: Path) -> None:
    generation_dir = stage_dir(run_dir, Stage.EXPERIMENT_GENERATION)
    workspace = generation_dir / "experiment"
    spec = ExperimentSpec.from_yaml(workspace / "experiment_plan.yaml")
    run_experiment_loop(
        spec,
        backend=LocalBackend(),
        workspace=workspace,
        runs_dir=stage_path / "runs",
        ledger_path=stage_path / "ledger.jsonl",
    )


def _execute_result_analysis_decision(*, stage_path: Path, run_dir: Path) -> None:
    ledger_path = stage_dir(run_dir, Stage.EXPERIMENT_LOOP) / "ledger.jsonl"
    entries = read_ledger(ledger_path)
    kept = [entry for entry in entries if entry.decision == "keep" and entry.metric is not None]
    best = kept[-1] if kept else None
    lines = ["# Result Analysis", ""]
    if not entries:
        lines.append("No experiment runs were recorded.")
    else:
        for entry in entries:
            lines.append(
                f"- `{entry.trial_id}`: status={entry.status}, "
                f"metric={entry.metric}, decision={entry.decision}"
            )
    if best is not None:
        lines.extend(["", f"Best kept trial: `{best.trial_id}` with metric {best.metric}."])
    (stage_path / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    decision = "PROCEED" if best is not None else "REFINE"
    reason = (
        f"Proceed with trial `{best.trial_id}` as the current evidence baseline."
        if best is not None
        else "No valid kept trial exists; refine experiment generation."
    )
    (stage_path / "decision.md").write_text(
        f"# Research Decision\n\nDecision: {decision}\n\n{reason}\n",
        encoding="utf-8",
    )


def _execute_paper_draft_revision(
    *,
    stage_path: Path,
    run_dir: Path,
    topic: str,
) -> None:
    cards = read_cards_jsonl(stage_dir(run_dir, Stage.SYNTHESIS) / "knowledge_cards.jsonl")
    ledger = read_ledger(stage_dir(run_dir, Stage.EXPERIMENT_LOOP) / "ledger.jsonl")
    decision_text = (
        stage_dir(run_dir, Stage.RESULT_ANALYSIS_DECISION) / "decision.md"
    ).read_text(encoding="utf-8")
    outline = build_outline(topic=topic, cards=cards, ledger=ledger)
    draft = draft_paper(
        topic=topic,
        cards=cards,
        ledger=ledger,
        decision_text=decision_text,
    )
    reviews = review_draft(draft)
    revised = revise_paper(draft, reviews)
    (stage_path / "paper_draft.md").write_text(
        outline + "\n" + draft,
        encoding="utf-8",
    )
    (stage_path / "reviews.md").write_text(reviews, encoding="utf-8")
    (stage_path / "paper_revised.md").write_text(revised, encoding="utf-8")


def _execute_final_verification_export(
    *,
    stage_path: Path,
    run_dir: Path,
    config: AutoresearchConfig,
) -> None:
    paper = (
        stage_dir(run_dir, Stage.PAPER_DRAFT_REVISION) / "paper_revised.md"
    ).read_text(encoding="utf-8")
    screened = read_screened_jsonl(
        stage_dir(run_dir, Stage.LITERATURE_SCREEN) / "shortlist.jsonl"
    )
    ledger = read_ledger(stage_dir(run_dir, Stage.EXPERIMENT_LOOP) / "ledger.jsonl")
    citation_verification = verify_citations(paper, screened)
    claim_verification = verify_numeric_claims(paper, ledger)
    experiment_plan = yaml.safe_load(
        (stage_dir(run_dir, Stage.EXPERIMENT_DESIGN) / "experiment_plan.yaml").read_text(
            encoding="utf-8"
        )
    ) or {}
    trials = list(experiment_plan.get("trials", ()))
    evidence = ResearchEvidence(
        screened_papers=len(screened),
        baselines=sum(
            1 for trial in trials if "baseline" in str(trial.get("trial_id", "")).lower()
        ),
        evaluation_units=len(experiment_plan.get("evaluation_units", ())),
        seeds=len(experiment_plan.get("seeds", ())),
        ablations=sum(
            1 for trial in trials if "baseline" not in str(trial.get("trial_id", "")).lower()
        ),
        verified_metrics=len(experiment_plan.get("metrics", ())),
        confidence_intervals=bool(experiment_plan.get("confidence_intervals", False)),
        effect_sizes=bool(experiment_plan.get("effect_sizes", False)),
        compute_reporting=bool(experiment_plan.get("compute_reporting", False)),
        hypothesis_outcomes=bool(experiment_plan.get("hypothesis_outcomes", False)),
    )
    quality_assessment = assess_venue_readiness(
        paper,
        citation_verification=citation_verification,
        claim_verification=claim_verification,
        profile=load_profile(config.research.profile),
        depth=config.research.depth,
        evidence=evidence,
    )
    export_bundle(
        stage_path=stage_path,
        paper_markdown=paper,
        bibtex=build_bibtex(screened),
        citation_verification=citation_verification,
        claim_verification=claim_verification,
        quality_assessment=quality_assessment,
    )
