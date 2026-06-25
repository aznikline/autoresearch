#!/usr/bin/env python3
"""Trace the intellectual lineage of a paper or idea via the OpenAlex citation graph.

Usage:
    python genealogy.py --query "Learned Cardinalities Estimating Correlated Joins" [--depth 2] [--out lineage.json]

OpenAlex is free, no API key required (set a mailto User-Agent for the polite pool).

Honesty notes (the skill's discipline):
- Reports "earliest indexed occurrence", NOT "the originator". Citation graphs are
  incomplete/biased. A 1997 hit is not proof the idea was invented in 1997.
- Untraced branches (referenced works OpenAlex has no record of) are marked, not dropped.
- The graph is not exhaustive — shows what OpenAlex indexes, not "all prior work".
"""
from __future__ import annotations
import argparse, json, sys, urllib.parse, urllib.request
from pathlib import Path

USER_AGENT = "research-genealogy/0.1 mailto:research@genealogy.local"
BASE = "https://api.openalex.org"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def search_seed(query):
    url = f"{BASE}/works?search={urllib.parse.quote(query)}&per-page=1&select=id,title,publication_year,authorships,referenced_works,cited_by_count"
    d = _get(url)
    if not d.get("results"):
        return None
    w = d["results"][0]
    return {
        "id": w["id"], "title": w.get("title", ""), "year": w.get("publication_year"),
        "authors": [a["author"]["display_name"] for a in w.get("authorships", [])][:5],
        "cited_by": w.get("cited_by_count", 0),
        "referenced_works": w.get("referenced_works", []),
    }


def fetch_works(ids):
    if not ids:
        return []
    idstr = "|".join(i.replace("https://openalex.org/", "") for i in ids)
    url = f"{BASE}/works?filter=openalex_id:{idstr}&per-page=200&select=id,title,publication_year,authorships,referenced_works"
    d = _get(url)
    out = []
    for w in d.get("results", []):
        out.append({
            "id": w["id"], "title": w.get("title", "") or "(no title)",
            "year": w.get("publication_year"),
            "authors": [a["author"]["display_name"] for a in w.get("authorships", [])][:3],
            "referenced_works": w.get("referenced_works", []),
        })
    return out


def _node(w):
    return {"id": w["id"], "title": w["title"], "year": w["year"], "authors": w.get("authors", [])}


def trace(query, depth=1):
    seed = search_seed(query)
    if not seed:
        return {"error": f"no seed paper found for query: {query}"}
    tree = {"seed": _node(seed), "seed_cited_by": seed["cited_by"], "ancestors": [], "untraced": [], "depth": depth,
            "note": "Reports earliest indexed occurrence in OpenAlex, NOT the originator. Citation graphs incomplete/biased. Untraced branches marked."}
    if depth < 1:
        return tree
    refs = seed["referenced_works"][:30]
    expanded = fetch_works(refs)
    found = {w["id"] for w in expanded}
    tree["untraced"] = [r for r in refs if r not in found]
    if depth == 1:
        tree["ancestors"] = [_node(w) for w in expanded]
        return tree
    for w in expanded:
        w["sub_refs"] = fetch_works(w.get("referenced_works", [])[:10])
    tree["ancestors"] = [_node(w) for w in expanded]
    return tree


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--depth", type=int, default=1, choices=[1, 2])
    p.add_argument("--out", default=None)
    args = p.parse_args()
    tree = trace(args.query, depth=args.depth)
    if "error" in tree:
        print(tree["error"], file=sys.stderr); return 1
    print(f"=== Lineage for: {tree['seed']['title']} ({tree['seed']['year']}) ===")
    print(f"NOTE: {tree['note']}")
    print(f"\nSeed: {tree['seed']['title']} | {tree['seed']['year']} | cited_by={tree.get('seed_cited_by','?')}")
    print(f"\nAncestors ({len(tree['ancestors'])} indexed, {len(tree['untraced'])} untraced):")
    for a in sorted(tree["ancestors"], key=lambda x: x.get("year") or 0):
        print(f"  {a.get('year','?')} | {a['title'][:75]}")
    if tree["untraced"]:
        print(f"\nUntraced ({len(tree['untraced'])} referenced works OpenAlex has no record of):")
        for u in tree["untraced"][:5]:
            print(f"  {u}")
    if args.out:
        Path(args.out).write_text(json.dumps(tree, indent=2, ensure_ascii=False))
        print(f"\nFull tree -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
