from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.llm.parse_json import parse_llm_json

if TYPE_CHECKING:
    from agentics.llm.base import LLMClient


class CriticResponseError(Exception):
    pass


class CriticAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "critic.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Critic prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    def evaluate(
        self,
        puml_text: str,
        diagram_type: str,
        requirements: list[str],
        related_diagrams: list[str],
    ) -> dict:
        req_text = "\n".join(f"- {r}" for r in requirements) if requirements else "(none)"
        related_text = (
            "\n".join(f"- {d}" for d in related_diagrams) if related_diagrams else "(none)"
        )
        prompt = (
            self._prompt_template.replace("{diagram_type}", diagram_type)
            .replace("{requirements}", req_text)
            .replace("{related_diagrams}", related_text)
            .replace("{puml_text}", puml_text)
        )
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        try:
            data = parse_llm_json(raw, "CriticAgent")
        except ValueError as e:
            raise CriticResponseError(str(e)) from e

        score = data.get("score")
        if not isinstance(score, (int, float)) or not (0 <= score <= 10):
            raise CriticResponseError(f"Critic score must be an integer 0-10, got: {score!r}")
        data["score"] = int(score)
        data.setdefault("issues", [])
        data.setdefault("suggestions", [])
        return data
