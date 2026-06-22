from __future__ import annotations

from pathlib import Path

from autoresearch.evidence.graph import EvidenceGraph


def test_exportable_claim_requires_complete_content_addressed_source_path(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "metric.json"
    raw.write_text('{"accuracy": 0.9}', encoding="utf-8")
    graph = EvidenceGraph()
    artifact = graph.add_artifact(kind="raw_output", path=raw)
    metric = graph.add_record(kind="metric", payload={"name": "accuracy", "value": 0.9})
    claim = graph.add_record(kind="claim", payload={"text": "Accuracy is 0.9"})
    graph.add_edge(artifact.node_id, metric.node_id, "supports")
    graph.add_edge(metric.node_id, claim.node_id, "supports")

    result = graph.validate(exportable_node_ids=(claim.node_id,))

    assert result.ok, result.issues


def test_evidence_graph_rejects_orphan_cycle_and_tampered_artifact(tmp_path: Path) -> None:
    raw = tmp_path / "metric.json"
    raw.write_text("original", encoding="utf-8")
    graph = EvidenceGraph()
    artifact = graph.add_artifact(kind="raw_output", path=raw)
    claim = graph.add_record(kind="claim", payload={"text": "unsupported"})
    graph.add_edge(claim.node_id, claim.node_id, "supports")
    raw.write_text("tampered", encoding="utf-8")

    result = graph.validate(exportable_node_ids=(claim.node_id, artifact.node_id))

    codes = {issue.code for issue in result.issues}
    assert {"cycle", "orphan_export", "hash_mismatch"} <= codes


def test_evidence_graph_rejects_missing_and_ambiguous_edges() -> None:
    graph = EvidenceGraph()
    source_a = graph.add_record(kind="literature", payload={"id": "a"})
    source_b = graph.add_record(kind="literature", payload={"id": "b"})
    claim = graph.add_record(kind="claim", payload={"text": "fact"})
    graph.add_edge(source_a.node_id, claim.node_id, "supports")
    graph.add_edge(source_b.node_id, claim.node_id, "supports")
    graph.add_edge("missing", claim.node_id, "supports")

    result = graph.validate(exportable_node_ids=(claim.node_id,))

    codes = {issue.code for issue in result.issues}
    assert "missing_node" in codes
    assert "ambiguous_provenance" in codes


def test_typed_graph_covers_prose_numbers_citations_tables_and_figures(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.json"
    output.write_text('{"metric": 0.9}', encoding="utf-8")
    graph = EvidenceGraph()
    literature = graph.add_record(kind="literature", payload={"doi": "10.1/x"})
    raw = graph.add_artifact(kind="raw_output", path=output)
    citation = graph.add_record(kind="citation", payload={"key": "paper2026"})
    number = graph.add_record(kind="numeric_claim", payload={"value": 0.9})
    prose = graph.add_record(kind="prose_claim", payload={"text": "Improves quality"})
    table = graph.add_record(kind="table", payload={"id": "tab:main"})
    figure = graph.add_record(kind="figure", payload={"id": "fig:main"})
    graph.add_edge(literature.node_id, citation.node_id, "supports")
    graph.add_edge(raw.node_id, number.node_id, "supports")
    graph.add_edge(number.node_id, prose.node_id, "supports")
    graph.add_edge(raw.node_id, table.node_id, "renders")
    graph.add_edge(raw.node_id, figure.node_id, "renders")

    result = graph.validate(
        exportable_node_ids=tuple(
            node.node_id for node in (citation, number, prose, table, figure)
        )
    )

    assert result.ok, result.issues


def test_typed_graph_rejects_wrong_source_kind_unknown_relation_and_record_tamper(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.json"
    output.write_text("{}", encoding="utf-8")
    graph = EvidenceGraph()
    raw = graph.add_artifact(kind="raw_output", path=output)
    citation = graph.add_record(kind="citation", payload={"key": "fake"})
    graph.add_edge(raw.node_id, citation.node_id, "invented_relation")
    assert citation.payload is not None
    citation.payload["key"] = "tampered"

    result = graph.validate(exportable_node_ids=(citation.node_id,))

    codes = {issue.code for issue in result.issues}
    assert {"invalid_relation", "record_hash_mismatch", "source_kind_mismatch"} <= codes
