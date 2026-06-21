import json
from unittest.mock import MagicMock, patch

from agentics.agents.use_case_extractor import UseCaseExtractorAgent

DOC = """
# Sistema de Autenticacao
REQ-001: O usuario deve poder realizar login com email e senha.
REQ-002: O administrador deve poder gerenciar usuarios cadastrados.
"""


def _make_agent(llm_response: str) -> UseCaseExtractorAgent:
    llm = MagicMock()
    llm.complete.return_value = llm_response
    with (
        patch("agentics.agents.use_case_extractor.Path.exists", return_value=True),
        patch(
            "agentics.agents.use_case_extractor.Path.read_text",
            return_value="t {requirements_text}",
        ),
    ):
        return UseCaseExtractorAgent(llm)


def test_extracts_use_cases():
    resp = json.dumps(
        {
            "use_cases": [
                {"name": "Realizar Login", "text": "O usuario deve poder realizar login com email e senha."},
                {"name": "Gerenciar Usuarios", "text": "O administrador deve poder gerenciar usuarios cadastrados."},
            ]
        }
    )
    agent = _make_agent(resp)
    out = agent.extract(DOC)
    assert len(out) == 2
    assert out[0]["name"] == "Realizar Login"
    assert "login" in out[0]["text"]


def test_malformed_json_returns_empty():
    agent = _make_agent("not json at all")
    assert agent.extract(DOC) == []


def test_empty_doc_returns_empty_without_llm_call():
    agent = _make_agent(json.dumps({"use_cases": [{"name": "x", "text": "y"}]}))
    assert agent.extract("   ") == []
    agent.llm.complete.assert_not_called()


def test_filters_entries_with_empty_text():
    resp = json.dumps(
        {
            "use_cases": [
                {"name": "ok", "text": "bom texto"},
                {"name": "vazio", "text": ""},
            ]
        }
    )
    agent = _make_agent(resp)
    out = agent.extract(DOC)
    assert len(out) == 1
    assert out[0]["name"] == "ok"


def test_no_use_cases_returns_empty():
    agent = _make_agent(json.dumps({"use_cases": []}))
    assert agent.extract(DOC) == []
