from __future__ import annotations

import json
from pathlib import Path

from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification
from autoresearch.paper.export import export_bundle, to_latex
from autoresearch.paper.quality import QualityAssessment


def test_to_latex_converts_basic_markdown() -> None:
    latex = to_latex("# Title\n\n## Abstract\nText & metric_1 [@key2026x].\n")

    assert "\\title{Title}" in latex
    assert "\\section{Abstract}" in latex
    assert "\\&" in latex
    assert "metric\\_1" in latex
    assert "\\cite{key2026x}" in latex


def test_export_bundle_writes_verification_report(tmp_path: Path) -> None:
    export_bundle(
        stage_path=tmp_path,
        paper_markdown="# Title\n\n## Abstract\nMetric 1.0.\n",
        bibtex="@misc{x}\n",
        citation_verification=CitationVerification(True, (), (), ()),
        claim_verification=ClaimVerification(True, (1.0,), (1.0,), ()),
        quality_assessment=QualityAssessment(
                score=5.0,
                threshold=4.0,
                evidence_complete=True,
                submission_ready=True,
                profile_id="ml-systems-efficiency",
                depth="top_venue",
                checks=(),
                blocking_issues=(),
                strengths=("verified",),
        ),
    )

    report = json.loads((tmp_path / "verification_report.json").read_text())
    quality = json.loads((tmp_path / "quality_report.json").read_text())
    index = json.loads((tmp_path / "bundle_index.json").read_text())
    assert report["artifact_verification_ok"] is True
    assert report["submission_ready"] is True
    assert quality["submission_ready"] is True
    assert index["artifact_verification_ok"] is True
    assert index["submission_ready"] is True
    assert (tmp_path / "paper.tex").exists()
    assert (tmp_path / "references.bib").exists()
