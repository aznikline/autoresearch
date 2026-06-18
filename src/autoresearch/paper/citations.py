from __future__ import annotations

import re
from dataclasses import dataclass

from autoresearch.literature.models import PaperRecord, ScreenedPaper


@dataclass(frozen=True)
class CitationVerification:
    ok: bool
    cited_keys: tuple[str, ...]
    supported_keys: tuple[str, ...]
    unsupported_keys: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "cited_keys": list(self.cited_keys),
            "supported_keys": list(self.supported_keys),
            "unsupported_keys": list(self.unsupported_keys),
        }


def build_bibtex(screened: list[ScreenedPaper]) -> str:
    papers = [item.paper for item in screened if item.decision == "keep"]
    return "\n\n".join(_paper_to_bibtex(paper) for paper in papers) + ("\n" if papers else "")


def verify_citations(markdown: str, screened: list[ScreenedPaper]) -> CitationVerification:
    cited = tuple(sorted(set(re.findall(r"\[@([A-Za-z0-9_:-]+)\]", markdown))))
    supported = tuple(sorted(item.paper.citation_key for item in screened if item.decision == "keep"))
    unsupported = tuple(key for key in cited if key not in supported)
    return CitationVerification(
        ok=not unsupported,
        cited_keys=cited,
        supported_keys=supported,
        unsupported_keys=unsupported,
    )


def _paper_to_bibtex(paper: PaperRecord) -> str:
    authors = " and ".join(paper.authors) or "Unknown"
    year = str(paper.year or "n.d.")
    fields = {
        "title": paper.title,
        "author": authors,
        "year": year,
        "url": paper.url,
    }
    if paper.venue:
        fields["booktitle"] = paper.venue
    body = "\n".join(f"  {key} = {{{value}}}," for key, value in fields.items())
    return f"@misc{{{paper.citation_key},\n{body}\n}}"
