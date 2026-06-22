# Multidomain Top-Venue Autoresearch Spec

Created: 2026-06-18
Status: normative product and completion contract
Supersedes: single-profile completion claims

## 1. Product Claim

`autoresearch` turns a research idea into an **auditable paper candidate** for a
registered domain and venue contract. It never guarantees novelty, scientific
correctness, acceptance, or submission readiness. Pipeline completion means
only that the workflow reached its terminal stage. `submission_ready=true` is
a separate evidence-backed verdict that must satisfy the selected domain
profile, venue-year contract, and global invariants.

The product MUST distinguish these capability levels:

1. `unsupported`: no compatible domain profile or current venue contract.
2. `contract_supported`: routing, templates, checks, and offline tests exist.
3. `integration_validated`: real provider, scholarly retrieval, and execution
   adapters have passed credentialed smoke tests for the profile.
4. `evidence_complete`: the specific project has all required structured
   evidence; this is not inferred from prose.
5. `submission_ready`: evidence is complete and all current venue checks pass.

No UI, CLI output, README, or report may shorten these levels to a generic
`done` or imply that `contract_supported` means a paper can be submitted.

## 2. Scope And Non-Goals

### 2.1 V1 supported research families

V1 MUST ship the following independently selectable profiles:

| Profile ID | Scope | Initial venue contracts |
| --- | --- | --- |
| `foundation-models-llm` | pretraining, post-training, evaluation, reasoning, alignment, retrieval, agents | NeurIPS, ICML, ICLR, COLM, ACL, EMNLP |
| `computer-vision` | recognition, generation, multimodal vision, video, 3D, embodied perception | CVPR, ICCV, ECCV, NeurIPS, ICML, ICLR |
| `natural-language-processing` | modeling, generation, multilingual NLP, information extraction, dialogue, evaluation | ACL, EMNLP, NAACL, COLING, NeurIPS, ICML, ICLR |
| `data-management-mining` | database systems, query processing, data management, data mining, graph/web data | SIGMOD, VLDB, ICDE, KDD, The Web Conference |
| `ml-systems-efficiency` | training/inference systems, optimizers, compression, fixed-resource evaluation | MLSys, NeurIPS, ICML, ICLR |

The exact V1 venue registry IDs are `neurips`, `icml`, `iclr`, `colm`, `acl`,
`emnlp`, `naacl`, `coling`, `cvpr`, `iccv`, `eccv`, `sigmod`, `vldb`, `icde`,
`kdd`, `thewebconf`, and `mlsys`. The initial scope is empirical computational
research in each venue's main/research track. Theory-only, demo, dataset,
industry, journal, findings, workshop, challenge, and special tracks require
their own explicit contracts even when they share a venue brand.

A project selects exactly one primary profile and may select secondary profiles
for cross-domain claims such as vision-language models or LLM-based data
systems. The effective evidence policy is the union of all selected profile
requirements; conflicts and incompatible venue routing fail closed. Secondary
profiles may add requirements but may never remove primary-profile checks.

“All top venues” means all venue IDs explicitly present in the versioned
registry above. It does not mean every workshop, journal, future conference, or
community using the phrase “top venue.” An unknown venue MUST fail closed with
an actionable “register and verify a venue contract” error.

### 2.2 Explicit exclusions

V1 does not certify pure mathematics, theorem-only work, clinical research,
human-subject studies requiring institutional approval, wet-lab experiments,
hardware fabrication, or research that cannot be executed and audited in the
configured environment. A profile may describe such work only after dedicated
ethics, safety, and evidence contracts exist.

## 3. Authoritative Source Policy

Venue rules change yearly. Every venue contract MUST be derived from official
conference, society, proceedings, or submission-system sources and record:

- venue ID, year, track, and contract schema version;
- official source URLs and retrieval timestamps;
- repository-auditable snapshots of every official source used for the contract;
- a strict material manifest binding each source URL and exact template path to
  its content hash;
- paper format/template identity and page-count rules;
- anonymity, dual-submission, supplementary-material, and author-response rules;
- mandatory checklists, impact/ethics statements, limitations, and disclosure;
- artifact, code, data, model, and reproducibility requirements;
- submission system and deadline timezone where relevant;
- verification status: `draft`, `verified`, `stale`, or `retired`.

A publish-targeted run MUST refuse `submission_ready=true` when the selected
contract is `draft`, `stale`, `retired`, lacks an official source, or targets a
different year/track. Rules are refreshed at run start when network access is
available; otherwise the run records degraded verification and remains blocked.

For each venue ID, `latest_verified` resolves to the newest officially
announced submission cycle whose contract has been reviewed and hashed. If a
newer cycle is announced but unverified, the older contract may reproduce an
older paper bundle but cannot claim readiness for the newer submission. This
resolution and its source timestamps are persisted in the alignment manifest.

Stable primary-source anchors include the NeurIPS paper checklist, official
ICML/ICLR author instructions, CVF conference author guidelines, ACL Rolling
Review and conference calls, ACM SIGMOD/KDD/Web Conference calls, VLDB
submission guidelines, IEEE ICDE calls, and MLSys calls. Annual URLs are data,
not hard-coded application logic.

## 4. Contract Architecture

### 4.1 Domain profile

Every profile MUST declare and validate:

- compatible venue IDs and paper tracks;
- accepted research paradigms and disallowed paradigms;
- claim types and the evidence types that may support them;
- strong, simple, matched, and diagnostic baseline policies;
- evaluation units, primary/secondary metrics, and failure metrics;
- statistical design, uncertainty, power/variance, and multiplicity policy;
- compute, latency, energy, memory, cost, and failed-run accounting policy;
- dataset/model licenses, privacy, contamination, and governance checks;
- stage-specific methodology and writing guidance;
- profile-specific quality checks and non-waivable invariants;
- a compatible project skill and progressive reference set.

Whenever this spec says “as applicable” or “where relevant,” the selected
profile/venue contract MUST resolve the item to `required`, `not_required`, or
`blocked_unknown`. `not_required` needs a machine-readable rationale linked to
the affected claim; `blocked_unknown` prevents readiness. Omission is never
interpreted as false or not required.

### 4.2 Venue contract

Every venue-year-track contract MUST be machine-readable and composable with a
domain profile. Venue contracts control format and venue policy, not scientific
truth. They MUST NOT weaken global or domain evidence requirements.

### 4.3 Alignment manifest

Before any paid call or experiment, the CLI MUST show and persist:

- topic, scoped research question, domain profile, venue/year/track, and depth;
- primary claim type and expected contribution type;
- selected provider/model IDs and scholarly sources;
- data/model inputs and their license/privacy status;
- compute, money, wall-clock, storage, and API-call budgets;
- execution backend and available hardware/environment;
- all proposed waivers and their alternative tests;
- hashes of the domain profile, venue contract, prompts, config, and evaluator;
- capability level and every reason it cannot advance to the next level.

Changing domain, venue year/track, primary metric, confirmatory hypothesis,
evaluator, or non-exploratory data split invalidates prior approval and requires
a new alignment gate.

## 5. Real Provider And Prompt Contract

Publish-targeted runs MUST use a real configured provider. Deterministic fake
providers are allowed only for tests and demos and MUST permanently mark the run
`synthetic=true`, which blocks `evidence_complete` and `submission_ready`.

The provider interface MUST support:

- structured request/response schemas with validation and repair limits;
- model/provider/version identity, sampling parameters, and request IDs;
- token, latency, and cost accounting per stage and for the full run;
- retries with bounded backoff and typed terminal errors;
- redacted request/response persistence for audit and replay;
- explicit tool permissions and local agent CLI adapters;
- cancellation, budget exhaustion, and resumable idempotency keys;
- prompt composition from global policy, domain profile, venue contract,
  project `program.md`, stage template, retrieved evidence, and prior lessons;
- prompt and response hashes linked to generated artifacts.

Generated text is never evidence. A model may propose a claim, citation,
experiment, or number, but registries and verifiers decide whether it survives.

## 6. Scholarly Retrieval And Novelty Contract

The literature subsystem MUST provide real adapters for at least arXiv plus two
independent scholarly metadata/index sources such as OpenAlex, Crossref, or
Semantic Scholar. It MUST:

- persist normalized raw responses, query strings, dates, pagination, source
  status, rate-limit events, and provenance;
- deduplicate by stable IDs and conservative title/author/year matching;
- distinguish metadata, abstract, full text, and model-generated summaries;
- respect access rights and never store or redistribute unlicensed full text;
- perform claim-scoped search over synonyms, cited/citing work, nearest methods,
  contradictory results, surveys, and venue-specific recent work;
- record screened-out papers and reasons, not only accepted papers;
- produce literature-gap records with nearest work and unresolved uncertainty;
- quantify a local saturation rule, including the consecutive-round patience
  and maximum marginal-new-candidate ratio, and record why search stopped;
- block novelty wording when retrieval is degraded, stale, seed-only, or below
  the selected profile’s saturation threshold.

## 7. Data, Model, And Ethics Contract

Every external dataset, model, benchmark, annotation, and API MUST have a
registry record containing identity/version, source, license/terms, checksum,
download date, intended use, privacy/PII status, known restrictions, and split
provenance. Real evidence MUST bind each registry record to the actual local
file and verify that it is a non-symlink file within the registry directory
whose SHA-256 matches the record. The workflow MUST block use when rights,
privacy status, or local-file integrity are unknown.

Runs MUST detect and report test-set leakage, benchmark contamination,
train/test overlap, tuning on held-out data, model-evaluator overlap, and use of
private or sensitive data. Human annotations require protocol, instructions,
consent/compensation status where applicable, demographics/languages when
relevant, inter-annotator analysis, and institutional-review determination.

Ethics, safety, dual-use, environmental, and broader-impact checks are
non-waivable when required by the domain or venue contract.

## 8. Experiment And Evidence Contract

### 8.1 Global invariants

1. Exploratory and confirmatory experiments are labeled and separated.
2. Confirmatory hypotheses, primary metrics, exclusions, splits, evaluator,
   tuning allowance, stopping rule, and resource budget are frozen before run.
3. Every run has immutable IDs, code/config/data/model/evaluator hashes,
   environment and hardware identity, commands, raw stdout/stderr, and outputs.
4. Baselines use protocol parity unless the difference is the studied variable
   and is explicitly disclosed.
5. Failed, null, negative, timed-out, invalid, and excluded runs remain in the
   append-only ledger.
6. Statistical outputs link to run IDs and include assumptions and diagnostics.
7. Every hypothesis ends `supported`, `refuted`, or `inconclusive`.
8. Every paper claim resolves to evidence registry entries; prose cannot create
   citations, facts, measurements, tables, or figures.
9. Seeds, evaluation units, metrics, confidence intervals, effect sizes, and
   compute reporting count only when observed in successful raw trial outputs;
   declarations in an experiment plan are not evidence.

### 8.2 LLM-specific requirements

- exact base model/checkpoint, tokenizer, prompt/template, decoding parameters,
  context policy, tool configuration, and judge model/version;
- contamination and memorization analysis for benchmark claims;
- quality, safety, calibration, latency, throughput, memory, token, and cost
  trade-offs as applicable;
- multiple evaluator forms or documented human validation for model-judge
  claims, with position/order bias controls;
- strong closed/open baselines under matched access and compute assumptions;
- repeated sampling and uncertainty appropriate to stochastic generation.

### 8.3 Computer-vision requirements

- dataset version/split, image/video preprocessing, augmentation, resolution,
  label policy, and evaluation implementation identity;
- pretrained data/model provenance and leakage/duplicate analysis;
- task-standard quality metrics plus calibration, robustness, subgroup, latency,
  throughput, memory, and compute measures as applicable;
- seeds, confidence intervals, sensitivity analysis, ablations, and matched
  training/tuning budgets;
- qualitative examples selected by a declared policy, including failures.

### 8.4 NLP-specific requirements

- dataset/corpus version, language/domain coverage, tokenization, normalization,
  annotation, and evaluation-script identity;
- multilingual and demographic scope aligned with claims;
- automatic metrics complemented by human or task-valid evaluation when their
  known limitations affect the claim;
- significance/uncertainty, seeds, contamination, prompt/model version, and
  error analysis with negative and subgroup outcomes;
- licensing and privacy checks for corpora and generated data.

### 8.5 Data-management/mining requirements

- system/database version, schema, workload/query set, scale factor, indexes,
  optimizer/configuration, hardware/storage, concurrency, and isolation level;
- cold/warm-cache policy, warm-up, repetitions, timeout, failure, and variance;
- latency distributions, throughput, resource use, correctness, and monetary
  cost as applicable, not only mean latency;
- workload representativeness and comparison against tuned strong systems under
  matched hardware/resource budgets;
- data-mining claims additionally require split/time leakage controls, ranking
  or predictive uncertainty, subgroup/error analysis, and reproducible features.

## 9. Paper And Venue Export Contract

The paper generator MUST create an evidence-linked outline before prose. Every
section, table, figure, citation, numeric value, and contribution statement MUST
retain registry links through drafting, review, revision, and export.

The exported bundle MUST contain:

- source manuscript and the exact venue-year template;
- compiled PDF when the required local toolchain is available;
- BibTeX plus citation registry and retrieval provenance;
- figures/tables plus source data and generation commands;
- experiment code/config/specs, environment lock, run ledger, and raw-output
  manifest or durable references when raw artifacts are too large;
- data/model registry, license/privacy report, compute/cost report, and model
  assistance disclosure;
- claim-evidence graph, verification report, quality report, venue checklist,
  limitations/ethics statements, artifact manifest, and reproducibility guide;
- simulated reviews and responses clearly marked as model-generated signals.

Formatting checks MUST include template identity, page limits, anonymity,
forbidden metadata, bibliography/supplement policy, required sections, and file
presence. A generic LaTeX article MUST never pass a venue export contract.

## 10. Orchestration, HITL, Recovery, And Memory

The pipeline remains inspectable and stage-contract based. It MUST support:

- `init`, `plan`, `run`, `status`, `approve`, `reject`, `resume`, `verify`, and
  `export` with equivalent Python APIs;
- mandatory gates for alignment, literature scope/saturation, hypotheses,
  confirmatory experiment design, pivot/proceed decisions, evidence freeze,
  paper claims, and final venue readiness;
- append-only decisions with actor, reason, artifact/profile/contract hashes,
  timestamps, and one-time consumption;
- atomic checkpoints, interruption recovery from running stages, idempotent
  retries, rollback without destroying prior evidence, and config identity;
- per-stage budget and failure policy, cancellation, and actionable errors;
- durable lessons from failed runs, rejected gates, verifier failures, and
  accepted prompt/process improvements, with provenance and topic matching.

Approval never certifies truth; it authorizes the next transition. Rejection and
rollback never delete the rejected artifact or its decision history.

## 11. Security And Operational Contract

- Secrets are referenced by environment-variable name or credential provider
  and never persisted in prompts, artifacts, logs, or manifests.
- Generated code executes in an explicit sandbox policy. “Local subprocess” is
  not described as isolation. Publish-targeted untrusted code requires a
  container or equivalent boundary with filesystem/network/resource controls.
- External content is untrusted data and cannot override system/project policy.
- Provider, retrieval, compute, and storage budgets are enforced before and
  during work; overruns pause rather than silently continue.
- Artifact writes are atomic where state corruption would prevent recovery.
- Large artifacts use content-addressed references with integrity checks.

## 12. Machine-Readable Registry Layout

The normative implementation layout is:

```text
src/autoresearch/profiles/<profile-id>.yaml
src/autoresearch/venues/<venue-id>/<year>/<track>.yaml
skills/autoresearch-<profile-id>/...
src/autoresearch/adapters/{llm,literature,execution}/...
src/autoresearch/evidence/...
src/autoresearch/templates/<venue-id>/<year>/...
tests/fixtures/venues/...
tests/e2e/...
```

Schemas MUST reject unknown fields, missing requirements, duplicate IDs,
incompatible profile/venue pairs, stale contracts, missing official sources,
missing skills/templates, and references escaping their registry directory.

## 13. Requirement IDs And Acceptance Evidence

| ID | Requirement | Completion evidence |
| --- | --- | --- |
| MD-001 | Five domain profiles load and validate | schema tests plus registry inventory |
| MD-002 | All listed venue-year-track contracts are versioned and verified | contract fixtures, official-source metadata, stale-contract tests |
| MD-003 | Unknown/incompatible venues fail closed | CLI and selector error-path tests |
| MD-004 | Real provider path is auditable and budgeted | recorded integration tests and credentialed smoke evidence |
| MD-005 | Multi-source live literature path preserves provenance and degradation | adapter contract tests, recorded responses, live smoke evidence |
| MD-006 | Data/model/license/privacy registries block unknown status | registry and policy tests |
| MD-007 | Domain experiment plugins enforce sections 8.2-8.5 | one reference project and adversarial fixture per profile |
| MD-008 | Claim-evidence graph covers prose, numbers, citations, tables, figures | graph integrity and fabricated-evidence tests |
| MD-009 | Venue export uses exact versioned template and policy checks | render/compile fixtures for every registered venue contract |
| MD-010 | HITL, crash recovery, idempotency, rollback, and memory are durable | interruption and restart E2E tests |
| MD-011 | Security and budget controls fail closed | secret-leak, path/network, resource, prompt-injection tests |
| MD-012 | Capability levels cannot be conflated | CLI/report/README snapshot tests |
| MD-013 | Four representative real-domain runs reach `evidence_complete` only from real artifacts | LLM, CV, NLP, and data reference-run audit bundles |
| MD-014 | `submission_ready` requires global, domain, and venue checks | full matrix gate tests and negative controls |
| MD-015 | Operator documentation reproduces both auto and HITL paths | clean-environment runbook E2E |

## 14. Spec Change Control

The completion auditor pins the SHA-256 of this spec and the implementation
plan. Any change to supported profiles, venue IDs, capability semantics,
requirement IDs, or the completion gate MUST update the spec first, record the
rationale and migration impact in the plan, and invalidate prior completion
audits. Requirements may be strengthened during the active goal. They may not
be removed, reworded to fit existing code, or reclassified as optional merely
to obtain a passing audit.

## 15. Full-Matrix Completion Gate

This persistent goal is complete only when all of the following are true:

1. MD-001 through MD-015 each have direct, current evidence and no waiver.
2. Every supported profile has a compatible skill, experiment plugin, quality
   rubric, reference fixture, and at least one integration-validated path.
3. Every registered venue contract has official-source metadata, exact template
   identity, formatting/checklist tests, and stale-contract handling.
4. Offline tests pass across every compatible profile/venue pair and reject all
   incompatible pairs.
5. Recorded integration tests pass for each provider/retrieval/execution adapter.
6. An authenticated remote-provider smoke or digest-attested local-model smoke
   exists for the real provider, and live official-source smoke evidence exists
   for scholarly sources; missing provider identity remains an unresolved
   completion blocker.
7. Four domain reference runs produce auditable bundles; synthetic fixtures are
   not accepted as real-run evidence.
8. Adversarial tests prove unsupported citations/numbers, leakage, evaluator
   mutation, stale venue rules, unknown licenses, prompt injection, secret
   leakage, budget overruns, interrupted stages, and fabricated readiness fail.
9. README, architecture, runbook, first-paper playbooks, and CLI help match.
10. A final audit maps every requirement and matrix cell to artifacts and test
    output. Passing a phase, a subset of tests, or one domain cannot complete the
    goal.

## 16. Current-State Audit

As of 2026-06-20 the repository audit passes 12 of 15 requirements. It has all
five strict profiles, an auditable OpenAI-compatible provider with a
digest-attested local-model smoke, live arXiv/OpenAlex/Crossref evidence,
domain protocol validators, content-addressed claim evidence, asset governance,
durable HITL/recovery/memory checks, security controls, and clean-process
operator tests. Thirteen venue contracts (NeurIPS, ICML, ICLR, COLM, ACL,
EMNLP, CVPR, ECCV, PVLDB, ICDE, KDD, The Web Conference, and MLSys 2026)
have repository-auditable official snapshots and exact template bundles; four
remain drafts. Real experiment mode now requires and executes a copied,
content-hashed operator workspace with its own frozen `experiment_plan.yaml`
rather than the toy generator, and reference bundles require `top_venue`
depth. The Data and Database reference run is exported from live
OpenAlex/Crossref retrieval and eight real SQLite trials with a locally
hash-bound CC BY 4.0 UCI dataset; it is `evidence_complete` but correctly
remains `submission_ready=false` until its venue template is materialized.
MD-002, MD-009, and MD-013 remain blocked because the complete 17-venue matrix
is not verified and the LLM, CV, and NLP real reference bundles are still
missing. The default run remains a
deterministic scaffold with seed literature and toy local experiments.
Therefore it MUST NOT claim multidomain direct output or submission readiness.
