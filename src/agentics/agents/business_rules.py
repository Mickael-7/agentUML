from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.llm.parse_json import parse_llm_json

if TYPE_CHECKING:
    from agentics.llm.base import LLMClient


class BusinessRulesError(Exception):
    pass


class BusinessRulesAgent:
    """Extracts and clusters business rules from requirements (Phase 1 of Super-Prompt)."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "business_rules.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    def extract(self, requirements_text: str) -> dict:
        """Returns dict with keys: 'rules' (list of dicts), 'rules_text' (formatted string)."""
        prompt = self._prompt_template.replace("{requirements_text}", requirements_text)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        data = parse_llm_json(raw, "BusinessRulesAgent")

        rules = data.get("rules", [])
        rules_lines = []
        for rule in rules:
            rule_id = rule.get("id", "BR-???")
            rule_text = rule.get("text", "")
            rule_domain = rule.get("domain", "general")
            rules_lines.append(f"- [{rule_id}] ({rule_domain}) {rule_text}")
        rules_text = "\n".join(rules_lines)

        return {
            "rules": rules,
            "rules_text": rules_text,
            "domains": data.get("domains", []),
            "summary": data.get("summary", ""),
        }
