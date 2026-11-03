"""Anthropic provider for townlight_core.llm.

Concrete LLMProvider implementation backed by the official ``anthropic`` SDK,
which ships as an OPTIONAL extra (``pip install townlight_core[anthropic]``). The
SDK is imported lazily inside ``__init__`` so that townlight_core continues to
import cleanly when the extra is not installed; if a caller instantiates
``AnthropicProvider`` without the SDK present, a clear ``ImportError`` is
raised directing them to install the extra.

Embeddings are explicitly NOT supported. Anthropic does not ship a native
embedding endpoint and officially recommends a third-party embedding service
(OpenAI, Voyage AI, etc.) for vector operations. Both ``embed()`` and
``embed_batch()`` therefore raise ``NotImplementedError`` with a message
redirecting the caller to an embedding-capable provider.

Default model: ``claude-haiku-4-5`` (the latest small/fast Claude model).
"""

from __future__ import annotations

from townlight_core.llm.providers.base import LLMProvider
from townlight_core.llm.providers.registry import register_provider


@register_provider("anthropic")
class AnthropicProvider(LLMProvider):
    """Anthropic API provider using the official anthropic SDK.

    Requires the optional extra: pip install townlight_core[anthropic].
    Default model: claude-haiku-4-5 (latest small/fast model).

    Embeddings are NOT supported — Anthropic does not ship a native embedding
    endpoint. Use the OpenAI provider or another embedding provider for vector
    operations. Calling embed() / embed_batch() raises NotImplementedError with
    a helpful message.
    """

    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str = "claude-haiku-4-5",
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError(
                "anthropic SDK is required for AnthropicProvider. Install it: pip install anthropic "
                "(or pip install 'townlight_core[anthropic]' once townlight_core is published to PyPI)."
            ) from e
        self._client = AsyncAnthropic(api_key=api_key)
        self.default_model = default_model
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "anthropic"

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
        parts: list[str] = []
        if chunks:
            parts.append("\n\n".join(chunks))
        if exemption_rules:
            parts.append("Exemption rules:\n" + "\n".join(exemption_rules))
        parts.append(user_content)
        composed = "\n\n".join(parts)

        # Build user message content: text + optional images
        if images:
            content_blocks: list[dict] = []
            for img in images:
                # Anthropic expects base64 source for images
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img,
                    },
                })
            content_blocks.append({"type": "text", "text": composed})
            user_message: dict = {"role": "user", "content": content_blocks}
        else:
            user_message = {"role": "user", "content": composed}

        # Anthropic uses top-level system param, not a system message
        resp = await self._client.messages.create(
            model=model,
            system=system_prompt,
            messages=[user_message],
            max_tokens=self.max_tokens,
            timeout=timeout,
        )
        # Response content is a list of blocks; concatenate text blocks
        chunks_out: list[str] = []
        for block in resp.content:
            if hasattr(block, "text"):
                chunks_out.append(block.text)
        return "".join(chunks_out)

    async def embed(self, text: str, *, model: str | None = None) -> list[float]:
        raise NotImplementedError(
            "AnthropicProvider does not support embeddings. Anthropic does not "
            "ship a native embedding endpoint. Use OpenAIProvider or another "
            "embedding-capable provider (e.g. Voyage AI) for vector operations."
        )

    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        raise NotImplementedError(
            "AnthropicProvider does not support embeddings. Anthropic does not "
            "ship a native embedding endpoint. Use OpenAIProvider or another "
            "embedding-capable provider (e.g. Voyage AI) for vector operations."
        )


__all__ = ["AnthropicProvider"]
