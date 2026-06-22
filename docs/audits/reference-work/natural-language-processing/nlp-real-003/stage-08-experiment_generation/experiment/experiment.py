from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from collections import Counter
from pathlib import Path


TRIALS = {
    "baseline-majority-seed0": (0, "majority", 1.0, 1),
    "baseline-length-seed1": (1, "length", 1.0, 1),
    "baseline-lexicon-seed2": (2, "lexicon", 1.0, 1),
    "baseline-unigram-seed3": (3, "unigram", 1.0, 1),
    "ablation-unigram-alpha05-seed1": (1, "unigram", 0.5, 1),
    "ablation-unigram-minfreq2-seed2": (2, "unigram", 1.0, 2),
    "ablation-bigram-seed3": (3, "bigram", 1.0, 1),
    "ablation-bigram-minfreq2-seed4": (4, "bigram", 1.0, 2),
}
DOMAINS = ("amazon", "imdb", "yelp")
POSITIVE = {"good", "great", "excellent", "love", "best", "amazing", "wonderful"}
NEGATIVE = {"bad", "worst", "poor", "hate", "awful", "terrible", "boring"}


def tokens(text: str, mode: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    if mode == "bigram":
        return words + [f"{left}::{right}" for left, right in zip(words, words[1:])]
    return words


def load_corpus(root: Path) -> list[tuple[str, str, int]]:
    examples = []
    for domain in DOMAINS:
        for line in (root / "data" / f"{domain}.tsv").read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            if "\t" not in line:
                continue
            text, label = line.rsplit("\t", 1)
            examples.append((domain, text, int(label)))
    return examples


def fixed_split(
    examples: list[tuple[str, str, int]],
    manifest: dict[str, object],
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    partitions = {
        str(item["example_sha256"]): str(item["partition"])
        for item in manifest["examples"]
    }
    train = []
    test = []
    for example in examples:
        domain, text, label = example
        identity = hashlib.sha256(f"{domain}\0{label}\0{text}".encode()).hexdigest()
        (test if partitions[identity] == "test" else train).append(example)
    return train, test


def train_nb(
    train: list[tuple[str, str, int]], mode: str, minimum_frequency: int
) -> tuple[dict[int, Counter[str]], dict[int, int], set[str], dict[int, int]]:
    counts = {0: Counter(), 1: Counter()}
    documents = {0: 0, 1: 0}
    total = Counter()
    for _, text, label in train:
        documents[label] += 1
        features = tokens(text, mode)
        counts[label].update(features)
        total.update(features)
    vocabulary = {feature for feature, count in total.items() if count >= minimum_frequency}
    token_totals = {
        label: sum(count for feature, count in counts[label].items() if feature in vocabulary)
        for label in (0, 1)
    }
    return counts, documents, vocabulary, token_totals


def predict_nb(
    text: str,
    mode: str,
    alpha: float,
    model: tuple[dict[int, Counter[str]], dict[int, int], set[str], dict[int, int]],
) -> tuple[int, float]:
    counts, documents, vocabulary, totals = model
    observed = [feature for feature in tokens(text, mode) if feature in vocabulary]
    scores = {}
    for label in (0, 1):
        score = math.log(documents[label] / sum(documents.values()))
        denominator = totals[label] + alpha * len(vocabulary)
        score += sum(
            math.log((counts[label][feature] + alpha) / denominator)
            for feature in observed
        )
        scores[label] = score
    offset = max(scores.values())
    positive_probability = math.exp(scores[1] - offset) / sum(
        math.exp(value - offset) for value in scores.values()
    )
    return int(positive_probability >= 0.5), positive_probability


def predictions(
    train: list[tuple[str, str, int]],
    test: list[tuple[str, str, int]],
    mode: str,
    alpha: float,
    minimum_frequency: int,
) -> list[dict[str, object]]:
    nb_mode = "bigram" if mode == "bigram" else "unigram"
    model = train_nb(train, nb_mode, minimum_frequency)
    output = []
    for domain, text, label in test:
        if mode == "majority":
            prediction, probability = 0, 0.0
        elif mode == "length":
            probability = min(1.0, max(0.0, (len(text) - 55) / 100))
            prediction = int(probability >= 0.5)
        elif mode == "lexicon":
            words = set(tokens(text, "unigram"))
            score = len(words & POSITIVE) - len(words & NEGATIVE)
            probability = 1 / (1 + math.exp(-score))
            prediction = int(score >= 0)
        else:
            prediction, probability = predict_nb(text, nb_mode, alpha, model)
        output.append(
            {
                "domain": domain,
                "label": label,
                "prediction": prediction,
                "positive_probability": probability,
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return output


def scores(items: list[dict[str, object]]) -> dict[str, float]:
    tp = sum(item["label"] == item["prediction"] == 1 for item in items)
    tn = sum(item["label"] == item["prediction"] == 0 for item in items)
    fp = sum(item["label"] == 0 and item["prediction"] == 1 for item in items)
    fn = sum(item["label"] == 1 and item["prediction"] == 0 for item in items)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1_positive = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    negative_precision = tn / (tn + fn) if tn + fn else 0.0
    negative_recall = tn / (tn + fp) if tn + fp else 0.0
    f1_negative = (
        2 * negative_precision * negative_recall / (negative_precision + negative_recall)
        if negative_precision + negative_recall
        else 0.0
    )
    return {
        "accuracy": (tp + tn) / len(items),
        "macro_f1": (f1_positive + f1_negative) / 2,
        "precision": precision,
        "recall": recall,
        "brier_score": sum(
            (float(item["positive_probability"]) - int(item["label"])) ** 2
            for item in items
        ) / len(items),
    }


def bootstrap_interval(items: list[dict[str, object]], seed: int) -> tuple[float, float]:
    generator = random.Random(seed)
    values = []
    for _ in range(200):
        sample = [items[generator.randrange(len(items))] for _ in items]
        values.append(scores(sample)["macro_f1"])
    values.sort()
    return values[5], values[-6]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True, choices=sorted(TRIALS))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    seed, mode, alpha, minimum_frequency = TRIALS[args.trial]
    examples = load_corpus(Path(__file__).resolve().parent)
    manifest = json.loads(
        (Path(__file__).resolve().parent / "split_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    train, test = fixed_split(examples, manifest)
    items = predictions(train, test, mode, alpha, minimum_frequency)
    measured = scores(items)
    per_domain = {
        domain: scores([item for item in items if item["domain"] == domain])["macro_f1"]
        for domain in DOMAINS
    }
    ci_low, ci_high = bootstrap_interval(items, seed)
    majority = scores(predictions(train, test, "majority", 1.0, 1))["macro_f1"]
    elapsed = time.perf_counter() - started
    payload = {
        "primary_metric": measured["macro_f1"],
        **measured,
        "domain_gap": max(per_domain.values()) - min(per_domain.values()),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "effect_size": (measured["macro_f1"] - majority) / max(1e-12, math.sqrt(majority * (1 - majority))),
        "runtime_sec": elapsed,
        "compute_units": float(len(train) + len(test) * 201),
        "seed": seed,
        "evaluation_units": list(DOMAINS),
        "trial_id": args.trial,
        "model": mode,
        "train_examples": len(train),
        "test_examples": len(test),
        "per_domain_macro_f1": per_domain,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    prediction_path = destination.parent / "predictions.jsonl"
    prediction_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in items),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
