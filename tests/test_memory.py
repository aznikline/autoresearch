from __future__ import annotations

from pathlib import Path

from autoresearch.config import AutoresearchConfig
from autoresearch.hitl.session import record_decision
from autoresearch.memory.store import MemoryStore
from autoresearch.pipeline.runner import PipelineRunner


def test_memory_store_is_durable_and_deduplicates_lessons(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "lessons.jsonl")

    first = store.append_human_lesson(
        project="p",
        run_id="r1",
        stage="experiment_design",
        lesson="Baselines use mismatched budgets.",
    )
    second = store.append_human_lesson(
        project="p",
        run_id="r1",
        stage="experiment_design",
        lesson="Baselines use mismatched budgets.",
    )

    assert first.lesson_id == second.lesson_id
    assert len(store.read()) == 1
    assert "mismatched budgets" in MemoryStore(tmp_path / "lessons.jsonl").render()


def test_memory_prompt_retrieval_is_topic_matched_and_accepted_only(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path / "lessons.jsonl")
    store.append_human_lesson(
        project="p",
        run_id="r1",
        stage="experiment_design",
        lesson="Use a stronger vision baseline.",
        topic="image segmentation robustness",
        evidence_ref="sha256:abc",
    )
    store.append_event(
        project="p",
        run_id="r2",
        stage="experiment_loop",
        lesson="Provider timeout",
        topic="language model evaluation",
        source="stage_failure",
        evidence_ref="checkpoint:r2",
    )

    assert "vision baseline" in store.render(topic="image robustness")
    assert "vision baseline" not in store.render(topic="database latency")
    assert "Provider timeout" not in store.render(topic="language model")
    assert len(store.read()) == 2


def test_rejected_gate_promotes_human_reason_to_project_memory(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    paused = runner.run(topic="test idea", run_id="memory-run")
    run_dir = Path(paused["run_dir"])
    record_decision(
        run_dir,
        decision="reject",
        reason="Search scope omitted a critical benchmark family.",
    )

    runner.resume(run_dir)

    memory_path = (
        Path(config.runtime.artifacts_root)
        / "_memory"
        / "test-project.jsonl"
    )
    lessons = MemoryStore(memory_path).read()
    assert len(lessons) == 1
    assert lessons[0].source == "human_rejection"
    assert lessons[0].stage == "literature_screen"
    assert lessons[0].topic == "test idea"
    assert lessons[0].accepted is True
    assert lessons[0].evidence_ref.startswith("sha256:")


def test_final_verifier_blockers_are_durable_but_not_prompt_lessons(
    config: AutoresearchConfig,
) -> None:
    runner = PipelineRunner(config)
    runner.run(topic="test idea", run_id="verifier-memory", auto_approve=True)

    events = runner.memory_store.read()
    verifier_events = [item for item in events if item.source == "verifier_failure"]
    assert len(verifier_events) == 1
    assert verifier_events[0].accepted is False
    assert verifier_events[0].evidence_ref.startswith("sha256:")
    assert "submission readiness blocked" not in runner.memory_store.render(
        topic="test idea"
    )
