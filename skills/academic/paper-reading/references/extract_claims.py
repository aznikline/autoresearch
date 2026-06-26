#!/usr/bin/env python3
"""Extract structured numeric claims from a PDF, with page anchors.

Uses qwen3.7-max (DashScope) to parse each page into structured claims
(number + context + claim_type + page). Smart layer over extract_pdf.py.

Usage: python extract_claims.py <pdf> [--pages 1-5] [--out claims.json]
Requires: pymupdf + DASHSCOPE_API_KEY (degrades to text-only without key).
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from urllib.request import Request, urlopen

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.7-max"


def extract_text(pdf_path, pages):
    import fitz
    doc = fitz.open(pdf_path)
    n = doc.page_count
    if pages:
        start, end = max(0, pages[0]-1), min(n, pages[1])
    else:
        start, end = 0, n
    result = [(i+1, doc[i].get_text()) for i in range(start, end)]
    doc.close()
    return result


def llm_extract_claims(page_num, text, api_key):
    if not text.strip(): return []
    prompt = (
        f"From page {page_num} of an academic paper, extract ALL numeric claims "
        f"(percentages, counts, metrics). Return JSON array of objects with keys: "
        f"number (string), context (one sentence), claim_type "
        f"(coverage/performance/count/dataset/budget/other). No numbers = []."
        f"\n\nPage {page_num}:\n{text[:2500]}"
    )
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000}).encode()
    req = Request(f"{DASHSCOPE_BASE}/chat/completions", data=body,
                  headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        content = d["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
            content = content.rsplit("```", 1)[0] if "```" in content else content
        parsed = json.loads(content)
        if isinstance(parsed, list):
            for c in parsed: c["page"] = page_num
            return parsed
    except Exception: pass
    return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdf")
    p.add_argument("--pages", default=None)
    p.add_argument("--out", default=None)
    args = p.parse_args()
    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.is_file(): print(f"error: {pdf_path}", file=sys.stderr); return 1
    pages = None
    if args.pages:
        if "-" in args.pages:
            lo, hi = args.pages.split("-", 1); pages = (int(lo), int(hi))
        else: pages = (int(args.pages), int(args.pages))
    page_texts = extract_text(str(pdf_path), pages)
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    all_claims = []
    for page_num, text in page_texts:
        print(f"=== 第 {page_num} 页 ===", file=sys.stderr)
        if api_key:
            claims = llm_extract_claims(page_num, text, api_key)
            for c in claims:
                print(f"  p.{c['page']} | {c['number']} | {c['claim_type']} | {c['context'][:80]}")
            all_claims.extend(claims)
        else: print(text[:500])
    if args.out:
        Path(args.out).write_text(json.dumps(all_claims, indent=2, ensure_ascii=False))
        print(f"\n{len(all_claims)} claims -> {args.out}", file=sys.stderr)
    print(f"\n=== {len(all_claims)} structured claims ===", file=sys.stderr)
    return 0


if __name__ == "__main__": raise SystemExit(main())
