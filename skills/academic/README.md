# academic/ skills

Five Claude Code academic-research skills, bundled with autoresearch. They cover gaps that open-source suites (PaperSpine etc.) don't: single-paper reading with page-anchored discipline, academic citation genealogy, honest novelty reporting, venue-rules lookup, and preregistration.

## Skills

| skill | what it does | runs standalone? |
|-------|--------------|------------------|
| `paper-reading` | Read a real PDF → structured reading card with page-anchored numbers + honest "not stated" fields. | yes (needs `pymupdf`) |
| `research-genealogy` | Trace a paper's lineage via OpenAlex citation graph. "earliest indexed occurrence" not "originator". | yes (OpenAlex API) |
| `question-validator` | Validate a research question (well-posed/falsifiable/scoped/novel). Novelty verdict is NEVER "this is novel". | yes (OpenAlex + arXiv) |
| `academic-paper-skills` | Venue structure reference (IMRaD variants, page limits, citation styles). | richer in-repo (reads `src/autoresearch/venues/`) |
| `academic-research-skills` | Methodology reference (field-aware) + preregistration helper. | richer in-repo (reads `program.md` + domain methodology) |

## In-repo advantages

Bundled here, `academic-paper-skills` reads the 13 verified venue yamls at `src/autoresearch/venues/<venue>/<year>/main.yaml` (relative paths, repo-rooted). `academic-research-skills` references `program.md` (repo root) + the 5 domain methodology files at `../autoresearch-*/references/methodology.md`. The skills are self-contained markdown but are *richest* when this repo is present.

## Install (to ~/.claude/skills/)

```bash
# from autoresearch repo root
cp -r skills/academic/{paper-reading,research-genealogy,question-validator} ~/.claude/skills/
cp -r skills/academic/{academic-paper-skills,academic-research-skills} ~/.claude/skills/
```

Then install `pymupdf` for paper-reading: `pip install pymupdf` (or `uv add pymupdf` — already in this repo's venv).

## Relation to the 5 domain skills (../autoresearch-*)

The domain skills (`../autoresearch-data-management-mining/` etc.) are *experiment-methodology* skills used **inside** autoresearch's 12-stage pipeline. The `academic/` skills here are *general academic-workflow* skills used **outside** the pipeline — reading papers, tracing lineage, validating questions, looking up venue rules, writing preregistrations. `academic-research-skills` *extracts* the domain methodology from the 5 domain skills for reuse outside a full pipeline run.

## Discipline (the differentiator)

Every skill enforces evidence-binding discipline:
- page-anchored numbers (not abstract-only)
- "not stated in paper" is a valid field (no fabrication)
- "earliest indexed occurrence" not "originator" (genealogy)
- novelty is "no overlapping hit found as of date D" not "this is novel"
- no novelty-from-model-judgment (from `program.md` charter)

This discipline is why these skills exist as separate from open-source suites that focus on prose fluency.

## Also published

These 5 skills are also published as a standalone public repo (for use without autoresearch):
https://github.com/aznikline/academic-skills — there, the 2 autoresearch-dependent skills degrade gracefully (venue rules fall back to generic reference, methodology files are self-contained copies).
