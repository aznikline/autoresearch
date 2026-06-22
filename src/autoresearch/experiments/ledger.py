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
    run_id: str = ""
    metric_definition: str = ""
    experiment_spec_sha256: str = ""
    code_sha256: str = ""
    config_sha256: str = ""
    protocol_fingerprint: str = ""
    environment: str = ""
    raw_outputs: tuple[str, ...] = ()
    evaluator_immutable: bool = True

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
                run_id=str(data.get("run_id", data["trial_id"])),
                metric_definition=str(data.get("metric_definition", "")),
                experiment_spec_sha256=str(data.get("experiment_spec_sha256", "")),
                code_sha256=str(data.get("code_sha256", "")),
                config_sha256=str(data.get("config_sha256", "")),
                protocol_fingerprint=str(data.get("protocol_fingerprint", "")),
                environment=str(data.get("environment", "")),
                raw_outputs=tuple(str(item) for item in data.get("raw_outputs", ())),
                evaluator_immutable=bool(data.get("evaluator_immutable", True)),
            )
        )
    return entries
