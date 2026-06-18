from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class LedgerEntry:
    trial_id: str
    metric: float | None
    status: str
    decision: str
    description: str
    reason: str
    metrics_path: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def append_entry(path: Path, entry: LedgerEntry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")


def read_ledger(path: Path) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        entries.append(
            LedgerEntry(
                trial_id=str(data["trial_id"]),
                metric=(
                    float(data["metric"])
                    if data.get("metric") is not None
                    else None
                ),
                status=str(data["status"]),
                decision=str(data["decision"]),
                description=str(data.get("description", "")),
                reason=str(data.get("reason", "")),
                metrics_path=str(data.get("metrics_path", "")),
            )
        )
    return entries
