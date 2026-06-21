import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agentics.agents.use_case_evaluator import UseCaseDocumentEvaluator

DOC_WITH_DIAGRAM = """
# Login
Requisito: O usuario deve poder logar com email e senha.
Ator: Usuario. Fluxo principal: acessar, informar credenciais, validar, acessar painel.
@startuml
actor "Usuario" as U
usecase "Login" as UC1
U --> UC1
@enduml
"""

DOC_NO_DIAGRAM = """
# Login
Requisito: O usuario deve poder logar com email e senha.
Ator: Usuario. Fluxo principal: acessar, informar, validar, acessar painel.
"""

CORRECT_JSON = json.dumps(
    {
        "verdict": "correct",
        "checks": {
            "has_requirement": True,
            "has_use_case_context": True,
            "symbology_correct": True,
        },
        "errors": [],
        "justification": "Documento completo com requisito e contexto.",
        "correction": "",
        "summary": "ok",
    }
)

INCORRECT_JSON = json.dumps(
    {
        "verdict": "incorrect",
        "checks": {
            "has_requirement": True,
            "has_use_case_context": False,
            "symbology_correct": True,
        },
        "errors": ["Sem contexto de caso de uso."],
        "justification": "Falta o contexto.",
        "correction": "Adicione o fluxo principal.",
        "summary": "incompleto",
    }
)

NULL_SYM_JSON = json.dumps(
    {
        "verdict": "correct",
        "checks": {
            "has_requirement": True,
            "has_use_case_context": True,
            "symbology_correct": None,
        },
        "errors": [],
        "justification": "ok",
        "correction": "",
        "summary": "ok",
    }
)


def _make_agent(
    llm_response: str,
    plantuml_validator: object | None = None,
    semantic_validator: object | None = None,
) -> UseCaseDocumentEvaluator:
    llm = MagicMock()
    llm.complete.return_value = llm_response
    with (
        patch("agentics.agents.use_case_evaluator.Path.exists", return_value=True),
        patch(
            "agentics.agents.use_case_evaluator.Path.read_text",
            return_value="t {document_text} | {diagram_validation} | {semantic_validation}",
        ),
    ):
        return UseCaseDocumentEvaluator(
            llm,
            plantuml_validator=plantuml_validator,
            semantic_validator=semantic_validator,
        )


def test_correct_document_returns_correct():
    agent = _make_agent(CORRECT_JSON)
    result = agent.evaluate_document(DOC_WITH_DIAGRAM)
    assert result["verdict"] == "correct"
    assert result["checks"]["has_requirement"] is True
    assert result["correction"] == ""  # cleared when correct


def test_incorrect_document_returns_incorrect():
    agent = _make_agent(INCORRECT_JSON)
    result = agent.evaluate_document(DOC_WITH_DIAGRAM)
    assert result["verdict"] == "incorrect"
    assert result["checks"]["has_use_case_context"] is False
    assert result["correction"]  # non-empty
    assert result["errors"]


def test_empty_document_short_circuits():
    agent = _make_agent(CORRECT_JSON)
    result = agent.evaluate_document("   ")
    assert result["verdict"] == "incorrect"
    agent.llm.complete.assert_not_called()


def test_malformed_json_returns_incorrect():
    agent = _make_agent("not json at all")
    result = agent.evaluate_document(DOC_NO_DIAGRAM)
    assert result["verdict"] == "incorrect"
    assert result["errors"]  # parse-failure error present


def test_document_without_diagram_yields_null_symbology():
    pval = MagicMock()
    sval = MagicMock()
    agent = _make_agent(NULL_SYM_JSON, plantuml_validator=pval, semantic_validator=sval)
    result = agent.evaluate_document(DOC_NO_DIAGRAM)
    assert result["checks"]["symbology_correct"] is None
    # No diagram -> validators must not be invoked.
    pval.check.assert_not_called()
    sval.validate.assert_not_called()


def test_evaluate_documents_resilient_to_failure():
    llm = MagicMock()
    llm.complete.side_effect = RuntimeError("boom")
    with (
        patch("agentics.agents.use_case_evaluator.Path.exists", return_value=True),
        patch(
            "agentics.agents.use_case_evaluator.Path.read_text",
            return_value="t {document_text} | {diagram_validation} | {semantic_validation}",
        ),
    ):
        agent = UseCaseDocumentEvaluator(llm)
    results = agent.evaluate_documents(
        [{"text": DOC_NO_DIAGRAM}, {"text": DOC_NO_DIAGRAM}, {"text": DOC_NO_DIAGRAM}]
    )
    assert len(results) == 3
    # Batch survives: every failure becomes a synthetic 'incorrect' result.
    assert all(r["verdict"] == "incorrect" for r in results)
    assert all(r["errors"] for r in results)


def test_plantuml_evidence_injected_into_prompt():
    pval = MagicMock()
    pval.check.return_value = (True, "")  # valid syntax
    sval = MagicMock()
    sval.validate.return_value = SimpleNamespace(errors=[])  # no semantic errors
    agent = _make_agent(CORRECT_JSON, plantuml_validator=pval, semantic_validator=sval)
    agent.evaluate_document(DOC_WITH_DIAGRAM)

    sent_prompt = agent.llm.complete.call_args.args[0][0]["content"]
    assert "Sintaxe PlantUML válida." in sent_prompt
    assert "Sem erros semânticos relevantes." in sent_prompt
    pval.check.assert_called_once()


DOC_MERMAID_OK = """
# Login
Requisito: O usuario deve poder logar.
Ator: Usuario. Fluxo: acessar, informar, validar.
```mermaid
graph LR
  Usuario -->|usa| Login
```
"""

DOC_MERMAID_BAD = """
# Login
Requisito: O usuario deve poder logar.
Ator: Usuario. Fluxo: acessar, informar, validar.
```mermaid
xyzgarbage
  Usuario --> Login
```
"""


def test_mermaid_block_detected_validators_skipped():
    pval = MagicMock()
    sval = MagicMock()
    agent = _make_agent(CORRECT_JSON, plantuml_validator=pval, semantic_validator=sval)
    result = agent.evaluate_document(DOC_MERMAID_OK)
    assert result["verdict"] == "correct"
    # Mermaid path -> PlantUML / semantic validators must not run.
    pval.check.assert_not_called()
    sval.validate.assert_not_called()
    sent_prompt = agent.llm.complete.call_args.args[0][0]["content"]
    assert "Diagrama Mermaid detectado" in sent_prompt
    assert "plaus" in sent_prompt


def test_mermaid_malformed_type_flagged_in_evidence():
    agent = _make_agent(INCORRECT_JSON)
    agent.evaluate_document(DOC_MERMAID_BAD)
    sent_prompt = agent.llm.complete.call_args.args[0][0]["content"]
    assert "malformado" in sent_prompt


def test_mermaid_wrong_notation_classdiagram_flagged():
    # Valid Mermaid syntax but classDiagram = wrong notation for a use case.
    doc = DOC_NO_DIAGRAM + "\n```mermaid\nclassDiagram\n  Usuario --> Pedido\n```"
    agent = _make_agent(CORRECT_JSON)
    agent.evaluate_document(doc)
    sent_prompt = agent.llm.complete.call_args.args[0][0]["content"]
    assert "Diagrama Mermaid detectado (tipo: classdiagram)" in sent_prompt
    assert "plaus" in sent_prompt  # recognized type -> plausible syntax
