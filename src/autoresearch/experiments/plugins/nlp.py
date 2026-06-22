from autoresearch.experiments.plugins.base import ExperimentPlugin


class NLPExperimentPlugin(ExperimentPlugin):
    plugin_id = "natural-language-processing"
    required_fields = frozenset(
        {
            "corpus_version",
            "languages",
            "domains",
            "tokenization",
            "normalization",
            "split_hash",
            "evaluation_script_hash",
            "annotation_protocol",
            "human_evaluation",
            "contamination_analysis",
            "license_privacy_review",
            "subgroup_error_analysis",
        }
    )
    resolved_fields = frozenset(
        {"contamination_analysis", "license_privacy_review"}
    )
    sha256_fields = frozenset({"split_hash", "evaluation_script_hash"})
