"""LLM provider abstraction (Phase 2 extraction).

This module defines :class:`LLMProvider`, the abstract base class that every
concrete LLM backend in Townlight must implement. The surface here is
deliberately narrow and was extracted in Phase 2 of the townlight_core split from
the records-ai status quo:

* :meth:`LLMProvider.generate` mirrors the call shape used by
  ``app/llm/client.py`` in records-ai (system prompt + user content, with
  optional retrieval ``chunks``, ``exemption_rules``, and ``images`` for
  vision-capable providers).
* :meth:`LLMProvider.embed` and :meth:`LLMProvider.embed_batch` mirror the
  single- and batch-embedding paths in ``app/ingestion/embedder.py``.
* :attr:`LLMProvider.name` and :attr:`LLMProvider.supports_images` expose the
  metadata the registry and routing code need without forcing callers to
  ``isinstance``-check concrete classes.

There is intentionally **no** ``chat()`` method on this ABC. Per ADR-0004 §6,
multi-turn chat is deferred until v0.3.0 — there is no concrete consumer of
multi-turn semantics in the current codebase, and locking in a chat surface
before a real call site exists would over-fit the abstraction. Adding
``chat()`` later is a backward-compatible change; getting it wrong now is not.

All methods are declared ``async`` because every existing concrete provider
(Anthropic, Ollama, OpenAI-compatible) is I/O-bound on an HTTP call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["LLMProvider"]


class LLMProvider(ABC):
    """Abstract base class for an LLM backend.

    Concrete implementations live alongside this module (e.g.
    ``townlight_core.llm.providers.anthropic``) and register themselves with the
    decorator registry in :mod:`townlight_core.llm.providers.registry`.
    """

    @abstractmethod
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
        """Generate a single completion.

        Args:
            system_prompt: System / instruction message.
            user_content: The user-turn content.
            model: Optional model identifier override. Providers SHOULD fall
                back to a sensible default when ``None``.
            chunks: Optional retrieval chunks to splice into the prompt.
            exemption_rules: Optional FOIA exemption rule text injected by
                records-ai redaction flows.
            images: Optional list of image references (base64 or URL,
                provider-defined) for vision-capable providers. Providers
                that return ``supports_images == False`` MUST raise if a
                non-empty list is passed.
            timeout: Request timeout in seconds.

        Returns:
            The model's text response.
        """

    @abstractmethod
    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """Embed a single string and return its vector."""

    @abstractmethod
    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Embed a batch of strings and return one vector per input, in order."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider name (matches the registry key)."""

    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """Whether this provider accepts the ``images`` argument to ``generate``."""
