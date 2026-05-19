import json
from unittest.mock import MagicMock, patch

import pytest

from agentics.agents.partitioner import PartitionerAgent, PartitionError

VALID_RESPONSE = json.dumps(
    {
        "requirement_ids": {
            "req1": "Usuário faz login com email e senha.",
            "req2": "Administrador gerencia usuários.",
            "req3": "Sistema valida credenciais.",
        },
        "partitions": [
            {
                "partition_id": "uc_1",
                "diagram_type": "use_case",
                "name": "Gestão de Autenticação",
                "requirements": ["req1", "req2"],
            },
            {
                "partition_id": "domain_1",
                "diagram_type": "domain_class",
                "name": "Domínio de Autenticação",
                "requirements": ["req1", "req2", "req3"],
            },
        ],
    }
)

UNCOVERED_RESPONSE = json.dumps(
    {
        "requirement_ids": {"req1": "A", "req2": "B", "req3": "C"},
        "partitions": [
            {
                "partition_id": "uc_1",
                "diagram_type": "use_case",
                "name": "UC",
                "requirements": ["req1"],
            },
        ],
    }
)


def _make_partitioner(response: str) -> PartitionerAgent:
    llm = MagicMock()
    llm.complete.return_value = response
    writer = MagicMock()
    writer.write_partition.return_value = MagicMock()
    with (
        patch("agentics.agents.partitioner.Path.exists", return_value=True),
        patch(
            "agentics.agents.partitioner.Path.read_text", return_value="tmpl {requirements_text}"
        ),
    ):
        return PartitionerAgent(llm, writer)


def test_partition_returns_list():
    agent = _make_partitioner(VALID_RESPONSE)
    partitions = agent.partition("req1: login\nreq2: admin\nreq3: validate")
    assert len(partitions) == 2
    assert partitions[0].partition_id == "uc_1"
    assert partitions[0].diagram_type == "use_case"
    assert "req1" in partitions[0].requirements


def test_partition_persists_to_disk():
    agent = _make_partitioner(VALID_RESPONSE)
    agent.partition("req1: login\nreq2: admin\nreq3: validate")
    assert agent.writer.write_partition.call_count == 2


def test_uncovered_requirements_raises():
    agent = _make_partitioner(UNCOVERED_RESPONSE)
    with pytest.raises(PartitionError, match="req2"):
        agent.partition("some requirements")


def test_empty_partitions_raises():
    response = json.dumps({"requirement_ids": {}, "partitions": []})
    agent = _make_partitioner(response)
    with pytest.raises(PartitionError, match="no partitions"):
        agent.partition("requirements")


def test_invalid_json_raises():
    agent = _make_partitioner("not json")
    with pytest.raises(PartitionError):
        agent.partition("requirements")
