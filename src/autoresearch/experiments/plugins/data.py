from autoresearch.experiments.plugins.base import ExperimentPlugin


class DataExperimentPlugin(ExperimentPlugin):
    plugin_id = "data-management-mining"
    required_fields = frozenset(
        {
            "system_versions",
            "schema_hash",
            "workload_hash",
            "scale_factor",
            "indexes",
            "optimizer_config",
            "hardware_storage",
            "concurrency",
            "isolation_level",
            "cache_policy",
            "warmup",
            "repetitions",
            "timeout_policy",
            "latency_distribution",
            "correctness_check",
            "matched_hardware",
        }
    )
    required_true_fields = frozenset({"matched_hardware"})
    positive_fields = frozenset({"scale_factor", "concurrency", "repetitions"})
    sha256_fields = frozenset({"schema_hash", "workload_hash"})
    required_items = {
        "latency_distribution": frozenset({"p50", "p95", "p99"}),
    }
