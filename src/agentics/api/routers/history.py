from __future__ import annotations

from fastapi import APIRouter, Request

from agentics.api.services.job_store import JobStore

router = APIRouter()


def _get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store


@router.get("/history")
async def list_history(limit: int = 20, offset: int = 0, request: Request = None) -> dict:
    job_store = _get_job_store(request)
    jobs, total = job_store.list_jobs(limit=limit, offset=offset)
    return {"jobs": jobs, "total": total}


@router.delete("/history/{job_id}")
async def delete_job(job_id: str, request: Request) -> dict:
    job_store = _get_job_store(request)
    deleted = job_store.delete_job(job_id)
    return {"deleted": deleted}
