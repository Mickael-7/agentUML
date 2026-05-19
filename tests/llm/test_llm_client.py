from unittest.mock import MagicMock, patch

import pytest

from agentics.llm.base import LLMClient, create_llm_client


class MockLLMClient(LLMClient):
    def complete(self, messages: list[dict], **kwargs) -> str:
        return "mock response"


def test_mock_client_satisfies_interface():
    client = MockLLMClient()
    result = client.complete([{"role": "user", "content": "hello"}])
    assert result == "mock response"


def test_create_llm_client_anthropic():
    cfg = MagicMock()
    cfg.llm_provider = "anthropic"
    cfg.anthropic_api_key = "sk-ant-test"
    cfg.llm_model = "claude-opus-4-7"
    cfg.llm_temperature = 0.2

    with patch("agentics.llm.anthropic_client.anthropic.Anthropic"):
        client = create_llm_client(cfg)
    from agentics.llm.anthropic_client import AnthropicClient

    assert isinstance(client, AnthropicClient)


def test_create_llm_client_openai():
    cfg = MagicMock()
    cfg.llm_provider = "openai"
    cfg.openai_api_key = "sk-test"
    cfg.llm_model = "gpt-4o"
    cfg.llm_temperature = 0.2

    with patch("agentics.llm.openai_client.OpenAI"):
        client = create_llm_client(cfg)
    from agentics.llm.openai_client import OpenAIClient

    assert isinstance(client, OpenAIClient)


def test_create_llm_client_gemini():
    cfg = MagicMock()
    cfg.llm_provider = "gemini"
    cfg.gemini_api_key = "AIza-test"
    cfg.llm_model = "gemini-1.5-pro"
    cfg.llm_temperature = 0.2

    with (
        patch("agentics.llm.gemini_client.genai.configure"),
        patch("agentics.llm.gemini_client.genai.GenerativeModel"),
    ):
        client = create_llm_client(cfg)
    from agentics.llm.gemini_client import GeminiClient

    assert isinstance(client, GeminiClient)


def test_create_llm_client_unknown_provider():
    cfg = MagicMock()
    cfg.llm_provider = "unknown"
    with pytest.raises(EnvironmentError, match="Unknown LLM_PROVIDER"):
        create_llm_client(cfg)


def test_anthropic_client_raises_without_api_key():
    from agentics.llm.anthropic_client import AnthropicClient

    cfg = MagicMock()
    cfg.anthropic_api_key = ""
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        AnthropicClient(cfg)
