---
name: research-genealogy
description: Trace the intellectual lineage of a paper or idea via the OpenAlex citation graph. Given a paper title or idea, produce a lineage tree (seed + its referenced works expanded with title/year/authors, recursively up to depth 2). Use when the user asks "where does this idea come from" / "what's the prior work for X" / "trace the lineage of this paper". Honest about citation-graph limits — reports "earliest indexed occurrence" not "the originator", marks untraced branches.
---

# Research Genealogy

Trace the **intellectual lineage** of a paper or idea via the OpenAlex citation graph — which prior works a paper builds on, and (recursively) what those built on. Genuinely differentiated: no existing skill does genealogical traversal.

## When to Use

- User gives a paper and asks "where does this come from" / "what's the prior work" / "trace its roots"
- User has an idea and asks "what's the lineage of this concept"
- User wants a reading queue of foundational works before a paper

## How to Run

```bash
python ~/.claude/skills/research-genealogy/references/genealogy.py --query "<paper title or idea>" [--depth 1|2] [--out lineage.json]
```

- `--depth 1`: the seed paper's direct references (ancestors), expanded with title/year.
- `--depth 2`: also each ancestor's references (one more hop). Slower, larger.
- `--out`: write the full tree as JSON for downstream use.

OpenAlex is free, no API key. The script sets a mailto User-Agent for the polite pool.

## Output

A readable summary (stdout) + optional JSON tree (—out):
- **Seed**: the matched paper (title, year, cited_by count)
- **Ancestors**: indexed referenced works, sorted by year, each with title/year/authors
- **Untraced**: referenced works OpenAlex has no record of (marked, not dropped)

## Discipline Rules (non-negotiable)

1. **Report "earliest indexed occurrence", NOT "the originator".** A 1997 hit means OpenAlex indexes a 1997 paper that the seed cited — it does NOT prove the idea was invented in 1997. Citation graphs are incomplete (OpenAlex backfills unevenly; older works have fewer indexed citations; some fields index better than others).
2. **Mark untraced branches.** If OpenAlex has no record of a referenced work, list it under untraced — do not silently drop it or guess what it was.
3. **State the limits explicitly.** The output's NOTE field says "earliest indexed occurrence, not the originator; citation graphs incomplete/biased". Keep that note in any summary you give the user.
4. **No "this is the first" claims.** Genealogy shows documented citation links, not absolute priority. If the user asks "who invented X", answer with "the earliest indexed citation in this lineage is <year, paper>, but priority claims require manual verification beyond this graph."
5. **Cap depth.** depth=2 is the practical max — deeper exhausts API budget and the tree becomes unreadable. For deeper exploration, do targeted hops on specific interesting ancestors, not a full tree.

## How other skills use this

- **Paper-Reading**: when reading a paper, can call genealogy to build a reading queue of its foundational ancestors.
- **Question-Validator**: when assessing novelty, genealogy shows what prior work exists — but the "no overlapping hit found as of date D" report must come from a search, not from genealogy alone (genealogy is seed-relative, not exhaustive search).
- **Source-Tracing**: genealogy gives the citation chain; Source-Tracing verifies a specific claim is actually supported by the cited original (the harder, full-text check).

## Limitations to state to the user

- OpenAlex coverage is uneven across fields and years.
- The seed match is by search — if the query is ambiguous, the wrong paper may be selected. Always show the seed title+year for the user to confirm.
- depth=2 can take 30+ seconds and ~30 API calls.
- Citation ≠ influence — a cited paper may be cited for critique, not adoption.
