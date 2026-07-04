from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.llm.parse_json import parse_llm_json

if TYPE_CHECKING:
    from agentics.llm.base import LLMClient


class UseCaseExtractorAgent:
    """Extracts the use cases described in a requirements document."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "use_case_extractor.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    def extract(self, requirements_text: str) -> list[dict]:
        if not requirements_text or not requirements_text.strip():
            return []

        prompt = self._prompt_template.replace("{requirements_text}", requirements_text)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1, max_tokens=16384)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> list[dict]:
        try:
            data = parse_llm_json(raw, "UseCaseExtractorAgent")
        except ValueError as e:
            self.logger.error("UseCaseExtractorAgent parse failed: %s", e)
            return []

        use_cases = data.get("use_cases") or []
        if not isinstance(use_cases, list):
            return []

        cleaned: list[dict] = []
        for uc in use_cases:
            if not isinstance(uc, dict):
                continue
            text = str(uc.get("text", "") or "").strip()
            name = str(uc.get("name", "") or "").strip()
            if not text:
                continue  # nothing to evaluate
            cleaned.append({"name": name, "text": text})
        return cleaned

    def __call__(self, requirements_text: str) -> list[dict]:
        return self.extract(requirements_text)
