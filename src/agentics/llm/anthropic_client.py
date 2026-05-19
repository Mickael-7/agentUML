from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

from agentics.llm.base import LLMClient

if TYPE_CHECKING:
    from agentics.config import Config


class AnthropicClient(LLMClient):
    def __init__(self, config: Config) -> None:
        if not config.anthropic_api_key:
            raise OSError("ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self._model = config.llm_model
        self._temperature = config.llm_temperature

    def complete(self, messages: list[dict], **kwargs) -> str:
        # Anthropic separates system prompt from the messages list
        system = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", 8192),
            temperature=kwargs.get("temperature", self._temperature),
            system=system or anthropic.NOT_GIVEN,
            messages=user_messages,
        )
        return response.content[0].text
