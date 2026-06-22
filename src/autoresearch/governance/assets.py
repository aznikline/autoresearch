from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    kind: str
    source_url: str
    sha256: str
    license_id: str
    privacy_status: str
    split_hash: str = ""
    governance_approval: str = ""
    consent_basis: str = ""
    local_path: str = ""


@dataclass(frozen=True)
class GovernanceIssue:
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class GovernanceValidation:
    ok: bool
    issues: tuple[GovernanceIssue, ...]


def validate_asset(asset: AssetRecord) -> GovernanceValidation:
    issues: list[GovernanceIssue] = []
    if not asset.source_url.startswith("https://"):
        issues.append(GovernanceIssue("missing_source", "source_url", "HTTPS source is required"))
    if not re.fullmatch(r"[0-9a-f]{64}", asset.sha256):
        issues.append(GovernanceIssue("invalid_hash", "sha256", "valid SHA-256 is required"))
    if not asset.license_id or asset.license_id.lower() == "unknown":
        issues.append(GovernanceIssue("unknown_license", "license_id", "rights must be resolved"))
    if asset.privacy_status not in {
        "public-non-sensitive",
        "sensitive-approved",
        "synthetic",
    }:
        issues.append(GovernanceIssue("unknown_privacy", "privacy_status", "privacy must be resolved"))
    if asset.kind in {"dataset", "corpus", "human_annotations"} and not re.fullmatch(
        r"[0-9a-f]{64}", asset.split_hash
    ):
        issues.append(
            GovernanceIssue("missing_split_hash", "split_hash", "immutable split hash is required")
        )
    if asset.privacy_status == "sensitive-approved":
        if not asset.governance_approval:
            issues.append(
                GovernanceIssue(
                    "missing_governance_approval",
                    "governance_approval",
                    "sensitive assets require approval evidence",
                )
            )
        if not asset.consent_basis:
            issues.append(
                GovernanceIssue(
                    "missing_consent_basis",
                    "consent_basis",
                    "sensitive assets require a consent or lawful-use basis",
                )
            )
    return GovernanceValidation(not issues, tuple(issues))
