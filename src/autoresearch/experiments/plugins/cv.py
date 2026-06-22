from autoresearch.experiments.plugins.base import ExperimentPlugin


class ComputerVisionExperimentPlugin(ExperimentPlugin):
    plugin_id = "computer-vision"
    required_fields = frozenset(
        {
            "dataset_version",
            "split_hash",
            "preprocessing",
            "augmentation",
            "resolution",
            "evaluation_implementation_hash",
            "pretraining_provenance",
            "duplicate_leakage_analysis",
            "robustness_metrics",
            "subgroup_metrics",
            "qualitative_selection_policy",
        }
    )
    resolved_fields = frozenset(
        {"pretraining_provenance", "duplicate_leakage_analysis"}
    )
    sha256_fields = frozenset({"split_hash", "evaluation_implementation_hash"})
