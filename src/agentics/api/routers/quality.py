from __future__ import annotations

import tempfile
from pathlib import Path

import shutil

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from agentics.agents.requirements_quality import RequirementsQualityAgent
from agentics.config import Config
from agentics.llm.base import create_llm_client

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
        raise HTTPException(status_code=503, detail=str(e))

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
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    background_tasks.add_task(shutil.rmtree, tmp_dir, True)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="quality_report.pdf",
    )
