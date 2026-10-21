"""Townlight Core LLM abstraction.

Public API entry point for downstream apps (records-ai, civicclerk). Exposes:

- Provider abstraction (LLMProvider ABC, registry, built-in Ollama/OpenAI/Anthropic).
- Prompt template ORM, rendering, and 3-step override resolution (DB override → code-level override → civiccore default).
- Model registry ORM, Pydantic schemas, async service, and FastAPI admin router.
- Token-budgeted context assembly and prompt-injection defense.
- Structured-output helper (Pydantic-validated, retry-on-malformed).

Importing this package triggers registration of the three built-in providers
(Ollama, OpenAI, Anthropic) via decorator side effects.

Per ADR-0004: NO cost tracking, NO budget enforcement, NO live LLM calls
performed at import time.
"""
from __future__ import annotations

# Providers (Step 3b)
from civiccore.llm.providers import (
    PROVIDER_REGISTRY,
    AnthropicConfig,
    AnthropicProvider,
    LLMProvider,
    OllamaConfig,
    OllamaProvider,
    OpenAIConfig,
    OpenAIProvider,
    get_provider,
    list_providers,
    register_provider,
)

# Provider factory (Step 3 audit fix — PROVIDER-CONFIG-001)
from civiccore.llm.factory import CONFIG_SCHEMAS, build_provider

# Templates (Step 3a + 3c)
from civiccore.llm.templates import (
    CIVICCORE_DEFAULT_APP,
    OVERRIDE_REGISTRY,
    PromptTemplate,
    PromptTemplateCreate,
    PromptTemplateError,
    PromptTemplateNotFoundError,
    PromptTemplateRead,
    PromptTemplateRenderError,
    RenderedPrompt,
    register_template_override,
    render_template,
    resolve_template,
    unregister_template_override,
)

# Registry (Step 3a + 3d)
from civiccore.llm.registry import (
    MissingModelError,
    ModelRegistry,
    ModelRegistryCreate,
    ModelRegistryRead,
    ModelRegistryServiceError,
    ModelRegistryUpdate,
    get_active_model,
    get_active_model_context_window,
    model_registry_router,
    require_active_model,
)

# Context utilities (Step 3d)
from civiccore.llm.context import (
    DEFAULT_CONTEXT_WINDOW,
    ContextBlock,
    TokenBudget,
    assemble_context,
    blocks_to_prompt,
    count_tokens,
    estimate_tokens,
    sanitize_for_llm,
)

# Structured output (Step 3d)
from civiccore.llm.structured import (
    DEFAULT_MAX_ATTEMPTS,
    StructuredOutput,
    StructuredOutputFailure,
)

__all__ = [
    # Providers
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
    # Provider factory
    "build_provider",
    "CONFIG_SCHEMAS",
    # Templates
    "PromptTemplate",
    "PromptTemplateCreate",
    "PromptTemplateRead",
    "RenderedPrompt",
    "render_template",
    "resolve_template",
    "CIVICCORE_DEFAULT_APP",
    "PromptTemplateError",
    "PromptTemplateNotFoundError",
    "PromptTemplateRenderError",
    "OVERRIDE_REGISTRY",
    "register_template_override",
    "unregister_template_override",
    # Registry
    "ModelRegistry",
    "ModelRegistryCreate",
    "ModelRegistryRead",
    "ModelRegistryUpdate",
    "model_registry_router",
    "MissingModelError",
    "ModelRegistryServiceError",
    "get_active_model",
    "require_active_model",
    "get_active_model_context_window",
    # Context utilities
    "TokenBudget",
    "ContextBlock",
    "estimate_tokens",
    "count_tokens",
    "sanitize_for_llm",
    "assemble_context",
    "blocks_to_prompt",
    "DEFAULT_CONTEXT_WINDOW",
    # Structured output
    "StructuredOutput",
    "StructuredOutputFailure",
    "DEFAULT_MAX_ATTEMPTS",
]
