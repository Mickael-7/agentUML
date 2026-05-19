from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentics.config import Config


class PlantUMLValidator:
    def __init__(self, config: Config) -> None:
        self._jar = config.plantuml_jar

    def _build_cmd(self, puml_path: str) -> list[str]:
        jar = self._jar
        if jar.endswith(".jar"):
            return ["java", "-jar", jar, "-checkonly", puml_path]
        return [jar, "-checkonly", puml_path]

    def check(self, puml_text: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".puml", delete=False, encoding="utf-8"
        ) as f:
            f.write(puml_text)
            tmp_path = f.name

        try:
            cmd = self._build_cmd(tmp_path)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, ""
            error_msg = (result.stderr or result.stdout).strip()
            return False, error_msg
        except subprocess.TimeoutExpired:
            return False, "PlantUML validation timed out after 30s"
        except FileNotFoundError as e:
            return False, f"PlantUML command not found: {e}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
