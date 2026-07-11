from __future__ import annotations

import json
import hashlib
import re
from datetime import date
from pathlib import Path

import yaml

from autoresearch.adapters.llm.base import LLMProvider
from autoresearch.adapters.literature.arxiv import ArxivSource
from autoresearch.adapters.literature.crossref import CrossrefSource
from autoresearch.adapters.literature.openalex import OpenAlexSource
from autoresearch.adapters.literature.web_research import WebResearchSource
from autoresearch.config import AutoresearchConfig
from autoresearch.domains.profile import load_profile
from autoresearch.experiments.backends.local import LocalBackend
from autoresearch.experiments.ledger import read_ledger
from autoresearch.experiments.evidence import observe_experiment_evidence
from autoresearch.experiments.loop import run_experiment_loop
from autoresearch.experiments.plugins import plugin_for
from autoresearch.experiments.spec import ExperimentSpec
from autoresearch.experiments.workspace import create_workspace, write_spec_markdown
from autoresearch.evidence.graph import EvidenceGraph
from autoresearch.governance.registry import AssetRegistry
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
from autoresearch.literature.search import collect_query_plan
from autoresearch.literature.sources import seed_source
from autoresearch.paper.citations import build_bibtex, verify_citations
from autoresearch.paper.claims import _is_supported, verify_numeric_claims
from autoresearch.paper.draft import draft_paper
from autoresearch.paper.evidence import (
    build_block_registry,
    paper_blocks,
    verify_block_registry,
)
from autoresearch.paper.export import export_bundle
from autoresearch.paper.outline import build_outline
from autoresearch.paper.prose import ProseContext, rewrite_paper_to_prose
from autoresearch.paper.quality import ResearchEvidence, assess_venue_readiness
from autoresearch.paper.review import review_draft
from autoresearch.paper.revision import revise_paper
from autoresearch.paper.venue import assess_venue_export
from autoresearch.pipeline.artifacts import stage_dir, write_json
from autoresearch.pipeline.contracts import contract_for
from autoresearch.pipeline.stages import Stage
from autoresearch.prompts.manager import PromptContext, compose_stage_prompt
from autoresearch.strategy.contributions import mine_contributions, write_contribution_report
from autoresearch.strategy.models import VenueStrategy
from autoresearch.strategy.reviewer import simulate_review, write_review_report
from autoresearch.venues.schema import VenueContract


def execute_placeholder_stage(
    stage: Stage,
    *,
    stage_path: Path,
    run_dir: Path,
    config: AutoresearchConfig,
    topic: str,
    llm_provider: LLMProvider | None = None,
    prompt_context: str = "",
    venue_guidance: str = "",
    venue_contract: VenueContract | None = None,
    venue_strategy: VenueStrategy | None = None,
    prior_lessons: str = "",
) -> None:
    """Write minimal contract artifacts for the current pipeline spine.

    These artifacts are placeholders by design. They make the orchestration,
    checkpoint, and contract layers executable while later units replace each
    stage body with real literature, experiment, and paper-generation logic.
    """

    if stage is Stage.LITERATURE_COLLECT:
        _execute_literature_collect(
            stage_path=stage_path,
            config=config,
            topic=topic,
        )
        return
    if stage is Stage.LITERATURE_SCREEN:
        _execute_literature_screen(stage_path=stage_path, run_dir=run_dir, topic=topic)
        return
    if stage is Stage.SYNTHESIS:
        _execute_synthesis(stage_path=stage_path, run_dir=run_dir, topic=topic)
        return
    if stage is Stage.HYPOTHESIS_GENERATION:
        _execute_hypothesis_generation(
            stage_path=stage_path,
            topic=topic,
            llm_provider=llm_provider,
            prompt_context=prompt_context,
            venue_guidance=venue_guidance,
            prior_lessons=prior_lessons,
        )
        return
    if stage is Stage.EXPERIMENT_DESIGN:
        _execute_experiment_design(stage_path=stage_path, config=config, topic=topic)
        return
    if stage is Stage.EXPERIMENT_GENERATION:
        _execute_experiment_generation(
            stage_path=stage_path,
            run_dir=run_dir,
            config=config,
        )
        return
    if stage is Stage.EXPERIMENT_LOOP:
        _execute_experiment_loop(stage_path=stage_path, run_dir=run_dir, config=config)
        return
    if stage is Stage.RESULT_ANALYSIS_DECISION:
        _execute_result_analysis_decision(
            stage_path=stage_path,
            run_dir=run_dir,
            config=config,
        )
        return
    if stage is Stage.PAPER_DRAFT_REVISION:
        _execute_paper_draft_revision(
            stage_path=stage_path,
            run_dir=run_dir,
            topic=topic,
            config=config,
            llm_provider=llm_provider,
            venue_strategy=venue_strategy,
        )
        return
    if stage is Stage.FINAL_VERIFICATION_EXPORT:
        _execute_final_verification_export(
            stage_path=stage_path,
            run_dir=run_dir,
            config=config,
            venue_contract=venue_contract,
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


def _execute_literature_collect(
    *,
    stage_path: Path,
    config: AutoresearchConfig,
    topic: str,
) -> None:
    if config.literature.mode == "synthetic":
        sources = [seed_source()]
    else:
        source_types = {
            "arxiv": (ArxivSource, config.literature.arxiv_base_url),
            "openalex": (OpenAlexSource, config.literature.openalex_base_url),
            "crossref": (CrossrefSource, config.literature.crossref_base_url),
            "web_research": (WebResearchSource, "https://api.openalex.org"),
        }
        sources = [
            source_type(
                base_url=base_url,
                cache_dir=stage_path / "retrieval" / source_name,
                max_retries=config.literature.max_retries,
                timeout_sec=config.literature.timeout_sec,
            )
            for source_name in config.literature.sources
            for source_type, base_url in (source_types[source_name],)
        ]
    queries = config.literature.queries or (topic,)
    candidates, report = collect_query_plan(
        queries,
        sources,
        per_source_limit=config.literature.per_source_limit,
        saturation_patience=config.literature.saturation_patience,
        saturation_max_new_ratio=config.literature.saturation_max_new_ratio,
    )
    write_papers_jsonl(stage_path / "candidates.jsonl", candidates)
    (stage_path / "search_report.md").write_text(report.to_markdown(), encoding="utf-8")
    write_json(stage_path / "search_report.json", report.to_dict())


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
    write_json(
        stage_path / "literature_gaps.json",
        [
            {
                "gap_id": "gap-1",
                "novelty_statement": f"The exact evidence gap for {topic} remains unresolved.",
                "search_scope": topic,
                "search_date": date.today().isoformat(),
                "sources": sorted({card.evidence_source for card in cards}),
                "nearest_work": [card.citation_key for card in cards],
                "unresolved_uncertainty": "Seed-only retrieval is not a saturation search.",
            }
        ],
    )


def _execute_hypothesis_generation(
    *,
    stage_path: Path,
    topic: str,
    llm_provider: LLMProvider | None,
    prompt_context: str,
    venue_guidance: str,
    prior_lessons: str,
) -> None:
    hypotheses: list[dict[str, object]] = [
        {
            "hypothesis_id": "H1",
            "statement": f"A constrained intervention improves the primary metric for {topic}.",
            "expected_direction": "improve",
            "disconfirming_evidence": "No protocol-matched improvement over baseline.",
            "competes_with": "H2",
        },
        {
            "hypothesis_id": "H2",
            "statement": "Any observed change is explained by variance or resource mismatch.",
            "expected_direction": "no material change",
            "disconfirming_evidence": "A repeated protocol-matched effect with uncertainty bounds.",
            "competes_with": "H1",
        },
    ]
    if llm_provider is not None:
        program_path = Path("program.md")
        program = (
            program_path.read_text(encoding="utf-8") if program_path.is_file() else ""
        )
        prompt = compose_stage_prompt(
            PromptContext(
                stage="hypothesis_generation",
                global_policy=(
                    "Generated claims are proposals, not evidence. Return JSON only."
                ),
                domain_guidance=prompt_context,
                venue_guidance=venue_guidance,
                program_guidance=program,
                stage_template=(
                    "Return an object with a hypotheses array. Each hypothesis needs "
                    "hypothesis_id, statement, expected_direction, "
                    "disconfirming_evidence, and competes_with."
                ),
                retrieved_evidence=topic,
                prior_lessons=prior_lessons,
            )
        )
        try:
            response = llm_provider.complete_json(
                stage="hypothesis_generation",
                messages=(("system", prompt), ("user", f"Research topic: {topic}")),
                required_keys=("hypotheses",),
            )
            hypotheses = _validate_hypotheses(response.data.get("hypotheses"))
        except Exception as exc:  # noqa: BLE001 — fall back to default hypotheses if LLM/validate fails
            import logging

            logging.getLogger("autoresearch.hypothesis").warning(
                "live hypothesis generation failed; using default hypotheses: %s", exc
            )
            # hypotheses already holds the defaults from above
    write_json(stage_path / "hypotheses.json", hypotheses)
    (stage_path / "hypotheses.md").write_text(
        "# Competing Hypotheses\n\n"
        + "\n".join(f"- **{item['hypothesis_id']}**: {item['statement']}" for item in hypotheses)
        + "\n",
        encoding="utf-8",
    )


def _validate_hypotheses(value: object) -> list[dict[str, object]]:
    required = {
        "hypothesis_id",
        "statement",
        "expected_direction",
        "disconfirming_evidence",
        "competes_with",
    }
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("live hypothesis response requires at least two hypotheses")
    hypotheses: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or any(
            not str(item.get(key, "")).strip() for key in required
        ):
            raise ValueError(
                f"live hypothesis response item {index} is missing required fields"
            )
        hypotheses.append({str(key): field for key, field in item.items()})
    return hypotheses


def _execute_experiment_design(
    *,
    stage_path: Path,
    config: AutoresearchConfig,
    topic: str,
) -> None:
    if config.experiment.evidence_mode == "real":
        source_plan = (
            Path(config.experiment.workspace_source).expanduser()
            / "experiment_plan.yaml"
        )
        if not source_plan.is_file():
            raise ValueError("real experiment source requires experiment_plan.yaml")
        protocol = yaml.safe_load(source_plan.read_text(encoding="utf-8")) or {}
        if not isinstance(protocol, dict):
            raise ValueError("real experiment plan must be a mapping")
        spec = ExperimentSpec.from_yaml(source_plan)
        expected = {
            "topic": topic,
            "metric_key": config.experiment.metric_key,
            "metric_direction": config.experiment.metric_direction,
            "time_budget_sec": config.experiment.time_budget_sec,
        }
        actual = {key: getattr(spec, key) for key in expected}
        if actual != expected:
            raise ValueError(
                "real experiment plan execution fields do not match run config: "
                f"expected {expected}, got {actual}"
            )
    else:
        spec = ExperimentSpec.default(
            topic=topic,
            metric_key=config.experiment.metric_key,
            metric_direction=config.experiment.metric_direction,
            time_budget_sec=config.experiment.time_budget_sec,
        )
        protocol = {**spec.to_dict(), **config.experiment.protocol}
    (stage_path / "experiment_plan.yaml").write_text(
        yaml.safe_dump(protocol, sort_keys=False),
        encoding="utf-8",
    )
    profile = load_profile(config.research.profile)
    validation = plugin_for(profile.plugin_id).validate(protocol)
    write_json(stage_path / "protocol_validation.json", validation.to_dict())


def _execute_experiment_generation(
    *, stage_path: Path, run_dir: Path, config: AutoresearchConfig
) -> None:
    plan_path = stage_dir(run_dir, Stage.EXPERIMENT_DESIGN) / "experiment_plan.yaml"
    spec = ExperimentSpec.from_yaml(plan_path)
    workspace = stage_path / "experiment"
    source = (
        Path(config.experiment.workspace_source).expanduser()
        if config.experiment.evidence_mode == "real"
        else None
    )
    create_workspace(
        workspace,
        spec,
        source_dir=source,
        plan_path=plan_path if source is not None else None,
    )
    write_spec_markdown(stage_path / "experiment_spec.md", spec)


def _execute_experiment_loop(
    *, stage_path: Path, run_dir: Path, config: AutoresearchConfig
) -> None:
    generation_dir = stage_dir(run_dir, Stage.EXPERIMENT_GENERATION)
    workspace = generation_dir / "experiment"
    spec = ExperimentSpec.from_yaml(workspace / "experiment_plan.yaml")
    run_experiment_loop(
        spec,
        backend=LocalBackend(allowed_imports=config.experiment.allowed_imports),
        workspace=workspace,
        runs_dir=stage_path / "runs",
        ledger_path=stage_path / "ledger.jsonl",
    )


def _execute_result_analysis_decision(
    *, stage_path: Path, run_dir: Path, config: AutoresearchConfig
) -> None:
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
    hypotheses = json.loads(
        (stage_dir(run_dir, Stage.HYPOTHESIS_GENERATION) / "hypotheses.json").read_text(
            encoding="utf-8"
        )
    )
    outcome_reason = (
        "All prespecified real-workspace trials are recorded; the current evidence "
        "does not resolve the competing hypotheses."
        if config.experiment.evidence_mode == "real"
        else "The deterministic scaffold cannot establish scientific support."
    )
    write_json(
        stage_path / "hypothesis_outcomes.json",
        [
            {
                "hypothesis_id": item["hypothesis_id"],
                "outcome": "inconclusive",
                "run_ids": [entry.run_id for entry in entries],
                "reason": outcome_reason,
            }
            for item in hypotheses
        ],
    )


def _maybe_rewrite_prose(
    *,
    template_draft: str,
    topic: str,
    cards: list,
    ledger: list,
    decision_text: str,
    llm_provider: LLMProvider | None,
    config: AutoresearchConfig,
) -> str | None:
    """Rewrite the template draft into venue-grade prose via the LLM provider.

    Returns None when prose rewriting is not applicable (synthetic mode or no
    provider), so the caller falls back to the deterministic template draft.
    """
    if llm_provider is None:
        return None
    if config.llm.mode != "live":
        return None
    if config.experiment.evidence_mode != "real":
        return None
    try:
        return rewrite_paper_to_prose(
            template_draft=template_draft,
            context=ProseContext(
                topic=topic,
                ledger=tuple(ledger),
                cards=tuple(cards),
                decision_text=decision_text,
            ),
            provider=llm_provider,
        )
    except Exception as exc:  # noqa: BLE001 — prose is best-effort; never block the run
        import logging

        logging.getLogger("autoresearch.paper.prose").warning(
            "prose rewrite failed; falling back to template draft: %s", exc
        )
        return None


def _execute_paper_draft_revision(
    *,
    stage_path: Path,
    run_dir: Path,
    topic: str,
    config: AutoresearchConfig,
    llm_provider: LLMProvider | None = None,
    venue_strategy: VenueStrategy | None = None,
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
        evidence_mode=config.experiment.evidence_mode,
    )
    prose_draft = _maybe_rewrite_prose(
        template_draft=outline + "\n" + draft,
        topic=topic,
        cards=cards,
        ledger=ledger,
        decision_text=decision_text,
        llm_provider=llm_provider,
        config=config,
    )
    reviews = review_draft(draft, evidence_mode=config.experiment.evidence_mode)
    revised = prose_draft if prose_draft is not None else revise_paper(draft, reviews)
    (stage_path / "paper_draft.md").write_text(
        outline + "\n" + draft,
        encoding="utf-8",
    )
    (stage_path / "reviews.md").write_text(reviews, encoding="utf-8")
    (stage_path / "paper_revised.md").write_text(revised, encoding="utf-8")

    # Venue strategy: reviewer simulation + contribution mining
    if venue_strategy is not None:
        _run_strategy_analysis(
            stage_path=stage_path,
            paper_markdown=revised,
            venue_strategy=venue_strategy,
            ledger=tuple(ledger),
            llm_provider=llm_provider,
            topic=topic,
        )

    linked = [entry for entry in ledger if entry.metric is not None]
    write_json(
        stage_path / "empirical_claims.json",
        [
            {
                "claim_id": "empirical-1",
                "statement": f"The recorded primary metric is {linked[-1].metric}.",
                "run_ids": [entry.run_id for entry in linked],
                "metric_definition": linked[-1].metric_definition,
                "experiment_spec_sha256": linked[-1].experiment_spec_sha256,
                "code_sha256": linked[-1].code_sha256,
                "config_sha256": linked[-1].config_sha256,
                "environment": linked[-1].environment,
                "raw_outputs": [path for entry in linked for path in entry.raw_outputs],
            }
        ]
        if linked
        else [],
    )


def _run_strategy_analysis(
    *,
    stage_path: Path,
    paper_markdown: str,
    venue_strategy: VenueStrategy,
    ledger: tuple,
    llm_provider: LLMProvider | None,
    topic: str,
) -> None:
    """Run venue-aware reviewer simulation and contribution mining."""
    import logging

    logger = logging.getLogger("autoresearch.strategy")

    # Reviewer simulation
    try:
        review = simulate_review(
            paper_markdown=paper_markdown,
            venue_strategy=venue_strategy,
            ledger=ledger,
            llm_provider=llm_provider,
        )
        write_review_report(review, stage_path / "strategy_review.json")
        (stage_path / "strategy_review.md").write_text(
            f"# {venue_strategy.display_name} Strategy Review\n\n"
            f"**Overall Score:** {review.overall_score}/10  \n"
            f"**Confidence:** {review.confidence:.0%}\n\n"
            f"## Strengths\n\n"
            + "\n".join(f"- {s}" for s in review.strengths)
            + "\n\n## Weaknesses\n\n"
            + "\n".join(
                f"- **[{w.severity}]** {w.claim}: {w.suggested_fix}"
                for w in review.weaknesses
            )
            + "\n\n## Suggested Experiments\n\n"
            + "\n".join(f"- {e}" for e in review.suggested_experiments)
            + "\n\n## Narrative Suggestions\n\n"
            + "\n".join(f"- {n}" for n in review.narrative_suggestions)
            + f"\n\n## Summary\n\n{review.summary}\n",
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("reviewer simulation failed: %s", exc)

    # Contribution mining
    try:
        claims_path = stage_path / "empirical_claims.json"
        claims_raw: tuple[dict[str, object], ...] = ()
        if claims_path.exists():
            import json

            loaded = json.loads(claims_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                claims_raw = tuple(
                    item for item in loaded if isinstance(item, dict)
                )

        mining = mine_contributions(
            venue_strategy=venue_strategy,
            ledger=ledger,
            claims=claims_raw,
            llm_provider=llm_provider,
            topic=topic,
        )
        write_contribution_report(mining, stage_path / "strategy_contributions.json")
        (stage_path / "strategy_contributions.md").write_text(
            f"# Contribution Mining for {venue_strategy.display_name}\n\n"
            f"**Venue Fit Score:** {mining.venue_fit_score:.2f}\n\n"
            + "\n".join(
                f"## {i+1}. {c.description}\n"
                f"- Relevance: {c.venue_relevance:.0%}\n"
                f"- Strength: {c.strength_score:.0%}\n"
                f"- Hook: {c.narrative_hook}\n"
                for i, c in enumerate(mining.contributions)
            )
            + f"\n{mining.summary}\n",
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("contribution mining failed: %s", exc)


def _execute_final_verification_export(
    *,
    stage_path: Path,
    run_dir: Path,
    config: AutoresearchConfig,
    venue_contract: VenueContract | None,
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
    protocol_validation = json.loads(
        (
            stage_dir(run_dir, Stage.EXPERIMENT_DESIGN)
            / "protocol_validation.json"
        ).read_text(encoding="utf-8")
    )
    trials = list(experiment_plan.get("trials", ()))
    gaps = json.loads(
        (stage_dir(run_dir, Stage.SYNTHESIS) / "literature_gaps.json").read_text(
            encoding="utf-8"
        )
    )
    retrieval = json.loads(
        (
            stage_dir(run_dir, Stage.LITERATURE_COLLECT) / "search_report.json"
        ).read_text(encoding="utf-8")
    )
    hypotheses = json.loads(
        (stage_dir(run_dir, Stage.HYPOTHESIS_GENERATION) / "hypotheses.json").read_text(
            encoding="utf-8"
        )
    )
    outcomes = json.loads(
        (stage_dir(run_dir, Stage.RESULT_ANALYSIS_DECISION) / "hypothesis_outcomes.json").read_text(
            encoding="utf-8"
        )
    )
    claims = json.loads(
        (stage_dir(run_dir, Stage.PAPER_DRAFT_REVISION) / "empirical_claims.json").read_text(
            encoding="utf-8"
        )
    )
    evidence_graph = EvidenceGraph()
    exportable_claim_ids: list[str] = []
    citation_nodes: dict[str, object] = {}
    cited_keys = set(citation_verification.cited_keys)
    for item in screened:
        if item.paper.citation_key not in cited_keys:
            continue
        literature_node = evidence_graph.add_record(
            kind="literature",
            payload=item.paper.to_dict(),
        )
        citation_node = evidence_graph.add_record(
            kind="citation",
            payload={"citation_key": item.paper.citation_key},
        )
        citation_nodes[item.paper.citation_key] = citation_node
        evidence_graph.add_edge(
            literature_node.node_id,
            citation_node.node_id,
            "cites",
        )
        exportable_claim_ids.append(citation_node.node_id)
    entries_by_run = {entry.run_id: entry for entry in ledger}
    metric_nodes: list[tuple[object, object]] = []
    for claim in claims:
        claim_node = evidence_graph.add_record(kind="numeric_claim", payload=claim)
        exportable_claim_ids.append(claim_node.node_id)
        for run_id in claim.get("run_ids", ()):
            entry = entries_by_run.get(run_id)
            if entry is None:
                continue
            metric_node = evidence_graph.add_record(
                kind="metric",
                payload={
                    "run_id": entry.run_id,
                    "metric": entry.metric,
                    "metric_definition": entry.metric_definition,
                },
            )
            metric_nodes.append((entry, metric_node))
            evidence_graph.add_edge(metric_node.node_id, claim_node.node_id, "supports")
            for raw_output in entry.raw_outputs:
                artifact_node = evidence_graph.add_artifact(
                    kind="raw_output",
                    path=stage_dir(run_dir, Stage.EXPERIMENT_LOOP) / raw_output,
                )
                evidence_graph.add_edge(
                    artifact_node.node_id,
                    metric_node.node_id,
                    "produces",
                )
    fallback_artifact = evidence_graph.add_artifact(
        kind="raw_output",
        path=stage_dir(run_dir, Stage.EXPERIMENT_DESIGN) / "experiment_plan.yaml",
    )
    block_node_ids: list[str] = []
    for index, block in enumerate(paper_blocks(paper)):
        citation_keys = re.findall(r"\[@([A-Za-z0-9_:-]+)\]", block)
        number_strings = re.findall(r"(?<![A-Za-z0-9_.-])\d+(?:\.\d+)?", block)
        # Match prose numbers against ledger values with the same rounding
        # tolerance used by verify_numeric_claims (5% relative + 0.05 absolute),
        # so a block is a numeric_claim (provenance-linked) when its numbers
        # round-trip to the ledger — even if the LLM wrote a rounded form like
        # "1.041" for a ledger value of 1.0412165834860359. Without this the
        # block falls back to prose_claim (orphan) and breaks evidence_graph.
        parsed_numbers: list[float] = []
        for token in number_strings:
            try:
                parsed_numbers.append(float(token))
            except ValueError:
                continue
        matched_metrics = [
            (entry, metric_node)
            for entry, metric_node in metric_nodes
            if entry.metric is not None
            and any(_is_supported(num, entry.metric) for num in parsed_numbers)
        ]
        block_node = evidence_graph.add_record(
            kind="numeric_claim" if matched_metrics else "prose_claim",
            payload={"index": index, "text": block},
        )
        block_node_ids.append(block_node.node_id)
        exportable_claim_ids.append(block_node.node_id)
        for citation_key in citation_keys:
            citation_node = citation_nodes.get(citation_key)
            if citation_node is not None:
                evidence_graph.add_edge(
                    citation_node.node_id,
                    block_node.node_id,
                    "supports",
                )
        for _, metric_node in matched_metrics:
            evidence_graph.add_edge(
                metric_node.node_id,
                block_node.node_id,
                "supports",
            )
        if not number_strings and not citation_keys:
            evidence_graph.add_edge(
                fallback_artifact.node_id,
                block_node.node_id,
                "supports",
            )
        if number_strings and not matched_metrics and not citation_keys:
            # Leave the node orphaned so validation blocks fabricated numbers.
            pass
    block_registry = build_block_registry(paper, node_ids=tuple(block_node_ids))
    block_verification = verify_block_registry(paper, block_registry)
    write_json(
        stage_path / "paper_evidence.json",
        {
            **block_registry,
            "verification": {
                "ok": block_verification.ok,
                "issues": list(block_verification.issues),
            },
        },
    )
    graph_validation = evidence_graph.validate(
        exportable_node_ids=tuple(exportable_claim_ids)
    )
    write_json(
        stage_path / "evidence_graph.json",
        {
            "nodes": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "sha256": node.sha256,
                    "path": node.path,
                    "payload": node.payload,
                }
                for node in evidence_graph.nodes.values()
            ],
            "edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation": edge.relation,
                }
                for edge in evidence_graph.edges
            ],
            "validation": {
                "ok": graph_validation.ok,
                "issues": [
                    {
                        "code": issue.code,
                        "node_id": issue.node_id,
                        "message": issue.message,
                    }
                    for issue in graph_validation.issues
                ],
            },
        },
    )
    governance_report = (
        AssetRegistry.load(config.governance.assets_file).to_report(
            require_local=config.experiment.evidence_mode == "real"
        )
        if config.governance.assets_file
        else {
            "ok": False,
            "assets": [],
            "issues": [
                {
                    "code": "no_registered_assets",
                    "message": "No governed dataset, corpus, or model assets are registered.",
                }
            ],
        }
    )
    write_json(stage_path / "governance_report.json", governance_report)
    venue_export = (
        assess_venue_export(
            venue_contract,
            paper_markdown=paper,
            template_materialized=False,
            on=date.today(),
        )
        if venue_contract is not None
        else None
    )
    venue_export_report = (
        venue_export.to_dict()
        if venue_export is not None
        else {
            "ok": False,
            "venue_id": "",
            "year": 0,
            "track": "",
            "template_identity": "",
            "blockers": ["venue_contract_missing"],
        }
    )
    write_json(stage_path / "venue_export.json", venue_export_report)
    manifest = _build_artifact_manifest(run_dir, stage_path)
    write_json(stage_path / "artifact_manifest.json", manifest)
    loop_dir = stage_dir(run_dir, Stage.EXPERIMENT_LOOP)
    provenance_ok = bool(ledger) and all(
        entry.experiment_spec_sha256
        and entry.code_sha256
        and entry.config_sha256
        and entry.environment
        and entry.raw_outputs
        and all((loop_dir / path).is_file() for path in entry.raw_outputs)
        for entry in ledger
    )
    code_hashes = {entry.code_sha256 for entry in ledger if entry.code_sha256}
    protocol_fingerprints = {
        entry.protocol_fingerprint for entry in ledger if entry.protocol_fingerprint
    }
    observed = observe_experiment_evidence(
        experiment_plan,
        ledger=ledger,
        loop_dir=loop_dir,
    )
    evidence = ResearchEvidence(
        screened_papers=len(screened),
        baselines=observed.baselines,
        evaluation_units=observed.evaluation_units,
        seeds=observed.seeds,
        ablations=observed.ablations,
        verified_metrics=observed.verified_metrics,
        confidence_intervals=observed.confidence_intervals,
        effect_sizes=observed.effect_sizes,
        compute_reporting=observed.compute_reporting,
        hypothesis_outcomes=bool(outcomes)
        and {item.get("hypothesis_id") for item in outcomes}
        == {item.get("hypothesis_id") for item in hypotheses}
        and all(
            item.get("outcome") in {"supported", "refuted", "inconclusive"}
            for item in outcomes
        ),
        literature_gap_records=bool(gaps) and all(
            gap.get("search_scope")
            and gap.get("search_date")
            and gap.get("sources")
            and gap.get("nearest_work")
            and gap.get("unresolved_uncertainty")
            for gap in gaps
        ),
        literature_retrieval_integrity=(
            retrieval.get("status") == "ok"
            and retrieval.get("synthetic") is False
            and retrieval.get("saturated") is True
            and bool(retrieval.get("source_results"))
        ),
        domain_protocol_valid=protocol_validation.get("ok") is True,
        evidence_graph_valid=(
            graph_validation.ok
            and block_verification.ok
            and bool(exportable_claim_ids)
        ),
        asset_governance_valid=governance_report["ok"] is True,
        venue_export_valid=venue_export_report["ok"] is True,
        empirical_claim_links=bool(claims) and all(
            claim.get("run_ids")
            and claim.get("metric_definition")
            and claim.get("experiment_spec_sha256")
            and claim.get("code_sha256")
            and claim.get("config_sha256")
            and claim.get("environment")
            and claim.get("raw_outputs")
            for claim in claims
        ),
        preregistered_confirmatory_spec=bool(experiment_plan.get("confirmatory"))
        and bool(experiment_plan.get("hypotheses"))
        and bool(experiment_plan.get("stopping_rule"))
        and bool(experiment_plan.get("metrics")),
        immutable_evaluation=bool(ledger)
        and len(code_hashes) == 1
        and all(entry.evaluator_immutable for entry in ledger),
        protocol_parity=bool(ledger) and len(protocol_fingerprints) == 1,
        failed_runs_accounted=len(ledger) == len(trials),
        limitations="limitations" in paper.lower(),
        artifact_manifest=bool(manifest["artifacts"]),
        artifact_provenance=provenance_ok,
        competing_hypotheses=len(hypotheses) >= 2
        and all(item.get("competes_with") for item in hypotheses),
    )
    quality_assessment = assess_venue_readiness(
        paper,
        citation_verification=citation_verification,
        claim_verification=claim_verification,
        profile=load_profile(config.research.profile),
        depth=config.research.depth,
        evidence=evidence,
        threshold=config.research.quality_threshold,
    )
    export_bundle(
        stage_path=stage_path,
        paper_markdown=paper,
        bibtex=build_bibtex(screened),
        citation_verification=citation_verification,
        claim_verification=claim_verification,
        quality_assessment=quality_assessment,
    )
    write_json(stage_path / "artifact_manifest.json", _build_artifact_manifest(run_dir, stage_path))


def _build_artifact_manifest(run_dir: Path, stage_path: Path) -> dict[str, object]:
    artifacts = []
    operational_files = {
        run_dir / "checkpoint.json",
        run_dir / "checkpoint_events.jsonl",
        run_dir / "decisions.jsonl",
    }
    for path in sorted(run_dir.rglob("*")):
        if (
            not path.is_file()
            or path == stage_path / "artifact_manifest.json"
            or path in operational_files
        ):
            continue
        artifacts.append(
            {
                "path": path.relative_to(run_dir).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
        )
    return {"artifacts": artifacts}
