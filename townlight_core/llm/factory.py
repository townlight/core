"""Validated factory for constructing LLMProvider instances.

Pairs a provider name with a Pydantic config instance, validates the config
matches the schema registered for that provider, then constructs the provider.
This is the recommended construction path per ADR-0004 §6 — it surfaces
misconfiguration at startup rather than at first generate() call.

Direct calls to provider constructors (e.g., OllamaProvider(...)) still work
for backwards compatibility, but skip the centralized validation step.
"""
from __future__ import annotations

from pydantic import BaseModel

from townlight_core.llm.providers.base import LLMProvider
from townlight_core.llm.providers.config import (
    AnthropicConfig,
    OllamaConfig,
    OpenAIConfig,
)
from townlight_core.llm.providers.registry import PROVIDER_REGISTRY

# Mapping of provider name -> expected Pydantic config schema.
# Third-party providers registered via @register_provider can extend this map
# by importing CONFIG_SCHEMAS and inserting their own entry.
CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "ollama": OllamaConfig,
    "openai": OpenAIConfig,
    "anthropic": AnthropicConfig,
}


def build_provider(name: str, config: BaseModel) -> LLMProvider:
    """Construct a provider with explicit Pydantic config validation.

    Args:
        name: Registered provider name (must be in PROVIDER_REGISTRY).
        config: Pydantic BaseModel instance whose type matches the registered
            schema for `name` (per CONFIG_SCHEMAS). For built-ins:
            'ollama' -> OllamaConfig, 'openai' -> OpenAIConfig,
            'anthropic' -> AnthropicConfig.

    Returns:
        Constructed LLMProvider instance.

    Raises:
        KeyError: If `name` is not registered.
        TypeError: If `config` is not an instance of the schema registered
            for `name`. Error message names both expected and actual types.
        pydantic.ValidationError: If the config instance is invalid (e.g.,
            empty api_key).  This typically surfaces at config construction
            time, not here, but build_provider re-validates defensively.
    """
    if name not in PROVIDER_REGISTRY:
        raise KeyError(
            f"Provider {name!r} not registered. Available: {sorted(PROVIDER_REGISTRY)}"
        )

    expected = CONFIG_SCHEMAS.get(name)
    if expected is not None and not isinstance(config, expected):
        raise TypeError(
            f"Provider {name!r} expects config type {expected.__name__}, "
            f"got {type(config).__name__}. Construct {expected.__name__}(...)."
        )

    # Re-validate defensively (no-op if config was created via the schema).
    if expected is not None:
        config = expected.model_validate(config.model_dump())

    cls = PROVIDER_REGISTRY[name]
    return cls(**config.model_dump())


__all__ = ["build_provider", "CONFIG_SCHEMAS"]
