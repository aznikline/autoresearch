from __future__ import annotations

import pytest
from pathlib import Path
import yaml

from autoresearch.experiments.plugins import plugin_for


COMMON = {
    "confirmatory": True,
    "hypotheses": ["h1", "h2"],
    "primary_metrics": ["quality"],
    "exclusions": ["corrupt input"],
    "evaluator_hash": "a" * 64,
    "stopping_rule": "fixed budget",
    "resource_budget": "matched",
    "seeds": [1, 2, 3],
    "uncertainty": "bootstrap confidence interval",
}

VALID_DOMAIN_PROTOCOLS = {
    "foundation-models-llm": {
        "model_checkpoint": "model@sha256:abc",
        "tokenizer": "tokenizer-v1",
        "prompt_template_hash": "b" * 64,
        "decoding": {"temperature": 0.0},
        "context_policy": "fixed 8k",
        "judge_model": "judge-v1",
        "evaluator_forms": ["judge", "exact-match"],
        "judge_bias_controls": ["position randomization", "order swap"],
        "contamination_analysis": "benchmark overlap scan",
        "cost_metrics": ["tokens", "latency", "usd"],
    },
    "computer-vision": {
        "dataset_version": "dataset-v1",
        "split_hash": "c" * 64,
        "preprocessing": "resize-normalize-v1",
        "augmentation": "train-only flip",
        "resolution": "224x224",
        "evaluation_implementation_hash": "d" * 64,
        "pretraining_provenance": "public corpus manifest",
        "duplicate_leakage_analysis": "perceptual hash scan",
        "robustness_metrics": ["corruption accuracy"],
        "subgroup_metrics": ["class-balanced accuracy"],
        "qualitative_selection_policy": "fixed first failures per class",
    },
    "natural-language-processing": {
        "corpus_version": "corpus-v1",
        "languages": ["en", "zh"],
        "domains": ["news"],
        "tokenization": "tokenizer-v1",
        "normalization": "NFC",
        "split_hash": "e" * 64,
        "evaluation_script_hash": "f" * 64,
        "annotation_protocol": "double blind adjudication",
        "human_evaluation": "task-valid paired rating",
        "contamination_analysis": "document hash scan",
        "license_privacy_review": "approved",
        "subgroup_error_analysis": "by language and label",
    },
    "data-management-mining": {
        "system_versions": ["db-v1", "db-v2"],
        "schema_hash": "1" * 64,
        "workload_hash": "2" * 64,
        "scale_factor": 10,
        "indexes": ["primary", "secondary"],
        "optimizer_config": "default plus tuned",
        "hardware_storage": "same host and NVMe",
        "concurrency": 8,
        "isolation_level": "snapshot",
        "cache_policy": "cold and warm reported separately",
        "warmup": "five unmeasured rounds",
        "repetitions": 10,
        "timeout_policy": "60 seconds recorded as timeout",
        "latency_distribution": ["p50", "p95", "p99"],
        "correctness_check": "result checksum",
        "matched_hardware": True,
    },
    "ml-systems-efficiency": {
        "dataset_version": "dataset-v1",
        "split_hash": "3" * 64,
        "model_checkpoint": "model-v1",
        "matched_resource_budgets": True,
        "immutable_evaluator": True,
        "quality_metrics": ["accuracy"],
        "efficiency_metrics": ["latency", "throughput", "memory", "compute"],
        "baseline_tuning_policy": "same budget",
    },
}


@pytest.mark.parametrize("plugin_id", sorted(VALID_DOMAIN_PROTOCOLS))
def test_domain_plugin_accepts_complete_protocol(plugin_id: str) -> None:
    protocol = {**COMMON, **VALID_DOMAIN_PROTOCOLS[plugin_id]}

    result = plugin_for(plugin_id).validate(protocol)

    assert result.ok, result.issues
    assert result.plugin_id == plugin_id


@pytest.mark.parametrize("plugin_id", sorted(VALID_DOMAIN_PROTOCOLS))
def test_domain_plugin_fails_closed_when_a_domain_field_is_missing(
    plugin_id: str,
) -> None:
    domain = dict(VALID_DOMAIN_PROTOCOLS[plugin_id])
    missing = next(iter(domain))
    domain.pop(missing)

    result = plugin_for(plugin_id).validate({**COMMON, **domain})

    assert not result.ok
    assert any(issue.field == missing for issue in result.issues)


def test_llm_judge_requires_bias_controls() -> None:
    protocol = {**COMMON, **VALID_DOMAIN_PROTOCOLS["foundation-models-llm"]}
    protocol["judge_bias_controls"] = []

    result = plugin_for("foundation-models-llm").validate(protocol)

    assert not result.ok
    assert any(issue.code == "empty_required_evidence" for issue in result.issues)


def test_data_plugin_rejects_unmatched_hardware() -> None:
    protocol = {**COMMON, **VALID_DOMAIN_PROTOCOLS["data-management-mining"]}
    protocol["matched_hardware"] = False

    result = plugin_for("data-management-mining").validate(protocol)

    assert not result.ok
    assert any(issue.code == "required_true" for issue in result.issues)


def test_unknown_plugin_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown experiment plugin"):
        plugin_for("quantum-biology")


@pytest.mark.parametrize(
    ("plugin_id", "field", "value", "code"),
    [
        ("foundation-models-llm", "evaluator_forms", ["judge"], "insufficient_items"),
        ("computer-vision", "duplicate_leakage_analysis", "unknown", "unresolved_evidence"),
        ("natural-language-processing", "license_privacy_review", "unknown", "unresolved_evidence"),
        ("data-management-mining", "concurrency", 0, "non_positive_value"),
        ("ml-systems-efficiency", "matched_resource_budgets", False, "required_true"),
    ],
)
def test_domain_semantic_controls_fail_closed(
    plugin_id: str,
    field: str,
    value: object,
    code: str,
) -> None:
    protocol = {**COMMON, **VALID_DOMAIN_PROTOCOLS[plugin_id], field: value}

    result = plugin_for(plugin_id).validate(protocol)

    assert not result.ok
    assert any(issue.field == field and issue.code == code for issue in result.issues)


def test_every_reference_fixture_is_explicitly_synthetic_and_contract_valid() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures/projects"
    fixtures = sorted(root.glob("*/protocol.yaml"))

    assert {path.parent.name for path in fixtures} == {
        "llm", "cv", "nlp", "data", "mlsystems"
    }
    for path in fixtures:
        payload = yaml.safe_load(path.read_text())
        assert payload["synthetic"] is True
        result = plugin_for(payload["plugin_id"]).validate(payload["protocol"])
        assert result.ok, (path, result.issues)
