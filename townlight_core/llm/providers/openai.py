"""OpenAI LLM provider for townlight_core.

This module implements :class:`OpenAIProvider`, a concrete
:class:`~townlight_core.llm.providers.base.LLMProvider` backed by the official
``openai`` Python SDK.

The ``openai`` SDK is an **optional extra**. Install with::

    pip install 'townlight_core[openai]'

The SDK import is performed lazily inside ``__init__`` so that this module
(and therefore the provider registry decorator) can be imported cleanly even
when the SDK is not installed. Constructing an :class:`OpenAIProvider`
instance without the SDK raises a clear :class:`ImportError` directing the
user to install the optional extra.

Default models are chosen for a cost/quality balance:

* Chat: ``gpt-4o-mini``
* Embeddings: ``text-embedding-3-small``
"""

from __future__ import annotations

from townlight_core.llm.providers.base import LLMProvider
from townlight_core.llm.providers.registry import register_provider


@register_provider("openai")
class OpenAIProvider(LLMProvider):
    """OpenAI API provider using the official openai SDK.

    Requires the optional extra: ``pip install 'townlight_core[openai]'``.
    Default chat model: ``gpt-4o-mini``. Default embed model:
    ``text-embedding-3-small``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        default_embed_model: str = "text-embedding-3-small",
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "openai SDK is required for OpenAIProvider. Install it: pip install openai "
                "(or pip install 'townlight_core[openai]' once townlight_core is published to PyPI)."
            ) from e
        self._client = AsyncOpenAI(api_key=api_key)
        self.default_model = default_model
        self.default_embed_model = default_embed_model

    @property
    def name(self) -> str:
        return "openai"

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

        # Compose user content: chunks + exemption rules + main content
        parts: list[str] = []
        if chunks:
            parts.append("\n\n".join(chunks))
        if exemption_rules:
            parts.append("Exemption rules:\n" + "\n".join(exemption_rules))
        parts.append(user_content)
        composed = "\n\n".join(parts)

        # Build messages; if images, embed as image_url parts in user message
        if images:
            user_parts: list[dict] = [{"type": "text", "text": composed}]
            for img in images:
                # OpenAI expects either http(s) URLs or data URLs (base64)
                url = (
                    img
                    if img.startswith(("http://", "https://", "data:"))
                    else f"data:image/png;base64,{img}"
                )
                user_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": url},
                    }
                )
            user_message: dict = {"role": "user", "content": user_parts}
        else:
            user_message = {"role": "user", "content": composed}

        messages = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]

        resp = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=timeout,
        )
        return resp.choices[0].message.content or ""

    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        model = model or self.default_embed_model
        resp = await self._client.embeddings.create(model=model, input=text)
        return list(resp.data[0].embedding)

    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        model = model or self.default_embed_model
        resp = await self._client.embeddings.create(model=model, input=texts)
        return [list(item.embedding) for item in resp.data]


__all__ = ["OpenAIProvider"]
