"""Unit tests for townlight_core.llm.providers.

No live HTTP, no real API keys. httpx-based providers are mocked with respx;
optional-SDK providers (openai, anthropic) are mocked via unittest.mock.

Per Hard Rule 4a (NEVER skip tests), the openai and anthropic SDKs are
included in the [dev] extras of pyproject.toml so this file always runs
fully — no pytest.importorskip, no conditional branches. The "SDK missing"
ImportError branch is exercised via monkeypatched sys.modules entries.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from townlight_core.llm.providers import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    PROVIDER_REGISTRY,
    get_provider,
    list_providers,
    register_provider,
)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_three_builtin_providers_registered():
    """Importing townlight_core.llm.providers must register all three built-ins."""
    assert {"ollama", "openai", "anthropic"}.issubset(set(list_providers()))


def test_register_duplicate_raises():
    """Re-registering an already-known provider name raises ValueError."""
    with pytest.raises(ValueError):

        @register_provider("ollama")
        class DuplicateOllama(LLMProvider):  # pragma: no cover - registration fails
            name = "ollama"
            supports_images = False

            async def generate(self, system_prompt, user_content, **kwargs):
                return ""

            async def embed(self, text, **kwargs):
                return []

            async def embed_batch(self, texts, **kwargs):
                return []


def test_register_non_subclass_raises():
    """Decorating a non-LLMProvider class raises TypeError."""
    with pytest.raises(TypeError):

        @register_provider("bogus_not_a_provider")
        class NotAProvider:  # pragma: no cover - registration fails
            pass


def test_get_unknown_provider_raises():
    """Looking up an unregistered provider raises KeyError."""
    with pytest.raises(KeyError):
        get_provider("nonexistent_provider_xyz")


def test_fourth_provider_extensibility():
    """Prove a fourth provider can be registered without editing townlight_core source.

    This test imports ONLY the public API (register_provider, list_providers,
    get_provider, LLMProvider) and demonstrates that a downstream consumer can
    add their own provider with no townlight_core source changes.
    """
    try:

        @register_provider("synthetic_test")
        class SyntheticProvider(LLMProvider):
            name = "synthetic_test"
            supports_images = False

            async def generate(self, system_prompt, user_content, **kwargs):
                return "synthetic"

            async def embed(self, text, **kwargs):
                return [0.0]

            async def embed_batch(self, texts, **kwargs):
                return [[0.0] for _ in texts]

        assert "synthetic_test" in list_providers()
        provider = get_provider("synthetic_test")
        assert isinstance(provider, SyntheticProvider)
        assert provider.name == "synthetic_test"
    finally:
        PROVIDER_REGISTRY.pop("synthetic_test", None)


# ---------------------------------------------------------------------------
# Ollama provider tests (httpx + respx)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_generate_mocked():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url, assert_all_called=True) as mock:
        route = mock.post("/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "hello world"})
        )
        result = await provider.generate(system_prompt="s", user_content="u")
    assert result == "hello world"
    assert route.called
    request_payload = route.calls[0].request.read()
    import json

    body = json.loads(request_payload)
    assert "model" in body
    assert body.get("system") == "s"
    assert body.get("prompt") == "u"
    assert body.get("stream") is False


@pytest.mark.asyncio
async def test_ollama_embed_mocked():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url, assert_all_called=True) as mock:
        route = mock.post("/api/embed").mock(
            return_value=httpx.Response(
                200, json={"embeddings": [[0.1, 0.2, 0.3]]}
            )
        )
        vec = await provider.embed("hello")
    assert vec == [0.1, 0.2, 0.3]
    assert route.called
    request_payload = route.calls[0].request.read()
    import json

    body = json.loads(request_payload)
    assert "model" in body
    assert body.get("input") == "hello"


@pytest.mark.asyncio
async def test_ollama_embed_batch_single_request():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url) as mock:
        route = mock.post("/api/embed").mock(
            return_value=httpx.Response(
                200, json={"embeddings": [[1.0], [2.0], [3.0]]}
            )
        )
        vectors = await provider.embed_batch(["a", "b", "c"])
    assert vectors == [[1.0], [2.0], [3.0]]
    assert route.call_count == 1
    request_payload = route.calls[0].request.read()
    import json

    body = json.loads(request_payload)
    assert body.get("input") == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_ollama_embed_raises_on_empty_response():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url) as mock:
        mock.post("/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": []})
        )
        with pytest.raises(ValueError, match="No embedding returned"):
            await provider.embed("text")


@pytest.mark.asyncio
async def test_ollama_embed_batch_raises_on_count_mismatch():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url) as mock:
        mock.post("/api/embed").mock(
            return_value=httpx.Response(
                200, json={"embeddings": [[1.0], [2.0]]}
            )
        )
        with pytest.raises(ValueError, match="Expected 3 embeddings"):
            await provider.embed_batch(["a", "b", "c"])


@pytest.mark.asyncio
async def test_ollama_embed_batch_empty_returns_empty_no_http():
    base_url = "http://test-ollama"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url, assert_all_called=False) as mock:
        route = mock.post("/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": []})
        )
        result = await provider.embed_batch([])
    assert result == []
    assert route.call_count == 0


# ---------------------------------------------------------------------------
# OpenAI provider tests (optional SDK)
# ---------------------------------------------------------------------------


def test_openai_provider_constructs_with_sdk():
    """With openai SDK installed (always, via [dev] extras), provider constructs."""
    provider = OpenAIProvider(api_key="k")
    assert provider.name == "openai"


def test_openai_provider_raises_clear_error_without_sdk(monkeypatch):
    """When the openai SDK can't be imported, OpenAIProvider raises ImportError
    with an actionable install hint pointing at the [openai] extra."""
    import sys

    # Force `from openai import AsyncOpenAI` inside __init__ to fail. Setting
    # sys.modules["openai"] = None causes Python's import machinery to raise
    # ImportError on subsequent imports of that name. Delete first to ensure a
    # fresh resolution path even if the SDK was already imported elsewhere.
    monkeypatch.delitem(sys.modules, "openai", raising=False)
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ImportError, match=r"townlight_core\[openai\]"):
        OpenAIProvider(api_key="dummy")


def test_anthropic_provider_raises_clear_error_without_sdk(monkeypatch):
    """When the anthropic SDK can't be imported, AnthropicProvider raises
    ImportError with an actionable install hint pointing at the [anthropic] extra."""
    import sys

    monkeypatch.delitem(sys.modules, "anthropic", raising=False)
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(ImportError, match=r"townlight_core\[anthropic\]"):
        AnthropicProvider(api_key="dummy")


@pytest.mark.asyncio
async def test_openai_generate_mocked(monkeypatch):
    provider = OpenAIProvider(api_key="k")
    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="result"))]
    )
    fake_create = AsyncMock(return_value=fake_resp)
    # Patch the underlying client's chat.completions.create
    monkeypatch.setattr(
        provider._client.chat.completions, "create", fake_create, raising=False
    )
    result = await provider.generate(system_prompt="s", user_content="u")
    assert result == "result"
    assert fake_create.await_count == 1


# ---------------------------------------------------------------------------
# Anthropic provider tests (optional SDK)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_generate_mocked(monkeypatch):
    provider = AnthropicProvider(api_key="k")
    fake_resp = SimpleNamespace(content=[SimpleNamespace(text="result")])
    fake_create = AsyncMock(return_value=fake_resp)
    monkeypatch.setattr(
        provider._client.messages, "create", fake_create, raising=False
    )
    result = await provider.generate(system_prompt="s", user_content="u")
    assert result == "result"
    assert fake_create.await_count == 1


@pytest.mark.asyncio
async def test_anthropic_embed_raises_not_implemented():
    provider = AnthropicProvider(api_key="k")
    with pytest.raises(NotImplementedError, match="Anthropic does not"):
        await provider.embed("text")


@pytest.mark.asyncio
async def test_anthropic_embed_batch_raises_not_implemented():
    provider = AnthropicProvider(api_key="k")
    with pytest.raises(NotImplementedError, match="Anthropic does not"):
        await provider.embed_batch(["text"])


# ---------------------------------------------------------------------------
# supports_images
# ---------------------------------------------------------------------------


def test_supports_images_property():
    assert OllamaProvider(base_url="http://x").supports_images is True
    assert OpenAIProvider(api_key="k").supports_images is True
    assert AnthropicProvider(api_key="k").supports_images is True


# ---------------------------------------------------------------------------
# Factory + Pydantic config schema tests (ADR-0004 §6 / PROVIDER-CONFIG-001)
# ---------------------------------------------------------------------------


def test_ollama_config_defaults():
    """OllamaConfig builds with no fields supplied; sensible defaults."""
    from townlight_core.llm.providers import OllamaConfig
    cfg = OllamaConfig()
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.default_model == "gemma4:e4b"


def test_openai_config_requires_api_key():
    """OpenAIConfig.api_key is required and must be non-empty."""
    from townlight_core.llm.providers import OpenAIConfig
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        OpenAIConfig()  # missing api_key
    with pytest.raises(ValidationError):
        OpenAIConfig(api_key="")  # empty api_key


def test_anthropic_config_requires_api_key_and_positive_max_tokens():
    """AnthropicConfig validates api_key and max_tokens > 0."""
    from townlight_core.llm.providers import AnthropicConfig
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AnthropicConfig()  # missing api_key
    with pytest.raises(ValidationError):
        AnthropicConfig(api_key="k", max_tokens=0)  # not > 0


@pytest.mark.asyncio
async def test_build_provider_validates_config_type():
    """build_provider raises TypeError when given the wrong config schema."""
    from townlight_core.llm.factory import build_provider
    from townlight_core.llm.providers import OpenAIConfig
    # Pass OpenAIConfig to ollama; should be rejected
    with pytest.raises(TypeError, match="ollama.*expects config type OllamaConfig"):
        build_provider("ollama", OpenAIConfig(api_key="k"))


@pytest.mark.asyncio
async def test_build_provider_unknown_name_raises_key_error():
    """build_provider raises KeyError naming available providers."""
    from townlight_core.llm.factory import build_provider
    from townlight_core.llm.providers import OllamaConfig
    with pytest.raises(KeyError, match="not registered"):
        build_provider("nonexistent_provider", OllamaConfig())


@pytest.mark.asyncio
async def test_build_provider_constructs_ollama_with_valid_config():
    """build_provider with valid OllamaConfig returns a working provider instance."""
    from townlight_core.llm.factory import build_provider
    from townlight_core.llm.providers import OllamaConfig, OllamaProvider
    cfg = OllamaConfig(base_url="http://test:11434", default_model="custom")
    provider = build_provider("ollama", cfg)
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://test:11434"
    assert provider.default_model == "custom"
    assert provider.name == "ollama"


@pytest.mark.asyncio
async def test_build_provider_constructs_openai_with_valid_config():
    """build_provider with valid OpenAIConfig returns OpenAIProvider."""
    from townlight_core.llm.factory import build_provider
    from townlight_core.llm.providers import OpenAIConfig, OpenAIProvider
    cfg = OpenAIConfig(api_key="dummy")
    provider = build_provider("openai", cfg)
    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"


@pytest.mark.asyncio
async def test_build_provider_constructs_anthropic_with_valid_config():
    """build_provider with valid AnthropicConfig returns AnthropicProvider."""
    from townlight_core.llm.factory import build_provider
    from townlight_core.llm.providers import AnthropicConfig, AnthropicProvider
    cfg = AnthropicConfig(api_key="dummy")
    provider = build_provider("anthropic", cfg)
    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "anthropic"
