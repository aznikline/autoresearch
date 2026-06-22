from autoresearch.experiments.plugins.base import ExperimentPlugin


class LLMExperimentPlugin(ExperimentPlugin):
    plugin_id = "foundation-models-llm"
    required_fields = frozenset(
        {
            "model_checkpoint",
            "tokenizer",
            "prompt_template_hash",
            "decoding",
            "context_policy",
            "judge_model",
            "evaluator_forms",
            "judge_bias_controls",
            "contamination_analysis",
            "cost_metrics",
        }
    )
    min_list_lengths = {"evaluator_forms": 2, "judge_bias_controls": 2}
    resolved_fields = frozenset({"contamination_analysis"})
    required_items = {
        "cost_metrics": frozenset({"tokens", "latency", "usd"}),
    }
