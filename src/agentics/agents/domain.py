from __future__ import annotations

from agentics.agents.base import Agent, Partition


class DomainAgent(Agent):
    diagram_type = "domain_class"

    def build_prompt(self, partition: Partition, error_context: str = "") -> list[dict]:
        return self.build_prompt_from_template(partition, "domain.md", error_context)

    def parse_output(self, raw: str) -> str:
        return self.parse_puml_output(raw)


if __name__ == "__main__":
    import argparse
    import json
    import logging
    from pathlib import Path

    from agentics.agents.critic import CriticAgent
    from agentics.config import config
    from agentics.io.writer import DiagramWriter
    from agentics.llm.base import create_llm_client
    from agentics.validators.plantuml_cli import PlantUMLValidator
    from agentics.validators.semantic import SemanticValidator

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.partition).read_text(encoding="utf-8"))
    partition = Partition.from_dict(data)

    llm = create_llm_client(config)
    writer = DiagramWriter(config)
    agent = DomainAgent(
        llm=llm,
        config=config,
        writer=writer,
        validator_cli=PlantUMLValidator(config),
        semantic_validator=SemanticValidator(),
        critic=CriticAgent(llm),
    )
    result = agent.run(partition)
    print(f"Output: {result}")
