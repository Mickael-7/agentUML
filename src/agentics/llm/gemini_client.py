from __future__ import annotations

from typing import TYPE_CHECKING

import google.generativeai as genai

from agentics.llm.base import LLMClient

if TYPE_CHECKING:
    from agentics.config import Config


class GeminiClient(LLMClient):
    def __init__(self, config: Config) -> None:
        if not config.gemini_api_key:
            raise OSError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=config.gemini_api_key)
        self._model = genai.GenerativeModel(config.llm_model)
        self._temperature = config.llm_temperature

    def complete(self, messages: list[dict], **kwargs) -> str:
        # Convert OpenAI-style messages to Gemini contents format
        contents = []
        system_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [msg["content"]]})

        # Prepend system prompt to the first user message if present
        if system_parts and contents:
            system_text = "\n".join(system_parts)
            first = contents[0]
            first["parts"] = [system_text + "\n\n" + first["parts"][0]] + first["parts"][1:]

        generation_config = genai.types.GenerationConfig(
            temperature=kwargs.get("temperature", self._temperature),
            max_output_tokens=kwargs.get("max_tokens", 8192),
        )
        response = self._model.generate_content(contents, generation_config=generation_config)
        return response.text
