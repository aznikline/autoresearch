from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class CapabilityError(ValueError):
    """Raised when capability evidence is internally inconsistent."""


class CapabilityLevel(IntEnum):
    UNSUPPORTED = 0
    CONTRACT_SUPPORTED = 1
    INTEGRATION_VALIDATED = 2
    EVIDENCE_COMPLETE = 3
    SUBMISSION_READY = 4


@dataclass(frozen=True)
class CapabilityAssessment:
    level: CapabilityLevel
    blockers: tuple[str, ...]


def assess_capability(
    *,
    contract_supported: bool,
    integration_validated: bool,
    evidence_complete: bool,
    submission_ready: bool,
    blockers: tuple[str, ...] = (),
) -> CapabilityAssessment:
    flags = (
        contract_supported,
        integration_validated,
        evidence_complete,
        submission_ready,
    )
    names = (
        "contract_supported",
        "integration_validated",
        "evidence_complete",
        "submission_ready",
    )
    for index, enabled in enumerate(flags):
        if enabled and index > 0 and not flags[index - 1]:
            raise CapabilityError(f"{names[index]} requires {names[index - 1]}")
    if not contract_supported and not blockers:
        raise CapabilityError("unsupported capability requires at least one blocker")

    level = CapabilityLevel.UNSUPPORTED
    for candidate, enabled in zip(tuple(CapabilityLevel)[1:], flags, strict=True):
        if not enabled:
            break
        level = candidate
    return CapabilityAssessment(level=level, blockers=tuple(blockers))
