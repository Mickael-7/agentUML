from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentics.config import Config


class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Send messages to the LLM and return the text response."""


def create_llm_client(config: Config) -> LLMClient:
    provider = config.llm_provider.lower()
    if provider == "anthropic":
        from agentics.llm.anthropic_client import AnthropicClient

        return AnthropicClient(config)
    elif provider == "openai":
        from agentics.llm.openai_client import OpenAIClient

        return OpenAIClient(config)
    elif provider == "gemini":
        from agentics.llm.gemini_client import GeminiClient

        return GeminiClient(config)
    else:
        raise OSError(f"Unknown LLM_PROVIDER '{provider}'. Choose from: anthropic, openai, gemini")
