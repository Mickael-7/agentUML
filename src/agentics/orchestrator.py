from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agentics.agents.base import Partition, ValidationError
from agentics.agents.critic import CriticAgent
from agentics.agents.domain import DomainAgent
from agentics.agents.partitioner import PartitionerAgent
from agentics.agents.requirements_quality import RequirementsQualityAgent
from agentics.agents.sequence import SequenceAgent
from agentics.agents.specialization import SpecializationAgent
from agentics.agents.use_case import UseCaseAgent
from agentics.config import Config
from agentics.io.reader import DocumentReader
from agentics.io.writer import DiagramWriter
from agentics.llm.base import create_llm_client
from agentics.validators.plantuml_cli import PlantUMLValidator
from agentics.validators.semantic import SemanticValidator, cross_validate

logger = logging.getLogger(__name__)

_AGENT_MAP = {
    "use_case": UseCaseAgent,
    "domain_class": DomainAgent,
    "sequence": SequenceAgent,
    "specialized_class": SpecializationAgent,
}


def _run_group(
    partition: Partition,
    llm,
    config: Config,
    writer: DiagramWriter,
    validator_cli: PlantUMLValidator,
    sem_validator: SemanticValidator,
    critic: CriticAgent,
) -> tuple[str, str | None]:
    """Run GVCR cycle for a single partition. Returns (diagram_id, error_or_None)."""
    AgentClass = _AGENT_MAP.get(partition.diagram_type)
    if AgentClass is None:
        return partition.partition_id, f"Unknown diagram type: {partition.diagram_type}"
    agent = AgentClass(
        llm=llm,
        config=config,
        writer=writer,
        validator_cli=validator_cli,
        semantic_validator=sem_validator,
        critic=critic,
    )
    try:
        path = agent.run(partition)
        logger.info("✓ %s → %s", partition.partition_id, path)
        return partition.partition_id, None
    except ValidationError as e:
        logger.error("✗ %s validation failed: %s", partition.partition_id, e)
        return partition.partition_id, str(e)
    except Exception as e:
        logger.error("✗ %s unexpected error: %s", partition.partition_id, e)
        return partition.partition_id, str(e)


def _run_type_groups(
    type_partitions: list[Partition],
    llm,
    config: Config,
    writer: DiagramWriter,
    validator_cli: PlantUMLValidator,
    sem_validator: SemanticValidator,
    critic: CriticAgent,
) -> list[tuple[str, str | None]]:
    """Process all partitions of a single type sequentially."""
    results = []
    for partition in type_partitions:
        results.append(
            _run_group(partition, llm, config, writer, validator_cli, sem_validator, critic)
        )
    return results


def run_pipeline(input_path: str, output_dir: str | None = None) -> int:
    """
    Run the full Agentics pipeline.
    Returns exit code: 0 = success, 1 = requirements gate failed, 2 = partial failures.
    """
    cfg = Config()
    if output_dir:
        cfg.output_dir = Path(output_dir)
    cfg.validate_llm()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    reader = DocumentReader()
    writer = DiagramWriter(cfg)
    llm = create_llm_client(cfg)
    critic = CriticAgent(llm)
    validator_cli = PlantUMLValidator(cfg)
    sem_validator = SemanticValidator()

    # ── Step 1: Read requirements ──────────────────────────────────────────
    logger.info("Reading requirements from %s", input_path)
    req_text = reader.read(input_path)

    # ── Step 2: Requirements quality gate ──────────────────────────────────
    logger.info("Running requirements quality gate...")
    quality_agent = RequirementsQualityAgent(llm)
    quality_result = quality_agent.evaluate(req_text)

    if not quality_result["is_valid"]:
        logger.error("GATE FAILED: Requirements quality check failed.")
        logger.error("Report:\n%s", quality_result["report"])
        writer.write_report(
            "requirements_quality_report.md",
            f"# Requirements Quality Report\n\n**Status**: FAILED\n\n{quality_result['report']}\n",
        )
        return 1

    logger.info("Requirements quality gate passed.")
    writer.write_report(
        "requirements_quality_report.md",
        f"# Requirements Quality Report\n\n**Status**: PASSED\n\n{quality_result['report']}\n",
    )

    # ── Step 3: Partitioning ───────────────────────────────────────────────
    logger.info("Running partitioner...")
    partitioner = PartitionerAgent(llm, writer)
    partitions = partitioner.partition(req_text)
    logger.info("Created %d partitions.", len(partitions))

    # Group partitions by diagram type for parallel execution
    groups: dict[str, list[Partition]] = {}
    for p in partitions:
        groups.setdefault(p.diagram_type, []).append(p)

    # ── Step 4: Run agents in parallel (one thread per type) ──────────────
    logger.info("Starting diagram generation (%d types in parallel)...", len(groups))
    all_errors: list[tuple[str, str]] = []
    generated_pumls: list[dict] = []

    with ThreadPoolExecutor(max_workers=len(groups) or 1) as executor:
        futures = {
            executor.submit(
                _run_type_groups,
                type_partitions,
                llm,
                cfg,
                writer,
                validator_cli,
                sem_validator,
                critic,
            ): diagram_type
            for diagram_type, type_partitions in groups.items()
        }
        for future in as_completed(futures):
            diagram_type = futures[future]
            try:
                results = future.result()
                for diagram_id, error in results:
                    if error:
                        all_errors.append((diagram_id, error))
                    else:
                        puml_path = cfg.output_dir / f"{diagram_id}.puml"
                        if puml_path.exists():
                            generated_pumls.append(
                                {
                                    "diagram_id": diagram_id,
                                    "diagram_type": diagram_type,
                                    "puml_text": puml_path.read_text(encoding="utf-8"),
                                }
                            )
            except Exception as e:
                logger.error("Thread for '%s' crashed: %s", diagram_type, e)
                all_errors.append((diagram_type, str(e)))

    # ── Step 5: Cross-diagram validation ──────────────────────────────────
    logger.info("Running cross-diagram validation on %d diagrams...", len(generated_pumls))
    cross_report = cross_validate(generated_pumls)
    writer.write_report("cross_validation_report.md", cross_report.to_markdown())

    if cross_report.inconsistencies:
        logger.warning(
            "Cross-validation found %d inconsistencies (see cross_validation_report.md).",
            len(cross_report.inconsistencies),
        )

    # ── Summary ────────────────────────────────────────────────────────────
    total = len(partitions)
    failed = len(all_errors)
    succeeded = total - failed
    logger.info(
        "Pipeline complete: %d/%d diagrams generated successfully.",
        succeeded,
        total,
    )
    if all_errors:
        for diagram_id, err in all_errors:
            logger.warning("  FAILED: %s — %s", diagram_id, err)
        return 2

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentics: Generate PlantUML diagrams from requirements."
    )
    parser.add_argument("--input", required=True, help="Path to the requirements document")
    parser.add_argument("--output", default=None, help="Output directory for .puml files")
    args = parser.parse_args()

    sys.exit(run_pipeline(args.input, args.output))


if __name__ == "__main__":
    main()
