"""Embedding helpers for the shared Townlight Core ingestion pipeline."""

from __future__ import annotations

import os

from townlight_core.llm.providers import OllamaProvider

_providers: dict[str, OllamaProvider] = {}


def _default_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _get_provider(base_url: str = "http://localhost:11434") -> OllamaProvider:
    if base_url not in _providers:
        _providers[base_url] = OllamaProvider(base_url=base_url, default_model="gemma4:e4b")
    return _providers[base_url]


async def embed_text(
    text: str,
    model: str = "nomic-embed-text",
    *,
    base_url: str | None = None,
) -> list[float]:
    """Embed one text string with the local Ollama embedding model."""

    base_url = base_url or _default_ollama_base_url()
    provider = _get_provider(base_url=base_url)
    return await provider.embed(text, model=model)


async def embed_batch(
    texts: list[str],
    model: str = "nomic-embed-text",
    *,
    base_url: str | None = None,
    batch_size: int = 8,
) -> list[list[float]]:
    """Embed a batch of text strings with the local Ollama embedding model."""

    if not texts:
        return []
    base_url = base_url or _default_ollama_base_url()
    provider = _get_provider(base_url=base_url)
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        embeddings.extend(await provider.embed_batch(batch, model=model))
    return embeddings


__all__ = ["embed_batch", "embed_text"]
