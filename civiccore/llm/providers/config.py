"""Pydantic config schemas for built-in LLM providers (per ADR-0004 §6).

Each schema declares the fields the provider needs and validates them at
startup (via `civiccore.llm.factory.build_provider`) rather than at first
generate() call. Misconfiguration surfaces immediately.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    """Config schema for OllamaProvider.

    All fields have sensible defaults — Ollama runs locally and does not
    require credentials.
    """
    base_url: str = Field(default="http://localhost:11434")
    default_model: str = Field(default="gemma4:e4b")
    default_embed_model: str = Field(default="nomic-embed-text")
    # Reasoning models on the local runtime accept True/False or a level string.
    # Left as None so the field is not sent at all unless configured.
    think: bool | str | None = Field(default=None)


class OpenAIConfig(BaseModel):
    """Config schema for OpenAIProvider.

    api_key is required; passing it via env var is the caller's responsibility
    (e.g., `OpenAIConfig(api_key=os.environ["OPENAI_API_KEY"])`).
    """
    api_key: str = Field(min_length=1, description="OpenAI API key")
    default_model: str = Field(default="gpt-4o-mini")
    default_embed_model: str = Field(default="text-embedding-3-small")


class AnthropicConfig(BaseModel):
    """Config schema for AnthropicProvider.

    api_key is required. max_tokens is a sensible default (4096) and can be
    increased for longer outputs.
    """
    api_key: str = Field(min_length=1, description="Anthropic API key")
    default_model: str = Field(default="claude-haiku-4-5")
    max_tokens: int = Field(default=4096, gt=0)


__all__ = ["OllamaConfig", "OpenAIConfig", "AnthropicConfig"]
