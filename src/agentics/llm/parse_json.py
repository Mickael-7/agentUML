"""Shared utility: robust JSON parsing from LLM responses."""
from __future__ import annotations

import json
import re
import logging

logger = logging.getLogger(__name__)


def _try_loads(text: str) -> dict | None:
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return None


def _fix_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


def _recover_truncated(text: str) -> dict | None:
    """Try to close a truncated JSON object by appending closing tokens."""
    # Count unclosed structures to figure out what's missing
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1

    if depth_brace <= 0:
        return None  # nothing to close

    # Truncate to last complete string/value boundary then close open structures
    # Find the last comma or colon-terminated value we can safely cut at
    safe_cut = max(
        text.rfind(","),
        text.rfind("]"),
        text.rfind("}"),
    )
    if safe_cut < 10:
        return None

    truncated = text[: safe_cut + 1]
    closing = "]" * depth_bracket + "}" * depth_brace
    candidate = _fix_trailing_commas(truncated + closing)
    return _try_loads(candidate)


def parse_llm_json(raw: str, agent_name: str = "Agent") -> dict:
    """Parse JSON from an LLM response with robust error recovery.

    Handles:
    - Markdown code fences (```json ... ```)
    - Trailing commas before } or ]
    - JSON embedded inside prose text
    - Truncated responses (token-limit cut-off)
    """
    # Step 1: Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Step 2: Try parsing the whole cleaned string
    result = _try_loads(cleaned)
    if result is not None:
        return result

    # Step 3: Fix trailing commas then retry
    result = _try_loads(_fix_trailing_commas(cleaned))
    if result is not None:
        return result

    # Step 4: Extract the first {...} block and retry
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        extracted = match.group()
        result = _try_loads(extracted) or _try_loads(_fix_trailing_commas(extracted))
        if result is not None:
            return result

    # Step 5: Response may be truncated — try to close open structures
    result = _recover_truncated(cleaned)
    if result is not None:
        logger.warning("%s returned a truncated JSON response — recovered partial result", agent_name)
        return result

    raise ValueError(
        f"{agent_name} did not return a JSON object. Response:\n{raw[:500]}"
    )
