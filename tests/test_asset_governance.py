from __future__ import annotations

from autoresearch.governance.assets import AssetRecord, validate_asset


def test_governed_public_asset_passes() -> None:
    result = validate_asset(
        AssetRecord(
            asset_id="dataset-1",
            kind="dataset",
            source_url="https://example.test/dataset",
            sha256="a" * 64,
            license_id="Apache-2.0",
            privacy_status="public-non-sensitive",
            split_hash="b" * 64,
        )
    )

    assert result.ok


def test_unknown_rights_privacy_and_hash_fail_closed() -> None:
    result = validate_asset(
        AssetRecord(
            asset_id="corpus-1",
            kind="corpus",
            source_url="",
            sha256="unknown",
            license_id="unknown",
            privacy_status="unknown",
            split_hash="",
        )
    )

    assert not result.ok
    assert {issue.code for issue in result.issues} == {
        "missing_source",
        "invalid_hash",
        "unknown_license",
        "unknown_privacy",
        "missing_split_hash",
    }


def test_sensitive_asset_requires_approval_and_consent_basis() -> None:
    result = validate_asset(
        AssetRecord(
            asset_id="human-1",
            kind="human_annotations",
            source_url="https://example.test/private",
            sha256="c" * 64,
            license_id="consented-research-use",
            privacy_status="sensitive-approved",
            split_hash="d" * 64,
            governance_approval="",
            consent_basis="",
        )
    )

    assert {issue.code for issue in result.issues} == {
        "missing_governance_approval",
        "missing_consent_basis",
    }
