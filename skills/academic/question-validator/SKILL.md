---
name: question-validator
description: Validate a research question or hypothesis — is it well-posed, falsifiable, scoped to a doable experiment, answerable within a budget, and how novel is it against existing literature. Returns a bounded-claim spec + honest novelty report ("no overlapping hit found as of date D", NEVER "this is novel") + suggested disconfirming experiment. Use when the user proposes a research question and wants to know if it's worth pursuing / well-formed / already answered.
---

# Question Validator

Take a research question or hypothesis and return a structured verdict: well-posed? falsifiable? scoped? budgetable? novel? Plus a bounded-claim spec and a suggested cheapest disconfirming experiment. Pure reasoning + retrieval, no execution wall.

## When to Use

- User proposes a research question and asks "is this a good question" / "is this novel" / "has someone done this"
- User has a hypothesis and wants to know if it's testable / already answered
- Before committing to a research project, to check it's well-formed

## How to Run

1. **Novelty search** (the grounding step — do NOT verdict from memory):
   ```bash
   python ~/.claude/skills/question-validator/references/novelty_search.py --question "<the question>" [--out novelty.json]
   ```
   Searches OpenAlex + arXiv, returns hits with title/year. The verdict is grounded in these hits, not in the model's world knowledge.

2. **Structural assessment** (your reasoning over the question + the search results):
   - well-posed? (one clear claim, not a vague topic)
   - falsifiable? (what evidence would disconfirm it)
   - scoped? (doable in one experiment, not "understand all of X")
   - budgetable? (estimable compute/data/time)
   - novelty? (grounded in the search — see discipline rule 1)

## Output: the bounded-claim spec

```
**Question**: <the question>
**Verdict**: well-posed / ill-posed (reason) | falsifiable / not (falsifier) | scoped / over-broad | budgetable / not
**Novelty report**: <"no overlapping hit found as of <date> in OpenAlex+arXiv" OR "<N> hits — NOT novel without manual review, top hits: ...">
**Bounded claim**: <the precise, falsifiable version of the claim — primary metric, direction, scope>
**Falsifier**: <the cheapest experiment that would disconfirm it>
**Budget**: <rough compute/data/time to run the falsifier>
**Suggested disconfirming experiment**: <the actual experiment design, minimal>
```

## Discipline Rules (non-negotiable)

1. **Novelty verdict is NEVER "this is novel".** It is always "no overlapping hit found as of date D in OpenAlex+arXiv" (when search returns nothing) OR "<N> hits — NOT novel without manual review" (when it does). Absence of evidence is not evidence of absence — the search is not exhaustive, OpenAlex/arXiv coverage is uneven, and the question's phrasing affects hits. Any "novelty" claim requires human review of the hits.
2. **The verdict is grounded in the search, not memory.** Run novelty_search.py and cite what it returned. Do not verdict "this has been done" from the model's world knowledge — that is the same fabrication risk as inventing a number.
3. **Falsifier must be the cheapest disconfirming experiment, not the most thorough.** A question worth pursuing has a cheap test that could kill it. If you can't name one, the question may be unfalsifiable.
4. **"Scoped" means one experiment, not a research program.** "Understand learned cardinality estimation" is not a question. "Does estimator X's Q-error degrade by >2x under distribution shift Y on dataset Z" is.
5. **Budget honesty.** If the falsifier needs a GPU cluster or novel hardware, say so — do not imply it's a laptop experiment.

## How other skills use this

- **Research-Genealogy**: genealogy shows the lineage (what a paper built on); Question-Validator shows if a NEW question overlaps existing work (exhaustive search, not seed-relative). Complementary: genealogy = backward from a paper, validator = outward from a question.
- **Academic-Research-Skills**: the bounded-claim spec from this skill is the input to a preregistration — the human approves the spec before any experiment runs.
- **Paper-Writer**: the bounded claim becomes the paper's central contribution statement.

## Limitations to state to the user

- OpenAlex + arXiv are not exhaustive (no Semantic Scholar when rate-limited, no paywalled venues, no workshop-only papers indexed unevenly).
- The search is keyword-based — a semantically identical question with different terms may miss. Refine the query if the first pass looks suspiciously empty.
- Novelty ≠ significance. A question can be novel but trivial, or already-asked-but-not-answered (which may still be worth pursuing).
