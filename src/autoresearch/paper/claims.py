from __future__ import annotations

import re
from dataclasses import dataclass

from autoresearch.experiments.ledger import LedgerEntry


@dataclass(frozen=True)
class ClaimVerification:
    ok: bool
    checked_numbers: tuple[float, ...]
    verified_numbers: tuple[float, ...]
    unsupported_numbers: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checked_numbers": list(self.checked_numbers),
            "verified_numbers": list(self.verified_numbers),
            "unsupported_numbers": list(self.unsupported_numbers),
        }


def verify_numeric_claims(markdown: str, ledger: list[LedgerEntry]) -> ClaimVerification:
    numbers = tuple(float(match) for match in re.findall(r"(?<![A-Za-z])\d+\.\d+", markdown))
    verified_values = tuple(entry.metric for entry in ledger if entry.metric is not None)
    unsupported = tuple(
        number
        for number in numbers
        if not any(abs(number - value) <= 1e-9 for value in verified_values)
    )
    verified = tuple(number for number in numbers if number not in unsupported)
    return ClaimVerification(
        ok=not unsupported,
        checked_numbers=numbers,
        verified_numbers=verified,
        unsupported_numbers=unsupported,
    )
