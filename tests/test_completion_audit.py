from __future__ import annotations

import json
from pathlib import Path

from autoresearch.audit.completion import REQUIREMENT_IDS, audit_repository


def test_current_repository_audit_is_incomplete_and_names_real_blockers() -> None:
    root = Path(__file__).resolve().parents[1]

    audit = audit_repository(root)

    assert not audit.complete
    assert set(audit.requirements) == set(REQUIREMENT_IDS)
    assert "MD-002" in audit.blocked_requirements
    assert "MD-009" in audit.blocked_requirements
    assert "MD-013" in audit.blocked_requirements
    assert any("not verified" in blocker for blocker in audit.requirements["MD-002"].blockers)


def test_synthetic_or_stale_attestation_cannot_satisfy_requirement(
    tmp_path: Path,
) -> None:
    root = tmp_path
    artifact = root / "artifact.txt"
    artifact.write_text("current", encoding="utf-8")
    evidence_dir = root / "docs" / "audits" / "evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "MD-004.json").write_text(
        json.dumps(
            {
                "requirement_id": "MD-004",
                "status": "passed",
                "synthetic": True,
                "credentialed": False,
                "artifacts": [
                    {"path": "artifact.txt", "sha256": "0" * 64}
                ],
            }
        ),
        encoding="utf-8",
    )

    audit = audit_repository(root)

    blockers = audit.requirements["MD-004"].blockers
    assert "synthetic evidence is not accepted" in blockers
    assert (
        "authenticated remote or digest-attested local provider evidence is required"
        in blockers
    )
    assert any("artifact hash mismatch" in blocker for blocker in blockers)


def test_audit_json_records_spec_and_plan_hashes() -> None:
    root = Path(__file__).resolve().parents[1]

    payload = audit_repository(root).to_dict()

    assert len(payload["spec_sha256"]) == 64
    assert len(payload["plan_sha256"]) == 64
    assert payload["complete"] is False


def test_attestation_rejects_unknown_fields_and_repository_escape(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "docs/audits/evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "MD-006.json").write_text(
        json.dumps(
            {
                "requirement_id": "MD-006",
                "status": "passed",
                "synthetic": False,
                "credentialed": False,
                "guaranteed": True,
                "artifacts": [
                    {"path": "../outside", "sha256": "a" * 64},
                    {"path": "../outside", "sha256": "a" * 64},
                ],
            }
        ),
        encoding="utf-8",
    )

    blockers = audit_repository(tmp_path).requirements["MD-006"].blockers

    assert "attestation unknown fields: guaranteed" in blockers
    assert "duplicate artifact path: ../outside" in blockers
    assert "artifact path escapes repository: ../outside" in blockers


def test_attestation_is_invalidated_when_spec_or_plan_changes(tmp_path: Path) -> None:
    spec = tmp_path / "docs/specs/multidomain-top-venue-autoresearch.md"
    plan = tmp_path / "docs/plans/2026-06-18-002-feat-multidomain-top-venue-autoresearch-plan.md"
    evidence = tmp_path / "docs/audits/evidence/MD-012.json"
    artifact = tmp_path / "proof.txt"
    spec.parent.mkdir(parents=True)
    plan.parent.mkdir(parents=True)
    evidence.parent.mkdir(parents=True)
    spec.write_text("new spec")
    plan.write_text("new plan")
    artifact.write_text("proof")
    evidence.write_text(
        json.dumps(
            {
                "requirement_id": "MD-012",
                "status": "passed",
                "synthetic": False,
                "credentialed": False,
                "spec_sha256": "0" * 64,
                "plan_sha256": "0" * 64,
                "artifacts": [{"path": "proof.txt", "sha256": "0" * 64}],
            }
        )
    )

    blockers = audit_repository(tmp_path).requirements["MD-012"].blockers

    assert "attestation spec hash mismatch" in blockers
    assert "attestation plan hash mismatch" in blockers
