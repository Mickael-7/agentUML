from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.agents.base import Partition

if TYPE_CHECKING:
    from agentics.io.writer import DiagramWriter
    from agentics.llm.base import LLMClient


class PartitionError(Exception):
    pass


class PartitionerAgent:
    def __init__(self, llm: LLMClient, writer: DiagramWriter) -> None:
        self.llm = llm
        self.writer = writer
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "partitioner.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    def partition(self, requirements_text: str) -> list[Partition]:
        prompt = self._prompt_template.replace("{requirements_text}", requirements_text)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1)
        data = self._parse_response(raw)

        req_ids = data.get("requirement_ids", {})
        partitions_data = data.get("partitions", [])

        if not partitions_data:
            raise PartitionError("Partitioner returned no partitions.")

        all_req_ids = set(req_ids.keys())
        covered = set()
        partitions: list[Partition] = []

        for p_data in partitions_data:
            reqs = p_data.get("requirements", [])
            covered.update(reqs)
            req_texts = {r: req_ids.get(r, "") for r in reqs}
            partition = Partition(
                partition_id=p_data["partition_id"],
                diagram_type=p_data["diagram_type"],
                requirements=reqs,
                name=p_data.get("name", p_data["partition_id"]),
                req_texts=req_texts,
            )
            partitions.append(partition)
            # Persist to disk
            self.writer.write_partition(partition.partition_id, partition.to_dict())
            self.logger.info(
                "Partition '%s' (%s) saved with %d requirements.",
                partition.partition_id,
                partition.diagram_type,
                len(reqs),
            )

        uncovered = all_req_ids - covered
        if uncovered:
            raise PartitionError(f"Requirements not covered by any partition: {sorted(uncovered)}")

        return partitions

    def _parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise PartitionError(f"Partitioner did not return JSON. Response:\n{raw[:500]}")
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise PartitionError(f"Invalid JSON from partitioner: {e}") from e
