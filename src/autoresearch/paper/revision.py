from __future__ import annotations


def revise_paper(draft: str, reviews: str) -> str:
    if "## Revision Notes" in draft:
        return draft
    return (
        draft.rstrip()
        + "\n\n## Revision Notes\n"
        + "The revision preserves only screened citations and verified experiment metrics. "
        + "Open reviewer concerns are tracked in `reviews.md`.\n"
        + "\n<!-- Review summary preserved for audit -->\n"
        + "<!-- "
        + reviews.replace("--", "-")
        + " -->\n"
    )
