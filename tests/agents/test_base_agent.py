from unittest.mock import MagicMock

import pytest

from agentics.agents.base import Agent, Partition, ValidationError

VALID_PUML = """@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Test
' source_requirements: [req1]
' === END METADATA ===
actor "Usuário" as ator_usuario <<primary>>
usecase "Login" as uc_login << req:req1 >>
ator_usuario --> uc_login
@enduml"""


def _make_agent(
    llm_response=VALID_PUML,
    syntax_valid=True,
    semantic_valid=True,
    critic_score=8,
):
    class ConcreteAgent(Agent):
        diagram_type = "use_case"

        def build_prompt(self, partition, error_context=""):
            return [{"role": "user", "content": "generate"}]

        def parse_output(self, raw):
            return raw

    llm = MagicMock()
    llm.complete.return_value = llm_response

    config = MagicMock()
    config.max_validation_retries = 3
    config.max_refinement_rounds = 2
    config.critic_score_threshold = 7

    writer = MagicMock()
    writer.write_puml.return_value = "/output/uc_1.puml"

    validator_cli = MagicMock()
    validator_cli.check.return_value = (syntax_valid, "" if syntax_valid else "Syntax error")

    sem_validator = MagicMock()
    sem_result = MagicMock()
    sem_result.is_valid = semantic_valid
    sem_result.errors = []
    sem_validator.validate.return_value = sem_result

    critic = MagicMock()
    critic.evaluate.return_value = {"score": critic_score, "issues": [], "suggestions": []}

    return ConcreteAgent(
        llm=llm,
        config=config,
        writer=writer,
        validator_cli=validator_cli,
        semantic_validator=sem_validator,
        critic=critic,
    )


def _make_partition(diagram_type="use_case"):
    return Partition(
        partition_id="uc_1",
        diagram_type=diagram_type,
        requirements=["req1"],
        name="Test UC",
    )


def test_successful_run_first_attempt():
    agent = _make_agent(critic_score=9)
    result = agent.run(_make_partition())
    assert result == "/output/uc_1.puml"
    agent.writer.write_puml.assert_called_once_with("uc_1", VALID_PUML, draft=False)


def test_syntax_retry_then_success():
    agent = _make_agent(syntax_valid=True, critic_score=8)
    # First call fails, second succeeds
    agent.validator_cli.check.side_effect = [(False, "error"), (True, ""), (True, "")]
    agent.run(_make_partition())
    assert agent.llm.complete.call_count == 2


def test_validation_failure_saves_draft():
    agent = _make_agent(syntax_valid=False)
    agent.validator_cli.check.return_value = (False, "Syntax error")
    with pytest.raises(ValidationError):
        agent.run(_make_partition())
    agent.writer.write_puml.assert_called_once_with("uc_1", VALID_PUML, draft=True)


def test_critic_below_threshold_triggers_refinement():
    agent = _make_agent(critic_score=5)
    # Score below threshold first, then above
    agent.critic.evaluate.side_effect = [
        {"score": 5, "issues": ["missing actor"], "suggestions": ["add actor"]},
        {"score": 8, "issues": [], "suggestions": []},
    ]
    agent.run(_make_partition())
    assert agent.critic.evaluate.call_count == 2
    agent.writer.write_puml.assert_called_with("uc_1", VALID_PUML, draft=False)


def test_wrong_diagram_type_raises():
    agent = _make_agent()
    partition = _make_partition(diagram_type="domain_class")
    with pytest.raises(ValueError, match="use_case"):
        agent.run(partition)
