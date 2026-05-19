from __future__ import annotations

from typing import TYPE_CHECKING

from openai import OpenAI

from agentics.llm.base import LLMClient

if TYPE_CHECKING:
    from agentics.config import Config


class OpenAIClient(LLMClient):
    def __init__(self, config: Config) -> None:
        if not config.openai_api_key:
            raise OSError("OPENAI_API_KEY is not set.")
        self._client = OpenAI(api_key=config.openai_api_key)
        self._model = config.llm_model
        self._temperature = config.llm_temperature

    def complete(self, messages: list[dict], **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", self._temperature),
            max_tokens=kwargs.get("max_tokens", 8192),
        )
        return response.choices[0].message.content or ""
