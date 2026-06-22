from __future__ import annotations

import hashlib
import json
from pathlib import Path

from autoresearch.audit.venues import audit_venue_materials


CONTRACT = """
schema_version: 1
venue_id: testconf
display_name: TestConf
year: 2026
track: main
status: verified
compatible_profiles: [foundation-models-llm]
official_sources:
  - url: https://example.test/rules
    retrieved_at: 2026-06-19
    sha256: {source_hash}
template:
  identity: testconf-2026-main
  source_url: https://example.test/template.zip
  sha256: {template_hash}
policy:
  anonymity: double_blind
  page_limit: 9
  supplement_allowed: true
  checklist_required: true
  checklist_delivery: paper
  ethics_required: true
  limitations_required: true
  artifact_policy: optional
  required_sections: []
valid_until: 2026-12-31
"""


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_verified(root: Path) -> tuple[Path, Path, Path]:
    source_root = root / "docs/audits/venue-sources/testconf/2026/main"
    template_root = root / "src/autoresearch/templates/testconf/2026"
    contract_path = root / "src/autoresearch/venues/testconf/2026/main.yaml"
    source_root.mkdir(parents=True)
    template_root.mkdir(parents=True)
    contract_path.parent.mkdir(parents=True)
    source = source_root / "rules.html"
    template = template_root / "template.zip"
    source.write_text("official rules", encoding="utf-8")
    template.write_bytes(b"exact template")
    contract_path.write_text(
        CONTRACT.format(source_hash=_hash(source), template_hash=_hash(template)),
        encoding="utf-8",
    )
    manifest = {
        "venue_id": "testconf",
        "year": 2026,
        "track": "main",
        "sources": [
            {
                "url": "https://example.test/rules",
                "path": "rules.html",
                "sha256": _hash(source),
            }
        ],
        "template": {
            "identity": "testconf-2026-main",
            "source_url": "https://example.test/template.zip",
            "path": "src/autoresearch/templates/testconf/2026/template.zip",
            "sha256": _hash(template),
        },
    }
    (source_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return contract_path, source, template


def test_verified_materials_with_matching_manifest_pass(tmp_path: Path) -> None:
    _write_verified(tmp_path)

    result = audit_venue_materials(tmp_path)

    assert result.source_ok, result.source_blockers
    assert result.template_ok, result.template_blockers


def test_draft_contract_blocks_both_source_and_template(tmp_path: Path) -> None:
    contract, _, _ = _write_verified(tmp_path)
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("status: verified", "status: draft"),
        encoding="utf-8",
    )

    result = audit_venue_materials(tmp_path)

    assert any("not verified" in item for item in result.source_blockers)
    assert any("not verified" in item for item in result.template_blockers)


def test_tampered_source_and_template_are_rejected(tmp_path: Path) -> None:
    _, source, template = _write_verified(tmp_path)
    source.write_text("tampered", encoding="utf-8")
    template.write_bytes(b"tampered")

    result = audit_venue_materials(tmp_path)

    assert any("source hash mismatch" in item for item in result.source_blockers)
    assert any("template hash mismatch" in item for item in result.template_blockers)


def test_template_manifest_cannot_escape_repository(tmp_path: Path) -> None:
    _write_verified(tmp_path)
    manifest_path = tmp_path / "docs/audits/venue-sources/testconf/2026/main/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["template"]["path"] = "../outside.zip"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = audit_venue_materials(tmp_path)

    assert any("template path" in item for item in result.template_blockers)
