from unittest.mock import MagicMock

import pytest

from agentics.agents.base import Partition
from agentics.agents.domain import DomainAgent
from agentics.agents.sequence import SequenceAgent
from agentics.agents.specialization import SpecializationAgent
from agentics.agents.use_case import UseCaseAgent

VALID_UC_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Auth
' source_requirements: [req1]
' === END METADATA ===
left to right direction
actor "Usuário" as ator_usuario <<primary>>
usecase "Login" as uc_login << req:req1 >>
ator_usuario --> uc_login
@enduml"""

VALID_DOMAIN_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: domain_1
' diagram_type: domain_class
' name: Domain
' source_requirements: [req1]
' === END METADATA ===
class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
}
@enduml"""

VALID_SEQ_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: seq_1
' diagram_type: sequence
' name: Seq
' source_requirements: [req1]
' === END METADATA ===
actor "Usuário" as ll_usuario
control "Ctrl" as ll_ctrl
ll_usuario -> ll_ctrl : acao()
ll_ctrl --> ll_usuario : ok
@enduml"""

VALID_SPEC_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: spec_1
' diagram_type: specialized_class
' name: Spec
' source_requirements: [req1]
' === END METADATA ===
class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
  + autenticar(senha: String): Boolean
}
@enduml"""


def _make_deps(llm_response, syntax_valid=True, critic_score=9):
    llm = MagicMock()
    llm.complete.return_value = llm_response

    config = MagicMock()
    config.max_validation_retries = 3
    config.max_refinement_rounds = 2
    config.critic_score_threshold = 7

    writer = MagicMock()
    writer.write_puml.return_value = "/output/test.puml"

    validator_cli = MagicMock()
    validator_cli.check.return_value = (syntax_valid, "")

    sem = MagicMock()
    sem_result = MagicMock()
    sem_result.is_valid = True
    sem_result.errors = []
    sem.validate.return_value = sem_result

    critic = MagicMock()
    critic.evaluate.return_value = {"score": critic_score, "issues": [], "suggestions": []}

    return llm, config, writer, validator_cli, sem, critic


def _partition(pid, dtype):
    return Partition(
        partition_id=pid,
        diagram_type=dtype,
        requirements=["req1"],
        name="Test",
        req_texts={"req1": "test req"},
    )


@pytest.mark.parametrize(
    "AgentClass,puml,dtype,pid",
    [
        (UseCaseAgent, VALID_UC_PUML, "use_case", "uc_1"),
        (DomainAgent, VALID_DOMAIN_PUML, "domain_class", "domain_1"),
        (SequenceAgent, VALID_SEQ_PUML, "sequence", "seq_1"),
        (SpecializationAgent, VALID_SPEC_PUML, "specialized_class", "spec_1"),
    ],
)
def test_agent_run_success(AgentClass, puml, dtype, pid):
    from unittest.mock import patch

    llm, config, writer, validator_cli, sem, critic = _make_deps(puml)
    prompt_content = (
        "generate {requirements} {error_context} {diagram_id} {diagram_name} {req_list}"
    )

    with patch.object(AgentClass, "_load_prompt", return_value=prompt_content):
        agent = AgentClass(
            llm=llm,
            config=config,
            writer=writer,
            validator_cli=validator_cli,
            semantic_validator=sem,
            critic=critic,
        )
    result = agent.run(_partition(pid, dtype))
    assert result == "/output/test.puml"
    writer.write_puml.assert_called_once_with(pid, puml, draft=False)


def test_use_case_rejects_wrong_type():
    llm, config, writer, validator_cli, sem, critic = _make_deps(VALID_DOMAIN_PUML)
    from unittest.mock import patch

    with patch.object(
        UseCaseAgent,
        "_load_prompt",
        return_value="tmpl {requirements} {error_context} {diagram_id} {diagram_name} {req_list}",
    ):
        agent = UseCaseAgent(
            llm=llm,
            config=config,
            writer=writer,
            validator_cli=validator_cli,
            semantic_validator=sem,
            critic=critic,
        )
    with pytest.raises(ValueError, match="use_case"):
        agent.run(_partition("domain_1", "domain_class"))
