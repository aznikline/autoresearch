from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


SOURCE_KINDS = frozenset({"raw_output", "literature", "dataset", "model", "corpus"})
ALLOWED_RELATIONS = frozenset({"supports", "produces", "renders", "cites", "derived_from"})
EXPORT_SOURCE_KINDS = {
    "citation": frozenset({"literature"}),
    "numeric_claim": frozenset({"raw_output", "dataset", "corpus"}),
    "table": frozenset({"raw_output", "dataset", "corpus"}),
    "figure": frozenset({"raw_output", "dataset", "corpus"}),
    "prose_claim": SOURCE_KINDS,
    "claim": SOURCE_KINDS,
}


@dataclass(frozen=True)
class EvidenceNode:
    node_id: str
    kind: str
    sha256: str
    path: str = ""
    payload: dict[str, object] | None = None


@dataclass(frozen=True)
class EvidenceEdge:
    source_id: str
    target_id: str
    relation: str


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    node_id: str
    message: str


@dataclass(frozen=True)
class EvidenceValidation:
    ok: bool
    issues: tuple[EvidenceIssue, ...]


class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, EvidenceNode] = {}
        self.edges: list[EvidenceEdge] = []

    def add_artifact(self, *, kind: str, path: str | Path) -> EvidenceNode:
        artifact_path = Path(path).resolve()
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        node = EvidenceNode(
            node_id=f"{kind}:{digest}",
            kind=kind,
            sha256=digest,
            path=artifact_path.as_posix(),
        )
        self.nodes[node.node_id] = node
        return node

    def add_record(self, *, kind: str, payload: dict[str, object]) -> EvidenceNode:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        node = EvidenceNode(
            node_id=f"{kind}:{digest}",
            kind=kind,
            sha256=digest,
            payload=payload,
        )
        self.nodes[node.node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relation: str) -> None:
        self.edges.append(EvidenceEdge(source_id, target_id, relation))

    def validate(self, *, exportable_node_ids: tuple[str, ...]) -> EvidenceValidation:
        issues: list[EvidenceIssue] = []
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        incoming: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            if edge.relation not in ALLOWED_RELATIONS:
                issues.append(
                    EvidenceIssue(
                        "invalid_relation",
                        edge.target_id,
                        f"unknown evidence relation: {edge.relation}",
                    )
                )
            if edge.source_id not in self.nodes:
                issues.append(
                    EvidenceIssue("missing_node", edge.source_id, "edge source is missing")
                )
                continue
            if edge.target_id not in self.nodes:
                issues.append(
                    EvidenceIssue("missing_node", edge.target_id, "edge target is missing")
                )
                continue
            adjacency[edge.source_id].append(edge.target_id)
            incoming[edge.target_id].append(edge.source_id)

        for node in self.nodes.values():
            if node.path:
                path = Path(node.path)
                actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
                if actual != node.sha256:
                    issues.append(
                        EvidenceIssue(
                            "hash_mismatch",
                            node.node_id,
                            "artifact content no longer matches its registered hash",
                        )
                    )
            elif node.payload is not None:
                encoded = json.dumps(
                    node.payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                if hashlib.sha256(encoded).hexdigest() != node.sha256:
                    issues.append(
                        EvidenceIssue(
                            "record_hash_mismatch",
                            node.node_id,
                            "record payload no longer matches its registered hash",
                        )
                    )

        for node_id in _cyclic_nodes(adjacency):
            issues.append(EvidenceIssue("cycle", node_id, "evidence graph contains a cycle"))

        for node_id in exportable_node_ids:
            if node_id not in self.nodes:
                issues.append(EvidenceIssue("missing_node", node_id, "export node is missing"))
                continue
            direct_sources = incoming[node_id]
            if len(direct_sources) > 1 and all(
                self.nodes[source_id].kind in SOURCE_KINDS for source_id in direct_sources
            ):
                issues.append(
                    EvidenceIssue(
                        "ambiguous_provenance",
                        node_id,
                        "multiple raw sources require an explicit aggregation record",
                    )
                )
            if not _reaches_source(node_id, incoming, self.nodes, set()):
                issues.append(
                    EvidenceIssue(
                        "orphan_export",
                        node_id,
                        "exportable node has no provenance path to a source artifact",
                    )
                )
            required_source_kinds = EXPORT_SOURCE_KINDS.get(self.nodes[node_id].kind)
            if required_source_kinds is not None:
                reachable = _reachable_source_kinds(
                    node_id,
                    incoming,
                    self.nodes,
                    set(),
                )
                if not reachable & required_source_kinds:
                    issues.append(
                        EvidenceIssue(
                            "source_kind_mismatch",
                            node_id,
                            "exportable node has no valid typed source provenance",
                        )
                    )
        return EvidenceValidation(not issues, tuple(issues))


def _reaches_source(
    node_id: str,
    incoming: dict[str, list[str]],
    nodes: dict[str, EvidenceNode],
    visited: set[str],
) -> bool:
    if node_id in visited:
        return False
    if nodes[node_id].kind in SOURCE_KINDS:
        return True
    visited.add(node_id)
    return any(
        _reaches_source(source_id, incoming, nodes, visited.copy())
        for source_id in incoming[node_id]
    )


def _cyclic_nodes(adjacency: dict[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cyclic: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            cyclic.add(node_id)
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for target_id in adjacency[node_id]:
            visit(target_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id)
    return cyclic


def _reachable_source_kinds(
    node_id: str,
    incoming: dict[str, list[str]],
    nodes: dict[str, EvidenceNode],
    visited: set[str],
) -> set[str]:
    if node_id in visited:
        return set()
    node = nodes[node_id]
    if node.kind in SOURCE_KINDS:
        return {node.kind}
    visited.add(node_id)
    kinds: set[str] = set()
    for source_id in incoming[node_id]:
        kinds.update(
            _reachable_source_kinds(source_id, incoming, nodes, visited.copy())
        )
    return kinds
