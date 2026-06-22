from __future__ import annotations

import pytest

from autoresearch.config import AutoresearchConfig, ConfigError


def test_literature_live_config_parses_sources_and_network_limits() -> None:
    config = AutoresearchConfig.from_mapping(
        {
            "project": {"name": "test"},
            "literature": {
                "mode": "live",
                "sources": ["arxiv", "openalex", "crossref"],
                "per_source_limit": 25,
                "max_retries": 1,
                "timeout_sec": 12,
                "queries": ["q1", "q2", "q3"],
                "saturation_patience": 2,
                "saturation_max_new_ratio": 0.15,
            },
        }
    )

    assert config.literature.mode == "live"
    assert config.literature.sources == ("arxiv", "openalex", "crossref")
    assert config.literature.per_source_limit == 25
    assert config.literature.queries == ("q1", "q2", "q3")
    assert config.literature.saturation_max_new_ratio == 0.15
    assert config.redacted_dict()["literature"]["mode"] == "live"


@pytest.mark.parametrize(
    "literature",
    [
        {"mode": "unknown"},
        {"mode": "live", "sources": []},
        {"mode": "live", "sources": ["semantic-scholar"]},
        {"per_source_limit": 0},
        {"max_retries": -1},
        {"timeout_sec": 0},
        {"queries": ["same query", " same   query "]},
        {"saturation_max_new_ratio": 1.1},
    ],
)
def test_literature_config_rejects_unsafe_or_unknown_values(
    literature: dict[str, object],
) -> None:
    with pytest.raises(ConfigError):
        AutoresearchConfig.from_mapping(
            {"project": {"name": "test"}, "literature": literature}
        )
