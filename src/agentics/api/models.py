from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class LLMProviderEnum(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    gemini = "gemini"
    glm = "glm"
    grok = "grok"
    groq = "groq"


class GenerateRequest(BaseModel):
    text: str | None = None
    filename: str | None = None
    provider: LLMProviderEnum | None = None
    model: str | None = None


class DiagramInfo(BaseModel):
    diagram_id: str
    diagram_type: str
    name: str
    status: str  # "generating" | "completed" | "failed"
    error: str | None = None
    puml_text: str | None = None
    image_url: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # "queued" | "quality_gate" | "extracting_rules" | "partitioning" | "generating" | "completed" | "failed"
    created_at: str
    completed_at: str | None = None
    diagrams: list[DiagramInfo] = []
    quality_report: str | None = None
    cross_validation_report: str | None = None
    error: str | None = None


class ConfigResponse(BaseModel):
    provider: str
    model: str
    temperature: float
    available_providers: list[str]
    provider_models: dict[str, list[str]]


class ConfigUpdateRequest(BaseModel):
    provider: LLMProviderEnum | None = None
    model: str | None = None
    temperature: float | None = None
