# autoresearch

An **auditable research scaffold**: turn a research idea into a paper candidate where every claim traces to a verified evidence ledger. Not a venue-ready paper generator — it produces an auditable evidence trail + a scaffolded draft a human finishes.

## What this is (honest)

autoresearch is a 12-stage pipeline (idea → literature → experiment → paper → export) built around an **evidence ledger**: every numeric claim in the prose must round-trip to a ledger entry, and the ledger records code_sha256 / config_sha256 / protocol_fingerprint / evaluator_immutable for reproducibility. It is **not** a system that produces venue-ready science unattended — the hardest walls (genuinely novel claim, real data, real compute, peer review) are not LLM capability gaps. What it does give you: a disciplined scaffold where experiments are auditable, claims are verified, and the readiness ladder (`unsupported → contract_supported → integration_validated → evidence_complete → submission_ready`) is honest by design.

## What's here

- **12-stage pipeline**: config → plan → literature (arXiv/OpenAlex/Crossref) → synthesis → hypothesis → experiment design → experiment loop → result analysis → paper draft + prose revision → final verification export. Gates pause for human review; checkpoints are append-only.
- **Evidence ledger** (`experiments/ledger.py`): per-trial primary metric + extra_metrics (multi-metric: degradation_ratio, effect_size, ci_low/high, etc.), code/config SHA, protocol fingerprint, environment.
- **Claim verification** (`paper/claims.py`): rounding-tolerant (5% rel + 0.05 abs) — admits legitimate rounding, rejects fabrication (446.5 → 5.0).
- **Venue registry** (`src/autoresearch/venues/`): 13 verified venue contracts (VLDB/NeurIPS/ICML/ICLR/CoLM/KDD/EMNLP/NAACL/MLSys/ECCV/CVPR/TheWebConf/SIGMOD) with sha256-anchored official sources.
- **5 domain methodology skills** (`skills/autoresearch-*/`): DB / ML-systems / NLP / CV / foundation-models — field-aware experiment rigor.
- **5 academic workflow skills** (`skills/academic/`): paper-reading, research-genealogy, question-validator, academic-paper-skills, academic-research-skills — general academic work outside the pipeline (also published standalone at github.com/aznikline/academic-skills).
- **Best run bundle** (`docs/audits/best-bundle/`): a score-3.95 paper run (Q-error robustness, 40 trials, live literature, claim verification OK) — submission_ready=false by design (3 venue-metadata blockers remain).

## Honest boundaries

This project has been pushed hard against the "produce a submittable paper unattended" goal. The honest conclusion (see `docs/specs/multidomain-top-venue-autoresearch.md` §16):

- **What works**: experiment scaffolding, evidence ledger, multi-metric claim verification, literature retrieval with HTTPException retry, venue contracts, the readiness ladder, the discipline (no novelty-from-model-judgment, preserve null/negative).
- **What does not work (and is not an LLM gap you can prompt around)**: producing genuinely novel claims, acquiring real data + real compute, passing peer review. The prose module scaffolds evidence-linked text; it never authors science.
- **`submission_ready` stays false by design** — the README said so from the start and it stays that way. The system's value is the auditable trail, not the paper.

If you want a submittable paper, use autoresearch as the evidence/audit substrate and do the real research (data, baselines, contribution) with a human in the loop. The `skills/academic/` skills (paper-reading, question-validator, etc.) and open-source PaperSpine (github.com/WUBING2023/PaperSpine) complement it for the reading/writing side.

## Current Local Flow

```bash
uv sync --extra dev
python -m autoresearch init --path config.yaml
uv run autoresearch plan --config config.yaml --topic "Your research idea"
uv run autoresearch run --config config.yaml --topic "Your research idea" --auto-approve
uv run autoresearch status artifacts/<run_id>
uv run autoresearch export artifacts/<run_id>
uv run autoresearch verify artifacts/<run_id> --config config.yaml
uv run autoresearch reference-bundle artifacts/<run_id> --config config.yaml \
  --output-root docs/audits/reference-runs
uv run autoresearch capabilities --config config.yaml
uv run autoresearch audit-completion \
  --root . --output docs/audits/multidomain-completion.json
uv run --extra dev pytest -q
uv run python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/autoresearch-ml-systems
```

Without `--auto-approve`, the runner pauses before each gate so the user can
inspect artifacts and continue explicitly:

```bash
uv run autoresearch run --config config.yaml --topic "Your research idea"
uv run autoresearch status artifacts/<run_id>
uv run autoresearch approve artifacts/<run_id> --actor reviewer --reason "reviewed"
uv run autoresearch resume artifacts/<run_id> --config config.yaml --actor reviewer
uv run autoresearch recover artifacts/<run_id> --config config.yaml
uv run autoresearch cancel artifacts/<run_id> --actor reviewer --reason "budget revoked"
```

Repeat `approve` and `resume` for the literature, experiment design, result
decision, and final export gates. `reject --reason "..."` followed by `resume`
rolls back to the configured earlier stage and pauses again for review. Gate
decisions are appended to `decisions.jsonl`; each decision is consumed once.
Resume rejects a config whose fingerprint differs from the original run.
`recover` is reserved for `running` or `failed` checkpoints and restarts from
the interrupted stage; checkpoint transitions remain append-only in
`checkpoint_events.jsonl`.

The current runner writes structured artifacts for both the bundled seed path
and live arXiv/OpenAlex/Crossref retrieval, plus the local experiment and paper
export paths: candidates, content-addressed raw responses, source request
audit records, screened
shortlist, knowledge cards, experiment workspace, subprocess run metrics,
ledger decisions, a proceed/refine decision, revised paper markdown, BibTeX,
LaTeX, bundle index, citation/numeric-claim verification report, and a
venue-readiness quality report. Artifact integrity can pass while
`submission_ready` remains false; this is intentional because the scientific
content is still a deterministic scaffold, not a venue-ready paper.

`literature.mode: synthetic` is the offline default. For live retrieval, set
`literature.mode: live` and choose one or more of `arxiv`, `openalex`, and
`crossref` in `literature.sources`. Source failures are bounded, recorded, and
reported as degraded while other sources continue. Synthetic or degraded
retrieval fails the `literature_retrieval_integrity` quality requirement and
cannot support a novelty-readiness claim. `literature.saturation_patience` and
`literature.saturation_max_new_ratio` define the consecutive-round marginal
gain rule and are recorded in the search report; the ratio defaults to zero.

`audit-completion` is the only repository-wide completion verdict. It verifies
MD-001 through MD-015 attestations against current artifact hashes and returns
nonzero while any requirement is missing, stale, synthetic, or blocked.
Passing the test suite or finishing a pipeline run does not complete that
audit.

`reference-bundle` is the only supported MD-013 export path. It rejects
synthetic/incomplete runs, requires live literature and
`experiment.evidence_mode: real`, requires a live LLM for the LLM profile,
verifies the source run, enforces the artifact byte budget, and copies the
complete run into a content-hashed portable bundle. It never upgrades a
quality report or overwrites an existing reference bundle.

## Capability Levels

Capability is monotonic and evidence-based: `unsupported`,
`contract_supported`, `integration_validated`, `evidence_complete`, then
`submission_ready`. Each level requires every lower level. A completed pipeline run does not advance the capability level. Artifacts, tests, or compilation
cannot bypass evidence. Use
`uv run autoresearch capabilities --config config.yaml` for the configured
profile/venue verdict and inspect every blocker.

## Security Boundary

`experiment.mode: local` is a subprocess backend, not an isolation boundary.
The separate `experiment.evidence_mode` defaults to `synthetic`; only an
explicit `real` run can qualify for an evidence-complete reference bundle.
Real mode also requires `experiment.workspace_source` with `experiment.py` and
a complete frozen `experiment_plan.yaml`; the directory is copied and hashed
in the run. Every governed real asset must set `local_path`, remain inside its
registry directory, and match its registered SHA-256. Any additional Python modules
must be named in the minimal `experiment.allowed_imports` list. Local execution
remains a trusted generated-code policy. `untrusted` code and
unimplemented `docker`/`ssh`
backends fail before execution. Live LLM endpoints require an explicit host
allowlist and HTTPS except for loopback tests; scholarly adapters accept only
their official hosts or loopback tests. Credentials remain environment
references and are excluded from every run artifact. Provider requests,
retrieval retries, trial time, and artifact storage are bounded; storage
overruns pause the run instead of continuing silently.

Before stage execution, each run writes `alignment.json` and returns the same
summary from the CLI. It records the selected profile, depth, venue family,
primary claim type, time/iteration/compute budget, and proposed threshold
waivers. Configure `research.primary_claim_type`,
`experiment.total_compute_budget`, and `research.threshold_waivers` in
`config.yaml` before a costly run. A waiver must name its affected claim,
rationale, and alternative test.

## Research Alignment

The default is empirical ML systems and efficient training at `top_venue`
depth. It favors fixed-resource comparisons, strong matched baselines,
mechanism and ablation evidence, uncertainty and effect-size reporting, compute
disclosure, and honest null results. See
[`docs/specs/research-alignment.md`](docs/specs/research-alignment.md) for the
source-backed domain decision and depth contract.

The numeric depth floors are project defaults, not requirements imposed by
NeurIPS, ICML, ICLR, or MLSys. Change `research.profile` or `research.depth` in
the config before a run. A different research domain requires a compatible
profile and skill, not only a different venue label.

## Skill Harness

Project skills live under `skills/`. Each skill has standard `SKILL.md` and
`agents/openai.yaml` files plus `harness.yaml` for stage/profile/depth matching,
stage instructions, and progressive reference loading. Every executed stage
writes `skill_context.md` and `skills_applied.json` for auditability.

The final `quality_report.json` records the selected profile and depth and a
required/observed/pass result for every machine-readable depth requirement.
Missing structured evidence blocks readiness even when all pipeline stages and
citation checks complete.

The evidence chain also includes `literature_gaps.json`, competing
`hypotheses.json`, `hypothesis_outcomes.json`, `empirical_claims.json`, enriched
experiment ledger records, and `artifact_manifest.json`. Ledger entries bind
claims to run IDs, metric definitions, experiment/code/config hashes,
environment identity, protocol fingerprints, and raw outputs. The local backend
rejects an experiment that changes its evaluator during execution.

Citation integrity, immutable evaluation, protocol parity, and artifact
provenance cannot be waived. The final quality report lists each requirement,
observed evidence, pass/fail state, and a blocking reason for failures. A
profile override is rejected when enabled project skills do not support that
profile and depth; disabling skills remains explicit and is recorded per stage.

## Target Direction

- Idea intake and problem decomposition
- Literature collection with provenance
- Hypothesis and experiment design gates
- Local sandbox experiment execution
- Fixed-budget edit/run/evaluate loop
- Paper drafting, review, revision, and export
- Citation and numeric claim verification
- Durable run memory

## Install

```bash
git clone https://github.com/aznikline/autoresearch.git
cd autoresearch
uv sync --extra dev
```

Requires Python 3.11+. The `paper-reading` skill (in `skills/academic/`) uses `pymupdf` (already in dependencies).

## Quick start

```bash
uv run autoresearch plan --config reference-projects/qerror-robustness/config.yaml \
  --topic "Q-error robustness of cardinality estimators under distribution shift"
uv run autoresearch run --config reference-projects/qerror-robustness/config.yaml \
  --topic "..." --auto-approve
uv run autoresearch capabilities --config reference-projects/qerror-robustness/config.yaml
```

The `reference-projects/qerror-robustness/` workspace is a worked example: 40 trials (5 seeds × 4 estimators × 2 conditions) on a JOB-Light-style synthetic schema, with multi-metric ledger (degradation_ratio, effect_size, CIs).

## License

MIT — see [LICENSE](LICENSE).
