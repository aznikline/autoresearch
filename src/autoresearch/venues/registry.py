from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from autoresearch.venues.schema import (
    VenueContract,
    VenueContractError,
    load_venue_contract,
)


@dataclass(frozen=True)
class VenueRegistry:
    contracts: tuple[VenueContract, ...]

    @classmethod
    def load(cls, root: Path) -> "VenueRegistry":
        contracts: list[VenueContract] = []
        seen: dict[tuple[str, int, str], Path] = {}
        for path in sorted(root.rglob("*.yaml")):
            contract = load_venue_contract(path)
            if contract.key in seen:
                raise VenueContractError(
                    "duplicate venue contract "
                    f"{contract.venue_id}/{contract.year}/{contract.track}: "
                    f"{seen[contract.key]} and {path}"
                )
            seen[contract.key] = path
            contracts.append(contract)
        return cls(tuple(contracts))

    def resolve(
        self,
        venue_id: str,
        *,
        year: int | str,
        track: str,
        profile_id: str,
        on: date,
    ) -> VenueContract:
        candidates = [
            contract
            for contract in self.contracts
            if contract.venue_id == venue_id and contract.track == track
        ]
        if not candidates:
            raise VenueContractError(f"venue contract not found: {venue_id}/{track}")
        if year == "latest_verified":
            current = [contract for contract in candidates if contract.is_verified(on=on)]
            if not current:
                raise VenueContractError(
                    f"no current verified contract for {venue_id}/{track} on {on}"
                )
            contract = max(current, key=lambda item: item.year)
        else:
            try:
                resolved_year = int(year)
            except (TypeError, ValueError) as exc:
                raise VenueContractError("year must be an integer or latest_verified") from exc
            matching = [item for item in candidates if item.year == resolved_year]
            if not matching:
                raise VenueContractError(
                    f"venue contract not found: {venue_id}/{resolved_year}/{track}"
                )
            contract = matching[0]
            if not contract.is_verified(on=on):
                raise VenueContractError(
                    f"venue contract is not current and verified: {venue_id}/{resolved_year}/{track}"
                )
        if not contract.compatible_with(profile_id):
            raise VenueContractError(
                f"venue {venue_id}/{contract.year}/{track} is not compatible with {profile_id}"
            )
        return contract

    def select(
        self,
        venue_id: str,
        *,
        year: int | str,
        track: str,
        profile_id: str,
    ) -> VenueContract:
        candidates = [
            contract
            for contract in self.contracts
            if contract.venue_id == venue_id and contract.track == track
        ]
        if not candidates:
            raise VenueContractError(f"venue contract not found: {venue_id}/{track}")
        if year == "latest_available":
            contract = max(candidates, key=lambda item: item.year)
        else:
            try:
                resolved_year = int(year)
            except (TypeError, ValueError) as exc:
                raise VenueContractError(
                    "year must be an integer or latest_available"
                ) from exc
            matching = [item for item in candidates if item.year == resolved_year]
            if not matching:
                raise VenueContractError(
                    f"venue contract not found: {venue_id}/{resolved_year}/{track}"
                )
            contract = matching[0]
        if not contract.compatible_with(profile_id):
            raise VenueContractError(
                f"venue {venue_id}/{contract.year}/{track} is not compatible with {profile_id}"
            )
        return contract
