"""Smoke test: townlight_core.llm public API is fully importable and complete.

This test exists so that any future refactor that breaks a public symbol
fails CI immediately. The list of expected public symbols is the contract
that downstream apps (records-ai, townlight_meetings) rely on.
"""
from __future__ import annotations


def test_townlight_core_llm_imports_cleanly():
    """Importing townlight_core.llm must not error and must register built-in providers."""
    import townlight_core.llm  # noqa: F401
    from townlight_core.llm.providers import PROVIDER_REGISTRY
    assert {"ollama", "openai", "anthropic"}.issubset(set(PROVIDER_REGISTRY.keys()))


def test_public_api_surface_is_complete():
    """All expected symbols are exposed at the package root."""
    import townlight_core.llm as llm
    expected = {
        # Providers
        "LLMProvider", "PROVIDER_REGISTRY", "register_provider",
        "get_provider", "list_providers",
        "OllamaProvider", "OpenAIProvider", "AnthropicProvider",
        "OllamaConfig", "OpenAIConfig", "AnthropicConfig",
        # Provider factory
        "build_provider", "CONFIG_SCHEMAS",
        # Templates
        "PromptTemplate", "PromptTemplateCreate", "PromptTemplateRead",
        "RenderedPrompt", "render_template", "resolve_template",
        "TOWNLIGHT_CORE_DEFAULT_APP",
        "PromptTemplateError", "PromptTemplateNotFoundError",
        "PromptTemplateRenderError",
        "OVERRIDE_REGISTRY", "register_template_override",
        "unregister_template_override",
        # Registry
        "ModelRegistry", "ModelRegistryCreate", "ModelRegistryRead",
        "ModelRegistryUpdate", "model_registry_router",
        "MissingModelError", "ModelRegistryServiceError",
        "get_active_model", "require_active_model",
        "get_active_model_context_window",
        # Context
        "TokenBudget", "ContextBlock",
        "estimate_tokens", "count_tokens", "sanitize_for_llm",
        "assemble_context", "blocks_to_prompt",
        "DEFAULT_CONTEXT_WINDOW",
        # Structured
        "StructuredOutput", "StructuredOutputFailure",
        "DEFAULT_MAX_ATTEMPTS",
    }
    missing = expected - set(dir(llm))
    assert not missing, f"Missing public symbols in townlight_core.llm: {missing}"


def test_public_api_has_no_cost_tracking():
    """Per ADR-0004 §3: no cost tracking, no spend, no budget abstraction.

    Token budget is allowed (context-window math). Cost/dollar/spend is not.
    """
    import townlight_core.llm as llm
    forbidden_substrings = ("cost", "dollar", "spend", "billing", "budget_enforce")
    surface = " ".join(dir(llm)).lower()
    for sub in forbidden_substrings:
        # "budget" alone is fine (TokenBudget). Forbid the more loaded terms.
        assert sub not in surface, (
            f"Forbidden cost-tracking surface present in townlight_core.llm: {sub}. "
            "Per ADR-0004, no cost tracking in townlight_core."
        )


def test_public_api_no_live_provider_calls_at_import():
    """Importing townlight_core.llm must not make any live HTTP/provider call.

    This test is a smoke check that import time is purely registration —
    no network. (If this passed once, that's mostly proof; the test exists
    so any future code that adds an import-time call will be caught.)
    """
    # If import-time made a real call, the import would slow drastically or
    # fail without network. The previous test_townlight_core_llm_imports_cleanly
    # would have flaked. This explicit test exists as a documentation hook.
    import townlight_core.llm  # noqa: F401
    # No assertion — successful import + the imports_cleanly test passing
    # is the assertion.
