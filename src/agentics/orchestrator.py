from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from agentics.agents.base import PipelineContext
from agentics.agents.business_rules import BusinessRulesAgent
from agentics.agents.critic import CriticAgent
from agentics.agents.partitioner import PartitionerAgent
from agentics.agents.requirements_quality import RequirementsQualityAgent
from agentics.config import Config
from agentics.io.reader import DocumentReader
from agentics.io.writer import DiagramWriter
from agentics.llm.base import create_llm_client
from agentics.validators.plantuml_cli import PlantUMLValidator
from agentics.validators.semantic import SemanticValidator, cross_validate
from agentics.api.services.pipeline_runner import run_phases

logger = logging.getLogger(__name__)


def run_pipeline(input_path: str, output_dir: str | None = None) -> int:
    """
    Run the full Agentics pipeline (CLI entry point).
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

    # ── Step 4: Business Rules Extraction ──────────────────────────────────
    ctx = PipelineContext()
    if cfg.super_prompt_mode and cfg.enable_business_rules:
        logger.info("Extracting business rules...")
        rules_agent = BusinessRulesAgent(llm)
        rules_result = rules_agent.extract(req_text)
        ctx = ctx.with_business_rules(rules_result["rules_text"])
        writer.write_report("business_rules.json", json.dumps(rules_result["rules"], indent=2, ensure_ascii=False))
        logger.info("Extracted %d business rules across %d domains", len(rules_result["rules"]), len(rules_result.get("domains", [])))

    # ── Step 5: Run phases ─────────────────────────────────────────────────
    generated_pumls, all_errors, _ = run_phases(
        partitions=partitions,
        ctx=ctx,
        cfg=cfg,
        llm=llm,
        writer=writer,
        validator_cli=validator_cli,
        sem_validator=sem_validator,
        critic=critic,
        super_prompt_mode=cfg.super_prompt_mode,
    )

    # ── Step 6: Cross-diagram validation ──────────────────────────────────
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

    usage = llm.token_usage.to_dict()
    logger.info(
        "Token usage: %d total (%d prompt / %d output / %d calls)",
        usage["total_tokens"], usage["prompt_tokens"], usage["completion_tokens"], usage["call_count"],
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
