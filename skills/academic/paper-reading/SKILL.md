---
name: paper-reading
description: Read a real academic paper (arXiv PDF / local PDF / markdown) and produce a structured reading card a researcher would use. Use when the user gives a paper and wants to understand it, summarize it, critique it, or decide whether to read it fully. Outputs: one-sentence claim, contribution type, method summary, dataset/baselines/metrics with numbers QUOTED WITH PAGE ANCHORS, stated limitations, and a reviewer-style critique. Discipline: every number traced to a page in the full text (not the abstract); say "not stated in paper" rather than fabricate.
---

# Paper Reading

Produce a **reading card** a researcher would actually use to decide whether to read a paper fully, and to recall it later. The card is grounded in the paper's **full text**, never its abstract alone.

## When to Use

- User gives a paper (PDF path, arXiv ID/URL, or markdown) and wants it read/summarized/critiqued
- User asks "what does this paper actually claim?" / "is this paper worth reading?" / "summarize this"
- User wants a structured card for later recall or comparison across papers

## How to Read the Paper

1. **Get the full text with page markers.** Use `references/extract_pdf.py` on a PDF:
   ```bash
   python ~/.claude/skills/paper-reading/references/extract_pdf.py <pdf-path>
   ```
   This prints `=== 第 N 页 ===` then the page text. For arXiv, fetch the PDF first (`https://arxiv.org/pdf/<id>.pdf`). For markdown, read directly.
   - The script uses `pymupdf` (must be installed: `pip install pymupdf` or use a venv that has it).
   - If pymupdf is unavailable, fall back to the Read tool with `pages` parameter (requires poppler: `brew install poppler`). **Do NOT build the card from the abstract only** — that is the failure mode this skill exists to prevent.

2. **Read all pages.** Do not skim only intro + abstract. The numbers, baselines, and limitations live in Sections 3-5 (Experiments / Results / Discussion), which the abstract does not contain.

## The Reading Card (output format)

```
**论文**: <title>
**venue**: <venue + year + pages> (p.<first page>)
**一句话 claim**: <one sentence — what the paper actually claims, not what it aspires to>
**contribution 类型**: <new method / empirical study / system/library / dataset / theory / reproduction>
**method 摘要**: <3-5 sentences — the actual approach, not buzzwords>
**dataset / baselines / 主指标 + 报告数字(带页码引用)**:
- <number or fact> (p.<N>)
- <number or fact> (p.<N>)
- ...
**stated limitations**:
- <limitation> (p.<N>, or "论文未设 Limitations 节" if absent)
**reviewer 式 critique**:
- <unsupported / overclaimed / missing experiment / unclear metric> — with reasoning
- ...
```

## Discipline Rules (non-negotiable)

1. **Every number must carry a page anchor** from the full text: `(p.7)`, `(p.2)`. A number without a page anchor is a fabrication risk.
2. **Quote, don't paraphrase numbers.** If the paper says "94% coverage", write `94%`, not "high coverage".
3. **Say "not stated in paper" when something is missing.** Common gaps: number of seeds, confidence intervals, significance tests, metric definitions, compute budget, hardware. **Never** fill these with plausible-sounding defaults.
4. **Distinguish claim from aspiration.** "we present X" (claim) vs "X enables future Y" (aspiration, not a result).
5. **Contribution type must be honest.** A software library paper is "system/library", not "new method" — even if it ships algorithms.
6. **Critique is reviewer-style, grounded.** "The 15% improvement has no reported seeds or CIs (论文未说明)" is valid. "This paper is bad" is not.

## Pass Criterion (the canary)

This skill exists because a naive "paper reading" degrades to reading the abstract and splitting the first sentence into a "claim". The card is only valid if:
- At least one number is quoted with a real page anchor from the **full text** (not the abstract).
- At least one field reads "not stated in paper" / "论文未说明" (proving the card didn't fabricate gaps).

If you cannot meet these from the full text, **say so explicitly** rather than degrade to abstract-only.

## Optional: 2-N paper synthesis

If the user asks to compare papers, produce the per-paper cards above PLUS a synthesis table (rows = papers, columns = claim / method / dataset / primary metric / reported number / limitation). The table is grounded in the individual cards; no new numbers appear in the table that aren't in a card.

## Citation follow-up (optional)

If the user wants a reading queue, list 2-5 papers cited in this one that are worth reading next, each with a one-line reason grounded in where this paper used it (e.g. "Duan et al. 2016 — this paper's benchmark setup follows it, p.2").
