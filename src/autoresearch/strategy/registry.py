from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autoresearch.strategy.models import (
    VenueStrategy,
    VenueStrategyError,
    load_venue_strategy,
)


@dataclass(frozen=True)
class VenueStrategyRegistry:
    strategies: tuple[VenueStrategy, ...]

    @classmethod
    def load(cls, root: Path) -> "VenueStrategyRegistry":
        strategies: list[VenueStrategy] = []
        seen: set[str] = set()
        for path in sorted(root.rglob("*.yaml")):
            strategy = load_venue_strategy(path)
            if strategy.venue_id in seen:
                raise VenueStrategyError(
                    f"duplicate strategy profile for {strategy.venue_id}: {path}"
                )
            seen.add(strategy.venue_id)
            strategies.append(strategy)
        return cls(tuple(strategies))

    def resolve(self, venue_id: str) -> VenueStrategy:
        for strategy in self.strategies:
            if strategy.venue_id == venue_id:
                return strategy
        raise VenueStrategyError(
            f"strategy profile not found for venue: {venue_id}"
        )

    def venue_ids(self) -> tuple[str, ...]:
        return tuple(s.venue_id for s in self.strategies)
