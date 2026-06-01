from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.llm.parse_json import parse_llm_json

if TYPE_CHECKING:
    from agentics.llm.base import LLMClient


class RequirementsQualityAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "requirements_quality.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    def evaluate(self, requirements_text: str) -> dict:
        if not requirements_text or not requirements_text.strip():
            return {
                "is_valid": False,
                "report": "The requirements document is empty.",
            }
        prompt = self._prompt_template.replace("{requirements_text}", requirements_text)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        try:
            data = parse_llm_json(raw, "RequirementsQualityAgent")
        except ValueError as e:
            self.logger.error("RequirementsQualityAgent parse failed: %s", e)
            return {
                "is_valid": False,
                "report": f"Failed to parse agent response: {e}",
            }
        return {
            "is_valid": bool(data.get("is_valid", False)),
            "report": str(data.get("report", "")),
        }

    def __call__(self, requirements_text: str) -> dict:
        return self.evaluate(requirements_text)
