# ML Systems Methodology

## Claim Design

Classify the primary claim as method quality, resource efficiency, mechanism,
system implementation, or reproducibility. Define the population over which it
generalizes. Do not broaden a workload-specific result into a general method
claim.

## Comparison Protocol

Hold data, splits, evaluator, tuning budget, stopping rule, and resource budget
constant. Include the strongest directly comparable method, a simple baseline,
and resource- or parameter-matched controls when relevant. Record deviations.

## Statistical Protocol

Choose the unit of replication and variability source before running. Report
all seeds, an effect size, an interval construction method, and multiplicity
handling when many comparisons support one claim. Prefer paired procedures when
the experimental design is paired. Distinguish statistical from practical
significance.

## Resource Protocol

Record worker type, accelerator and memory, software environment, per-run wall
time and compute estimate, total project compute, and failed/preliminary runs.
For fixed-time studies, treat results as platform-specific unless hardware and
software parity is established.

## Autonomy Controls

Keep the evaluator and raw evidence immutable. Separate agent suggestions from
executed specs. Require registry links for citations and numbers. An automated
reviewer may prioritize revisions but cannot certify correctness or novelty.
