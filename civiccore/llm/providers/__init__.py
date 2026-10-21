"""Townlight Core LLM provider abstraction and built-in implementations.

Importing this package triggers registration of three built-in providers:
ollama, openai, anthropic. Consumers may register additional providers via
`@register_provider` without modifying civiccore source.
"""
from __future__ import annotations

from civiccore.llm.providers.base import LLMProvider
from civiccore.llm.providers.registry import (
    PROVIDER_REGISTRY,
    get_provider,
    list_providers,
    register_provider,
)

# Trigger decorator-based registration of built-in providers.
# Concrete classes are also re-exported below for explicit imports.
from civiccore.llm.providers.ollama import OllamaProvider  # noqa: F401, E402
from civiccore.llm.providers.openai import OpenAIProvider  # noqa: F401, E402
from civiccore.llm.providers.anthropic import AnthropicProvider  # noqa: F401, E402

from civiccore.llm.providers.config import (
    AnthropicConfig,
    OllamaConfig,
    OpenAIConfig,
)

__all__ = [
    "LLMProvider",
    "PROVIDER_REGISTRY",
    "register_provider",
    "get_provider",
    "list_providers",
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaConfig",
    "OpenAIConfig",
    "AnthropicConfig",
]
