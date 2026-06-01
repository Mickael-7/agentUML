"""Generic OpenAI-compatible LLM client.

Used by providers that implement the OpenAI chat completions API
with a custom base_url (GLM, Grok, Groq, etc.).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from openai import OpenAI

from agentics.llm.base import LLMClient

if TYPE_CHECKING:
    from agentics.config import Config


class OpenAICompatibleClient(LLMClient):
    """Client for any OpenAI-compatible API endpoint."""

    def __init__(self, config: Config, *, api_key: str, base_url: str) -> None:
        if not api_key:
            raise OSError("API key is not set.")
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(verify=False),
        )
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
