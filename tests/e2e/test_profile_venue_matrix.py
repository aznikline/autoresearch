from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.config import AutoresearchConfig, ConfigError
from autoresearch.domains.profile import load_profiles
from autoresearch.pipeline.runner import PipelineRunner
from autoresearch.venues.registry import VenueRegistry


ROOT = Path(__file__).resolve().parents[2]
VENUES = ROOT / "src/autoresearch/venues"


def _config(profile_id: str, venue_id: str, tmp_path: Path) -> AutoresearchConfig:
    return AutoresearchConfig.from_mapping(
        {
            "project": {"name": f"matrix-{profile_id}-{venue_id}"},
            "research": {
                "profile": profile_id,
                "venue_id": venue_id,
                "venue_year": "latest_available",
                "venue_track": "main",
            },
            "runtime": {"artifacts_root": str(tmp_path / "artifacts")},
            "skills": {"directories": [str(ROOT / "skills")]},
        }
    )


def test_every_declared_profile_venue_pair_matches_contract_capability(
    tmp_path: Path,
) -> None:
    pairs = [
        (profile.profile_id, venue_id)
        for profile in load_profiles()
        for venue_id in profile.compatible_venue_ids
    ]

    for profile_id, venue_id in pairs:
        runner = PipelineRunner(_config(profile_id, venue_id, tmp_path))
        assert runner.venue_contract.venue_id == venue_id
        expected = (
            "contract_supported"
            if venue_id in {
                "acl", "emnlp", "neurips", "icml", "iclr", "colm", "cvpr",
                "eccv", "icde", "kdd", "mlsys", "thewebconf", "vldb",
            }
            else "unsupported"
        )
        assert runner.capability.level.name.lower() == expected


def test_every_undeclared_profile_venue_pair_fails_closed(tmp_path: Path) -> None:
    profiles = load_profiles()
    venue_ids = {
        contract.venue_id for contract in VenueRegistry.load(VENUES).contracts
    }

    for profile in profiles:
        for venue_id in venue_ids - set(profile.compatible_venue_ids):
            with pytest.raises(ConfigError, match="not compatible"):
                PipelineRunner(_config(profile.profile_id, venue_id, tmp_path))
