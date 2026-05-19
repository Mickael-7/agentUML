"""
End-to-end integration test for the Agentics pipeline.
Uses full mocks for LLM calls; PlantUML validation is also mocked.
"""

import json
from unittest.mock import MagicMock, patch

REQUIREMENTS_MD = """
# Sistema de Autenticação

req1: O usuário deve poder realizar login com email e senha.
req2: O administrador deve poder gerenciar usuários.
req3: O sistema deve validar credenciais contra o banco de dados.
"""

QUALITY_RESPONSE = json.dumps({"is_valid": True, "report": "Documento válido."})

PARTITION_RESPONSE = json.dumps(
    {
        "requirement_ids": {
            "req1": "O usuário deve poder realizar login.",
            "req2": "O administrador deve poder gerenciar usuários.",
            "req3": "O sistema deve validar credenciais.",
        },
        "partitions": [
            {
                "partition_id": "uc_1",
                "diagram_type": "use_case",
                "name": "Autenticação UC",
                "requirements": ["req1", "req2", "req3"],
            },
            {
                "partition_id": "domain_1",
                "diagram_type": "domain_class",
                "name": "Domínio Auth",
                "requirements": ["req1", "req2", "req3"],
            },
        ],
    }
)

UC_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Autenticação UC
' source_requirements: [req1, req2, req3]
' === END METADATA ===
left to right direction
actor "Usuário" as ator_usuario <<primary>>
usecase "Login" as uc_login << req:req1 >>
ator_usuario --> uc_login
@enduml"""

DOMAIN_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: domain_1
' diagram_type: domain_class
' name: Domínio Auth
' source_requirements: [req1, req2, req3]
' === END METADATA ===
class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
  - email: String
}
@enduml"""

CRITIC_RESPONSE = json.dumps({"score": 9, "issues": [], "suggestions": []})


def test_pipeline_end_to_end(tmp_path):
    req_file = tmp_path / "requirements.md"
    req_file.write_text(REQUIREMENTS_MD, encoding="utf-8")
    output_dir = tmp_path / "output"

    call_counter = {"n": 0}
    responses = [
        QUALITY_RESPONSE,
        PARTITION_RESPONSE,
        UC_PUML,  # UC generation
        CRITIC_RESPONSE,  # UC critique
        DOMAIN_PUML,  # Domain generation
        CRITIC_RESPONSE,  # Domain critique
    ]

    def mock_complete(messages, **kwargs):
        n = call_counter["n"]
        call_counter["n"] += 1
        if n < len(responses):
            return responses[n]
        return CRITIC_RESPONSE

    with (
        patch("agentics.orchestrator.Config.validate_llm"),
        patch("agentics.orchestrator.create_llm_client") as mock_llm_factory,
        patch("agentics.orchestrator.PlantUMLValidator") as mock_cli_class,
        patch(
            "agentics.agents.use_case.UseCaseAgent._load_prompt",
            return_value="generate {requirements} {error_context} {diagram_id} {diagram_name} {req_list}",
        ),
        patch(
            "agentics.agents.domain.DomainAgent._load_prompt",
            return_value="generate {requirements} {error_context} {diagram_id} {diagram_name} {req_list}",
        ),
        patch("agentics.agents.requirements_quality.Path.exists", return_value=True),
        patch(
            "agentics.agents.requirements_quality.Path.read_text",
            return_value="tmpl {requirements_text}",
        ),
        patch("agentics.agents.partitioner.Path.exists", return_value=True),
        patch(
            "agentics.agents.partitioner.Path.read_text", return_value="tmpl {requirements_text}"
        ),
        patch("agentics.agents.critic.Path.exists", return_value=True),
        patch(
            "agentics.agents.critic.Path.read_text",
            return_value="critic {diagram_type} {requirements} {related_diagrams} {puml_text}",
        ),
    ):

        mock_llm = MagicMock()
        mock_llm.complete.side_effect = mock_complete
        mock_llm_factory.return_value = mock_llm

        mock_cli = MagicMock()
        mock_cli.check.return_value = (True, "")
        mock_cli_class.return_value = mock_cli

        from agentics.orchestrator import run_pipeline

        exit_code = run_pipeline(str(req_file), str(output_dir))

    assert exit_code in (0, 2), f"Pipeline exit code was {exit_code}"
    assert output_dir.exists()
    assert (output_dir / "cross_validation_report.md").exists()
