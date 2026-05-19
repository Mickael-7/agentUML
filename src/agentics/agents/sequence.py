from __future__ import annotations

import re

from agentics.agents.base import Agent, Partition


class SequenceAgent(Agent):
    diagram_type = "sequence"

    def build_prompt(self, partition: Partition, error_context: str = "") -> list[dict]:
        template = self._load_prompt("sequence.md")
        diagram_id = partition.partition_id
        req_list = ", ".join(partition.requirements)
        req_lines = "\n".join(
            f"{rid}: {partition.req_texts.get(rid, '(sem texto)')}"
            for rid in partition.requirements
        )
        prompt = (
            template.replace("{diagram_id}", diagram_id)
            .replace("{diagram_name}", partition.name)
            .replace("{req_list}", req_list)
            .replace("{requirements}", req_lines)
            .replace("{error_context}", error_context or "(nenhum)")
        )
        return [{"role": "user", "content": prompt}]

    def parse_output(self, raw: str) -> str:
        match = re.search(r"(@startuml.*?@enduml)", raw, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return raw.strip()


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
    agent = SequenceAgent(
        llm=llm,
        config=config,
        writer=writer,
        validator_cli=PlantUMLValidator(config),
        semantic_validator=SemanticValidator(),
        critic=CriticAgent(llm),
    )
    result = agent.run(partition)
    print(f"Output: {result}")
