from __future__ import annotations

from typing import TYPE_CHECKING

from agentics.llm.base import LLMClient
from agentics.llm.openai_compatible_client import OpenAICompatibleClient

if TYPE_CHECKING:
    from agentics.config import Config


class GroqClient(LLMClient):
    def __init__(self, config: Config) -> None:
        self._impl = OpenAICompatibleClient(
            config,
            api_key=config.groq_api_key,
            base_url=config.groq_base_url,
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        return self._impl.complete(messages, **kwargs)
