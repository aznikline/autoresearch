from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.governance.registry import AssetRegistry, AssetRegistryError


VALID = """
schema_version: 1
assets:
  - asset_id: dataset-1
    kind: dataset
    source_url: https://example.test/dataset
    sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    license_id: Apache-2.0
    privacy_status: public-non-sensitive
    split_hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    governance_approval: ""
    consent_basis: ""
"""


def test_asset_registry_loads_only_governed_assets(tmp_path: Path) -> None:
    path = tmp_path / "assets.yaml"
    path.write_text(VALID, encoding="utf-8")

    registry = AssetRegistry.load(path)

    assert registry.ok
    assert registry.assets[0].asset_id == "dataset-1"


def test_asset_registry_rejects_duplicate_ids_and_unknown_fields(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(VALID + VALID.split("assets:\n", 1)[1], encoding="utf-8")
    with pytest.raises(AssetRegistryError, match="duplicate asset_id"):
        AssetRegistry.load(duplicate)

    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(VALID.replace("    consent_basis: \"\"", "    consent_basis: \"\"\n    approved: true"))
    with pytest.raises(AssetRegistryError, match="unknown fields.*approved"):
        AssetRegistry.load(unknown)


def test_asset_registry_keeps_invalid_governance_as_blocker(tmp_path: Path) -> None:
    path = tmp_path / "assets.yaml"
    path.write_text(VALID.replace("Apache-2.0", "unknown"), encoding="utf-8")

    registry = AssetRegistry.load(path)

    assert not registry.ok
    assert registry.validations[0].issues[0].code == "unknown_license"


def test_asset_registry_verifies_bound_local_file(tmp_path: Path) -> None:
    local = tmp_path / "dataset.csv"
    local.write_text("x\n1\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(local.read_bytes()).hexdigest()
    path = tmp_path / "assets.yaml"
    path.write_text(
        VALID.replace("a" * 64, digest).replace(
            '    consent_basis: ""',
            '    consent_basis: ""\n    local_path: dataset.csv',
        ),
        encoding="utf-8",
    )

    registry = AssetRegistry.load(path)

    assert registry.ok
    assert registry.locally_verified
    assert registry.to_report(require_local=True)["ok"] is True


def test_asset_registry_blocks_local_hash_mismatch_and_requires_binding(tmp_path: Path) -> None:
    local = tmp_path / "dataset.csv"
    local.write_text("tampered", encoding="utf-8")
    path = tmp_path / "assets.yaml"
    path.write_text(
        VALID.replace(
            '    consent_basis: ""',
            '    consent_basis: ""\n    local_path: dataset.csv',
        ),
        encoding="utf-8",
    )

    registry = AssetRegistry.load(path)

    assert not registry.ok
    assert registry.validations[0].issues[-1].code == "local_hash_mismatch"
    unbound = tmp_path / "unbound.yaml"
    unbound.write_text(VALID, encoding="utf-8")
    report = AssetRegistry.load(unbound).to_report(require_local=True)
    assert report["ok"] is False
    assert report["issues"][-1]["code"] == "local_verification_required"
