from __future__ import annotations


REQUIRED_SECTIONS = (
    "## Abstract",
    "## Introduction",
    "## Related Work",
    "## Method",
    "## Experiments",
    "## Results",
    "## Limitations",
    "## Conclusion",
)


def review_draft(markdown: str, *, evidence_mode: str = "synthetic") -> str:
    lines = ["# Reviews", ""]
    missing = [section for section in REQUIRED_SECTIONS if section not in markdown]
    if missing:
        lines.append("## Blocking Issues")
        for section in missing:
            lines.append(f"- Missing required section: {section}")
    else:
        lines.append("## Reviewer A: Methodology")
        lines.append("- The paper is structurally complete and reports the current evidence.")
        lines.append("## Reviewer B: Evidence")
        lines.append("- Claims should remain tied to verified metrics and screened citations.")
        lines.append("## Reviewer C: Venue Readiness")
        if evidence_mode == "real":
            lines.append(
                "- Venue readiness remains conditional on exact template and policy checks."
            )
        else:
            lines.append("- The scaffold is not venue-ready until the toy experiment is replaced.")
    return "\n".join(lines) + "\n"
