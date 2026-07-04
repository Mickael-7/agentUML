"""Shared pipeline runner used by both API service and CLI orchestrator.

Contains the sequential-phase execution logic with context accumulation
(Super-Prompt methodology) and the agent map.
"""
from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from agentics.agents.base import Partition, PipelineContext, ValidationError
from agentics.agents.critic import CriticAgent
from agentics.agents.domain import DomainAgent
from agentics.agents.sequence import SequenceAgent
from agentics.agents.specialization import SpecializationAgent
from agentics.agents.use_case import UseCaseAgent
from agentics.config import Config
from agentics.io.writer import DiagramWriter
from agentics.llm.base import create_llm_client
from agentics.validators.plantuml_cli import PlantUMLValidator
from agentics.validators.semantic import SemanticValidator

logger = logging.getLogger(__name__)

AGENT_MAP = {
    "use_case": UseCaseAgent,
    "domain_class": DomainAgent,
    "sequence": SequenceAgent,
    "specialized_class": SpecializationAgent,
}

PHASE_ORDER = ["use_case", "sequence", "domain_class", "specialized_class"]


def accumulate_context(ctx: PipelineContext, phase_type: str, puml_text: str) -> PipelineContext:
    """Accumulate generated diagram into pipeline context for subsequent phases."""
    if phase_type == "use_case":
        return ctx.with_use_case(puml_text)
    elif phase_type == "sequence":
        return ctx.with_sequence(puml_text)
    elif phase_type == "domain_class":
        return ctx.with_domain(puml_text)
    return ctx


def run_single_partition(
    partition: Partition,
    ctx: PipelineContext | None,
    cfg: Config,
    llm,
    writer: DiagramWriter,
    validator_cli: PlantUMLValidator,
    sem_validator: SemanticValidator,
    critic: CriticAgent,
    emit: Callable[[str, dict], None] | None = None,
) -> dict:
    """Run a single partition through the GVCR cycle. Returns result dict."""
    partition.pipeline_context = ctx

    diagram_id = (
        partition.partition_id
        if "_" in partition.partition_id
        else f"{partition.diagram_type.split('_')[0]}_{partition.partition_id}"
    )
    AgentClass = AGENT_MAP.get(partition.diagram_type)
    if AgentClass is None:
        return {
            "diagram_id": diagram_id,
            "diagram_type": partition.diagram_type,
            "name": partition.name,
            "puml_text": "",
            "error": f"Unknown diagram type: {partition.diagram_type}",
        }

    agent = AgentClass(
        llm=llm, config=cfg, writer=writer,
        validator_cli=validator_cli,
        semantic_validator=sem_validator, critic=critic,
        emit=emit,
    )
    try:
        path = agent.run(partition)
        logger.info("Diagram %s generated: %s", diagram_id, path)
        puml_path = cfg.output_dir / f"{diagram_id}.puml"
        puml_text = ""
        if puml_path.exists():
            puml_text = puml_path.read_text(encoding="utf-8")
        return {
            "diagram_id": diagram_id,
            "diagram_type": partition.diagram_type,
            "name": partition.name,
            "puml_text": puml_text,
            "error": None,
        }
    except ValidationError as e:
        logger.error("Validation failed for %s: %s", diagram_id, e)
        return {"diagram_id": diagram_id, "diagram_type": partition.diagram_type, "name": partition.name, "puml_text": "", "error": str(e)}
    except Exception as e:
        logger.error("Error generating %s: %s", diagram_id, e)
        return {"diagram_id": diagram_id, "diagram_type": partition.diagram_type, "name": partition.name, "puml_text": "", "error": str(e)}


def run_phases(
    partitions: list[Partition],
    ctx: PipelineContext,
    cfg: Config,
    llm,
    writer: DiagramWriter,
    validator_cli: PlantUMLValidator,
    sem_validator: SemanticValidator,
    critic: CriticAgent,
    on_diagram_complete: Callable[[dict], None] | None = None,
    super_prompt_mode: bool = True,
    emit: Callable[[str, dict], None] | None = None,
) -> tuple[list[dict], list[tuple[str, str]], PipelineContext]:
    """Execute all partitions through sequential phases with context accumulation.

    Args:
        partitions: List of partitions to process.
        ctx: Initial pipeline context (with business rules).
        cfg: Configuration.
        llm: LLM client.
        writer: Diagram writer.
        validator_cli: PlantUML validator.
        sem_validator: Semantic validator.
        critic: Critic agent.
        on_diagram_complete: Callback when a diagram completes (for SSE emission).
        super_prompt_mode: If True, run sequential with context. If False, run parallel.

    Returns:
        (generated_pumls, errors, final_context)
    """
    all_errors: list[tuple[str, str]] = []
    generated_pumls: list[dict] = []

    if super_prompt_mode:
        phase_partitions: dict[str, list[Partition]] = {}
        for p in partitions:
            phase_partitions.setdefault(p.diagram_type, []).append(p)

        for phase_type in PHASE_ORDER:
            if phase_type not in phase_partitions:
                continue

            phase_list = phase_partitions[phase_type]
            logger.info("Phase '%s': generating %d diagram(s)", phase_type, len(phase_list))

            if len(phase_list) == 1:
                result = run_single_partition(
                    phase_list[0], ctx, cfg, llm, writer,
                    validator_cli, sem_validator, critic,
                    emit=emit,
                )
                if on_diagram_complete:
                    on_diagram_complete(result)
                if result["error"]:
                    all_errors.append((result["diagram_id"], result["error"]))
                else:
                    if result["puml_text"]:
                        generated_pumls.append({
                            "diagram_id": result["diagram_id"],
                            "diagram_type": phase_type,
                            "puml_text": result["puml_text"],
                        })
                    ctx = accumulate_context(ctx, phase_type, result["puml_text"])
            else:
                phase_pumls: list[tuple[str, str]] = []
                with ThreadPoolExecutor(max_workers=min(len(phase_list), 4)) as executor:
                    futures = {
                        executor.submit(
                            run_single_partition, p, ctx, cfg, llm, writer,
                            validator_cli, sem_validator, critic,
                            emit=emit,
                        ): p
                        for p in phase_list
                    }
                    for future in as_completed(futures):
                        partition = futures[future]
                        try:
                            result = future.result()
                            if on_diagram_complete:
                                on_diagram_complete(result)
                            if result["error"]:
                                all_errors.append((result["diagram_id"], result["error"]))
                            else:
                                if result["puml_text"]:
                                    generated_pumls.append({
                                        "diagram_id": result["diagram_id"],
                                        "diagram_type": phase_type,
                                        "puml_text": result["puml_text"],
                                    })
                                    phase_pumls.append((partition.partition_id, result["puml_text"]))
                        except Exception as e:
                            logger.error("Phase '%s' partition crashed: %s", phase_type, e)
                            all_errors.append((partition.partition_id, str(e)))
                for _, puml in phase_pumls:
                    ctx = accumulate_context(ctx, phase_type, puml)
    else:
        # Legacy parallel mode
        for partition in partitions:
            result = run_single_partition(
                partition, None, cfg, llm, writer,
                validator_cli, sem_validator, critic,
                emit=emit,
            )
            if on_diagram_complete:
                on_diagram_complete(result)
            if result["error"]:
                all_errors.append((result["diagram_id"], result["error"]))
            else:
                if result["puml_text"]:
                    generated_pumls.append({
                        "diagram_id": result["diagram_id"],
                        "diagram_type": partition.diagram_type,
                        "puml_text": result["puml_text"],
                    })

    return generated_pumls, all_errors, ctx
