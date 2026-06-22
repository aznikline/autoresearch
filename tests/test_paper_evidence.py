from __future__ import annotations

from autoresearch.paper.evidence import (
    build_block_registry,
    verify_block_registry,
)


def test_block_registry_covers_every_non_heading_paper_line() -> None:
    paper = """# Title

## Results
The measured score is 0.9.
- Failure cases remain.
"""
    registry = build_block_registry(
        paper,
        node_ids=("numeric:1", "prose:2"),
    )

    result = verify_block_registry(paper, registry)

    assert result.ok
    assert len(registry["blocks"]) == 2


def test_block_registry_rejects_added_removed_or_reordered_prose() -> None:
    paper = "# Title\n\n## Results\nSupported result.\nKnown limitation.\n"
    registry = build_block_registry(paper, node_ids=("p1", "p2"))

    added = verify_block_registry(paper + "Fabricated contribution.\n", registry)
    reordered = verify_block_registry(
        "# Title\n\n## Results\nKnown limitation.\nSupported result.\n",
        registry,
    )

    assert not added.ok
    assert "paper block count mismatch" in added.issues
    assert not reordered.ok
    assert any("paper block hash mismatch" in issue for issue in reordered.issues)


def test_block_registry_rejects_missing_node_link() -> None:
    paper = "# Title\n\nUnlinked claim.\n"
    registry = build_block_registry(paper, node_ids=("",))

    result = verify_block_registry(paper, registry)

    assert not result.ok
    assert "paper block has no evidence node: 0" in result.issues
