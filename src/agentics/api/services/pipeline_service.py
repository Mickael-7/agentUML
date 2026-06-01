from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Callable

from agentics.agents.base import PipelineContext
from agentics.agents.business_rules import BusinessRulesAgent
from agentics.agents.critic import CriticAgent
from agentics.agents.requirements_quality import RequirementsQualityAgent
from agentics.agents.partitioner import PartitionerAgent
from agentics.config import Config
from agentics.io.writer import DiagramWriter
from agentics.llm.base import create_llm_client
from agentics.validators.plantuml_cli import PlantUMLValidator
from agentics.validators.semantic import SemanticValidator
from agentics.api.services.pipeline_runner import (
    run_phases,
    PHASE_ORDER,
)

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        job_id: str,
        config: Config,
        emit: Callable[[str, dict], None],
    ) -> None:
        self.job_id = job_id
        self.config = config
        self.emit = emit

    def run(self, text: str, input_filename: str | None = None) -> int:
        try:
            return self._run_sync(text, input_filename)
        except Exception as e:
            logger.exception("Pipeline failed for job %s", self.job_id)
            self.emit("error", {"message": str(e)})
            return 2

    def _run_sync(self, text: str, input_filename: str | None) -> int:
        suffix = ".txt"
        if input_filename:
            ext = Path(input_filename).suffix.lower()
            if ext in (".pdf", ".docx", ".md"):
                suffix = ext
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            tmp_path = f.name

        try:
            self.emit("status", {"status": "quality_gate", "message": "Checking requirements quality..."})

            cfg = self.config
            cfg.validate_llm()

            writer = DiagramWriter(cfg)
            llm = create_llm_client(cfg)
            critic = CriticAgent(llm)
            validator_cli = PlantUMLValidator(cfg)
            sem_validator = SemanticValidator()

            # ── Step 1: Quality gate ─────────────────────────────────────────
            logger.info("Quality gate for job %s", self.job_id)
            quality_agent = RequirementsQualityAgent(llm)
            quality_result = quality_agent.evaluate(text)

            if not quality_result["is_valid"]:
                self.emit("error", {"message": f"Quality gate failed: {quality_result['report']}"})
                return 1

            # ── Step 2: Partitioning ──────────────────────────────────────────
            self.emit("status", {"status": "partitioning", "message": "Partitioning requirements..."})
            partitioner = PartitionerAgent(llm, writer)
            partitions = partitioner.partition(text)

            # ── Step 3: Business Rules Extraction (Phase 1 - Super-Prompt) ───
            ctx = PipelineContext()
            if cfg.super_prompt_mode and cfg.enable_business_rules:
                self.emit("status", {"status": "extracting_rules", "message": "Extracting business rules..."})
                logger.info("Extracting business rules for job %s", self.job_id)
                rules_agent = BusinessRulesAgent(llm)
                rules_result = rules_agent.extract(text)
                ctx = ctx.with_business_rules(rules_result["rules_text"])
                writer.write_report("business_rules.json", json.dumps(rules_result["rules"], indent=2, ensure_ascii=False))
                logger.info("Extracted %d business rules across %d domains", len(rules_result["rules"]), len(rules_result.get("domains", [])))

            # ── Step 4: Diagram generation ───────────────────────────────────
            self.emit("status", {
                "status": "generating",
                "message": f"Generating {len(partitions)} diagrams in sequential phases...",
                "total": len(partitions),
            })

            # Register diagrams in metadata
            for p in partitions:
                self.emit("diagram", {
                    "diagram_id": p.partition_id,
                    "diagram_type": p.diagram_type,
                    "name": p.name,
                    "status": "generating",
                })

            # Callback for diagram completion events
            def on_diagram_complete(result: dict) -> None:
                diagram_id = result["diagram_id"]
                if result["error"]:
                    self.emit("diagram", {
                        "diagram_id": diagram_id,
                        "diagram_type": result["diagram_type"],
                        "name": result["name"],
                        "status": "failed",
                        "error": result["error"],
                    })
                else:
                    self.emit("diagram", {
                        "diagram_id": diagram_id,
                        "diagram_type": result["diagram_type"],
                        "name": result["name"],
                        "status": "completed",
                    })

            generated_pumls, all_errors, _ = run_phases(
                partitions=partitions,
                ctx=ctx,
                cfg=cfg,
                llm=llm,
                writer=writer,
                validator_cli=validator_cli,
                sem_validator=sem_validator,
                critic=critic,
                on_diagram_complete=on_diagram_complete,
                super_prompt_mode=cfg.super_prompt_mode,
                emit=self.emit,
            )

            # ── Step 5: Cross-validation ─────────────────────────────────────
            if generated_pumls:
                from agentics.validators.semantic import cross_validate
                cross_report = cross_validate(generated_pumls)
                writer.write_report("cross_validation_report.md", cross_report.to_markdown())

            total = len(partitions)
            succeeded = total - len(all_errors)
            exit_code = 0 if not all_errors else 2

            self.emit("complete", {
                "job_id": self.job_id,
                "exit_code": exit_code,
                "total": total,
                "succeeded": succeeded,
                "failed": len(all_errors),
                "token_usage": llm.token_usage.to_dict(),
            })
            return exit_code
        finally:
            Path(tmp_path).unlink(missing_ok=True)


def run_pipeline_background(
    job_id: str,
    text: str,
    config: Config,
    emit: Callable[[str, dict], None],
    input_filename: str | None = None,
) -> int:
    service = PipelineService(job_id, config, emit)
    return service.run(text, input_filename)
