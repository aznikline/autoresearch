# Data Management Real Reference Project

This project benchmarks SQLite index configurations on the UCI Bike Sharing
hourly dataset. The dataset is public and licensed CC BY 4.0. `assets.yaml`
binds the executed CSV to its source, license, immutable split hash, and local
SHA-256. The experiment plan freezes eight trials, five seeds, three query
units, warmup, repetitions, correctness checks, and resource reporting.

The benchmark is evidence for the pipeline's real-run acceptance path. It is
not a claim that these small local measurements constitute a publishable
database result.
