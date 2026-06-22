from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
import statistics
import time
from pathlib import Path


TRIALS = {
    "baseline-seed0": (0, "none"),
    "baseline-seed1": (1, "none"),
    "baseline-seed2": (2, "none"),
    "baseline-seed3": (3, "none"),
    "ablation-hour-index-seed1": (1, "hour"),
    "ablation-weather-index-seed2": (2, "weather"),
    "ablation-season-index-seed3": (3, "season"),
    "ablation-composite-index-seed4": (4, "composite"),
}
INDEXES = {
    "none": (),
    "hour": ("CREATE INDEX idx_rides_hr ON rides(hr)",),
    "weather": ("CREATE INDEX idx_rides_weather_work ON rides(weathersit, workingday)",),
    "season": ("CREATE INDEX idx_rides_season_year ON rides(season, yr)",),
    "composite": (
        "CREATE INDEX idx_rides_hr ON rides(hr)",
        "CREATE INDEX idx_rides_weather_work ON rides(weathersit, workingday)",
        "CREATE INDEX idx_rides_season_year ON rides(season, yr)",
    ),
}
INTEGER_COLUMNS = {
    "instant",
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "casual",
    "registered",
    "cnt",
}
def load_rows(path: Path) -> tuple[list[str], list[tuple[object, ...]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or ())
        rows = [
            tuple(
                int(row[field]) if field in INTEGER_COLUMNS else (
                    row[field] if field == "dteday" else float(row[field])
                )
                for field in fields
            )
            for row in reader
        ]
    return fields, rows


def build_database(
    fields: list[str],
    rows: list[tuple[object, ...]],
    index_mode: str,
    schema: str,
) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute(schema)
    placeholders = ",".join("?" for _ in fields)
    connection.executemany(
        f"INSERT INTO rides ({','.join(fields)}) VALUES ({placeholders})", rows
    )
    for statement in INDEXES[index_mode]:
        connection.execute(statement)
    connection.commit()
    return connection


def execute_workload(
    connection: sqlite3.Connection,
    workload: dict[str, dict[str, object]],
    *,
    seed: int,
    repetitions: int,
) -> tuple[dict[str, list[tuple[object, ...]]], dict[str, list[float]]]:
    names = list(workload)
    results: dict[str, list[tuple[object, ...]]] = {}
    timings = {name: [] for name in names}
    for name in names:
        item = workload[name]
        results[name] = connection.execute(
            str(item["sql"]), tuple(item["parameters"])
        ).fetchall()
    order = names * repetitions
    random.Random(seed).shuffle(order)
    for name in order:
        item = workload[name]
        started = time.perf_counter_ns()
        connection.execute(str(item["sql"]), tuple(item["parameters"])).fetchall()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        timings[name].append(elapsed_ms)
    return results, timings


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True, choices=sorted(TRIALS))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    root = Path(__file__).resolve().parent
    fields, rows = load_rows(root / "data" / "hour.csv")
    workload = json.loads((root / "workload.json").read_text(encoding="utf-8"))
    schema = (root / "schema.sql").read_text(encoding="utf-8")
    seed, index_mode = TRIALS[args.trial]

    baseline = build_database(fields, rows, "none", schema)
    baseline_results, baseline_timings = execute_workload(
        baseline, workload, seed=seed, repetitions=20
    )
    baseline.close()
    candidate = build_database(fields, rows, index_mode, schema)
    candidate_results, candidate_timings = execute_workload(
        candidate, workload, seed=seed, repetitions=20
    )
    candidate.close()

    correctness = sum(
        baseline_results[name] == candidate_results[name] for name in workload
    ) / len(workload)
    baseline_samples = [value for values in baseline_timings.values() for value in values]
    samples = [value for values in candidate_timings.values() for value in values]
    mean_latency = statistics.fmean(samples)
    baseline_mean = statistics.fmean(baseline_samples)
    baseline_std = statistics.stdev(baseline_samples) or 1e-12
    standard_error = statistics.stdev(samples) / math.sqrt(len(samples))
    runtime_sec = time.perf_counter() - started
    output = {
        "primary_metric": percentile(samples, 0.95),
        "p50_latency_ms": percentile(samples, 0.50),
        "p95_latency_ms": percentile(samples, 0.95),
        "p99_latency_ms": percentile(samples, 0.99),
        "throughput_qps": 1000.0 / mean_latency,
        "correctness_rate": correctness,
        "ci_low": mean_latency - 1.96 * standard_error,
        "ci_high": mean_latency + 1.96 * standard_error,
        "effect_size": (baseline_mean - mean_latency) / baseline_std,
        "runtime_sec": runtime_sec,
        "compute_units": float(len(samples) + len(baseline_samples)),
        "seed": seed,
        "evaluation_units": list(workload),
        "trial_id": args.trial,
        "index_mode": index_mode,
        "row_count": len(rows),
        "sqlite_version": sqlite3.sqlite_version,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
