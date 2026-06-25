#!/usr/bin/env python3
"""Extract full text from a PDF with page markers, for the paper-reading skill.

Usage:
    python extract_pdf.py <pdf-path> [--pages 1-5]

Prints `=== 第 N 页 ===` then the page text, for every page (or the given range).
The page markers are load-bearing: the reading card's discipline rules require
every quoted number to carry a page anchor, and that anchor must come from the
full text, not the abstract.

Requires pymupdf (`pip install pymupdf`). Falls back to a clear error if absent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PDF text with page markers.")
    parser.add_argument("pdf", help="Path to the PDF file.")
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range like '1-5' or '3'. Defaults to all pages.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.is_file():
        print(f"error: file not found: {pdf_path}", file=sys.stderr)
        return 1

    try:
        import fitz  # pymupdf
    except ImportError:
        print(
            "error: pymupdf not installed. Install with `pip install pymupdf` "
            "or use a venv that has it.",
            file=sys.stderr,
        )
        return 2

    doc = fitz.open(str(pdf_path))
    n = doc.page_count

    if args.pages:
        if "-" in args.pages:
            lo, hi = args.pages.split("-", 1)
            start, end = int(lo) - 1, int(hi)
        else:
            start = int(args.pages) - 1
            end = start + 1
        start = max(0, start)
        end = min(n, end)
    else:
        start, end = 0, n

    for i in range(start, end):
        text = doc[i].get_text()
        print(f"=== 第 {i + 1} 页 ===")
        print(text)
        print()

    doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
