# Operator Runbook

## Prepare

```bash
uv sync --extra dev
uv run autoresearch init --path config.yaml
uv run --extra dev pytest -q
```

Select a compatible `research.profile`, `research.venue_id`, year, and track.
Use `latest_verified` for any readiness-targeted run. It is expected to fail
while the registry has no current verified contract. Configure
`literature.mode: live` and `experiment.evidence_mode: real` for a real
reference run. Set `experiment.workspace_source` to a reviewed directory that
contains `experiment.py` and a complete frozen `experiment_plan.yaml`; list
only required top-level modules in
`experiment.allowed_imports`. The LLM profile also requires a live LLM
provider. Each real asset registry entry must bind `local_path` to a
non-symlink file below the registry directory whose SHA-256 matches the entry.
For live literature, record the bounded marginal-gain rule with
`saturation_patience` and `saturation_max_new_ratio`. Never put credentials in
YAML; set only the configured credential environment variable.

Inspect the side-effect-free plan and capability blockers first:

```bash
uv run autoresearch plan --config config.yaml --topic "Scoped research question"
uv run autoresearch capabilities --config config.yaml
```

## Automatic Artifact Run

```bash
uv run autoresearch run \
  --config config.yaml \
  --topic "Scoped research question" \
  --run-id my-run \
  --auto-approve
```

`--auto-approve` bypasses human pauses; it does not waive quality, governance,
domain, or venue blockers.

## Human-Gated Run

```bash
uv run autoresearch run --config config.yaml --topic "Scoped question"
uv run autoresearch status artifacts/<run_id>
uv run autoresearch approve artifacts/<run_id> \
  --actor reviewer --reason "evidence reviewed"
uv run autoresearch resume artifacts/<run_id> \
  --config config.yaml --actor reviewer
```

Repeat for every gate. Reject with a concrete reason, then resume to the
declared rollback stage:

```bash
uv run autoresearch reject artifacts/<run_id> \
  --actor reviewer --reason "protocol mismatch"
uv run autoresearch resume artifacts/<run_id> \
  --config config.yaml --actor reviewer
```

## Recover Interrupted Work

Use recovery only when the checkpoint status is `running` or `failed`:

```bash
uv run autoresearch recover artifacts/<run_id> --config config.yaml
```

Add `--auto-approve` only if later human gates should also be bypassed. Recovery
requires the original redacted-config fingerprint and re-executes from the
interrupted stage. `checkpoint_events.jsonl` preserves the transition history.

Cancel without requiring the original config to remain available:

```bash
uv run autoresearch cancel artifacts/<run_id> \
  --actor operator --reason "budget revoked"
```

## Verify And Audit

```bash
uv run autoresearch export artifacts/<run_id>
uv run autoresearch verify artifacts/<run_id> --config config.yaml
uv run autoresearch reference-bundle artifacts/<run_id> \
  --config config.yaml --output-root docs/audits/reference-runs
uv run autoresearch audit-completion \
  --root . \
  --output docs/audits/multidomain-completion.json
```

An export may exist with `submission_ready=false`. The completion command must
return zero before claiming the total spec is complete. Inspect every blocker;
do not edit an attestation hash or weaken a requirement to force a pass.
The reference command refuses incomplete, synthetic, tampered, over-budget, or
already-exported runs and copies the complete verified run into its bundle.
