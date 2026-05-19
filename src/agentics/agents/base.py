from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentics.agents.critic import CriticAgent
    from agentics.config import Config
    from agentics.io.writer import DiagramWriter
    from agentics.llm.base import LLMClient
    from agentics.validators.plantuml_cli import PlantUMLValidator
    from agentics.validators.semantic import SemanticValidator


class ValidationError(Exception):
    pass


@dataclass
class Partition:
    partition_id: str
    diagram_type: str
    requirements: list[str]
    name: str
    req_texts: dict[str, str] = None  # req_id -> full text

    def __post_init__(self):
        if self.req_texts is None:
            self.req_texts = {}

    @classmethod
    def from_dict(cls, data: dict) -> Partition:
        return cls(
            partition_id=data["partition_id"],
            diagram_type=data["diagram_type"],
            requirements=data["requirements"],
            name=data["name"],
            req_texts=data.get("req_texts", {}),
        )

    def to_dict(self) -> dict:
        return {
            "partition_id": self.partition_id,
            "diagram_type": self.diagram_type,
            "requirements": self.requirements,
            "name": self.name,
            "req_texts": self.req_texts,
        }


class Agent(ABC):
    diagram_type: str = ""

    def __init__(
        self,
        llm: LLMClient,
        config: Config,
        writer: DiagramWriter,
        validator_cli: PlantUMLValidator,
        semantic_validator: SemanticValidator,
        critic: CriticAgent,
    ) -> None:
        self.llm = llm
        self.config = config
        self.writer = writer
        self.validator_cli = validator_cli
        self.semantic_validator = semantic_validator
        self.critic = critic
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_prompt(self, name: str) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / name
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                "Create the prompt file before running this agent."
            )
        return prompt_path.read_text(encoding="utf-8")

    @abstractmethod
    def build_prompt(self, partition: Partition, error_context: str = "") -> list[dict]:
        """Return the messages list for the LLM."""

    @abstractmethod
    def parse_output(self, raw: str) -> str:
        """Extract clean PlantUML text from LLM response."""

    def run(self, partition: Partition) -> str:
        if self.diagram_type and partition.diagram_type != self.diagram_type:
            raise ValueError(
                f"{self.__class__.__name__} handles '{self.diagram_type}' diagrams "
                f"but received partition with type '{partition.diagram_type}'"
            )

        diagram_id = f"{partition.diagram_type.split('_')[0]}_{partition.partition_id}"
        # Use the partition_id directly if it already has the type prefix
        if "_" in partition.partition_id:
            diagram_id = partition.partition_id

        self.logger.info("Starting GVCR cycle for %s", diagram_id)

        puml_text = ""
        error_ctx = ""

        # ── GENERATION + VALIDATION RETRY LOOP ──────────────────────────────
        max_retries = self.config.max_validation_retries
        for attempt in range(1, max_retries + 1):
            self.logger.info("[%s] Generation attempt %d/%d", diagram_id, attempt, max_retries)
            messages = self.build_prompt(partition, error_context=error_ctx)
            raw = self.llm.complete(messages)
            puml_text = self.parse_output(raw)

            # Syntactic validation
            is_valid, syntax_err = self.validator_cli.check(puml_text)
            if not is_valid:
                self.logger.warning(
                    "[%s] Syntax error (attempt %d): %s", diagram_id, attempt, syntax_err
                )
                error_ctx = f"SYNTAX ERROR from PlantUML CLI:\n{syntax_err}"
                continue

            # Semantic validation
            sem_result = self.semantic_validator.validate(puml_text, partition.diagram_type)
            if not sem_result.is_valid:
                sem_errors = "; ".join(e.message for e in sem_result.errors)
                self.logger.warning(
                    "[%s] Semantic errors (attempt %d): %s", diagram_id, attempt, sem_errors
                )
                error_ctx = f"SEMANTIC ERRORS:\n{sem_errors}"
                continue

            # Validation passed — proceed to critique
            break
        else:
            # Exhausted retries — save draft and raise
            self.logger.error("[%s] Validation failed after %d attempts", diagram_id, max_retries)
            self.writer.write_puml(diagram_id, puml_text, draft=True)
            raise ValidationError(
                f"[{diagram_id}] Validation failed after {max_retries} retries. "
                f"Last error: {error_ctx}. Draft saved as {diagram_id}.draft.puml"
            )

        # ── CRITIQUE + REFINEMENT LOOP ───────────────────────────────────────
        max_refinements = self.config.max_refinement_rounds
        threshold = self.config.critic_score_threshold

        for round_num in range(max_refinements + 1):
            self.logger.info("[%s] Critique round %d/%d", diagram_id, round_num, max_refinements)
            critique = self.critic.evaluate(
                puml_text=puml_text,
                diagram_type=partition.diagram_type,
                requirements=partition.requirements,
                related_diagrams=[],
            )
            score = critique["score"]
            self.logger.info("[%s] Critic score=%d (threshold=%d)", diagram_id, score, threshold)

            if score >= threshold:
                self.logger.info("[%s] Approved by critic. Saving.", diagram_id)
                path = self.writer.write_puml(diagram_id, puml_text, draft=False)
                return str(path)

            if round_num >= max_refinements:
                # No more refinement rounds — save best draft
                self.logger.warning(
                    "[%s] Score %d below threshold after max refinements. Saving draft.",
                    diagram_id,
                    score,
                )
                path = self.writer.write_puml(diagram_id, puml_text, draft=True)
                return str(path)

            # Refine using critic feedback
            issues_text = "\n".join(f"- {i}" for i in critique.get("issues", []))
            suggestions_text = "\n".join(f"- {s}" for s in critique.get("suggestions", []))
            refinement_ctx = (
                f"CRITIC FEEDBACK (score={score}/{10}):\n"
                f"Issues:\n{issues_text}\n"
                f"Suggestions:\n{suggestions_text}"
            )
            self.logger.info("[%s] Refining based on critic feedback.", diagram_id)

            messages = self.build_prompt(partition, error_context=refinement_ctx)
            messages.append({"role": "assistant", "content": puml_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Please refine the PlantUML diagram above based on this feedback:\n\n"
                        f"{refinement_ctx}\n\n"
                        "Produce only the improved PlantUML code."
                    ),
                }
            )
            raw = self.llm.complete(messages)
            puml_text = self.parse_output(raw)

            # Re-validate after refinement
            is_valid, syntax_err = self.validator_cli.check(puml_text)
            if not is_valid:
                self.logger.warning(
                    "[%s] Refined diagram has syntax error: %s", diagram_id, syntax_err
                )
                # Use the pre-refinement version next cycle — skip sem validation
                # and keep puml_text as-is; critic will score it lower

        # Should not reach here
        path = self.writer.write_puml(diagram_id, puml_text, draft=True)
        return str(path)
