from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentics.api.routers import config_routes, diagrams, generate, history
from agentics.api.services.job_store import JobStore
from agentics.config import Config


def create_app() -> FastAPI:
    app = FastAPI(title="Agentics API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared state
    app.state.config = Config()
    app.state.job_store = JobStore(
        data_dir=os.getenv("AGENTICS_DATA_DIR", "./data/jobs")
    )
    app.state.executor = ThreadPoolExecutor(max_workers=2)

    # Routers
    app.include_router(generate.router, prefix="/api")
    app.include_router(diagrams.router, prefix="/api")
    app.include_router(config_routes.router, prefix="/api")
    app.include_router(history.router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


def run() -> None:
    import uvicorn

    uvicorn.run(
        "agentics.api.app:create_app",
        factory=True,
        reload=True,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    run()
