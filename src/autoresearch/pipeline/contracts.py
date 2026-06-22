from __future__ import annotations

from dataclasses import dataclass

from autoresearch.pipeline.stages import Stage


@dataclass(frozen=True)
class StageContract:
    stage: Stage
    input_files: tuple[str, ...]
    output_files: tuple[str, ...]
    definition_of_done: str


CONTRACTS: dict[Stage, StageContract] = {
    Stage.IDEA_INTAKE: StageContract(
        stage=Stage.IDEA_INTAKE,
        input_files=(),
        output_files=("goal.md", "run_config.json"),
        definition_of_done="Research idea translated into a scoped goal.",
    ),
    Stage.PROBLEM_DECOMPOSE: StageContract(
        stage=Stage.PROBLEM_DECOMPOSE,
        input_files=("goal.md",),
        output_files=("problem_tree.md",),
        definition_of_done="At least three sub-questions and constraints captured.",
    ),
    Stage.LITERATURE_COLLECT: StageContract(
        stage=Stage.LITERATURE_COLLECT,
        input_files=("problem_tree.md",),
        output_files=("candidates.jsonl", "search_report.md"),
        definition_of_done="Candidate literature collected with source provenance.",
    ),
    Stage.LITERATURE_SCREEN: StageContract(
        stage=Stage.LITERATURE_SCREEN,
        input_files=("candidates.jsonl",),
        output_files=("shortlist.jsonl", "screening_report.md"),
        definition_of_done="Literature screened for relevance and quality.",
    ),
    Stage.SYNTHESIS: StageContract(
        stage=Stage.SYNTHESIS,
        input_files=("shortlist.jsonl",),
        output_files=("synthesis.md", "knowledge_cards.jsonl", "literature_gaps.json"),
        definition_of_done="Research gaps and reusable knowledge cards produced.",
    ),
    Stage.HYPOTHESIS_GENERATION: StageContract(
        stage=Stage.HYPOTHESIS_GENERATION,
        input_files=("synthesis.md",),
        output_files=("hypotheses.md", "hypotheses.json"),
        definition_of_done="Falsifiable hypotheses created from synthesis.",
    ),
    Stage.EXPERIMENT_DESIGN: StageContract(
        stage=Stage.EXPERIMENT_DESIGN,
        input_files=("hypotheses.md",),
        output_files=("experiment_plan.yaml", "protocol_validation.json"),
        definition_of_done="Baselines, ablations, metrics, and resources defined.",
    ),
    Stage.EXPERIMENT_GENERATION: StageContract(
        stage=Stage.EXPERIMENT_GENERATION,
        input_files=("experiment_plan.yaml",),
        output_files=("experiment/", "experiment_spec.md"),
        definition_of_done="Experiment workspace and spec generated.",
    ),
    Stage.EXPERIMENT_LOOP: StageContract(
        stage=Stage.EXPERIMENT_LOOP,
        input_files=("experiment/", "experiment_spec.md"),
        output_files=("runs/", "ledger.jsonl"),
        definition_of_done="Fixed-budget experiment loop completed or converged.",
    ),
    Stage.RESULT_ANALYSIS_DECISION: StageContract(
        stage=Stage.RESULT_ANALYSIS_DECISION,
        input_files=("runs/", "ledger.jsonl"),
        output_files=("analysis.md", "decision.md", "hypothesis_outcomes.json"),
        definition_of_done="Results analyzed and proceed/refine/pivot decision made.",
    ),
    Stage.PAPER_DRAFT_REVISION: StageContract(
        stage=Stage.PAPER_DRAFT_REVISION,
        input_files=("analysis.md", "decision.md", "shortlist.jsonl"),
        output_files=(
            "paper_draft.md",
            "reviews.md",
            "paper_revised.md",
            "empirical_claims.json",
        ),
        definition_of_done="Paper drafted, reviewed, and revised.",
    ),
    Stage.FINAL_VERIFICATION_EXPORT: StageContract(
        stage=Stage.FINAL_VERIFICATION_EXPORT,
        input_files=("paper_revised.md",),
        output_files=(
            "paper.tex",
            "references.bib",
            "verification_report.json",
            "quality_report.json",
            "bundle_index.json",
            "artifact_manifest.json",
            "evidence_graph.json",
            "governance_report.json",
            "venue_export.json",
            "paper_evidence.json",
        ),
        definition_of_done="Paper bundle exported with citation and claim verification.",
    ),
}


def contract_for(stage: Stage) -> StageContract:
    return CONTRACTS[stage]
