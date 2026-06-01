from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
class PipelineContext:
    """Accumulated context from prior pipeline phases (Super-Prompt methodology)."""

    business_rules: str = ""
    use_case_puml: str = ""
    sequence_pumls: list[str] = field(default_factory=list)
    domain_pumls: list[str] = field(default_factory=list)

    def with_business_rules(self, rules: str) -> PipelineContext:
        return PipelineContext(
            business_rules=rules,
            use_case_puml=self.use_case_puml,
            sequence_pumls=list(self.sequence_pumls),
            domain_pumls=list(self.domain_pumls),
        )

    def with_use_case(self, puml: str) -> PipelineContext:
        return PipelineContext(
            business_rules=self.business_rules,
            use_case_puml=puml,
            sequence_pumls=list(self.sequence_pumls),
            domain_pumls=list(self.domain_pumls),
        )

    def with_sequence(self, puml: str) -> PipelineContext:
        return PipelineContext(
            business_rules=self.business_rules,
            use_case_puml=self.use_case_puml,
            sequence_pumls=self.sequence_pumls + [puml],
            domain_pumls=list(self.domain_pumls),
        )

    def with_domain(self, puml: str) -> PipelineContext:
        return PipelineContext(
            business_rules=self.business_rules,
            use_case_puml=self.use_case_puml,
            sequence_pumls=list(self.sequence_pumls),
            domain_pumls=self.domain_pumls + [puml],
        )


@dataclass
class Partition:
    partition_id: str
    diagram_type: str
    requirements: list[str]
    name: str
    req_texts: dict[str, str] = None  # req_id -> full text
    pipeline_context: PipelineContext = None  # accumulated context from prior phases

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

    @staticmethod
    def _build_context_section(ctx: PipelineContext | None) -> str:
        """Build a markdown section with accumulated context from prior phases."""
        if ctx is None:
            return "(no prior context)"
        parts = []
        if ctx.business_rules:
            parts.append(f"## Business Rules Extracted\n{ctx.business_rules}")
        if ctx.use_case_puml:
            parts.append(
                f"## Use Case Diagram (previously generated)\n```plantuml\n{ctx.use_case_puml}\n```"
            )
        if ctx.sequence_pumls:
            seq_text = "\n\n".join(f"```plantuml\n{s}\n```" for s in ctx.sequence_pumls)
            parts.append(f"## Sequence Diagrams (previously generated)\n{seq_text}")
        if ctx.domain_pumls:
            dom_text = "\n\n".join(f"```plantuml\n{d}\n```" for d in ctx.domain_pumls)
            parts.append(f"## Class Diagrams (previously generated)\n{dom_text}")
        return "\n\n".join(parts) if parts else "(no prior context)"

    @abstractmethod
    def build_prompt(self, partition: Partition, error_context: str = "") -> list[dict]:
        """Return the messages list for the LLM."""

    def build_prompt_from_template(self, partition: Partition, template_name: str, error_context: str = "") -> list[dict]:
        """Build prompt from a template file with standard placeholder substitution."""
        import re
        template = self._load_prompt(template_name)
        diagram_id = partition.partition_id
        req_list = ", ".join(partition.requirements)
        req_lines = "\n".join(
            f"{rid}: {partition.req_texts.get(rid, '(no text)')}"
            for rid in partition.requirements
        )
        context_section = self._build_context_section(partition.pipeline_context)
        prompt = (
            template.replace("{diagram_id}", diagram_id)
            .replace("{diagram_name}", partition.name)
            .replace("{req_list}", req_list)
            .replace("{requirements}", req_lines)
            .replace("{accumulated_context}", context_section)
            .replace("{error_context}", error_context or "(none)")
        )
        return [{"role": "user", "content": prompt}]

    @abstractmethod
    def parse_output(self, raw: str) -> str:
        """Extract clean PlantUML text from LLM response."""

    def parse_puml_output(self, raw: str) -> str:
        """Extract PlantUML code between @startuml/@enduml tags."""
        import re
        match = re.search(r"(@startuml.*?@enduml)", raw, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return raw.strip()

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

        # Build related_diagrams from pipeline context
        related: list[str] = []
        if partition.pipeline_context:
            ctx = partition.pipeline_context
            if ctx.use_case_puml:
                related.append(ctx.use_case_puml)
            related.extend(ctx.sequence_pumls)
            related.extend(ctx.domain_pumls)

        for round_num in range(max_refinements + 1):
            self.logger.info("[%s] Critique round %d/%d", diagram_id, round_num, max_refinements)
            critique = self.critic.evaluate(
                puml_text=puml_text,
                diagram_type=partition.diagram_type,
                requirements=partition.requirements,
                related_diagrams=related,
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
