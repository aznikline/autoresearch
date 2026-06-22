from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from autoresearch.config import ConfigError, load_config
from autoresearch.domains.profile import load_profile
from autoresearch.paper.citations import CitationVerification
from autoresearch.paper.claims import ClaimVerification
from autoresearch.paper.quality import ResearchEvidence, assess_venue_readiness
from autoresearch.pipeline.runner import PipelineRunner


def test_config_parses_alignment_surface_and_valid_threshold_waiver(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
project:
  name: aligned
research:
  profile: ml-systems-efficiency
  depth: publication
  target_venues: [MLSys]
  primary_claim_type: efficiency
  threshold_waivers:
    - requirement: seeds
      affected_claim: claim-1
      reason: deterministic exhaustive benchmark
      alternative_test: repeat on three hardware targets
experiment:
  time_budget_sec: 120
  total_compute_budget: 4 GPU-hours
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.research.primary_claim_type == "efficiency"
    assert config.experiment.total_compute_budget == "4 GPU-hours"
    assert config.research.threshold_waivers[0].requirement == "seeds"


@pytest.mark.parametrize(
    "requirement",
    ["citation_integrity", "immutable_evaluation", "protocol_parity", "artifact_provenance"],
)
def test_config_rejects_waiver_for_unwaivable_invariant(
    tmp_path: Path,
    requirement: str,
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        f"""
project:
  name: invalid-waiver
research:
  threshold_waivers:
    - requirement: {requirement}
      affected_claim: claim-1
      reason: inconvenient
      alternative_test: none
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="cannot be waived"):
        load_config(path)


def test_config_rejects_unknown_threshold_waiver(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
project:
  name: invalid-waiver
research:
  threshold_waivers:
    - requirement: reviewer_score
      affected_claim: claim-1
      reason: no reviewer available
      alternative_test: self review
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="unknown threshold requirement"):
        load_config(path)


def test_quality_report_keeps_unwaivable_invariants_blocking() -> None:
    assessment = assess_venue_readiness(
        "A complete paper with limitations.",
        citation_verification=CitationVerification(True, (), (), ()),
        claim_verification=ClaimVerification(True, (), (), ()),
        profile=load_profile("ml-systems-efficiency"),
        depth="exploratory",
        evidence=ResearchEvidence(
            screened_papers=8,
            baselines=1,
            evaluation_units=1,
            seeds=1,
            ablations=1,
            verified_metrics=2,
            compute_reporting=True,
            hypothesis_outcomes=True,
            literature_gap_records=True,
            empirical_claim_links=True,
            preregistered_confirmatory_spec=True,
            failed_runs_accounted=True,
            limitations=True,
            artifact_manifest=True,
            competing_hypotheses=True,
            immutable_evaluation=False,
            protocol_parity=False,
            artifact_provenance=False,
        ),
    )

    by_name = {check.requirement: check for check in assessment.checks}
    assert not by_name["immutable_evaluation"].passed
    assert not by_name["protocol_parity"].passed
    assert not by_name["artifact_provenance"].passed
    assert all(check.blocking_reason for check in assessment.checks if not check.passed)
    assert not assessment.submission_ready


def test_runner_writes_alignment_and_structured_evidence_artifacts(config) -> None:
    result = PipelineRunner(config).run(
        topic="machine learning optimization",
        run_id="alignment-run",
        auto_approve=True,
    )
    run_dir = Path(result["run_dir"])

    alignment = json.loads((run_dir / "alignment.json").read_text(encoding="utf-8"))
    gaps = json.loads(
        (run_dir / "stage-05-synthesis" / "literature_gaps.json").read_text(
            encoding="utf-8"
        )
    )
    hypotheses = json.loads(
        (run_dir / "stage-06-hypothesis_generation" / "hypotheses.json").read_text(
            encoding="utf-8"
        )
    )
    outcomes = json.loads(
        (run_dir / "stage-10-result_analysis_decision" / "hypothesis_outcomes.json").read_text(
            encoding="utf-8"
        )
    )
    claims = json.loads(
        (run_dir / "stage-11-paper_draft_revision" / "empirical_claims.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(
        (run_dir / "stage-12-final_verification_export" / "artifact_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["alignment"] == alignment
    assert alignment["profile"] == "ml-systems-efficiency"
    assert alignment["primary_claim_type"]
    assert alignment["resource_budget"]["time_budget_sec"] > 0
    assert alignment["venue_contract"]["venue_id"] == "mlsys"
    assert alignment["venue_contract"]["status"] == "verified"
    assert alignment["capability"]["level"] == "contract_supported"
    assert alignment["capability"]["blockers"]
    assert gaps[0]["search_scope"] and gaps[0]["nearest_work"]
    assert len(hypotheses) >= 2
    assert {item["outcome"] for item in outcomes} <= {
        "supported",
        "refuted",
        "inconclusive",
    }
    assert claims[0]["run_ids"] and claims[0]["raw_outputs"]
    assert manifest["artifacts"]
    assert all(item["sha256"] for item in manifest["artifacts"])
    assert "stage-12-final_verification_export/paper.tex" in {
        item["path"] for item in manifest["artifacts"]
    }

    quality = json.loads(
        (run_dir / "stage-12-final_verification_export" / "quality_report.json").read_text(
            encoding="utf-8"
        )
    )
    check_names = {check["requirement"] for check in quality["checks"]}
    checks = {check["requirement"]: check for check in quality["checks"]}
    assert {
        "literature_gap_records",
        "empirical_claim_links",
        "preregistered_confirmatory_spec",
        "immutable_evaluation",
        "protocol_parity",
        "failed_runs_accounted",
        "limitations",
        "artifact_manifest",
        "artifact_provenance",
        "competing_hypotheses",
    } <= check_names
    assert checks["hypothesis_outcomes"]["observed"] is True
    bundle = json.loads(
        (run_dir / "stage-12-final_verification_export" / "bundle_index.json").read_text(
            encoding="utf-8"
        )
    )
    assert "artifact_manifest.json" in bundle["files"]


def test_runner_rejects_profile_without_compatible_skill(config, tmp_path: Path) -> None:
    incompatible = replace(
        config,
        skills=replace(config.skills, directories=(str(tmp_path / "empty-skills"),)),
    )

    with pytest.raises(ConfigError, match="no compatible project skill"):
        PipelineRunner(incompatible)


def test_runner_rejects_incompatible_profile_and_venue(config) -> None:
    incompatible = replace(
        config,
        research=replace(
            config.research,
            profile="computer-vision",
            venue_id="mlsys",
            venue_year="latest_available",
        ),
    )

    with pytest.raises(ConfigError, match="not compatible"):
        PipelineRunner(incompatible)


def test_runner_rejects_unknown_venue(config) -> None:
    unknown = replace(
        config,
        research=replace(config.research, venue_id="unknownconf"),
    )

    with pytest.raises(ConfigError, match="venue contract not found"):
        PipelineRunner(unknown)
