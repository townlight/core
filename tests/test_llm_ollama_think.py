"""`think` support on the existing Ollama provider (continuation 42).

Measured against the deployment's already-running endpoint: `/api/generate`
accepts `think` as a bool or a level string. The default (field absent) must stay
byte-identical to the pre-existing request shape.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from civiccore.llm.providers import OllamaConfig, OllamaProvider


@pytest.mark.asyncio
async def test_think_is_omitted_by_default():
    base_url = "http://test-ollama-think"
    provider = OllamaProvider(base_url=base_url)
    async with respx.mock(base_url=base_url, assert_all_called=True) as mock:
        route = mock.post("/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "ok"}))
        await provider.generate(system_prompt="s", user_content="u")
    body = json.loads(route.calls[0].request.read())
    assert "think" not in body


@pytest.mark.asyncio
async def test_think_level_string_is_sent():
    base_url = "http://test-ollama-think"
    provider = OllamaProvider(base_url=base_url, think="low")
    async with respx.mock(base_url=base_url, assert_all_called=True) as mock:
        route = mock.post("/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "ok"}))
        await provider.generate(system_prompt="s", user_content="u", model="m")
    body = json.loads(route.calls[0].request.read())
    assert body["think"] == "low"
    assert body["model"] == "m"


def test_config_accepts_think_and_builds_provider():
    from civiccore.llm.factory import build_provider

    provider = build_provider("ollama", OllamaConfig(base_url="http://t", think=False))
    assert isinstance(provider, OllamaProvider)
    assert provider.think is False
    assert OllamaConfig().think is None
