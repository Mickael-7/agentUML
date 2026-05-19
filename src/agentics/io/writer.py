from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentics.config import Config


class DiagramWriter:
    def __init__(self, config: Config) -> None:
        self._output_dir = config.output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        (self._output_dir / "partitions").mkdir(exist_ok=True)

    def write_puml(self, diagram_id: str, content: str, draft: bool = False) -> Path:
        suffix = ".draft.puml" if draft else ".puml"
        path = self._output_dir / f"{diagram_id}{suffix}"
        path.write_text(content, encoding="utf-8")
        return path

    def write_report(self, name: str, content: str) -> Path:
        path = self._output_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def write_partition(self, partition_id: str, data: dict) -> Path:
        import json

        path = self._output_dir / "partitions" / f"partition_{partition_id}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
