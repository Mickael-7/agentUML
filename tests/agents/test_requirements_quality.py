import json
from unittest.mock import MagicMock, patch

from agentics.agents.requirements_quality import RequirementsQualityAgent

VALID_DOC = """
# Sistema de Autenticação

req1: O usuário deve poder realizar login com email e senha.
req2: O administrador deve poder gerenciar usuários.
req3: O sistema deve validar as credenciais contra o banco de dados.
"""

INVALID_DOC = "blah blah nothing here"


def _make_agent(llm_response: str) -> RequirementsQualityAgent:
    llm = MagicMock()
    llm.complete.return_value = llm_response
    with (
        patch("agentics.agents.requirements_quality.Path.exists", return_value=True),
        patch(
            "agentics.agents.requirements_quality.Path.read_text",
            return_value="template {requirements_text}",
        ),
    ):
        return RequirementsQualityAgent(llm)


def test_valid_document_returns_true():
    response = json.dumps({"is_valid": True, "report": "Documento válido com 3 requisitos."})
    agent = _make_agent(response)
    result = agent.evaluate(VALID_DOC)
    assert result["is_valid"] is True
    assert "report" in result


def test_invalid_document_returns_false():
    response = json.dumps({"is_valid": False, "report": "Sem atores identificáveis."})
    agent = _make_agent(response)
    result = agent.evaluate(INVALID_DOC)
    assert result["is_valid"] is False


def test_empty_document_short_circuits():
    llm = MagicMock()
    with (
        patch("agentics.agents.requirements_quality.Path.exists", return_value=True),
        patch(
            "agentics.agents.requirements_quality.Path.read_text",
            return_value="tmpl {requirements_text}",
        ),
    ):
        agent = RequirementsQualityAgent(llm)
    result = agent.evaluate("")
    assert result["is_valid"] is False
    llm.complete.assert_not_called()


def test_malformed_json_returns_false():
    agent = _make_agent("not json")
    result = agent.evaluate(VALID_DOC)
    assert result["is_valid"] is False
