"""Ollama local LLM runtime provider.

Uses httpx (already a civiccore dependency — no extra packages required) to
talk to a local Ollama daemon over its HTTP API.

Default generation model is ``gemma4:e4b``, which matches the current
records-ai production default. Default embedding model is
``nomic-embed-text``.

Embeddings use Ollama's ``/api/embed`` endpoint, which accepts either a
single string or a list of strings via the ``input`` field. This matches
records-ai's ``embedder.py`` contract verbatim.
"""

from __future__ import annotations

import httpx

from civiccore.llm.providers.base import LLMProvider
from civiccore.llm.providers.registry import register_provider


@register_provider("ollama")
class OllamaProvider(LLMProvider):
    """Ollama local LLM runtime provider.

    Talks to a local Ollama daemon at ``base_url`` (default
    ``http://localhost:11434``). Default model is ``gemma4:e4b``
    (records-ai's current production default). Supports both text and
    multimodal (images via base64) generation.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        default_model: str = "gemma4:e4b",
        default_embed_model: str = "nomic-embed-text",
        think: bool | str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.default_embed_model = default_embed_model
        # Ollama's `/api/generate` accepts ``think`` as a bool or a level
        # string ("low"/"medium"/"high"). ``None`` omits the field, which keeps
        # the pre-existing request shape for every existing caller.
        self.think = think

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def supports_images(self) -> bool:
        return True

    async def generate(
        self,
        *,
        system_prompt: str,
        user_content: str,
        model: str | None = None,
        chunks: list[str] | None = None,
        exemption_rules: list[str] | None = None,
        images: list[str] | None = None,
        timeout: float = 120.0,
    ) -> str:
        model = model or self.default_model
        # Compose user prompt: chunks + exemption rules + main content
        parts: list[str] = []
        if chunks:
            parts.append("\n\n".join(chunks))
        if exemption_rules:
            parts.append("Exemption rules:\n" + "\n".join(exemption_rules))
        parts.append(user_content)
        prompt = "\n\n".join(parts)

        payload: dict = {
            "model": model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images
        if self.think is not None:
            payload["think"] = self.think

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def embed(self, text: str, *, model: str | None = None) -> list[float]:
        model = model or self.default_embed_model
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            raise ValueError(
                f"No embedding returned from Ollama for model {model}"
            )

    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        # Ollama's /api/embed accepts a list via `input`; one request per batch.
        model = model or self.default_embed_model
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )
            return embeddings


__all__ = ["OllamaProvider"]
