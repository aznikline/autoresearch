---
name: academic-paper-skills
description: Reference backbone for academic paper structure — IMRaD + variants per field, venue families (NeurIPS/ICML/ACL/CVPR/Nature) with formatting/page-limit/reproducibility requirements, citation styles, abstract archetypes. Consulted BY Paper-Writer and Paper-Reading, never run standalone. Use when the user asks "what sections does a NeurIPS paper need" / "what's the page limit for PVLDB" / "how should I structure an empirical systems paper".
---

# Academic Paper Skills (Reference)

A **reference** skill, not an action skill. It encodes the structural conventions of academic papers so that Paper-Writer (writing) and Paper-Reading (reading) consult it for venue-correct structure. Never run standalone.

## Where the venue data lives

The authoritative venue registry is already implemented at:
`src/autoresearch/venues/<venue>/<year>/main.yaml`

13 venues verified as of 2026-06-19: vldb, neurips, icml, iclr, colm, kdd, emnlp, naacl, mlsys, eccv, cvpr, thewebconf, sigmod. Each `main.yaml` has: `display_name`, `status: verified`, `compatible_profiles`, `official_sources` (URL + sha256 + retrieved_at), `template` (identity + source_url + sha256), `policy` (anonymity, page_limit, supplement_allowed, checklist_required, ethics_required).

**When asked about a specific venue's rules, read its main.yaml directly** — do not paraphrase from memory. The yaml is the source of truth; venue rules change yearly.

## Structure by paper type (consult when writing or reading)

### Empirical / systems paper (PVLDB, VLDB Journal, TKDE, ICDE, SIGMOD, KDD, MLSys)
- Abstract → Introduction → Related Work → Method/System → Experiments → Results → Discussion → Limitations → Conclusion
- Experiments is the load-bearing section: datasets, baselines (tuned, matched hardware), metrics (primary + secondary), seeds, CIs, compute budget, reproducibility
- Limitations is now expected (reviewers downgrade missing limitations)
- Reproducibility checklist/artifact often required (PVLDB: artifact appendix; MLSys: code submission)

### ML methods paper (NeurIPS, ICML, ICLR)
- Abstract → Introduction → Related Work → Method → Experiments → Analysis → Limitations → Broader Impacts → Conclusion
- Broader Impacts often required (NeurIPS)
- Reproducibility checklist required (NeurIPS, ICLR)
- Anonymous submission (double-blind) — write in third person, no self-identifying URLs

### NLP paper (ACL, EMNLP, NAACL, COLM)
- Abstract → Introduction → Related Work → Method → Experiments → Analysis → Limitations → Conclusion
- Findings vs main track distinction (ACL/EMNLP)
- Limitations required (ACL rolling format since 2023)
- Citation: author-year (ACL style) or numeric

### CV paper (CVPR, ECCV, ICCV)
- Abstract → Introduction → Related Work → Method → Experiments → Conclusion
- Figures load-bearing (architecture diagrams, qualitative results)
- Double-blind
- Supplementary for additional experiments

### Nature/Science/Cell family
- Title → Abstract (structured, ~150-200 words) → Introduction → Results → Discussion → Methods (often after References, supplementary) → References
- NOT IMRaD-first — Results before Methods, narrative-driven
- "Nature" paragraph structure: context → gap → contribution → implication
- Severe length constraints

## Abstract archetypes (by contribution type)

- **New method**: context → gap → "we propose X" → key technical idea → main result (one number) → implication
- **Empirical study**: context → "we systematically study X" → setup (datasets/baselines) → headline finding → implication
- **System/library**: need → "we present X" → key design choices → performance number → availability
- **Dataset/benchmark**: gap → "we release X" → scale/coverage → baseline results → why it matters

## Citation styles

- Numeric (NeurIPS, ICML, ICLR, CVPR, PVLDB): `[1]` or `(Author, 2023)`
- Author-year (ACL, EMNLP, TKDE): `(Author, 2023)` — use natbib `\citep`/`\citet`
- Nature: superscript numbers
- BibTeX: prefer `@inproceedings` for venue papers, `@article` for journals; always include DOI/URL + pages when available

## How other skills use this

- **Paper-Reading**: contribution type (from this skill) shapes what the card's "contribution 类型" field should be; venue family tells the reader what structure to expect (e.g. Nature paper → look for Methods after References).
- **Paper-Writer**: consult the venue's main.yaml for page_limit/anonymity/checklist before drafting; pick the abstract archetype by contribution type; use the structure-by-type skeleton for section ordering.

## Maintenance

Venue rules drift. The autoresearch venue yaml files carry `retrieved_at` + sha256 for each official source. If a user asks about a venue whose main.yaml is older than the current CFP, flag it: "the verified snapshot is from <date>; confirm against the current CFP at <url>." Do not silently apply stale rules.
