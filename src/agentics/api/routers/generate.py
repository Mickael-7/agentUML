from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from agentics.api.services.job_store import JobStore
from agentics.api.services.pipeline_service import run_pipeline_background
from agentics.config import Config

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level event queues: job_id -> asyncio.Queue
_event_queues: dict[str, asyncio.Queue] = {}


def _get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store


def _emit_factory(job_id: str, loop: asyncio.AbstractEventLoop) -> callable:
    queue = _event_queues.setdefault(job_id, asyncio.Queue())

    def emit(event_type: str, data: dict) -> None:
        msg = json.dumps({"event": event_type, **data})
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    return emit


@router.post("/generate")
async def create_job(
    request: Request,
    text: str = Form(None),
    file: UploadFile = File(None),
    provider: str = Form(None),
    model: str = Form(None),
) -> dict:
    job_id = str(uuid.uuid4())[:8]
    job_store = _get_job_store(request)
    job_dir = job_store.create_job(job_id)

    # Read text from file upload if no text provided
    req_text = text or ""
    filename = None
    if file and not req_text:
        content = await file.read()
        req_text = content.decode("utf-8", errors="replace")
        filename = file.filename

    if not req_text.strip():
        return {"job_id": job_id, "error": "No requirements text provided"}

    # Use the shared app config as base (respects Settings dialog changes)
    base_config: Config = request.app.state.config
    config = base_config.copy()
    config.output_dir = job_dir / "output"
    # Apply per-request overrides (from frontend generation form)
    if provider:
        config.llm_provider = provider
    if model:
        config.llm_model = model

    loop = asyncio.get_event_loop()
    emit = _emit_factory(job_id, loop)

    def _run():
        exit_code = run_pipeline_background(job_id, req_text, config, emit, filename)
        # Update job metadata
        job_store.update_job_meta(job_id, {
            "status": "completed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
        })

    request.app.state.executor.submit(_run)

    return {"job_id": job_id}


@router.get("/generate/{job_id}/stream")
async def stream_progress(job_id: str) -> StreamingResponse:
    queue = _event_queues.setdefault(job_id, asyncio.Queue())

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=300)
                data = json.loads(msg)
                event_type = data.pop("event", "status")
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                if event_type in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield f"event: ping\ndata: {{}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
