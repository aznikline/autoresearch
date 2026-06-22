from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from autoresearch.audit.reference import (
    ReferenceBundleError,
    audit_reference_bundles,
    export_reference_bundle,
)
from autoresearch.config import AutoresearchConfig


def _write_bundle(root: Path, profile: str, *, synthetic: bool = False) -> None:
    bundle = root / profile
    bundle.mkdir(parents=True)
    artifact = bundle / "evidence.json"
    artifact.write_text('{"real": true}', encoding="utf-8")
    payload = {
        "profile_id": profile,
        "synthetic": synthetic,
        "capability": "evidence_complete",
        "depth": "top_venue",
        "literature_mode": "live",
        "experiment_mode": "real",
        "llm_mode": "live" if profile == "foundation-models-llm" else "not_applicable",
        "artifacts": [
            {
                "path": "evidence.json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        ],
    }
    (bundle / "audit.json").write_text(json.dumps(payload), encoding="utf-8")


def test_four_real_hashed_reference_bundles_pass(tmp_path: Path) -> None:
    for profile in (
        "foundation-models-llm",
        "computer-vision",
        "natural-language-processing",
        "data-management-mining",
    ):
        _write_bundle(tmp_path, profile)

    result = audit_reference_bundles(tmp_path)

    assert result.ok, result.blockers


def test_synthetic_tampered_and_incomplete_bundles_fail(tmp_path: Path) -> None:
    _write_bundle(tmp_path, "foundation-models-llm", synthetic=True)
    _write_bundle(tmp_path, "computer-vision")
    artifact = tmp_path / "computer-vision/evidence.json"
    artifact.write_text("tampered", encoding="utf-8")

    result = audit_reference_bundles(tmp_path)

    assert not result.ok
    assert any("synthetic" in blocker for blocker in result.blockers)
    assert any("hash mismatch" in blocker for blocker in result.blockers)
    assert any("missing real reference bundle" in blocker for blocker in result.blockers)


def _real_config(tmp_path: Path, profile: str) -> AutoresearchConfig:
    return AutoresearchConfig.from_mapping(
        {
            "project": {"name": "reference"},
            "research": {"profile": profile},
            "runtime": {
                "artifacts_root": str(tmp_path / "artifacts"),
                "max_artifact_bytes": 1_000_000,
            },
            "llm": {"mode": "live" if profile == "foundation-models-llm" else "synthetic"},
            "literature": {
                "mode": "live",
                "sources": ["arxiv", "openalex", "crossref"],
            },
            "experiment": {"evidence_mode": "real"},
        }
    )


def _minimal_verified_run(root: Path, config: AutoresearchConfig) -> Path:
    import hashlib as _hashlib

    run = root / "run"
    final = run / "stage-12-final_verification_export"
    final.mkdir(parents=True)
    fingerprint = _hashlib.sha256(
        json.dumps(config.redacted_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (run / "checkpoint.json").write_text('{"status":"done"}', encoding="utf-8")
    (run / "alignment.json").write_text(
        json.dumps(
            {
                "profile": config.research.profile,
                "depth": config.research.depth,
                "config_fingerprint": fingerprint,
                "llm": {"mode": config.llm.mode, "synthetic": config.llm.mode == "synthetic"},
                "literature": {"mode": "live", "synthetic": False},
                "experiment": {"evidence_mode": "real", "synthetic": False},
            }
        ),
        encoding="utf-8",
    )
    proof = final / "proof.json"
    proof.write_text('{"real":true}', encoding="utf-8")
    (final / "quality_report.json").write_text(
        '{"evidence_complete":true,"submission_ready":false}', encoding="utf-8"
    )
    (final / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "path": proof.relative_to(run).as_posix(),
                        "sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (final / "bundle_index.json").write_text(
        json.dumps({"files": ["quality_report.json", "proof.json"]}), encoding="utf-8"
    )
    return run


def test_export_reference_bundle_copies_and_hashes_verified_real_run(tmp_path: Path) -> None:
    config = _real_config(tmp_path, "computer-vision")
    run = _minimal_verified_run(tmp_path, config)

    output = export_reference_bundle(run, config=config, output_root=tmp_path / "bundles")

    audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert audit["profile_id"] == "computer-vision"
    assert audit["synthetic"] is False
    assert audit["capability"] == "evidence_complete"
    assert len(audit["artifacts"]) >= 6
    assert (output / "run/alignment.json").is_file()


def test_export_reference_bundle_rejects_synthetic_or_incomplete_run(tmp_path: Path) -> None:
    config = _real_config(tmp_path, "natural-language-processing")
    run = _minimal_verified_run(tmp_path, config)
    alignment_path = run / "alignment.json"
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    alignment["experiment"] = {"evidence_mode": "synthetic", "synthetic": True}
    alignment_path.write_text(json.dumps(alignment), encoding="utf-8")

    with pytest.raises(ReferenceBundleError, match="real experiment"):
        export_reference_bundle(run, config=config, output_root=tmp_path / "bundles")


def test_reference_bundle_rejects_non_top_venue_depth(tmp_path: Path) -> None:
    for profile in (
        "foundation-models-llm",
        "computer-vision",
        "natural-language-processing",
        "data-management-mining",
    ):
        _write_bundle(tmp_path, profile)
    audit_path = tmp_path / "computer-vision/audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["depth"] = "exploratory"
    audit_path.write_text(json.dumps(audit), encoding="utf-8")

    result = audit_reference_bundles(tmp_path)

    assert not result.ok
    assert any("top_venue" in blocker for blocker in result.blockers)
