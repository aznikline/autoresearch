from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class PaperEvidenceVerification:
    ok: bool
    issues: tuple[str, ...]


def paper_blocks(markdown: str) -> tuple[str, ...]:
    blocks: list[str] = []
    in_comment = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if "<!--" in line:
            in_comment = True
        if not in_comment and line and not line.startswith("#"):
            blocks.append(line)
        if "-->" in line:
            in_comment = False
    return tuple(blocks)


def build_block_registry(
    markdown: str,
    *,
    node_ids: tuple[str, ...],
) -> dict[str, object]:
    blocks = paper_blocks(markdown)
    if len(blocks) != len(node_ids):
        raise ValueError("one evidence node is required for every paper block")
    return {
        "blocks": [
            {
                "index": index,
                "sha256": hashlib.sha256(block.encode()).hexdigest(),
                "node_id": node_id,
            }
            for index, (block, node_id) in enumerate(zip(blocks, node_ids))
        ]
    }


def verify_block_registry(
    markdown: str,
    registry: dict[str, object],
) -> PaperEvidenceVerification:
    issues: list[str] = []
    blocks = paper_blocks(markdown)
    records = registry.get("blocks", ())
    if not isinstance(records, list):
        return PaperEvidenceVerification(False, ("paper block registry is invalid",))
    if len(blocks) != len(records):
        issues.append("paper block count mismatch")
    for index, (block, record) in enumerate(zip(blocks, records)):
        if not isinstance(record, dict):
            issues.append(f"paper block record is invalid: {index}")
            continue
        actual = hashlib.sha256(block.encode()).hexdigest()
        if record.get("sha256") != actual:
            issues.append(f"paper block hash mismatch: {index}")
        if not str(record.get("node_id", "")).strip():
            issues.append(f"paper block has no evidence node: {index}")
    return PaperEvidenceVerification(not issues, tuple(issues))
