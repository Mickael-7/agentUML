from __future__ import annotations

import copy
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    def __init__(self) -> None:
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
        self.llm_model: str = os.getenv("LLM_MODEL", "claude-opus-4-7")
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_validation_retries: int = int(os.getenv("LLM_MAX_VALIDATION_RETRIES", "3"))
        self.max_refinement_rounds: int = int(os.getenv("LLM_MAX_REFINEMENT_ROUNDS", "2"))
        self.critic_score_threshold: int = int(os.getenv("CRITIC_SCORE_THRESHOLD", "7"))

        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.glm_api_key: str = os.getenv("GLM_API_KEY", "")
        self.grok_api_key: str = os.getenv("GROK_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")

        self.glm_base_url: str = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        self.grok_base_url: str = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1/")
        self.groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1/")

        self.plantuml_jar: str = os.getenv("PLANTUML_JAR", "./tools/plantuml.jar")
        self.output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./output"))

        # Super-Prompt pipeline mode
        self.super_prompt_mode: bool = os.getenv("SUPER_PROMPT_MODE", "true").lower() in ("true", "1", "yes")
        self.enable_business_rules: bool = os.getenv("ENABLE_BUSINESS_RULES", "true").lower() in ("true", "1", "yes")

    def copy(self) -> Config:
        """Create a shallow copy of this config. Thread-safe for read-only attributes."""
        return copy.copy(self)

    def validate_llm(self) -> None:
        key_map = {
            "anthropic": ("ANTHROPIC_API_KEY", self.anthropic_api_key),
            "openai": ("OPENAI_API_KEY", self.openai_api_key),
            "gemini": ("GEMINI_API_KEY", self.gemini_api_key),
            "glm": ("GLM_API_KEY", self.glm_api_key),
            "grok": ("GROK_API_KEY", self.grok_api_key),
            "groq": ("GROQ_API_KEY", self.groq_api_key),
        }
        if self.llm_provider not in key_map:
            raise OSError(
                f"Unknown LLM_PROVIDER '{self.llm_provider}'. "
                f"Choose from: {', '.join(key_map.keys())}"
            )
        env_var, value = key_map[self.llm_provider]
        if not value:
            raise OSError(f"LLM_PROVIDER is '{self.llm_provider}' but {env_var} is not set.")

    def validate_plantuml(self) -> None:
        jar = self.plantuml_jar
        # If it's a bare command name (e.g. "plantuml"), check PATH
        if not jar.endswith(".jar"):
            if shutil.which(jar) is None:
                raise OSError(
                    f"PlantUML command '{jar}' not found on PATH. "
                    "Install PlantUML or set PLANTUML_JAR to the .jar path."
                )
            return
        # Otherwise check the file exists
        if not Path(jar).exists():
            raise OSError(
                f"PlantUML JAR not found at '{jar}'. "
                "Download plantuml.jar and place it at that path, "
                "or set PLANTUML_JAR to its location."
            )
        if shutil.which("java") is None:
            raise OSError("Java is not installed or not on PATH. " "PlantUML requires Java to run.")


config = Config()
