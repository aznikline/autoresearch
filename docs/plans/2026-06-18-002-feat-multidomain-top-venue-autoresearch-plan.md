---
title: "feat: Build multidomain top-venue autoresearch"
type: feat
status: active
date: 2026-06-18
origin: docs/specs/multidomain-top-venue-autoresearch.md
---

# feat: Build multidomain top-venue autoresearch

## Problem Frame

The current repository completes a deterministic ML-systems scaffold, not a
real multidomain idea-to-paper workflow. The implementation must satisfy the
normative contract in `docs/specs/multidomain-top-venue-autoresearch.md` without
turning phase completion or synthetic runs into a broad readiness claim.

This plan is executed under one persistent goal. Units and phases are progress
boundaries, not goal-completion boundaries.

## Requirements Trace

- Contract and routing: MD-001, MD-002, MD-003, MD-012, MD-014
- Real external integrations: MD-004, MD-005
- Data and evidence integrity: MD-006, MD-007, MD-008, MD-011
- Venue paper bundles: MD-009, MD-014
- Operability and continuity: MD-010, MD-015
- Real reference audits: MD-013

## Key Decisions

- Use one shared stage/state engine with domain plugins and venue contracts.
- Keep domain methodology separate from annual venue formatting/policy.
- Make provider and scholarly source interfaces recordable and replayable.
- Treat fake adapters as synthetic test infrastructure that cannot advance a
  run beyond `contract_supported`.
- Preserve the existing ML-systems profile as the first migrated plugin.
- Add no provider SDK initially; use standard-library HTTP behind narrow
  adapters, then justify SDK dependencies only when required.
- Fail closed on unknown licenses, stale venue contracts, incompatible routing,
  missing real integrations, and unsupported evidence.
- Require a repository-auditable material manifest for every verified venue;
  URL-only hashes or generic templates cannot satisfy MD-002 or MD-009.
- Require `experiment.workspace_source` for real evidence mode, copy and hash
  that workspace into the run, and require `top_venue` depth for MD-013 export.
- Derive quantitative readiness counts from successful raw metrics outputs;
  plan-declared seeds, units, uncertainty, effects, or compute do not count.

## Phase 1: Contract Foundation

### Unit 1: Add strict domain and venue schemas

**Goal:** Establish the machine-readable registry and capability vocabulary.

**Requirements:** MD-001, MD-002, MD-003, MD-012

**Files:**
- Create: `src/autoresearch/domains/schema.py`
- Create: `src/autoresearch/venues/schema.py`
- Create: `src/autoresearch/venues/registry.py`
- Create: `src/autoresearch/capabilities.py`
- Create: `src/autoresearch/venues/<venue-id>/<year>/<track>.yaml`
- Test: `tests/test_domain_registry.py`
- Test: `tests/test_venue_registry.py`
- Test: `tests/test_capabilities.py`

**Approach:** Define strict parsers, source freshness, compatibility, and
fail-closed errors. Migrate the existing profile parser without silently
accepting legacy omissions.

**Test scenarios:**
- Load every registered profile and compatible venue contract.
- Reject unknown fields, duplicate IDs, stale/draft contracts, missing official
  sources, incompatible profile/venue pairs, and path traversal.
- Prove pipeline completion cannot imply `evidence_complete` or
  `submission_ready`.

**Verification:** Registry inventory exactly matches the spec matrix and every
record has a current schema version.

### Unit 2: Add all domain profiles and skills

**Goal:** Encode methodology for LLM, CV, NLP, data, and ML systems.

**Requirements:** MD-001, MD-007

**Files:**
- Create: `src/autoresearch/profiles/foundation-models-llm.yaml`
- Create: `src/autoresearch/profiles/computer-vision.yaml`
- Create: `src/autoresearch/profiles/natural-language-processing.yaml`
- Create: `src/autoresearch/profiles/data-management-mining.yaml`
- Modify: `src/autoresearch/profiles/ml-systems-efficiency.yaml`
- Create: `skills/autoresearch-{profile-id}/...`
- Test: `tests/test_profile_matrix.py`
- Test: `tests/test_skill_matrix.py`

**Approach:** Reuse the stage-aware skill harness while extending profile
requirements to data/model governance, domain evidence, and experiment plugins.

**Test scenarios:**
- Deterministic profile/skill selection for every stage and depth.
- No cross-domain fallback when a compatible skill is missing.
- Domain-specific guidance appears only in applicable stages.

**Verification:** Each profile has one compatible skill, rubric, reference
fixture, and plugin ID.

## Phase 2: Real Inputs And Reasoning

### Unit 3: Implement provider and prompt adapters

**Goal:** Replace placeholder reasoning with auditable real model calls.

**Requirements:** MD-004, MD-011, MD-012

**Files:**
- Create: `src/autoresearch/adapters/llm/base.py`
- Create: `src/autoresearch/adapters/llm/openai_compatible.py`
- Create: `src/autoresearch/adapters/llm/agent_cli.py`
- Create: `src/autoresearch/prompts/manager.py`
- Create: `prompts/stages.yaml`
- Create: `program.md`
- Test: `tests/adapters/test_llm_contract.py`
- Test: `tests/adapters/test_llm_record_replay.py`
- Test: `tests/test_prompt_manager.py`

**Approach:** Use typed request/response records, schema validation, bounded
repair, budgets, idempotency, redaction, and replay fixtures. Mark fake/replay
runs synthetic unless backed by a recorded real integration attestation.

**Test scenarios:**
- Structured success, malformed JSON repair, retryable/terminal HTTP errors,
  cancellation, budget exhaustion, secret redaction, and request replay.
- Prompt precedence is deterministic and external text cannot override policy.
- Credentialed smoke test records provider/model/request identity.

**Verification:** At least one real provider path passes a credentialed smoke
test without secrets in artifacts.

### Unit 4: Implement live scholarly retrieval

**Goal:** Produce claim-scoped literature evidence from multiple real sources.

**Requirements:** MD-005, MD-008

**Files:**
- Create: `src/autoresearch/adapters/literature/base.py`
- Create: `src/autoresearch/adapters/literature/arxiv.py`
- Create: `src/autoresearch/adapters/literature/openalex.py`
- Create: `src/autoresearch/adapters/literature/crossref.py`
- Modify: `src/autoresearch/literature/search.py`
- Modify: `src/autoresearch/literature/screening.py`
- Test: `tests/adapters/test_literature_contract.py`
- Test: `tests/test_literature_saturation.py`
- Test: `tests/test_literature_provenance.py`

**Approach:** Normalize source records, cache raw responses, retain failures and
rejections, expand claim queries, traverse citation neighborhoods where
available, and block novelty claims on degraded or unsaturated retrieval. A
run records both consecutive-round patience and an explicit maximum marginal
new-candidate ratio; the zero-new default remains strict unless the operator
declares a bounded ratio in the run config.

**Test scenarios:**
- Pagination, rate limits, partial outage, deduplication conflicts, missing
  abstracts, unlicensed full text, contradictory papers, and stale cache.
- Recorded and credentialed live queries preserve exact provenance.

**Verification:** arXiv plus two independent metadata sources pass recorded
contract tests and live smoke checks.

## Phase 3: Domain Evidence Engines

### Unit 5: Add data/model governance and evidence graph

**Goal:** Make every generated claim traceable to lawful, immutable evidence.

**Requirements:** MD-006, MD-008, MD-011

**Files:**
- Create: `src/autoresearch/evidence/graph.py`
- Create: `src/autoresearch/evidence/registry.py`
- Create: `src/autoresearch/governance/assets.py`
- Create: `src/autoresearch/governance/policy.py`
- Modify: `src/autoresearch/paper/claims.py`
- Modify: `src/autoresearch/paper/citations.py`
- Test: `tests/test_evidence_graph.py`
- Test: `tests/test_asset_governance.py`
- Test: `tests/test_evidence_adversarial.py`

**Approach:** Use content-addressed nodes and typed edges for literature,
datasets, models, runs, metrics, claims, tables, and figures. Unknown rights,
privacy, hashes, or source edges block downstream promotion.

**Test scenarios:**
- Fabricated citation/number/table/figure, broken hash, unknown license, PII,
  contaminated split, orphan claim, and cyclic/ambiguous provenance.

**Verification:** Every exportable claim and visual has a complete path to
source artifacts; negative fixtures fail closed.

### Unit 6: Implement domain experiment plugins

**Goal:** Replace the toy experiment with domain-valid reference engines.

**Requirements:** MD-007, MD-013

**Files:**
- Create: `src/autoresearch/experiments/plugins/base.py`
- Create: `src/autoresearch/experiments/plugins/{llm,cv,nlp,data,mlsystems}.py`
- Create: `tests/fixtures/projects/{llm,cv,nlp,data,mlsystems}/...`
- Test: `tests/experiments/test_plugin_contract.py`
- Test: `tests/experiments/test_domain_plugins.py`
- Test: `tests/experiments/test_protocol_parity.py`

**Approach:** Plugins validate specs and evidence requirements but reuse shared
execution, ledger, statistics, and governance services. A real workspace owns
its complete frozen `experiment_plan.yaml`; the pipeline validates its
execution fields and preserves the full domain protocol. Real assets are bound
to local non-symlink files by SHA-256. Synthetic fixtures remain CI-only and
cannot satisfy MD-013.

**Test scenarios:**
- All global and section 8 domain requirements, plus leakage, evaluator
  mutation, judge bias, cache/warm-up errors, missing uncertainty, invalid
  exclusions, and resource mismatch.

**Verification:** Each profile’s reference fixture produces a valid evidence
graph and expected domain-specific failures.

## Phase 4: Venue Papers And Durable Operation

### Unit 7: Add venue templates, checklists, and exports

**Goal:** Produce exact venue-year bundles without weakening science checks.

**Requirements:** MD-002, MD-009, MD-014

**Files:**
- Create: `src/autoresearch/templates/<venue-id>/<year>/...`
- Create: `src/autoresearch/paper/venue.py`
- Modify: `src/autoresearch/paper/export.py`
- Modify: `src/autoresearch/paper/quality.py`
- Test: `tests/paper/test_venue_matrix.py`
- Test: `tests/paper/test_template_rendering.py`
- Test: `tests/paper/test_readiness_composition.py`

**Approach:** Render from venue contracts, compile where tooling is available,
and compose global + domain + venue checks. Preserve source URL/hash and block
stale contracts or generic templates.

**Test scenarios:**
- Every venue template/track; page/anonymity/checklist failures; stale source;
  missing ethics or disclosure; compatible and incompatible profiles.

**Verification:** Every registered venue contract passes its render fixture and
negative policy controls.

### Unit 8: Finish orchestration, recovery, and memory

**Goal:** Make long, expensive runs safely resumable and learn from outcomes.

**Requirements:** MD-010, MD-011, MD-015

**Files:**
- Create: `src/autoresearch/hitl/policy.py`
- Create: `src/autoresearch/hitl/smart_pause.py`
- Create: `src/autoresearch/memory/store.py`
- Create: `src/autoresearch/memory/lessons.py`
- Modify: `src/autoresearch/pipeline/runner.py`
- Modify: `src/autoresearch/pipeline/checkpoint.py`
- Modify: `src/autoresearch/cli.py`
- Test: `tests/test_crash_recovery.py`
- Test: `tests/test_hitl_policy.py`
- Test: `tests/test_memory_store.py`
- Test: `tests/e2e/test_operator_workflow.py`

**Approach:** Add atomic stage attempts, running-stage recovery, idempotency,
actor-bound approvals, preserved rollback history, budget pauses, and
provenance-linked lessons. Expose `plan` and `verify` commands.

**Test scenarios:**
- Kill/restart every stage boundary, repeated resume, stale approval, wrong
  actor/run/config, rejected rollback, timeout, cancellation, corrupted state,
  budget exhaustion, and lesson retrieval isolation.

**Verification:** A clean-process E2E survives forced interruption and exports
the same evidence hashes as an uninterrupted run.

## Phase 5: Full-Matrix Acceptance

### Unit 9: Build the completion auditor and reference runs

**Goal:** Prove the total spec rather than infer completion from green subsets.

**Requirements:** MD-001 through MD-015

**Files:**
- Create: `src/autoresearch/audit/completion.py`
- Create: `docs/architecture.md`
- Create: `docs/runbook.md`
- Create: `docs/first-paper-playbooks/{llm,cv,nlp,data}.md`
- Create: `docs/audits/multidomain-completion.json`
- Test: `tests/test_completion_audit.py`
- Test: `tests/e2e/test_profile_venue_matrix.py`
- Test: `tests/e2e/test_real_reference_bundles.py`

**Approach:** Generate the requirement-to-artifact matrix from registry and test
evidence. The auditor treats missing, stale, synthetic, indirect, or
credentialless evidence as incomplete.

**Test scenarios:**
- Every matrix cell, every MD requirement, missing evidence, stale evidence,
  synthetic substitution, partial domain success, and false readiness claims.

**Verification:** The generated audit proves every completion-gate item in
section 14 of the spec and all clean-environment documentation exercises pass.

## Dependencies And Risks

- Official annual venue pages and templates may not yet exist; such contracts
  remain `draft` and block completion rather than using guessed rules.
- Real provider and scholarly smoke tests require credentials/network. Recorded
  fixtures support deterministic development but cannot satisfy the final live
  integration gate alone.
- Four real reference runs require domain assets and compute. Budgets must be
  explicitly approved; tiny CI fixtures cannot substitute for real evidence.
- Some dataset/model licenses forbid redistribution. Store metadata and hashes,
  not restricted assets.
- Conference and template licenses must be checked before vendoring; otherwise
  store verified retrieval instructions and integrity hashes.

## Goal Completion Rule

Do not mark the active goal complete after any phase, profile, provider, venue,
test subset, or synthetic E2E. Completion requires the full section 15 audit in
`docs/specs/multidomain-top-venue-autoresearch.md` and no unresolved blocker.
