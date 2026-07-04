from __future__ import annotations

from fastapi import APIRouter, Request

from agentics.api.models import ConfigResponse, ConfigUpdateRequest
from agentics.config import Config

router = APIRouter()

PROVIDER_MODELS = {
    "anthropic": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "gemini": ["gemini-2.5-flash", "gemini-2.0-flash"],
    "glm": ["glm-4-plus", "glm-4", "glm-4-flash"],
    "grok": ["grok-3", "grok-3-mini"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
}

AVAILABLE_PROVIDERS = list(PROVIDER_MODELS.keys())


@router.get("/config")
async def get_config(request: Request) -> ConfigResponse:
    config: Config = request.app.state.config
    return ConfigResponse(
        provider=config.llm_provider,
        model=config.llm_model,
        temperature=config.llm_temperature,
        available_providers=AVAILABLE_PROVIDERS,
        provider_models=PROVIDER_MODELS,
    )


@router.put("/config")
async def update_config(
    request: Request, body: ConfigUpdateRequest
) -> ConfigResponse:
    config: Config = request.app.state.config
    if body.provider is not None:
        config.llm_provider = body.provider.value
    if body.model is not None:
        config.llm_model = body.model
    if body.temperature is not None:
        config.llm_temperature = body.temperature
    return ConfigResponse(
        provider=config.llm_provider,
        model=config.llm_model,
        temperature=config.llm_temperature,
        available_providers=AVAILABLE_PROVIDERS,
        provider_models=PROVIDER_MODELS,
    )
