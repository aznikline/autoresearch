from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import yaml

from autoresearch.governance.assets import (
    AssetRecord,
    GovernanceIssue,
    GovernanceValidation,
    validate_asset,
)


class AssetRegistryError(ValueError):
    pass


_ROOT_FIELDS = {"schema_version", "assets"}
_ASSET_FIELDS = set(AssetRecord.__dataclass_fields__)
_OPTIONAL_ASSET_FIELDS = {"split_hash", "governance_approval", "consent_basis", "local_path"}


@dataclass(frozen=True)
class AssetRegistry:
    assets: tuple[AssetRecord, ...]
    validations: tuple[GovernanceValidation, ...]
    source_path: Path

    @property
    def ok(self) -> bool:
        return bool(self.assets) and all(item.ok for item in self.validations)

    @property
    def locally_verified(self) -> bool:
        return bool(self.assets) and all(
            asset.local_path
            and not any(issue.code.startswith("local_") for issue in validation.issues)
            for asset, validation in zip(self.assets, self.validations)
        )

    @classmethod
    def load(cls, path: str | Path) -> "AssetRegistry":
        source_path = Path(path)
        try:
            raw = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError as exc:
            raise AssetRegistryError(f"asset registry not found: {source_path}") from exc
        except yaml.YAMLError as exc:
            raise AssetRegistryError(f"asset registry is not valid YAML: {source_path}") from exc
        if not isinstance(raw, dict):
            raise AssetRegistryError("asset registry must be a mapping")
        unknown_root = sorted(set(raw) - _ROOT_FIELDS)
        if unknown_root:
            raise AssetRegistryError(
                "asset registry unknown fields: " + ", ".join(unknown_root)
            )
        if raw.get("schema_version") != 1:
            raise AssetRegistryError("asset registry schema_version must be 1")
        items = raw.get("assets")
        if not isinstance(items, list) or not items:
            raise AssetRegistryError("asset registry assets must be a non-empty list")
        assets: list[AssetRecord] = []
        seen: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AssetRegistryError(f"assets[{index}] must be a mapping")
            unknown = sorted(set(item) - _ASSET_FIELDS)
            if unknown:
                raise AssetRegistryError(
                    f"assets[{index}] unknown fields: {', '.join(unknown)}"
                )
            missing = sorted(_ASSET_FIELDS - _OPTIONAL_ASSET_FIELDS - set(item))
            if missing:
                raise AssetRegistryError(
                    f"assets[{index}] missing fields: {', '.join(missing)}"
                )
            asset = AssetRecord(
                **{key: str(item.get(key, "")) for key in _ASSET_FIELDS}
            )
            if asset.asset_id in seen:
                raise AssetRegistryError(f"duplicate asset_id: {asset.asset_id}")
            seen.add(asset.asset_id)
            assets.append(asset)
        validations = tuple(
            _validate_registered_asset(asset, source_path=source_path)
            for asset in assets
        )
        return cls(tuple(assets), validations, source_path.resolve())

    def to_report(self, *, require_local: bool = False) -> dict[str, object]:
        local_requirement_met = self.locally_verified or not require_local
        return {
            "ok": self.ok and local_requirement_met,
            "source_path": self.source_path.as_posix(),
            "assets": [asset.asset_id for asset in self.assets],
            "locally_verified": self.locally_verified,
            "records": [
                {
                    field: getattr(asset, field)
                    for field in sorted(_ASSET_FIELDS)
                }
                for asset in self.assets
            ],
            "issues": [
                {
                    "asset_id": asset.asset_id,
                    "code": issue.code,
                    "field": issue.field,
                    "message": issue.message,
                }
                for asset, validation in zip(self.assets, self.validations)
                for issue in validation.issues
            ] + (
                [
                    {
                        "code": "local_verification_required",
                        "message": "Real evidence requires every asset to bind to a verified local file.",
                    }
                ]
                if require_local and not self.locally_verified
                else []
            ),
        }


def _validate_registered_asset(
    asset: AssetRecord,
    *,
    source_path: Path,
) -> GovernanceValidation:
    base = validate_asset(asset)
    issues = list(base.issues)
    if not asset.local_path:
        return base
    registry_root = source_path.resolve().parent
    unresolved = registry_root / asset.local_path
    if unresolved.is_symlink():
        issues.append(
            GovernanceIssue("local_symlink", "local_path", "local asset cannot be a symlink")
        )
        return GovernanceValidation(False, tuple(issues))
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(registry_root)
    except ValueError:
        issues.append(
            GovernanceIssue("local_path_escape", "local_path", "local asset escapes registry directory")
        )
        return GovernanceValidation(False, tuple(issues))
    if not candidate.is_file():
        issues.append(
            GovernanceIssue("local_file_missing", "local_path", "local asset file is missing")
        )
    elif hashlib.sha256(candidate.read_bytes()).hexdigest() != asset.sha256:
        issues.append(
            GovernanceIssue("local_hash_mismatch", "local_path", "local asset SHA-256 does not match registry")
        )
    return GovernanceValidation(not issues, tuple(issues))
