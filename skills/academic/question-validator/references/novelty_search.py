#!/usr/bin/env python3
"""Search prior work for a research question, to support an HONEST novelty report.

Usage:
    python novelty_search.py --question "Do learned cardinality estimators degrade more under distribution shift" [--out novelty.json]

Searches OpenAlex (free, no key) + arXiv (free, no key) for prior work matching the
question. Returns hits with title/year/abstract-snippet. Prints a readable summary
and writes JSON if --out given.

DISCIPLINE: this script returns what it found. The "novelty verdict" is NEVER
"this is novel" — it is "no overlapping hit found as of <date> in OpenAlex+arXiv".
Absence of evidence is not evidence of absence.
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

UA = "question-validator/0.1 mailto:research@validator.local"


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def search_openalex(question, limit=10):
    url = (
        "https://api.openalex.org/works?search="
        + urllib.parse.quote(question)
        + f"&per-page={limit}&select=id,title,publication_year,abstract_inverted_index,cited_by_count"
    )
    d = _get(url)
    out = []
    for w in d.get("results", []):
        abs_idx = w.get("abstract_inverted_index") or {}
        if abs_idx:
            positions = sorted(
                (pos, word) for word, plist in abs_idx.items() for pos in plist
            )
            abstract = " ".join(w for _, w in positions)[:200]
        else:
            abstract = "(no abstract)"
        out.append(
            {
                "source": "openalex",
                "id": w["id"],
                "title": w.get("title", ""),
                "year": w.get("publication_year"),
                "cited_by": w.get("cited_by_count", 0),
                "abstract": abstract,
            }
        )
    return {"count": d["meta"]["count"], "hits": out}


def search_arxiv(question, limit=10):
    url = (
        "http://export.arxiv.org/api/query?search_query=all:"
        + urllib.parse.quote(question)
        + f"&max_results={limit}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        tree = ET.parse(r)
    root = tree.getroot()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        title = (e.find("a:title", ns).text or "").strip()
        published = (e.find("a:published", ns).text or "")[:4]
        summary = (e.find("a:summary", ns).text or "").strip()[:200]
        arxiv_id = (e.find("a:id", ns).text or "").split("/")[-1]
        out.append(
            {
                "source": "arxiv",
                "id": arxiv_id,
                "title": title,
                "year": published,
                "abstract": summary,
            }
        )
    return {"count": len(out), "hits": out}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--question", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()
    today = date.today().isoformat()
    print(f"=== Novelty search for: {args.question} ===")
    print(f"Search date: {today}")
    print("Sources: OpenAlex + arXiv\n")
    try:
        oa = search_openalex(args.question)
    except Exception as e:
        oa = {"count": 0, "hits": [], "error": str(e)}
    try:
        ax = search_arxiv(args.question)
    except Exception as e:
        ax = {"count": 0, "hits": [], "error": str(e)}

    oa_count = oa.get("count", 0)
    ax_count = ax.get("count", 0)

    print(f"OpenAlex: {oa_count} hits total, top {len(oa.get('hits', []))}:")
    for h in oa.get("hits", [])[:5]:
        print(f"  {h.get('year','?')} | {h['title'][:70]} | cited_by={h.get('cited_by',0)}")
    print(f"\narXiv: {ax_count} hits:")
    for h in ax.get("hits", [])[:5]:
        print(f"  {h.get('year','?')} | {h['title'][:70]}")

    if oa_count == 0 and ax_count == 0:
        verdict = "no overlapping hit found"
    else:
        verdict = f"{oa_count} OpenAlex + {ax_count} arXiv hits — NOT novel without manual review"
    print(f"\nVERDICT (honest): {verdict}")
    print("NOTE: absence of evidence is not evidence of absence. Manual review required for any novelty claim.")

    if args.out:
        payload = {
            "question": args.question,
            "date": today,
            "openalex": oa,
            "arxiv": ax,
            "verdict": verdict,
        }
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"\nFull -> {args.out}")


if __name__ == "__main__":
    raise SystemExit(main())
