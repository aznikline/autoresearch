from __future__ import annotations

import hashlib
import json
from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.pipeline.checkpoint import read_checkpoint


def verify_run(run_dir: str | Path, *, config: AutoresearchConfig) -> dict[str, object]:
    root = Path(run_dir).resolve()
    issues: list[str] = []
    checkpoint = read_checkpoint(root)
    if checkpoint is None or checkpoint.get("status") != "done":
        issues.append("run checkpoint is not done")
    alignment = _read_json(root / "alignment.json", issues)
    expected_fingerprint = _config_fingerprint(config)
    if alignment.get("config_fingerprint") != expected_fingerprint:
        issues.append("config fingerprint mismatch")
    final_dir = root / "stage-12-final_verification_export"
    manifest = _read_json(final_dir / "artifact_manifest.json", issues)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        issues.append("artifact manifest is empty or invalid")
    else:
        for item in artifacts:
            if not isinstance(item, dict):
                issues.append("artifact manifest contains a non-object entry")
                continue
            relative = str(item.get("path", ""))
            path = (root / relative).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                issues.append(f"artifact path escapes run directory: {relative}")
                continue
            actual = _hash_file(path)
            if actual != str(item.get("sha256", "")):
                issues.append(f"artifact hash mismatch: {relative}")
    bundle = _read_json(final_dir / "bundle_index.json", issues)
    files = bundle.get("files", [])
    if not isinstance(files, list):
        issues.append("bundle index files are invalid")
    else:
        for relative in files:
            if not (final_dir / str(relative)).is_file():
                issues.append(f"bundle file missing: {relative}")
    return {
        "ok": not issues,
        "run_dir": root.as_posix(),
        "issues": issues,
        "artifact_count": len(artifacts) if isinstance(artifacts, list) else 0,
    }


def _config_fingerprint(config: AutoresearchConfig) -> str:
    payload = json.dumps(
        config.redacted_dict(), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path, issues: list[str]) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        issues.append(f"missing or invalid JSON: {path.name}")
        return {}
    if not isinstance(data, dict):
        issues.append(f"JSON root is not an object: {path.name}")
        return {}
    return data


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
