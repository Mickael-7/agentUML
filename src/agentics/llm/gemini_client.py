from __future__ import annotations

import re
import time
import logging
from typing import TYPE_CHECKING

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from agentics.llm.base import LLMClient

if TYPE_CHECKING:
    from agentics.config import Config

logger = logging.getLogger(__name__)

_503_DELAYS = [5, 15, 30]
_MAX_429_RETRIES = 5


def _parse_retry_delay(error: ClientError) -> float:
    """Extract retryDelay from 429 error details, fallback to 60s."""
    try:
        details = error.details or {}
        for item in (details.get("error", {}).get("details", []) if isinstance(details, dict) else []):
            if "retryDelay" in item:
                match = re.search(r"(\d+)", item["retryDelay"])
                if match:
                    return float(match.group(1)) + 2
    except Exception:
        pass
    return 60.0


class GeminiClient(LLMClient):
    def __init__(self, config: Config) -> None:
        if not config.gemini_api_key:
            raise OSError("GEMINI_API_KEY is not set.")
        self._api_key = config.gemini_api_key
        self._model = config.llm_model
        self._temperature = config.llm_temperature

    def complete(self, messages: list[dict], **kwargs) -> str:
        contents = []
        system_parts = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            elif msg["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))
            elif msg["role"] == "assistant":
                contents.append(types.Content(role="model", parts=[types.Part(text=msg["content"])]))

        if system_parts and contents:
            system_text = "\n".join(system_parts)
            first = contents[0]
            first.parts[0] = types.Part(text=system_text + "\n\n" + first.parts[0].text)

        gen_config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", self._temperature),
            max_output_tokens=kwargs.get("max_tokens", 8192),
        )

        retries_503 = 0
        retries_429 = 0

        while True:
            try:
                client = genai.Client(api_key=self._api_key)
                response = client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=gen_config,
                )
                return response.text

            except ServerError as e:
                retries_503 += 1
                if retries_503 > len(_503_DELAYS):
                    raise
                delay = _503_DELAYS[retries_503 - 1]
                logger.warning("Gemini 503 (attempt %d), retrying in %ds", retries_503, delay)
                time.sleep(delay)

            except ClientError as e:
                if e.code == 429:
                    retries_429 += 1
                    if retries_429 > _MAX_429_RETRIES:
                        raise
                    delay = _parse_retry_delay(e)
                    logger.warning(
                        "Gemini 429 rate limit (attempt %d/%d), retrying in %.0fs",
                        retries_429, _MAX_429_RETRIES, delay,
                    )
                    time.sleep(delay)
                else:
                    raise
