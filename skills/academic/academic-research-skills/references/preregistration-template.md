# Preregistration Template

A bounded-claim spec the human approves BEFORE any experiment runs. Filled by
Academic-Research-Skills from the user's idea, reviewed by the human, then frozen.

## Fields (all required before the experiment runs)

- **Research question**: one falsifiable question, scoped to one experiment.
  (Not "understand X". "Does X's Q-error degrade by >2x under shift Y on dataset Z".)
- **Primary claim (bounded)**: the precise claim, with primary metric + direction + scope.
  ("Estimator X's geomean Q-error under shift Y degrades by factor >2 vs in-distribution, on dataset Z.")
- **Falsifier**: the cheapest experiment that would disconfirm the claim.
  ("If degradation ratio < 1.5 across 3 seeds, claim is falsified.")
- **Success criterion**: the numeric threshold the primary metric must cross to support the claim.
- **Primary metric + definition**: exact name, how computed, direction (minimize/maximize).
- **Baselines**: which, tuned how, on matched resources. (No untuned strawman baselines.)
- **Datasets/splits**: exact identity + version + split + how frozen. (No train/test leakage.)
- **Seeds**: how many, how reported (mean ± std, or CIs).
- **Compute/resource budget**: realistic estimate (laptop / GPU / cluster).
- **Stopping rule**: when do trials stop (fixed N? improvement plateau? budget exhausted?).
- **Hypotheses (competing)**: H1 (the claim), H2 (the null/alternative). Both falsifiable.
- **What will be preserved**: null, negative, failed, invalid results — reported as-is, not omitted.

## Anti-patterns (reject the preregistration if present)

- Vague question ("understand", "explore", "investigate" without a metric)
- Untuned baseline (strawman to beat)
- No falsifier (unfalsifiable claim)
- No success criterion (can't tell if it worked)
- Compute budget unstated (implies laptop when it needs a cluster)
- Single seed (no variance estimate)
- Primary metric undefined or swapped mid-experiment

## Human approval

The preregistration is FROZEN on human approval. After the experiment runs, the
results are reported against this frozen spec — no post-hoc metric change, no
post-hoc baseline swap, no post-hoc seed addition. Deviations are disclosed, not hidden.
