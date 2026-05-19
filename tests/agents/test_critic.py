import json
from unittest.mock import MagicMock, patch

import pytest

from agentics.agents.critic import CriticAgent, CriticResponseError

VALID_RESPONSE = json.dumps(
    {
        "score": 8,
        "issues": ["Missing <<primary>> stereotype on one actor"],
        "suggestions": ["Add stereotype to ator_admin"],
    }
)

LOW_SCORE_RESPONSE = json.dumps(
    {"score": 3, "issues": ["No requirements covered"], "suggestions": []}
)


def _make_critic(response: str) -> CriticAgent:
    llm = MagicMock()
    llm.complete.return_value = response
    with (
        patch("agentics.agents.critic.Path.exists", return_value=True),
        patch(
            "agentics.agents.critic.Path.read_text",
            return_value="template {diagram_type} {requirements} {related_diagrams} {puml_text}",
        ),
    ):
        return CriticAgent(llm)


def test_evaluate_returns_score_and_feedback():
    critic = _make_critic(VALID_RESPONSE)
    result = critic.evaluate("@startuml\n@enduml", "use_case", ["req1"], [])
    assert result["score"] == 8
    assert isinstance(result["issues"], list)
    assert isinstance(result["suggestions"], list)


def test_evaluate_low_score():
    critic = _make_critic(LOW_SCORE_RESPONSE)
    result = critic.evaluate("@startuml\n@enduml", "domain_class", ["req1"], [])
    assert result["score"] == 3


def test_invalid_json_raises():
    critic = _make_critic("not json at all")
    with pytest.raises(CriticResponseError, match="JSON"):
        critic.evaluate("@startuml\n@enduml", "use_case", ["req1"], [])


def test_score_out_of_range_raises():
    critic = _make_critic(json.dumps({"score": 11, "issues": [], "suggestions": []}))
    with pytest.raises(CriticResponseError, match="score"):
        critic.evaluate("@startuml\n@enduml", "use_case", ["req1"], [])


def test_markdown_fenced_json_is_parsed():
    wrapped = f"```json\n{VALID_RESPONSE}\n```"
    critic = _make_critic(wrapped)
    result = critic.evaluate("@startuml\n@enduml", "sequence", ["req1"], [])
    assert result["score"] == 8
