from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.domains.profile import ProfileError, load_profile, load_profiles


EXPECTED_PROFILES = {
    "foundation-models-llm",
    "computer-vision",
    "natural-language-processing",
    "data-management-mining",
    "ml-systems-efficiency",
}

EXPECTED_VENUES = {
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


def test_profile_registry_matches_normative_matrix() -> None:
    profiles = load_profiles()

    assert {profile.profile_id for profile in profiles} == EXPECTED_PROFILES
    for profile in profiles:
        assert profile.plugin_id == profile.profile_id
        assert profile.compatible_venue_ids
        assert set(profile.compatible_venue_ids) <= EXPECTED_VENUES
        assert profile.claim_types
        assert profile.governance_checks
        assert profile.domain_checks
        assert set(profile.depth_requirements) == {
            "exploratory",
            "publication",
            "top_venue",
        }


def test_profile_parser_rejects_unknown_fields(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/autoresearch/profiles/ml-systems-efficiency.yaml"
    )
    path = tmp_path / "strict.yaml"
    path.write_text(
        source.read_text(encoding="utf-8") + "guaranteed_acceptance: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ProfileError, match="unknown fields.*guaranteed_acceptance"):
        load_profile("strict", profiles_dir=tmp_path)


def test_profile_parser_rejects_unknown_depth_requirement(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/autoresearch/profiles/ml-systems-efficiency.yaml"
    )
    text = source.read_text(encoding="utf-8").replace(
        "    require_hypothesis_outcomes: true\n",
        "    require_hypothesis_outcomes: true\n    reviewer_score: 8\n",
        1,
    )
    path = tmp_path / "strict.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ProfileError, match="unknown fields.*reviewer_score"):
        load_profile("strict", profiles_dir=tmp_path)
