# PROJECT.md — DeerFlow Briefing

## What this project is
Local idea-to-paper autonomous research workflow. A 12-stage pipeline (config → plan →
literature → experiment design → results → paper export) with checkpointing, gates,
evidence graph, and profile-aware quality gates. Currently a disciplined scaffold, not
yet a venue-ready unattended generator.

## How to run
- install: `uv sync --extra dev`
- test: `uv run pytest -q`
- dev: `uv run autoresearch plan --config config.yaml --topic "..."` then `run`, `export`, `verify`
- status: `uv run autoresearch status artifacts/<run_id>`

CLI entry points (see README "Current Local Flow"):
`init | plan | run | status | export | verify | reference-bundle | capabilities | audit-completion | approve | resume | reject | recover | cancel`

## Off-limits / safety
- `program.md` is the immutable research charter — never modify it.
- `artifacts/<run_id>/` are run outputs; do not edit in place. Read and analyze, don't rewrite.
- `decisions.jsonl` and `checkpoint_events.jsonl` are append-only — never delete entries.
- Do not fabricate evidence, metrics, or citations. `program.md` rule: generated prose is not
  evidence. Preserve null/negative/failed/invalid/rejected results as-is.
- `.venv/`, `.pytest_cache/`, `.worktrees/`, `.omx/`, `.superpowers/` — do not touch.
- Gate discipline: without `--auto-approve`, the runner pauses at each gate. Use
  `approve`/`reject`/`resume`, don't force the pipeline past a gate.

## What DeerFlow should help with
- Extending the pipeline / stages / paper modules (write code + tests).
- Augmenting execution: run the experiment stage's generated code inside DeerFlow's
  sandbox and feed real metrics back into the experiments ledger.
- Broadening literature retrieval with live web search beyond arXiv/OpenAlex/Crossref.
- Producing evidence-linked paper exports and audit bundles.

## See also
- `README.md` — full current flow and CLI reference
- `docs/plans/` — the build plan this project follows
- `docs/specs/multidomain-top-venue-autoresearch.md` — normative target and completion matrix
