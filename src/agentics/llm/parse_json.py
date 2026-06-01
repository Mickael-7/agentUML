"""Shared utility: robust JSON parsing from LLM responses."""
from __future__ import annotations

import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_llm_json(raw: str, agent_name: str = "Agent") -> dict:
    """Parse JSON from an LLM response with robust error recovery.

    Handles common LLM JSON issues:
    - Markdown code fences (```json ... ```)
    - Trailing commas before } or ]
    - JSON embedded inside prose text
    - Trailing backticks or whitespace

    Args:
        raw: The raw LLM response text.
        agent_name: Name for error messages.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON could be extracted.
    """
    # Step 1: Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Step 2: Try parsing the whole thing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Extract first JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"{agent_name} did not return a JSON object. Response:\n{raw[:500]}")

    json_str = match.group()

    # Step 4: Try parsing as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Step 5: Fix common LLM JSON errors — trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", json_str)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise ValueError(
        f"{agent_name} returned invalid JSON after recovery attempts. "
        f"Raw excerpt:\n{raw[:500]}"
    )
