from autoresearch.experiments.plugins.base import ExperimentPlugin
from autoresearch.experiments.plugins.cv import ComputerVisionExperimentPlugin
from autoresearch.experiments.plugins.data import DataExperimentPlugin
from autoresearch.experiments.plugins.llm import LLMExperimentPlugin
from autoresearch.experiments.plugins.mlsystems import MLSystemsExperimentPlugin
from autoresearch.experiments.plugins.nlp import NLPExperimentPlugin


_PLUGINS: dict[str, ExperimentPlugin] = {
    plugin.plugin_id: plugin
    for plugin in (
        LLMExperimentPlugin(),
        ComputerVisionExperimentPlugin(),
        NLPExperimentPlugin(),
        DataExperimentPlugin(),
        MLSystemsExperimentPlugin(),
    )
}


def plugin_for(plugin_id: str) -> ExperimentPlugin:
    try:
        return _PLUGINS[plugin_id]
    except KeyError as exc:
        raise ValueError(f"unknown experiment plugin: {plugin_id}") from exc


__all__ = ["plugin_for"]
