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


def _is_supported(number: float, value: float) -> bool:
    """Match a prose number against a ledger value, allowing rounding but not fabrication.

    Rounding (2.384 -> 2.3, 446.5 -> 446) is normal academic writing and must pass.
    Fabrication (446.5 -> 5.0) is an LLM hallucination and must fail. We use a
    two-tier tolerance: an absolute floor (0.05) for small values, and a relative
    tolerance (5%) for larger ones — together they admit one-decimal rounding
    (typically 1-4% error) while rejecting order-of-magnitude fabrications
    (>50% error). A fabricated 5.0 vs 446.5 differs by ~99% and is rejected.
    """
    if abs(number - value) <= 0.05:
        return True
    if value != 0 and abs(number - value) / abs(value) <= 0.05:
        return True
    return False


def verify_numeric_claims(markdown: str, ledger: list[LedgerEntry]) -> ClaimVerification:
    numbers = tuple(float(match) for match in re.findall(r"(?<![A-Za-z])\d+\.\d+", markdown))
    verified_values: list[float] = []
    for entry in ledger:
        if entry.metric is not None:
            verified_values.append(entry.metric)
        verified_values.extend(entry.extra_metrics.values())
    unsupported = tuple(
        number
        for number in numbers
        if not any(_is_supported(number, value) for value in verified_values)
    )
    verified = tuple(number for number in numbers if number not in unsupported)
    return ClaimVerification(
        ok=not unsupported,
        checked_numbers=numbers,
        verified_numbers=verified,
        unsupported_numbers=unsupported,
    )
