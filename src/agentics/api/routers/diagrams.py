from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from agentics.api.services.job_store import JobStore
from agentics.api.services.mermaid_service import MermaidConverter
from agentics.api.services.render_service import RenderService

router = APIRouter()

_mermaid = MermaidConverter()


def _get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store


@router.get("/diagrams/{job_id}")
async def get_job_diagrams(job_id: str, request: Request) -> dict:
    job_store = _get_job_store(request)
    meta = job_store.get_job_meta(job_id)
    if meta is None:
        return {"error": "Job not found"}
    return meta


@router.get("/diagrams/{job_id}/{diagram_id}")
async def get_diagram(job_id: str, diagram_id: str, request: Request) -> dict:
    job_store = _get_job_store(request)
    puml_text = job_store.get_puml_text(job_id, diagram_id)
    if puml_text is None:
        return {"error": "Diagram not found"}
    return {"diagram_id": diagram_id, "puml_text": puml_text}


@router.get("/diagrams/{job_id}/{diagram_id}/image")
async def get_diagram_image(
    job_id: str, diagram_id: str, format: str = "png", request: Request = None
) -> Response:
    job_store = _get_job_store(request)
    puml_text = job_store.get_puml_text(job_id, diagram_id)
    if puml_text is None:
        return Response(content="Diagram not found", status_code=404)

    config = request.app.state.config
    render = RenderService(config.plantuml_jar)
    fmt = "svg" if format == "svg" else "png"
    try:
        data = render.render(puml_text, fmt=fmt)
    except RuntimeError as e:
        return Response(content=str(e), status_code=500)

    media_type = "image/svg+xml" if fmt == "svg" else "image/png"
    return Response(content=data, media_type=media_type)


@router.get("/diagrams/{job_id}/{diagram_id}/puml")
async def get_diagram_puml(job_id: str, diagram_id: str, request: Request) -> Response:
    job_store = _get_job_store(request)
    puml_text = job_store.get_puml_text(job_id, diagram_id)
    if puml_text is None:
        return Response(content="Diagram not found", status_code=404)
    return Response(content=puml_text, media_type="text/plain")


@router.get("/diagrams/{job_id}/{diagram_id}/mermaid")
async def get_diagram_mermaid(
    job_id: str, diagram_id: str, diagram_type: str = "use_case", request: Request = None
) -> dict:
    job_store = _get_job_store(request)
    puml_text = job_store.get_puml_text(job_id, diagram_id)
    if puml_text is None:
        return {"error": "Diagram not found"}
    mermaid_text = _mermaid.convert(puml_text, diagram_type)
    return {"mermaid_text": mermaid_text}
