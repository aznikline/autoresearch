---
name: autoresearch-ml-systems
description: Turn an empirical ML systems or efficient-training idea into an auditable paper candidate with claim-scoped literature review, fair fixed-budget experiments, statistical and compute reporting, evidence-linked writing, and submission-readiness gates. Use for idea-to-paper runs, research planning, experiment design or analysis, and paper verification involving optimizers, training or inference efficiency, architectures under resource constraints, pruning, quantization, distillation, throughput, latency, memory, or agentic ML research.
---

# Autoresearch ML Systems

## Operating Rule

Treat pipeline completion as artifact production, not scientific success. Keep
`submission_ready` false until every configured evidence gate passes from
structured artifacts.

## Workflow

1. Convert the idea into a bounded claim, contribution type, target venue
   family, resource envelope, and falsifiable success criterion.
2. Search for the exact claim and nearest mechanisms. Record query, source,
   date, inclusion decision, and unresolved novelty risk.
3. Form competing hypotheses. State expected effect, disconfirming result,
   confounds, and the cheapest discriminating experiment.
4. Freeze the evaluator, data splits, primary metric, resource budget, stopping
   rule, seeds, baselines, and exclusions before confirmatory execution.
5. Run immutable specs. Preserve failed, null, and negative trials in the
   append-only ledger. Never select results by prose quality or reviewer score.
6. Analyze effect magnitude, uncertainty, practical significance, quality versus
   efficiency tradeoffs, and failure modes. Resolve every hypothesis.
7. Draft only from literature and experiment registries. Map every citation and
   numeric claim to provenance.
8. Verify the selected depth rubric. Report missing evidence as blockers instead
   of filling gaps with generated text.

## Non-Negotiable Checks

- Keep the evaluation harness immutable during a run.
- Compare baselines under protocol and resource parity.
- Separate exploratory tuning from confirmatory evaluation.
- Report per-run and total compute, including failed or preliminary runs.
- State the variability source and interval construction method.
- Reject SOTA or novelty language without protocol-matched evidence.
- Preserve negative results and label inconclusive evidence honestly.
- Require human approval for high-cost execution, ethical risk, and final
  submission claims.

## Stage References

The project harness loads only references declared for the active stage:

- Read `references/methodology.md` for hypothesis, experiment, analysis, and
  paper stages.
- Read `references/readiness-rubric.md` for experiment design and final
  verification.

Use the machine-readable domain profile as the configured threshold source.
Treat numeric thresholds as project defaults, not conference rules.
