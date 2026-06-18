# autoresearch

Local workflow for turning a research idea into an auditable paper candidate.

This project is being built from the plan in
`docs/plans/2026-06-15-001-feat-local-autoresearch-workflow-plan.md`.
The current implementation is an executable research scaffold: config loading,
12 stage contracts, checkpointing, a project skill harness, seed literature,
local toy experiments, evidence-linked paper export, and profile-aware quality
gates. It is not yet a system that can produce venue-ready science unattended.

## Current Local Flow

```bash
uv sync --extra dev
python -m autoresearch init --path config.yaml
uv run autoresearch run --config config.yaml --topic "Your research idea" --auto-approve
uv run autoresearch status artifacts/<run_id>
uv run --extra dev pytest -q
uv run python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/autoresearch-ml-systems
```

Without `--auto-approve`, the runner pauses before gate stages so the user can
inspect artifacts before continuing.

The current runner writes real structured artifacts for the seed literature
path, local experiment path, and paper export path: candidates, screened
shortlist, knowledge cards, experiment workspace, subprocess run metrics,
ledger decisions, a proceed/refine decision, revised paper markdown, BibTeX,
LaTeX, bundle index, citation/numeric-claim verification report, and a
venue-readiness quality report. Artifact integrity can pass while
`submission_ready` remains false; this is intentional because the scientific
content is still a deterministic scaffold, not a venue-ready paper.

## Research Alignment

The default is empirical ML systems and efficient training at `top_venue`
depth. It favors fixed-resource comparisons, strong matched baselines,
mechanism and ablation evidence, uncertainty and effect-size reporting, compute
disclosure, and honest null results. See
[`docs/specs/research-alignment.md`](docs/specs/research-alignment.md) for the
source-backed domain decision and depth contract.

The numeric depth floors are project defaults, not requirements imposed by
NeurIPS, ICML, ICLR, or MLSys. Change `research.profile` or `research.depth` in
the config before a run. A different research domain requires a compatible
profile and skill, not only a different venue label.

## Skill Harness

Project skills live under `skills/`. Each skill has standard `SKILL.md` and
`agents/openai.yaml` files plus `harness.yaml` for stage/profile/depth matching,
stage instructions, and progressive reference loading. Every executed stage
writes `skill_context.md` and `skills_applied.json` for auditability.

The final `quality_report.json` records the selected profile and depth and a
required/observed/pass result for every machine-readable depth requirement.
Missing structured evidence blocks readiness even when all pipeline stages and
citation checks complete.

## Target Direction

- Idea intake and problem decomposition
- Literature collection with provenance
- Hypothesis and experiment design gates
- Local sandbox experiment execution
- Fixed-budget edit/run/evaluate loop
- Paper drafting, review, revision, and export
- Citation and numeric claim verification
- Durable run memory
