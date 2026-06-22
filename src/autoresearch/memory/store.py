from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Lesson:
    lesson_id: str
    project: str
    run_id: str
    stage: str
    lesson: str
    source: str
    recorded_at: str
    topic: str = ""
    evidence_ref: str = ""
    accepted: bool = True


class MemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append_human_lesson(
        self,
        *,
        project: str,
        run_id: str,
        stage: str,
        lesson: str,
        topic: str = "",
        evidence_ref: str = "",
    ) -> Lesson:
        normalized = " ".join(lesson.split())
        digest = hashlib.sha256(
            json.dumps(
                {
                    "project": project,
                    "stage": stage,
                    "lesson": normalized,
                    "topic": topic.strip(),
                    "source": "human_rejection",
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = {item.lesson_id: item for item in self.read()}
        if digest in existing:
            return existing[digest]
        item = Lesson(
            lesson_id=digest,
            project=project,
            run_id=run_id,
            stage=stage,
            lesson=normalized,
            source="human_rejection",
            recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            topic=topic.strip(),
            evidence_ref=evidence_ref.strip(),
            accepted=True,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        return item

    def append_event(
        self,
        *,
        project: str,
        run_id: str,
        stage: str,
        lesson: str,
        topic: str,
        source: str,
        evidence_ref: str,
    ) -> Lesson:
        normalized = " ".join(lesson.split())
        digest = hashlib.sha256(
            json.dumps(
                {
                    "project": project,
                    "run_id": run_id,
                    "stage": stage,
                    "lesson": normalized,
                    "topic": topic.strip(),
                    "source": source,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = {item.lesson_id: item for item in self.read()}
        if digest in existing:
            return existing[digest]
        item = Lesson(
            lesson_id=digest,
            project=project,
            run_id=run_id,
            stage=stage,
            lesson=normalized,
            source=source,
            recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            topic=topic.strip(),
            evidence_ref=evidence_ref.strip(),
            accepted=False,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        return item

    def read(self) -> tuple[Lesson, ...]:
        if not self.path.is_file():
            return ()
        lessons: list[Lesson] = []
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            data = json.loads(line)
            try:
                lessons.append(Lesson(**data))
            except TypeError as exc:
                raise ValueError(
                    f"invalid memory record at line {line_number}: {self.path}"
                ) from exc
        return tuple(lessons)

    def render(self, *, topic: str = "") -> str:
        query_tokens = _tokens(topic)
        return "\n".join(
            f"- [{item.stage}] {item.lesson}"
            for item in self.read()
            if item.accepted
            and (
                not query_tokens
                or not item.topic
                or bool(query_tokens & _tokens(item.topic))
            )
        )


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in text.replace("-", " ").split()
        if len(token) >= 3
    }
