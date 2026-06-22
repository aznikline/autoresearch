from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from autoresearch.venues.registry import VenueRegistry
from autoresearch.venues.schema import VenueContractError, load_venue_contract


DEFAULT_VENUES = Path(__file__).resolve().parents[1] / "src/autoresearch/venues"
EXPECTED_VENUE_IDS = {
    "neurips",
    "icml",
    "iclr",
    "colm",
    "acl",
    "emnlp",
    "naacl",
    "coling",
    "cvpr",
    "iccv",
    "eccv",
    "sigmod",
    "vldb",
    "icde",
    "kdd",
    "thewebconf",
    "mlsys",
}


VALID_CONTRACT = """
schema_version: 1
venue_id: neurips
display_name: NeurIPS
year: 2026
track: main
status: verified
compatible_profiles:
  - foundation-models-llm
  - computer-vision
official_sources:
  - url: https://neurips.cc/Conferences/2026/CallForPapers
    retrieved_at: 2026-06-18
    sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
template:
  identity: neurips-2026-main
  source_url: https://neurips.cc/Conferences/2026/PaperInformation/StyleFiles
  sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
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


def _write_contract(root: Path, relative: str, text: str = VALID_CONTRACT) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_load_venue_contract_is_strict(tmp_path: Path) -> None:
    path = _write_contract(tmp_path, "neurips/2026/main.yaml")

    contract = load_venue_contract(path)

    assert contract.key == ("neurips", 2026, "main")
    assert contract.compatible_with("foundation-models-llm")
    assert contract.is_verified(on=date(2026, 6, 18))


def test_contract_rejects_unknown_fields(tmp_path: Path) -> None:
    path = _write_contract(
        tmp_path,
        "neurips/2026/main.yaml",
        VALID_CONTRACT + "guaranteed_acceptance: true\n",
    )

    with pytest.raises(VenueContractError, match="unknown fields.*guaranteed_acceptance"):
        load_venue_contract(path)


def test_draft_contract_may_record_unverified_source_candidates(tmp_path: Path) -> None:
    text = (
        VALID_CONTRACT.replace("status: verified", "status: draft")
        .replace("retrieved_at: 2026-06-18", "retrieved_at: null")
        .replace(
            "sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "sha256: null",
        )
        .replace(
            "sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sha256: null",
        )
        .replace("valid_until: 2026-12-31", "valid_until: null")
        .replace("anonymity: double_blind", "anonymity: unknown")
        .replace("supplement_allowed: true", "supplement_allowed: null")
        .replace("checklist_required: true", "checklist_required: null")
        .replace("ethics_required: true", "ethics_required: null")
        .replace("limitations_required: true", "limitations_required: null")
        .replace("artifact_policy: optional", "artifact_policy: unknown")
    )
    contract = load_venue_contract(
        _write_contract(tmp_path, "neurips/draft/main.yaml", text)
    )

    assert contract.status.value == "draft"
    assert contract.official_sources[0].sha256 is None
    assert contract.valid_until is None
    assert contract.policy.anonymity == "unknown"
    assert contract.policy.checklist_required is None
    assert not contract.is_verified(on=date(2026, 6, 18))


def test_verified_contract_requires_source_and_template_hashes(tmp_path: Path) -> None:
    text = VALID_CONTRACT.replace(
        "sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sha256: null",
    )

    with pytest.raises(VenueContractError, match="verified contract requires"):
        load_venue_contract(_write_contract(tmp_path, "neurips/2026/main.yaml", text))


def test_verified_contract_requires_resolved_policy(tmp_path: Path) -> None:
    text = VALID_CONTRACT.replace("checklist_required: true", "checklist_required: null")

    with pytest.raises(VenueContractError, match="verified contract requires resolved policy"):
        load_venue_contract(_write_contract(tmp_path, "neurips/2026/main.yaml", text))


@pytest.mark.parametrize("status", ["draft", "stale", "retired"])
def test_non_verified_contract_cannot_target_submission(
    tmp_path: Path,
    status: str,
) -> None:
    path = _write_contract(
        tmp_path,
        f"neurips/2026/{status}.yaml",
        VALID_CONTRACT.replace("status: verified", f"status: {status}"),
    )
    contract = load_venue_contract(path)

    assert not contract.is_verified(on=date(2026, 6, 18))


def test_registry_resolves_latest_current_verified_contract(tmp_path: Path) -> None:
    _write_contract(
        tmp_path,
        "neurips/2025/main.yaml",
        VALID_CONTRACT.replace("year: 2026", "year: 2025")
        .replace("neurips-2026-main", "neurips-2025-main")
        .replace("valid_until: 2026-12-31", "valid_until: 2025-12-31"),
    )
    _write_contract(tmp_path, "neurips/2026/main.yaml")
    registry = VenueRegistry.load(tmp_path)

    contract = registry.resolve(
        "neurips",
        year="latest_verified",
        track="main",
        profile_id="foundation-models-llm",
        on=date(2026, 6, 18),
    )

    assert contract.year == 2026


def test_registry_rejects_incompatible_profile(tmp_path: Path) -> None:
    _write_contract(tmp_path, "neurips/2026/main.yaml")
    registry = VenueRegistry.load(tmp_path)

    with pytest.raises(VenueContractError, match="not compatible"):
        registry.resolve(
            "neurips",
            year=2026,
            track="main",
            profile_id="data-management-mining",
            on=date(2026, 6, 18),
        )


def test_registry_selects_latest_available_draft_without_promoting_it(tmp_path: Path) -> None:
    text = VALID_CONTRACT.replace("status: verified", "status: draft")
    _write_contract(tmp_path, "neurips/2026/main.yaml", text)
    registry = VenueRegistry.load(tmp_path)

    contract = registry.select(
        "neurips",
        year="latest_available",
        track="main",
        profile_id="foundation-models-llm",
    )

    assert contract.year == 2026
    assert contract.status.value == "draft"


def test_registry_rejects_duplicate_contract_keys(tmp_path: Path) -> None:
    _write_contract(tmp_path, "a.yaml")
    _write_contract(tmp_path, "nested/b.yaml")

    with pytest.raises(VenueContractError, match="duplicate venue contract"):
        VenueRegistry.load(tmp_path)


def test_default_registry_has_every_normative_venue_with_explicit_status() -> None:
    registry = VenueRegistry.load(DEFAULT_VENUES)

    assert {contract.venue_id for contract in registry.contracts} == EXPECTED_VENUE_IDS
    statuses = {contract.venue_id: contract.status.value for contract in registry.contracts}
    verified = {venue for venue, status in statuses.items() if status == "verified"}
    assert verified == {
        "acl", "emnlp", "neurips", "icml", "iclr", "colm", "cvpr", "eccv",
        "icde", "kdd", "mlsys", "thewebconf", "vldb",
    }
    assert {status for venue, status in statuses.items() if venue not in verified} == {"draft"}
    assert all(contract.official_sources for contract in registry.contracts)
    assert all(contract.template.identity for contract in registry.contracts)
