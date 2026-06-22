from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LLMError(RuntimeError):
    """Base error for language-model provider failures."""


class LLMBudgetError(LLMError):
    """Raised before a call that would exceed configured budget."""


class LLMResponseError(LLMError):
    """Raised when a provider response cannot satisfy the requested schema."""


@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class StructuredLLMResponse:
    data: dict[str, Any]
    request_id: str
    model: str
    usage: LLMUsage
    cost_usd: float


class LLMProvider(Protocol):
    def complete_json(
        self,
        *,
        stage: str,
        messages: tuple[tuple[str, str], ...],
        required_keys: tuple[str, ...],
    ) -> StructuredLLMResponse: ...
