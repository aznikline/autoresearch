---
name: academic-research-skills
description: Methodology reference + preregistration helper for academic research. Bound a claim, form competing hypotheses, freeze evaluator+splits before confirmatory runs, run fair fixed-budget baselines under protocol parity, report effect sizes+CIs+compute, preserve negative/null/failed results. Field-aware (ML-sys vs NLP vs CV vs DB differ). Use when the user wants to design a research study / write a preregistration / check methodology rigor.
---

# Academic Research Skills

A **methodology reference + preregistration helper**. Two parts, both with explicit no-autonomy: (1) a methodology reference (bound the claim, form hypotheses, freeze protocol, fair baselines, honest reporting) that is field-aware; (2) a preregistration helper that produces a bounded-claim spec the human approves before any code runs. It does NOT generate novel ideas, does NOT run experiments, does NOT claim submission-readiness.

## When to Use

- User wants to design a research study (claim, hypotheses, experiment design)
- User wants a preregistration spec before running experiments
- User wants to check if a study's methodology is rigorous (fair baselines, seeds, leakage, etc.)
- User has an idea and wants to scope it to a doable, falsifiable experiment

## Part 1: Methodology reference (field-aware)

The methodology differs by field. Consult the matching reference file:
- Data management/mining (DB/systems): `references/methodology-data-management-mining.md` — record DB versions, schema, workload, tuned baselines on matched hardware, latency tails/throughput/correctness.
- ML systems: `references/methodology-ml-systems.md` — claim design (method quality / resource efficiency / mechanism), protocol parity.
- NLP: `references/methodology-natural-language-processing.md` — corpus identity, contamination, task-valid evaluation.
- CV: `references/methodology-computer-vision.md` — dataset/split/checksum, pretraining overlap.
- Foundation models/LLM: `references/methodology-foundation-models-llm.md` — exact checkpoint, prompt, judge validation, memorization.

**Domain-agnostic core** (applies to all):
1. **Bound the claim.** One falsifiable question, scoped to one experiment. Not "understand X".
2. **Competing hypotheses.** H1 (the claim) + H2 (the null/alternative). Both falsifiable, both reported.
3. **Freeze the protocol before confirmatory runs.** Evaluator, splits, metric, seeds — frozen before the results-generating run. No post-hoc metric/baseline swaps.
4. **Fair baselines.** Tuned, on matched resources. No untuned strawman.
5. **Report effect sizes + CIs + compute.** Not just point estimates. Mean ± std or bootstrap CIs. Compute budget stated.
6. **Preserve null/negative/failed/invalid/rejected.** Reported as-is, not omitted. (autoresearch's `program.md` charter.)

## Part 2: Preregistration helper

Fill `references/preregistration-template.md` from the user's idea. The template requires: research question, bounded claim, falsifier, success criterion, primary metric+definition, baselines, datasets/splits, seeds, compute budget, stopping rule, competing hypotheses, what's preserved.

**Anti-patterns to reject** (from the template): vague question, untuned baseline, no falsifier, no success criterion, unstated compute, single seed, undefined/swappable metric.

**The preregistration is FROZEN on human approval.** After the experiment, results are reported against the frozen spec. Deviations disclosed, not hidden.

## Discipline Rules (non-negotiable)

1. **No autonomy over novel ideas.** This skill scopes and structures; the research idea comes from the human. Do not "generate a research idea" — help bound the one the user has.
2. **No submission-readiness claims.** Methodology rigor ≠ acceptance. A well-preregistered study can still fail at review. Do not claim "this is ready to submit".
3. **No novelty-from-model-judgment.** (from `program.md`) Novelty is reported as "no overlapping hit found as of date D" via Question-Validator's search, never as "this is novel" from the model's judgment.
4. **Field-aware, not one-size-fits-all.** DB methodology (latency tails, tuned baselines) differs from NLP (contamination, task-valid eval) differs from CV (split/checksum). Use the right reference file.
5. **Preserve negative results.** A null result is a result. Do not pressure the user to only report positives.

## How other skills use this

- **Question-Validator**: produces the bounded-claim spec; Academic-Research-Skills turns it into a full preregistration (adds hypotheses, baselines, seeds, budget, stopping rule).
- **Paper-Writer**: the frozen preregistration's primary metric + success criterion become the paper's central claim; the experiment runs against the frozen spec.
- **autoresearch**: the 5 domain methodology files ARE the autoresearch domain skills' methodology, extracted for reuse outside a full 12-stage run. autoresearch's `program.md` charter (preserve null/negative, no novelty-from-model-judgment) is the source of the discipline here.

## Limitations to state to the user

- Methodology reference is a checklist, not a substitute for domain expertise. A DB expert will catch issues a generic checklist misses.
- Preregistration does not guarantee acceptance — it guarantees rigor (and reviewers increasingly require it).
- The field-aware references are dated snapshots; re-sync from autoresearch's `skills/autoresearch-*/references/methodology.md` if those change.

## Source

Methodology files: copied from `skills/autoresearch-*/references/methodology.md (within this repo)` (5 domain skills). Charter: `program.md (repo root)`. Preregistration template: derived from the bounded-claim spec concept (Question-Validator + autoresearch's hypothesis structure).
