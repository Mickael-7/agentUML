from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from agentics.agents.requirements_quality import RequirementsQualityAgent
from agentics.agents.use_case_evaluator import UseCaseDocumentEvaluator
from agentics.agents.use_case_extractor import UseCaseExtractorAgent
from agentics.api.models import UseCaseEvaluationRequest
from agentics.config import Config
from agentics.llm.base import create_llm_client
from agentics.validators.plantuml_cli import PlantUMLValidator
from agentics.validators.semantic import SemanticValidator

router = APIRouter()

_SUPPORTED_EXTS = {".md", ".txt", ".pdf", ".docx"}


async def _read_upload(file: UploadFile) -> str:
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()

    if suffix in {".md", ".txt", ""}:
        return content.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            return "\n".join(pages)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    if suffix == ".docx":
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            from docx import Document
            doc = Document(tmp_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return content.decode("utf-8", errors="replace")


@router.post("/quality")
async def analyze_quality(
    request: Request,
    text: str = Form(None),
    file: UploadFile = File(None),
) -> dict:
    req_text = text or ""
    if file and not req_text.strip():
        req_text = await _read_upload(file)

    if not req_text.strip():
        raise HTTPException(status_code=422, detail="No requirements text provided")

    config: Config = request.app.state.config
    try:
        config.validate_llm()
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    llm = create_llm_client(config)
    agent = RequirementsQualityAgent(llm)
    return agent.evaluate(req_text)


@router.post("/quality/pdf")
async def quality_pdf(body: dict, background_tasks: BackgroundTasks) -> FileResponse:
    """Accept a quality result JSON and return a downloadable PDF."""
    from agentics.io.pdf_report import generate_quality_pdf

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        pdf_path = generate_quality_pdf(body, tmp_dir)
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    background_tasks.add_task(shutil.rmtree, tmp_dir, True)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="quality_report.pdf",
    )


@router.post("/quality/use-cases")
async def evaluate_use_case_documents(
    request: Request,
    body: UseCaseEvaluationRequest,
) -> dict:
    """Evaluate a batch of use-case documents and classify each as correct/incorrect."""
    if not body.documents:
        raise HTTPException(status_code=422, detail="No documents provided")

    config: Config = request.app.state.config
    try:
        config.validate_llm()
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    # Apply the optional max_documents cap (take the FIRST N — do not let the LLM
    # pick "essentials", which would break the user's ground-truth labels).
    docs_in = body.documents
    if body.max_documents is not None and body.max_documents > 0:
        docs_in = docs_in[: body.max_documents]

    llm = create_llm_client(config)
    agent = UseCaseDocumentEvaluator(
        llm,
        plantuml_validator=PlantUMLValidator(config),
        semantic_validator=SemanticValidator(),
    )
    evaluated = agent.evaluate_documents([d.model_dump() for d in docs_in])

    # Merge evaluated results with input metadata and compute accuracy over the
    # labeled subset only.
    documents = []
    correct = 0
    labeled_hits = 0
    labeled_total = 0
    for src, res in zip(docs_in, evaluated, strict=True):
        verdict = res.get("verdict", "incorrect")
        if verdict == "correct":
            correct += 1
        expected = src.expected_verdict
        if expected is None:
            matches = None
        else:
            labeled_total += 1
            matches = verdict == expected
            if matches:
                labeled_hits += 1
        documents.append(
            {
                "name": src.name,
                "verdict": verdict,
                "checks": res.get("checks", {}),
                "errors": res.get("errors", []),
                "justification": res.get("justification", ""),
                "correction": res.get("correction", ""),
                "summary": res.get("summary", ""),
                "expected_verdict": expected,
                "matches_expected": matches,
            }
        )

    evaluated_count = len(documents)
    accuracy = round(100 * labeled_hits / labeled_total, 1) if labeled_total else None

    return {
        "summary": {
            "total": len(body.documents),
            "evaluated": evaluated_count,
            "correct": correct,
            "incorrect": evaluated_count - correct,
            "accuracy": accuracy,
        },
        "documents": documents,
    }


@router.post("/quality/use-cases/pdf")
async def use_case_eval_pdf(body: dict, background_tasks: BackgroundTasks) -> FileResponse:
    """Accept a use-case evaluation result JSON and return a downloadable PDF."""
    from agentics.io.pdf_report import generate_use_case_eval_pdf

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        pdf_path = generate_use_case_eval_pdf(body, tmp_dir)
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    background_tasks.add_task(shutil.rmtree, tmp_dir, True)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="use_case_evaluation.pdf",
    )


@router.post("/quality/analyze-all")
async def analyze_all(
    request: Request,
    text: str = Form(None),
    file: UploadFile = File(None),
) -> dict:
    """Integrated pipeline: requirements quality + extract & evaluate each use case."""
    req_text = text or ""
    if file and not req_text.strip():
        req_text = await _read_upload(file)

    if not req_text.strip():
        raise HTTPException(status_code=422, detail="No requirements text provided")

    config: Config = request.app.state.config
    try:
        config.validate_llm()
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    llm = create_llm_client(config)

    # 1) Overall requirements quality (4 dimensions).
    requirements = RequirementsQualityAgent(llm).evaluate(req_text)

    # 2) Extract the use cases described in the document.
    use_cases_in = UseCaseExtractorAgent(llm).extract(req_text)

    # 3) Evaluate each extracted use case (parallel internally).
    evaluator = UseCaseDocumentEvaluator(
        llm,
        plantuml_validator=PlantUMLValidator(config),
        semantic_validator=SemanticValidator(),
    )
    evaluated = evaluator.evaluate_documents([{"text": uc["text"]} for uc in use_cases_in])

    use_cases = []
    correct = 0
    for src, res in zip(use_cases_in, evaluated, strict=True):
        verdict = res.get("verdict", "incorrect")
        if verdict == "correct":
            correct += 1
        use_cases.append(
            {
                "name": src.get("name", ""),
                "verdict": verdict,
                "checks": res.get("checks", {}),
                "errors": res.get("errors", []),
                "justification": res.get("justification", ""),
                "correction": res.get("correction", ""),
                "summary": res.get("summary", ""),
            }
        )

    return {
        "requirements": requirements,
        "use_cases": use_cases,
        "summary": {
            "use_cases_found": len(use_cases),
            "correct": correct,
            "incorrect": len(use_cases) - correct,
        },
    }


@router.post("/quality/analyze-all/pdf")
async def analyze_all_pdf(body: dict, background_tasks: BackgroundTasks) -> FileResponse:
    """Accept an integrated-analysis result JSON and return a downloadable PDF."""
    from agentics.io.pdf_report import generate_analysis_pdf

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        pdf_path = generate_analysis_pdf(body, tmp_dir)
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    background_tasks.add_task(shutil.rmtree, tmp_dir, True)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="analysis_report.pdf",
    )
