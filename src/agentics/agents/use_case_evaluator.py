from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from agentics.llm.parse_json import parse_llm_json

if TYPE_CHECKING:
    from agentics.llm.base import LLMClient
    from agentics.validators.plantuml_cli import PlantUMLValidator
    from agentics.validators.semantic import SemanticValidator


_PUML_BLOCK = re.compile(r"@startuml[\s\S]*?@enduml", re.IGNORECASE)

# Mermaid fenced blocks: ```mermaid\n ... \n```
_MERMAID_BLOCK = re.compile(r"```mermaid\s*\n([\s\S]*?)\n?```", re.IGNORECASE)

# Recognized Mermaid diagram-type keywords (first token of the body). Used for a
# lightweight structural plausibility check — unlike PlantUML there is no
# bundled Mermaid syntax validator available.
_MERMAID_TYPES = {
    "graph", "flowchart", "sequencediagram", "classdiagram", "statediagram",
    "statediagram-v2", "erdiagram", "gantt", "pie", "journey", "gitgraph",
    "requirementdiagram", "usecase", "mindmap", "timeline", "quadrantchart",
    "xychart-beta", "sankey-beta", "block-beta", "architecture-beta",
    "packet-beta", "c4context", "c4container", "c4component",
}

# Error fragments that mean the validator tool itself is unavailable, not that
# the diagram is invalid. We must not flag symbology as incorrect in that case.
_UNAVAILABLE_MARKERS = ("not found", "not on path", "timed out", "timed-out")


def _check_mermaid(body: str) -> tuple[str, str]:
    """Lightweight Mermaid plausibility check.

    Returns ``(status, type)`` where ``status`` is ``"plausivel"`` if the body
    begins with a recognized Mermaid diagram type, else ``"malformado"``.
    """
    first = ""
    for line in body.splitlines():
        if line.strip():
            first = line.strip()
            break
    parts = first.split()
    token = parts[0].lower() if parts else ""
    base = token.split("-")[0]
    matched = token if token in _MERMAID_TYPES else (base if base in _MERMAID_TYPES else "")
    if matched:
        return "plausivel", matched
    return "malformado", token or "desconhecido"


def _incorrect(
    errors: list[str],
    *,
    checks: dict | None = None,
    justification: str = "",
    correction: str = "",
    summary: str = "",
) -> dict:
    """Build a synthetic 'incorrect' result (used for empty docs and failures)."""
    return {
        "verdict": "incorrect",
        "checks": checks
        or {"has_requirement": False, "has_use_case_context": False, "symbology_correct": False},
        "errors": errors,
        "justification": justification,
        "correction": correction,
        "summary": summary or "Documento avaliado como incorreto.",
    }


class UseCaseDocumentEvaluator:
    """Evaluates use-case documents and classifies each as correct/incorrect."""

    def __init__(
        self,
        llm: LLMClient,
        plantuml_validator: PlantUMLValidator | None = None,
        semantic_validator: SemanticValidator | None = None,
    ) -> None:
        self.llm = llm
        self.plantuml_validator = plantuml_validator
        self.semantic_validator = semantic_validator
        self.logger = logging.getLogger(self.__class__.__name__)
        prompt_path = Path(__file__).parent.parent / "prompts" / "use_case_doc_evaluation.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    # ── single document ──────────────────────────────────────────────────────
    def evaluate_document(self, text: str) -> dict:
        if not text or not text.strip():
            return _incorrect(["Documento vazio — sem conteúdo para avaliar."])

        diagram_ev, semantic_ev, has_diagram = self._build_evidence(text)

        prompt = (
            self._prompt_template.replace("{document_text}", text)
            .replace("{diagram_validation}", diagram_ev)
            .replace("{semantic_validation}", semantic_ev)
        )
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm.complete(messages, temperature=0.1, max_tokens=16384)
        return self._parse_response(raw, has_diagram=has_diagram)

    def _build_evidence(self, text: str) -> tuple[str, str, bool]:
        """Compute the deterministic diagram evidence strings.

        Returns ``(diagram_ev, semantic_ev, has_diagram)``. Supports PlantUML
        (``@startuml`` blocks, with real syntax + semantic validation) and
        Mermaid (``\\`\\`\\`mermaid`` blocks, with a lightweight structural check).
        PlantUML takes precedence when both are present.
        """
        puml_match = _PUML_BLOCK.search(text)
        if puml_match:
            diag_ev, sem_ev = self._plantuml_evidence(puml_match.group(0))
            return diag_ev, sem_ev, True

        merm_match = _MERMAID_BLOCK.search(text)
        if merm_match:
            status, dtype = _check_mermaid(merm_match.group(1))
            if status == "plausivel":
                diag_ev = f"Diagrama Mermaid detectado (tipo: {dtype}). Sintaxe estruturalmente plausível."
            else:
                diag_ev = (
                    f"Diagrama Mermaid detectado, mas malformado "
                    f"(tipo inicial não reconhecido: '{dtype}')."
                )
            sem_ev = "Validação semântica não aplicável a Mermaid (apenas PlantUML)."
            return diag_ev, sem_ev, True

        return (
            "Nenhum diagrama detectado (nem PlantUML @startuml nem Mermaid ```mermaid).",
            "Sem diagrama — validação semântica não aplicável.",
            False,
        )

    def _plantuml_evidence(self, puml: str) -> tuple[str, str]:
        """PlantUML-specific syntax + semantic evidence."""
        # ── syntax ───────────────────────────────────────────────────────────
        if self.plantuml_validator is None:
            diag_ev = "Validação PlantUML indisponível (ferramenta não configurada)."
        else:
            try:
                ok, msg = self.plantuml_validator.check(puml)
            except Exception as e:  # noqa: BLE001 — never let a validator crash the eval
                self.logger.warning("PlantUML validator crashed: %s", e)
                diag_ev = "Validação PlantUML indisponível (erro interno)."
            else:
                low = (msg or "").lower()
                if ok:
                    diag_ev = "Sintaxe PlantUML válida."
                elif any(m in low for m in _UNAVAILABLE_MARKERS):
                    diag_ev = "Validação PlantUML indisponível (ferramenta não configurada)."
                else:
                    diag_ev = f"Sintaxe PlantUML inválida: {msg}"

        # ── semantic ─────────────────────────────────────────────────────────
        if self.semantic_validator is None:
            sem_ev = "Validação semântica indisponível."
        else:
            try:
                result = self.semantic_validator.validate(puml, "use_case")
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Semantic validator crashed: %s", e)
                sem_ev = "Validação semântica indisponível (erro interno)."
            else:
                # The agentics-internal "metadata" rule is not meaningful for
                # external documents — filter it out to avoid misleading noise.
                relevant = [e for e in result.errors if e.rule != "metadata"]
                if not relevant:
                    sem_ev = "Sem erros semânticos relevantes."
                else:
                    sem_ev = "Erros semânticos: " + " | ".join(
                        f"{e.message}" for e in relevant
                    )

        return diag_ev, sem_ev

    def _parse_response(self, raw: str, *, has_diagram: bool) -> dict:
        try:
            data = parse_llm_json(raw, "UseCaseDocumentEvaluator")
        except ValueError as e:
            self.logger.error("UseCaseDocumentEvaluator parse failed: %s", e)
            return _incorrect([f"Falha ao interpretar resposta do agente: {e}"])

        checks = data.get("checks") or {}
        # Normalise checks to the expected shape with sensible defaults.
        has_req = bool(checks.get("has_requirement", False))
        has_ctx = bool(checks.get("has_use_case_context", False))
        # symbology may legitimately be null when there is no diagram.
        raw_sym = checks.get("symbology_correct", None)
        if has_diagram and raw_sym is None:
            # Document had a diagram but the model omitted the verdict — be strict.
            symbology = False
        else:
            symbology = None if raw_sym is None else bool(raw_sym)

        # Derive the verdict from the checks per the documented rule. We do NOT
        # trust a free-standing verdict that contradicts the evidence.
        verdict = "correct" if (has_req and has_ctx and symbology in (True, None)) else "incorrect"

        errors = data.get("errors") or []
        if not isinstance(errors, list):
            errors = [str(errors)]
        if verdict == "incorrect" and not errors:
            errors = ["Documento não atende aos critérios mínimos de qualidade."]

        justification = str(data.get("justification", "") or "")
        correction = str(data.get("correction", "") or "")
        if verdict == "correct":
            correction = ""
        summary = str(data.get("summary", "") or "")

        return {
            "verdict": verdict,
            "checks": {
                "has_requirement": has_req,
                "has_use_case_context": has_ctx,
                "symbology_correct": symbology,
            },
            "errors": [str(e) for e in errors],
            "justification": justification,
            "correction": correction,
            "summary": summary,
        }

    # ── batch ─────────────────────────────────────────────────────────────────
    def evaluate_documents(self, docs: list[dict]) -> list[dict]:
        """Evaluate many documents in parallel, preserving input order.

        Each doc is a dict with at least ``text``. A failing document becomes a
        synthetic 'incorrect' result rather than aborting the batch.
        """
        if not docs:
            return []

        indexed: list[tuple[int, dict]] = list(enumerate(docs))
        results: list[dict | None] = [None] * len(indexed)
        max_workers = min(4, len(indexed))

        def _safe(idx_text: tuple[int, dict]) -> tuple[int, dict]:
            idx, doc = idx_text
            try:
                res = self.evaluate_document(doc.get("text", ""))
            except Exception as e:  # noqa: BLE001 — resilient batch
                self.logger.exception("Evaluation failed for document #%d: %s", idx, e)
                res = _incorrect([f"Falha interna ao avaliar documento: {e}"])
            return idx, res

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_safe, item): item for item in indexed}
            for future in as_completed(futures):
                idx, res = future.result()
                results[idx] = res

        # Backfill any None (defensive — should not happen) with a failure result.
        return [r if r is not None else _incorrect(["Falha interna ao avaliar documento."]) for r in results]
