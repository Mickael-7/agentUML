from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentics.config import Config

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Tracks token usage across LLM calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, prompt: int, completion: int) -> None:
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += prompt + completion
            self.call_count += 1

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "call_count": self.call_count,
            }


class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Send messages to the LLM and return the text response."""


# Provider registry: name -> (module_path, class_name, api_key_attr, default_model)
_PROVIDER_REGISTRY = {
    "anthropic": ("agentics.llm.anthropic_client", "AnthropicClient", "anthropic_api_key", "claude-sonnet-4-6"),
    "openai": ("agentics.llm.openai_client", "OpenAIClient", "openai_api_key", "gpt-4o-mini"),
    "gemini": ("agentics.llm.gemini_client", "GeminiClient", "gemini_api_key", "gemini-2.5-flash"),
    "glm": ("agentics.llm.glm_client", "GLMClient", "glm_api_key", "glm-5.1"),
    "grok": ("agentics.llm.grok_client", "GrokClient", "grok_api_key", "grok-3-mini"),
    "groq": ("agentics.llm.groq_client", "GroqClient", "groq_api_key", "llama-3.3-70b-versatile"),
}

# Fallback order: free/cheap providers first, premium last
_FALLBACK_ORDER = ["groq", "gemini", "glm", "grok", "openai", "anthropic"]


def _import_client(module_path: str, class_name: str):
    """Dynamically import an LLM client class."""
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _get_available_providers(config: Config) -> list[str]:
    """Return providers that have API keys configured, in fallback order."""
    available = []
    for provider in _FALLBACK_ORDER:
        _, _, key_attr, _ = _PROVIDER_REGISTRY[provider]
        if getattr(config, key_attr, "").strip():
            available.append(provider)
    return available


def _estimate_tokens(messages: list[dict], response: str) -> tuple[int, int]:
    """Rough token estimation when exact counts aren't available.
    Uses ~4 chars per token heuristic."""
    prompt_chars = sum(len(m.get("content", "")) for m in messages)
    prompt_tokens = max(1, prompt_chars // 4)
    completion_tokens = max(1, len(response) // 4)
    return prompt_tokens, completion_tokens


class FallbackLLMClient(LLMClient):
    """LLM client that automatically falls back to other providers on failure.

    Thread-safe: does not mutate the shared config object.
    Tracks token usage across all calls.
    """

    def __init__(self, config: Config) -> None:
        self._config_ref = config  # stored for thread-safe copy in _make_client
        self._available = _get_available_providers(config)
        self.token_usage = TokenUsage()
        if not self._available:
            raise OSError(
                "No LLM providers available. Configure at least one API key "
                "in .env (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, "
                "GLM_API_KEY, GROK_API_KEY, or GROQ_API_KEY)."
            )
        # Use the configured provider if available, otherwise first available
        primary = config.llm_provider.lower()
        if primary in self._available:
            self._current_provider = primary
            self._available.remove(primary)
            self._available.insert(0, primary)
        else:
            self._current_provider = self._available[0]
            logger.warning(
                "Configured provider '%s' has no API key. Falling back to '%s'.",
                primary, self._current_provider,
            )

        logger.info(
            "FallbackLLMClient initialized. Provider order: %s",
            " -> ".join(self._available),
        )

    @property
    def current_provider(self) -> str:
        return self._current_provider

    def _make_client(self, provider: str, config: Config) -> LLMClient:
        """Create a client for the given provider using a thread-safe config copy."""
        import copy
        module_path, class_name, _, default_model = _PROVIDER_REGISTRY[provider]
        # Create an isolated config copy — thread-safe
        cfg = copy.copy(config)
        cfg.llm_provider = provider
        # Always use the default model for each provider
        cfg.llm_model = default_model
        ClientClass = _import_client(module_path, class_name)
        return ClientClass(cfg)

    def _track_response_tokens(self, client: LLMClient, messages: list[dict], result: str) -> None:
        """Extract token usage from the underlying client response when available."""
        # Try to get the raw response object from OpenAI-compatible clients
        # These clients store the last response on the _client object
        prompt_tokens, completion_tokens = _estimate_tokens(messages, result)

        try:
            raw_client = getattr(client, '_client', None)
            if raw_client is not None:
                # OpenAI-compatible clients (Groq, GLM, Grok, OpenAI)
                # Try to get usage from the last completion
                last_response = getattr(raw_client, '_last_response', None)
                if last_response and hasattr(last_response, 'usage') and last_response.usage:
                    prompt_tokens = last_response.usage.prompt_tokens or prompt_tokens
                    completion_tokens = last_response.usage.completion_tokens or completion_tokens
        except Exception:
            pass  # Fall back to estimation

        self.token_usage.add(prompt_tokens, completion_tokens)

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Try current provider, fall back to others on failure."""
        last_error = None
        tried_providers = []

        for provider in self._available:
            tried_providers.append(provider)
            try:
                client = self._make_client(provider, self._config_ref)
                result = client.complete(messages, **kwargs)
                if provider != self._current_provider:
                    logger.info(
                        "Successfully fell back from '%s' to '%s'.",
                        self._current_provider, provider,
                    )
                    self._current_provider = provider
                # Track token usage
                self._track_response_tokens(client, messages, result)
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e)[:200]
                logger.warning(
                    "Provider '%s' failed: %s. %s",
                    provider, type(e).__name__, error_msg,
                )
                if len(self._available) > len(tried_providers):
                    next_provider = self._available[len(tried_providers)]
                    logger.info("Trying next provider: '%s'", next_provider)
                continue

        raise RuntimeError(
            f"All LLM providers failed (tried: {', '.join(tried_providers)}). "
            f"Last error: {last_error}"
        ) from last_error


def create_llm_client(config: Config) -> FallbackLLMClient:
    """Create an LLM client with automatic fallback between providers."""
    return FallbackLLMClient(config)
