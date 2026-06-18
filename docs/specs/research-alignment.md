# Research Alignment Spec

Created: 2026-06-18
Status: normative for the default profile

## Product Claim

`autoresearch` turns one research idea into an **auditable paper candidate**. It
does not claim that a completed run is scientifically novel, correct, or ready
for submission. Those are gate outcomes supported by artifacts, not pipeline
completion states.

The default profile is `ml-systems-efficiency` at depth `top_venue`. It targets
empirical ML systems and efficient training, not arbitrary academic research.

## Domain Alignment

- **Primary domain:** empirical ML systems, efficient training, optimizer and
  architecture behavior under fixed resource budgets, inference efficiency,
  compression, and reproducible agentic research.
- **Venue family:** MLSys first for systems contributions; NeurIPS, ICML, and
  ICLR when the main contribution is a generally relevant ML method or finding.
- **Evidence bias:** controlled empirical evidence over speculative breadth;
  mechanism and ablation evidence over leaderboard-only gains.
- **Comparison bias:** claim-matched strong baselines under identical data,
  evaluation, tuning, and resource budgets.
- **Reporting bias:** effect sizes and uncertainty, resource and failed-run
  accounting, and explicit negative or inconclusive outcomes.
- **Autonomy bias:** agents may generate hypotheses and code, but cannot certify
  novelty, silently change the evaluation harness, or promote an unsupported
  claim into the paper.

This profile is intentionally unsuitable for pure theorem proving, clinical or
human-subject studies, wet-lab work, and hardware fabrication. Add a separate
profile and skill for those domains.

## Source Basis

The following are primary sources used to derive this contract:

- The [NeurIPS paper checklist](https://neurips.cc/public/guides/PaperChecklist)
  requires claim/scope alignment, limitations, reproducibility, full
  experimental settings, uncertainty reporting, and per-experiment plus total
  compute disclosure.
- The [NeurIPS 2025 call for papers](https://neurips.cc/Conferences/2025/CallForPapers)
  makes the checklist part of the submission and explicitly welcomes deep
  analysis of existing methods, including limitations and behavior.
- The [ICML 2026 author instructions](https://icml.cc/Conferences/2026/AuthorInstructions)
  state that critical evidence belongs in the paper and that code availability
  and reproducibility affect decisions.
- The [MLSys 2025 call for papers](https://mlsys.org/Conferences/2025/CallForPapers)
  evaluates novelty, quality, interest, and impact and uses ACM-style artifact
  evaluation for code, data, models, workflows, and results.
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) demonstrates
  a narrow fixed-time edit/run/measure loop with an immutable evaluator and
  append-only result log. It is an experiment optimizer, not an idea-to-paper
  scientific validity harness.
- [The AI Scientist](https://arxiv.org/abs/2408.06292) demonstrates an
  idea/code/experiment/paper/review loop. Its automated reviewer score is an
  evaluation signal, not proof of novelty or correctness.

Conference sources do **not** mandate universal counts for papers, datasets, or
random seeds. Numeric floors below are local operational defaults that force a
serious first pass. They must never be represented as venue rules.

## Depth Contract

### `exploratory`

Use for feasibility and falsification. A narrow result is acceptable. At least
one relevant baseline and evaluation unit, one ablation, resource reporting,
and an explicit outcome for every hypothesis are required. Statistical
uncertainty may be deferred only with a recorded reason.

### `publication`

Use for a defensible workshop or conference paper candidate. Require a
claim-scoped literature review, strong/simple/resource-matched baselines as
applicable, at least two evaluation units, repeated trials, uncertainty and
effect sizes, two ablations, compute disclosure, and reproducibility commands.

### `top_venue`

Use for a paper candidate intended to survive top-venue review. In addition to
the publication contract, require literature saturation around the exact
novelty claim, competing hypotheses, evaluation across at least three relevant
units (datasets, models, workloads, hardware targets, or environments), at
least five seeds or an explicit power/variance justification, three ablations,
multiple quality-and-efficiency metrics, failed-run accounting, limitations,
and an artifact manifest.

The machine-readable defaults live in
`src/autoresearch/profiles/ml-systems-efficiency.yaml`. A threshold waiver is
valid only when it names the affected claim, explains why the default is
inapplicable, and supplies an alternative test. Citation integrity, immutable
evaluation, protocol parity, and artifact provenance are never waivable.

## Claim And Evidence Invariants

1. Every novelty statement maps to a literature-gap record with search scope,
   date, sources, nearest work, and unresolved uncertainty.
2. Every empirical claim maps to immutable run IDs, exact metric definitions,
   an experiment spec, code/config identity, environment, and raw outputs.
3. Baseline comparisons use the same data split, evaluator, tuning allowance,
   stopping rule, and resource budget unless the difference is the studied
   variable and is disclosed.
4. Primary metrics, hypotheses, exclusions, and stopping rules are frozen before
   confirmatory execution. Exploratory changes are labeled exploratory.
5. Every hypothesis ends as `supported`, `refuted`, or `inconclusive`; null and
   negative outcomes remain in the ledger.
6. Paper citations and numbers resolve to registries. Generated prose cannot
   create evidence.
7. `submission_ready` is false if any required check is missing, failed, or only
   inferred from prose.

## Skill Harness Contract

Each project skill contains:

- `SKILL.md` with only `name` and `description` frontmatter;
- `harness.yaml` declaring profile/depth/stage applicability, matching terms,
  priority, stage-specific instructions, and stage-specific reference files;
- optional `references/` files loaded only for applicable stages;
- `agents/openai.yaml` for UI metadata.

The harness must validate metadata and reference paths at load time, select
skills deterministically, render only stage-relevant material, and write
`skill_context.md` plus `skills_applied.json` into every stage directory. A run
with skills disabled still records that no skill was applied.

The final quality report must identify profile, depth, each configured
requirement, observed evidence, pass/fail state, and blocking reason. Completing
all twelve pipeline stages is not evidence that these checks passed.

## User Alignment Surface

Before a costly run, show the selected profile, depth, target venue family,
primary claim type, resource budget, and any proposed threshold waiver. Changing
only a venue label is not a domain change. A profile override must select a
compatible skill and quality rubric.
