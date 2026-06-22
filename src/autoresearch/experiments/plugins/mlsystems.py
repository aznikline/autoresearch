from autoresearch.experiments.plugins.base import ExperimentPlugin


class MLSystemsExperimentPlugin(ExperimentPlugin):
    plugin_id = "ml-systems-efficiency"
    required_fields = frozenset(
        {
            "dataset_version",
            "split_hash",
            "model_checkpoint",
            "matched_resource_budgets",
            "immutable_evaluator",
            "quality_metrics",
            "efficiency_metrics",
            "baseline_tuning_policy",
        }
    )
    required_true_fields = frozenset(
        {"matched_resource_budgets", "immutable_evaluator"}
    )
    sha256_fields = frozenset({"split_hash"})
    required_items = {
        "efficiency_metrics": frozenset({"latency", "memory", "compute"}),
    }
