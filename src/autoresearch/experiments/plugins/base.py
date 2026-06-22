from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


COMMON_REQUIRED_FIELDS = frozenset(
    {
        "confirmatory",
        "hypotheses",
        "primary_metrics",
        "exclusions",
        "evaluator_hash",
        "stopping_rule",
        "resource_budget",
        "seeds",
        "uncertainty",
    }
)


@dataclass(frozen=True)
class ProtocolIssue:
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ProtocolValidation:
    plugin_id: str
    ok: bool
    issues: tuple[ProtocolIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "ok": self.ok,
            "issues": [
                {
                    "field": issue.field,
                    "code": issue.code,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


class ExperimentPlugin:
    plugin_id = ""
    required_fields: frozenset[str] = frozenset()
    required_true_fields: frozenset[str] = frozenset()
    min_list_lengths: dict[str, int] = {}
    resolved_fields: frozenset[str] = frozenset()
    positive_fields: frozenset[str] = frozenset()
    sha256_fields: frozenset[str] = frozenset()
    required_items: dict[str, frozenset[str]] = {}

    def validate(self, protocol: Mapping[str, object]) -> ProtocolValidation:
        issues: list[ProtocolIssue] = []
        for field in sorted(COMMON_REQUIRED_FIELDS | self.required_fields):
            if field not in protocol:
                issues.append(
                    ProtocolIssue(field, "missing_field", f"required field is missing: {field}")
                )
            elif protocol[field] in (None, "", [], (), {}):
                issues.append(
                    ProtocolIssue(
                        field,
                        "empty_required_evidence",
                        f"required evidence is empty: {field}",
                    )
                )
        if protocol.get("confirmatory") is not True:
            issues.append(
                ProtocolIssue(
                    "confirmatory",
                    "required_true",
                    "reference protocol must freeze confirmatory settings",
                )
            )
        for field in sorted(self.required_true_fields):
            if field in protocol and protocol[field] is not True:
                issues.append(
                    ProtocolIssue(field, "required_true", f"{field} must be true")
                )
        list_requirements = {
            "hypotheses": 2,
            "primary_metrics": 1,
            "seeds": 1,
            **self.min_list_lengths,
        }
        for field, minimum in sorted(list_requirements.items()):
            if field not in protocol:
                continue
            value = protocol[field]
            if not isinstance(value, (list, tuple)) or len(value) < minimum:
                issues.append(
                    ProtocolIssue(
                        field,
                        "insufficient_items",
                        f"{field} requires at least {minimum} items",
                    )
                )
        for field in sorted(self.resolved_fields):
            if str(protocol.get(field, "")).strip().lower() in {
                "",
                "unknown",
                "unreviewed",
                "pending",
                "none",
            }:
                issues.append(
                    ProtocolIssue(
                        field,
                        "unresolved_evidence",
                        f"{field} must contain resolved evidence",
                    )
                )
        for field in sorted(self.positive_fields):
            value = protocol.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                issues.append(
                    ProtocolIssue(
                        field,
                        "non_positive_value",
                        f"{field} must be a positive number",
                    )
                )
        for field in sorted({"evaluator_hash"} | set(self.sha256_fields)):
            if field in protocol and not re.fullmatch(
                r"[0-9a-f]{64}", str(protocol[field])
            ):
                issues.append(
                    ProtocolIssue(
                        field,
                        "invalid_hash",
                        f"{field} must be a lowercase SHA-256 digest",
                    )
                )
        for field, required in sorted(self.required_items.items()):
            value = protocol.get(field, ())
            observed = {
                str(item).strip().lower() for item in value
            } if isinstance(value, (list, tuple)) else set()
            missing = sorted(required - observed)
            if missing:
                issues.append(
                    ProtocolIssue(
                        field,
                        "missing_required_items",
                        f"{field} missing: {', '.join(missing)}",
                    )
                )
        return ProtocolValidation(self.plugin_id, not issues, tuple(issues))
