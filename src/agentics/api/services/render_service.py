from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class RenderService:
    def __init__(self, jar_path: str) -> None:
        self._jar = jar_path

    def render(self, puml_text: str, fmt: str = "png") -> bytes:
        flag = "-tsvg" if fmt == "svg" else ""
        with tempfile.TemporaryDirectory() as tmpdir:
            puml_file = Path(tmpdir) / "diagram.puml"
            puml_file.write_text(puml_text, encoding="utf-8")
            cmd = ["java", "-jar", self._jar, "-charset", "UTF-8"]
            if flag:
                cmd.append(flag)
            cmd.extend(["-output", tmpdir, str(puml_file)])
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"PlantUML render failed: {result.stderr.decode()}")
            ext = "svg" if fmt == "svg" else "png"
            output_file = Path(tmpdir) / f"diagram.{ext}"
            return output_file.read_bytes()
