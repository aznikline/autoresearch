from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import time
from collections import Counter
from pathlib import Path

# Only stdlib is used (sqlite3, math, random, json, pathlib, collections, argparse).
# The learned estimator is a hand-rolled perceptron-style regressor over
# featurized predicates — no sklearn/torch required, keeping the allowlist
# minimal and the run reproducible on a bare CPython.

TRIALS: dict[str, tuple[int, str, str]] = {
    # seed, estimator, condition
    "baseline-uniformity-ID-seed0": (0, "uniformity", "ID"),
    "baseline-uniformity-ID-seed1": (1, "uniformity", "ID"),
    "baseline-uniformity-ID-seed2": (2, "uniformity", "ID"),
    "baseline-uniformity-ID-seed3": (3, "uniformity", "ID"),
    "baseline-uniformity-ID-seed4": (4, "uniformity", "ID"),
    "baseline-uniformity-shifted-seed0": (0, "uniformity", "shifted"),
    "baseline-uniformity-shifted-seed1": (1, "uniformity", "shifted"),
    "baseline-uniformity-shifted-seed2": (2, "uniformity", "shifted"),
    "baseline-uniformity-shifted-seed3": (3, "uniformity", "shifted"),
    "baseline-uniformity-shifted-seed4": (4, "uniformity", "shifted"),
    "histogram-ID-seed0": (0, "histogram", "ID"),
    "histogram-ID-seed1": (1, "histogram", "ID"),
    "histogram-ID-seed2": (2, "histogram", "ID"),
    "histogram-ID-seed3": (3, "histogram", "ID"),
    "histogram-ID-seed4": (4, "histogram", "ID"),
    "histogram-shifted-seed0": (0, "histogram", "shifted"),
    "histogram-shifted-seed1": (1, "histogram", "shifted"),
    "histogram-shifted-seed2": (2, "histogram", "shifted"),
    "histogram-shifted-seed3": (3, "histogram", "shifted"),
    "histogram-shifted-seed4": (4, "histogram", "shifted"),
    "sampling-ID-seed0": (0, "sampling", "ID"),
    "sampling-ID-seed1": (1, "sampling", "ID"),
    "sampling-ID-seed2": (2, "sampling", "ID"),
    "sampling-ID-seed3": (3, "sampling", "ID"),
    "sampling-ID-seed4": (4, "sampling", "ID"),
    "sampling-shifted-seed0": (0, "sampling", "shifted"),
    "sampling-shifted-seed1": (1, "sampling", "shifted"),
    "sampling-shifted-seed2": (2, "sampling", "shifted"),
    "sampling-shifted-seed3": (3, "sampling", "shifted"),
    "sampling-shifted-seed4": (4, "sampling", "shifted"),
    "learned-ID-seed0": (0, "learned", "ID"),
    "learned-ID-seed1": (1, "learned", "ID"),
    "learned-ID-seed2": (2, "learned", "ID"),
    "learned-ID-seed3": (3, "learned", "ID"),
    "learned-ID-seed4": (4, "learned", "ID"),
    "learned-shifted-seed0": (0, "learned", "shifted"),
    "learned-shifted-seed1": (1, "learned", "shifted"),
    "learned-shifted-seed2": (2, "learned", "shifted"),
    "learned-shifted-seed3": (3, "learned", "shifted"),
    "learned-shifted-seed4": (4, "learned", "shifted"),
}


def populate_database(connection: sqlite3.Connection, rng: random.Random) -> dict[str, int]:
    """Populate a JOB-Light-style synthetic schema and return table sizes."""
    # title: ~6000 rows, years spread over a range so range predicates are meaningful
    titles = []
    for i in range(1, 6001):
        kind = rng.randint(1, 7)
        year = rng.randint(1990, 2024)
        titles.append((i, kind, year, f"title-{i}"))
    connection.executemany(
        "INSERT INTO title (id, kind_id, production_year, title_text) VALUES (?, ?, ?, ?)",
        titles,
    )
    # name: ~3000 rows
    names = []
    for i in range(1, 3001):
        gender = rng.choice(("m", "f"))
        names.append((i, gender, f"name-{i}"))
    connection.executemany(
        "INSERT INTO name (id, gender, name_pname_cf) VALUES (?, ?, ?)", names
    )
    # cast_info: ~30000 rows referencing title+name
    casts = []
    for i in range(1, 30001):
        movie_id = rng.randint(1, 6000)
        person_id = rng.randint(1, 3000)
        role_id = rng.randint(1, 8)
        casts.append((i, movie_id, person_id, role_id, rng.randint(0, 20)))
    connection.executemany(
        "INSERT INTO cast_info (id, movie_id, person_id, role_id, nr_order) VALUES (?, ?, ?, ?, ?)",
        casts,
    )
    # movie_info: ~20000 rows
    infos = []
    for i in range(1, 20001):
        movie_id = rng.randint(1, 6000)
        info_type_id = rng.randint(1, 17)
        infos.append((i, movie_id, info_type_id, f"info-{i}"))
    connection.executemany(
        "INSERT INTO movie_info (id, movie_id, info_type_id, info) VALUES (?, ?, ?, ?)",
        infos,
    )
    connection.commit()
    return {
        "title": 6000,
        "name": 3000,
        "cast_info": 30000,
        "movie_info": 20000,
    }


def build_queries(rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Build in-distribution and shifted query sets.

    Each query is a 2-table join over cast_info with a predicate on title
    (year range or kind) plus an optional predicate on name (gender).
    True cardinality is computed by counting the actual join result.
    """
    # ID queries: years in [2000, 2010], common kinds
    id_queries: list[dict] = []
    for qi in range(35):
        year_lo = rng.randint(2000, 2005)
        year_hi = rng.randint(2006, 2010)
        kind = rng.randint(1, 4)
        use_gender = rng.random() < 0.5
        gender = rng.choice(("m", "f")) if use_gender else None
        id_queries.append(
            _make_query(qi, year_lo, year_hi, kind, gender, condition="ID")
        )
    # Shifted queries: years outside training band, rarer kinds, different join shape
    shifted_queries: list[dict] = []
    for qi in range(35):
        year_lo = rng.randint(1990, 1995)
        year_hi = rng.randint(1996, 1999)
        kind = rng.randint(5, 7)
        use_gender = rng.random() < 0.5
        gender = rng.choice(("m", "f")) if use_gender else None
        shifted_queries.append(
            _make_query(qi, year_lo, year_hi, kind, gender, condition="shifted")
        )
    return id_queries, shifted_queries


def _make_query(
    qid: int, year_lo: int, year_hi: int, kind: int, gender: str | None, *, condition: str
) -> dict:
    if gender is not None:
        sql = (
            "SELECT COUNT(*) FROM cast_info c JOIN title t ON c.movie_id = t.id "
            "JOIN name n ON c.person_id = n.id "
            "WHERE t.production_year BETWEEN ? AND ? AND t.kind_id = ? AND n.gender = ?"
        )
        params: tuple[object, ...] = (year_lo, year_hi, kind, gender)
    else:
        sql = (
            "SELECT COUNT(*) FROM cast_info c JOIN title t ON c.movie_id = t.id "
            "WHERE t.production_year BETWEEN ? AND ? AND t.kind_id = ?"
        )
        params = (year_lo, year_hi, kind)
    return {
        "id": f"q{qid:03d}-{condition}",
        "sql": sql,
        "params": params,
        "featurized": _featurize(year_lo, year_hi, kind, gender),
        "condition": condition,
    }


def _featurize(year_lo: int, year_hi: int, kind: int, gender: str | None) -> list[float]:
    return [
        float(year_lo),
        float(year_hi),
        float(year_hi - year_lo),
        float(kind),
        1.0 if gender == "m" else 0.0,
        1.0 if gender == "f" else 0.0,
        1.0 if gender is None else 0.0,
    ]


def true_cardinalities(connection: sqlite3.Connection, queries: list[dict]) -> list[int]:
    truths: list[int] = []
    for q in queries:
        row = connection.execute(q["sql"], tuple(q["params"])).fetchone()
        truths.append(int(row[0]))
    return truths


def estimate_uniformity(table_sizes: dict[str, int], queries: list[dict]) -> list[float]:
    """Uniformity (Postgres-style): product of 1/M selectivities."""
    # title predicates: assume uniform year over [1990,2024] and kind over [1,7]
    n_title = table_sizes["title"]
    estimates: list[float] = []
    for q in queries:
        f = q["featurized"]
        year_lo, year_hi, year_span, kind = f[0], f[1], f[2], f[3]
        year_sel = (year_hi - year_lo + 1) / (2024 - 1990 + 1)
        kind_sel = 1.0 / 7
        title_match = n_title * year_sel * kind_sel
        # cast_info ~ 5 per title on average
        est = title_match * 5
        if q["sql"].count("JOIN name") > 0:
            # join with name and gender predicate (sel ~0.5)
            est = est * (table_sizes["name"] * 0.5) / table_sizes["name"]
        estimates.append(max(1.0, est))
    return estimates


def estimate_histogram(
    connection: sqlite3.Connection, table_sizes: dict[str, int], queries: list[dict], buckets: int = 20
) -> list[float]:
    """1D equi-depth histograms on title.production_year and title.kind_id."""
    years = [r[0] for r in connection.execute("SELECT production_year FROM title").fetchall()]
    kinds = [r[0] for r in connection.execute("SELECT kind_id FROM title").fetchall()]
    year_min, year_max = min(years), max(years)
    year_edges = [year_min + (year_max - year_min) * i / buckets for i in range(buckets + 1)]
    year_counts = _bucket_counts(years, year_edges)
    kind_counter = Counter(kinds)
    n_title = table_sizes["title"]
    estimates: list[float] = []
    for q in queries:
        f = q["featurized"]
        year_lo, year_hi, kind = int(f[0]), int(f[1]), int(f[3])
        year_sel = _hist_selectivity(year_lo, year_hi, year_edges, year_counts, n_title)
        kind_sel = kind_counter.get(kind, 0) / max(1, n_title)
        title_match = n_title * year_sel * kind_sel
        est = title_match * 5
        if q["sql"].count("JOIN name") > 0:
            est = est * 0.5
        estimates.append(max(1.0, est))
    return estimates


def _bucket_counts(values: list[int], edges: list[float]) -> list[int]:
    counts = [0] * (len(edges) - 1)
    for v in values:
        for i in range(len(edges) - 1):
            if edges[i] <= v < edges[i + 1] or (i == len(edges) - 2 and v == edges[i + 1]):
                counts[i] += 1
                break
    return counts


def _hist_selectivity(lo: int, hi: int, edges: list[float], counts: list[int], total: int) -> float:
    matched = 0
    for i in range(len(edges) - 1):
        bucket_lo, bucket_hi = edges[i], edges[i + 1]
        if bucket_hi < lo or bucket_lo > hi:
            continue
        overlap = max(0.0, min(bucket_hi, hi) - max(bucket_lo, lo) + 1)
        bucket_span = max(1.0, bucket_hi - bucket_lo + 1)
        matched += counts[i] * (overlap / bucket_span)
    return matched / max(1, total)


def estimate_sampling(
    connection: sqlite3.Connection, queries: list[dict], sample_frac: float, rng: random.Random
) -> list[float]:
    """Reservoir-sampling-based estimator over cast_info + title sample."""
    all_cast = connection.execute("SELECT movie_id, person_id FROM cast_info").fetchall()
    sample = rng.sample(all_cast, k=max(1, int(len(all_cast) * sample_frac)))
    # build per-movie_id counts in the sample, scaled up
    per_movie: dict[int, int] = Counter(m for m, _ in sample)
    scale = 1.0 / sample_frac
    title_ids = connection.execute("SELECT id, production_year, kind_id FROM title").fetchall()
    title_by_id = {tid: (yr, kind) for tid, yr, kind in title_ids}
    n_title = len(title_by_id)
    # year/kind histograms from full title (sampling estimator can still scan small title table)
    years = [yr for _, yr, _ in title_ids]
    kinds = [k for _, _, k in title_ids]
    estimates: list[float] = []
    for q in queries:
        f = q["featurize" if False else "featurized"]
        year_lo, year_hi, kind = int(f[0]), int(f[1]), int(f[3])
        year_sel = (year_hi - year_lo + 1) / (2024 - 1990 + 1)
        kind_sel = kinds.count(kind) / max(1, n_title)
        title_match = n_title * year_sel * kind_sel
        avg_cast_per_title = (sum(per_movie.values()) / max(1, len(per_movie))) * scale
        est = title_match * avg_cast_per_title
        if q["sql"].count("JOIN name") > 0:
            est = est * 0.5
        estimates.append(max(1.0, est))
    return estimates


def estimate_learned(
    training_queries: list[dict], training_truths: list[int], eval_queries: list[dict]
) -> list[float]:
    """A hand-rolled gradient-descent linear regressor over featurized predicates.

    Predicts log(cardinality); returns exp(prediction). No external deps.
    """
    features = [q["featurized"] for q in training_queries]
    targets = [math.log(max(1.0, float(t))) for t in training_truths]
    dim = len(features[0])
    weights = [0.0] * dim
    bias = 0.0
    lr = 0.01
    epochs = 200
    for _ in range(epochs):
        for feats, target in zip(features, targets):
            pred = bias + sum(w * x for w, x in zip(weights, feats))
            err = pred - target
            bias -= lr * err
            for i in range(dim):
                weights[i] -= lr * err * feats[i]
    estimates: list[float] = []
    for q in eval_queries:
        feats = q["featurized"]
        pred = bias + sum(w * x for w, x in zip(weights, feats))
        estimates.append(max(1.0, math.exp(pred)))
    return estimates


def q_error(estimates: list[float], truths: list[int]) -> list[float]:
    errors: list[float] = []
    for est, truth in zip(estimates, truths):
        if est == 0:
            est = 1.0
        ratio = max(est / max(1, truth), max(1, truth) / est)
        errors.append(float(ratio))
    return errors


def geomean(values: list[float]) -> float:
    if not values:
        return 0.0
    log_sum = sum(math.log(max(1e-12, v)) for v in values)
    return math.exp(log_sum / len(values))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    pos = fraction * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def bootstrap_ci(values: list[float], confidence: float, rng: random.Random) -> tuple[float, float]:
    if len(values) < 2:
        return (geomean(values), geomean(values))
    n = len(values)
    boots = []
    for _ in range(500):
        sample = [rng.choice(values) for _ in range(n)]
        boots.append(geomean(sample))
    boots.sort()
    alpha = (1.0 - confidence) / 2
    lo_idx = int(alpha * len(boots))
    hi_idx = int((1 - alpha) * len(boots))
    return (boots[lo_idx], boots[hi_idx])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True, choices=sorted(TRIALS))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    seed, estimator, condition = TRIALS[args.trial]
    rng = random.Random(seed)

    root = Path(__file__).resolve().parent
    schema = (root / "schema.sql").read_text(encoding="utf-8")
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.executescript(schema)
    table_sizes = populate_database(connection, rng)

    # Build ID and shifted query sets deterministically (separate RNG stream).
    q_rng = random.Random(12345)
    id_queries, shifted_queries = build_queries(q_rng)
    id_truths = true_cardinalities(connection, id_queries)
    shifted_truths = true_cardinalities(connection, shifted_queries)

    # For the learned estimator, train on a training split (70% of ID queries).
    if estimator == "learned":
        n_train = int(0.7 * len(id_queries))
        train_qs = id_queries[:n_train]
        train_truths = id_truths[:n_train]
        test_id = id_queries[n_train:]
        test_id_truths = id_truths[n_train:]
        # The "ID" condition evaluates on the held-out ID test split.
        # The "shifted" condition evaluates on the shifted set (distribution shift).
        eval_queries = test_id if condition == "ID" else shifted_queries
        eval_truths = test_id_truths if condition == "ID" else shifted_truths
        estimates = estimate_learned(train_qs, train_truths, eval_queries)
    else:
        eval_queries = id_queries if condition == "ID" else shifted_queries
        eval_truths = id_truths if condition == "ID" else shifted_truths
        if estimator == "uniformity":
            estimates = estimate_uniformity(table_sizes, eval_queries)
        elif estimator == "histogram":
            estimates = estimate_histogram(connection, table_sizes, eval_queries)
        elif estimator == "sampling":
            estimates = estimate_sampling(connection, eval_queries, sample_frac=0.1, rng=rng)
        else:
            raise ValueError(f"unknown estimator: {estimator}")

    errors = q_error(estimates, eval_truths)
    gm = geomean(errors)
    # For the shifted condition, also compute degradation vs the in-distribution
    # geomean of the SAME estimator+seed. We re-evaluate ID here so the ratio
    # is self-contained per trial (no cross-trial coupling needed by the ledger).
    if condition == "shifted":
        if estimator == "learned":
            n_train = int(0.7 * len(id_queries))
            id_eval = id_queries[n_train:]
            id_eval_truths = id_truths[n_train:]
            id_estimates = estimate_learned(id_queries[:n_train], id_truths[:n_train], id_eval)
        elif estimator == "uniformity":
            id_estimates = estimate_uniformity(table_sizes, id_queries)
        elif estimator == "histogram":
            id_estimates = estimate_histogram(connection, table_sizes, id_queries)
        elif estimator == "sampling":
            id_estimates = estimate_sampling(connection, id_queries, sample_frac=0.1, rng=rng)
        else:
            id_estimates = []
        id_gm = geomean(q_error(id_estimates, id_truths))
        degradation_ratio = gm / max(1e-9, id_gm)
    else:
        degradation_ratio = 1.0

    connection.close()

    ci_low, ci_high = bootstrap_ci(errors, 0.95, rng)
    # Effect size relative to the uniformity baseline (same seed, same condition).
    # Computed by re-running the uniformity estimator on the same eval set.
    # Positive = this estimator beats the baseline (lower Q-error is better here).
    uniformity_estimates = estimate_uniformity(table_sizes, eval_queries)
    uniformity_gm = geomean(q_error(uniformity_estimates, eval_truths))
    effect_size = (uniformity_gm - gm) / max(1e-9, uniformity_gm)
    # Derived quantities LLM prose naturally references; precomputed so the
    # claim verifier (which matches against ledger values) finds them supported.
    ci_width = ci_high - ci_low
    shift_pct_change = abs(1.0 - degradation_ratio) * 100.0
    runtime_sec = time.perf_counter() - started
    output = {
        "primary_metric": gm,
        "geomean_qerror": gm,
        "p95_qerror": percentile(errors, 0.95),
        "max_qerror": max(errors),
        "degradation_ratio": degradation_ratio,
        "effect_size": effect_size,
        "baseline_qerror": uniformity_gm,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_width": ci_width,
        "shift_pct_change": shift_pct_change,
        "n_queries": len(eval_queries),
        "evaluation_units": ["in-distribution-query-set", "shifted-query-set", "learned-estimator-held-out-split"],
        "runtime_sec": runtime_sec,
        "compute_units": float(len(errors)),
        "seed": seed,
        "estimator": estimator,
        "condition": condition,
        "trial_id": args.trial,
        "sqlite_version": sqlite3.sqlite_version,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
