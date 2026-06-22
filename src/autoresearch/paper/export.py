from __future__ import annotations

import json
import re
from pathlib import Path

from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification
from autoresearch.paper.quality import QualityAssessment


def export_bundle(
    *,
    stage_path: Path,
    paper_markdown: str,
    bibtex: str,
    citation_verification: CitationVerification,
    claim_verification: ClaimVerification,
    quality_assessment: QualityAssessment,
) -> None:
    stage_path.mkdir(parents=True, exist_ok=True)
    (stage_path / "paper.tex").write_text(to_latex(paper_markdown), encoding="utf-8")
    (stage_path / "references.bib").write_text(bibtex, encoding="utf-8")
    report = {
        "artifact_verification_ok": citation_verification.ok and claim_verification.ok,
        "submission_ready": quality_assessment.submission_ready,
        "citations": citation_verification.to_dict(),
        "numeric_claims": claim_verification.to_dict(),
    }
    (stage_path / "verification_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (stage_path / "quality_report.json").write_text(
        json.dumps(quality_assessment.to_dict(), indent=2),
        encoding="utf-8",
    )
    (stage_path / "bundle_index.json").write_text(
        json.dumps(
            {
                "files": [
                    "paper.tex",
                    "references.bib",
                    "verification_report.json",
                    "quality_report.json",
                    "artifact_manifest.json",
                    "evidence_graph.json",
                    "governance_report.json",
                    "venue_export.json",
                    "paper_evidence.json",
                ],
                "artifact_verification_ok": report["artifact_verification_ok"],
                "submission_ready": quality_assessment.submission_ready,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def to_latex(markdown: str) -> str:
    body_lines = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            body_lines.append(f"\\title{{{_escape(line[2:])}}}")
            body_lines.append("\\maketitle")
        elif line.startswith("## "):
            body_lines.append(f"\\section{{{_escape(line[3:])}}}")
        elif line.startswith("- "):
            body_lines.append(f"\\noindent {_format_inline(line[2:])}\\\\")
        elif line.strip():
            body_lines.append(_format_inline(line))
        else:
            body_lines.append("")
    return (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        + "\n".join(body_lines)
        + "\n\\end{document}\n"
    )


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def _format_inline(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in re.finditer(r"\[@([A-Za-z0-9_:-]+)\]", text):
        parts.append(_escape(text[cursor:match.start()]))
        parts.append(f"\\cite{{{match.group(1)}}}")
        cursor = match.end()
    parts.append(_escape(text[cursor:]))
    return "".join(parts)
