from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class JobStore:
    def __init__(self, data_dir: str = "./data/jobs") -> None:
        self._base = Path(data_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _validate_job_id(self, job_id: str) -> None:
        """Prevent path traversal attacks."""
        if not job_id or not all(c.isalnum() or c in "-_" for c in job_id):
            raise ValueError(f"Invalid job_id: '{job_id}'. Only alphanumeric, hyphens, and underscores allowed.")
        resolved = (self._base / job_id).resolve()
        if not str(resolved).startswith(str(self._base)):
            raise ValueError(f"Path traversal detected in job_id: '{job_id}'")

    def _safe_job_dir(self, job_id: str) -> Path:
        """Return validated job directory path."""
        self._validate_job_id(job_id)
        return self._base / job_id

    def _validate_diagram_id(self, diagram_id: str) -> None:
        """Prevent path traversal in diagram IDs."""
        if not diagram_id or not all(c.isalnum() or c in "-_." for c in diagram_id):
            raise ValueError(f"Invalid diagram_id: '{diagram_id}'")

    def create_job(self, job_id: str) -> Path:
        job_dir = self._safe_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "output").mkdir(exist_ok=True)
        meta = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "diagrams": [],
        }
        (job_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        return job_dir

    def get_job_meta(self, job_id: str) -> dict | None:
        meta_path = self._safe_job_dir(job_id) / "meta.json"
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text())

    def update_job_meta(self, job_id: str, updates: dict) -> None:
        meta = self.get_job_meta(job_id)
        if meta is None:
            return
        meta.update(updates)
        (self._safe_job_dir(job_id) / "meta.json").write_text(json.dumps(meta, indent=2))

    def get_puml_text(self, job_id: str, diagram_id: str) -> str | None:
        self._validate_diagram_id(diagram_id)
        job_dir = self._safe_job_dir(job_id) / "output"
        for suffix in (".puml", ".draft.puml"):
            p = job_dir / f"{diagram_id}{suffix}"
            if p.exists():
                return p.read_text(encoding="utf-8")
        return None

    def list_jobs(self, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        jobs = []
        for d in sorted(self._base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if d.is_dir() and (d / "meta.json").exists():
                jobs.append(json.loads((d / "meta.json").read_text()))
        total = len(jobs)
        return jobs[offset : offset + limit], total

    def delete_job(self, job_id: str) -> bool:
        import shutil

        job_dir = self._safe_job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir)
            return True
        return False
