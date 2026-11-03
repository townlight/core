"""Tests for townlight_core.llm.structured.StructuredOutput.

All tests use a fake LLMProvider with canned responses - NO live provider
calls, NO DB, NO network.
"""
from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import BaseModel

from townlight_core.llm.providers.base import LLMProvider
from townlight_core.llm.structured import StructuredOutput, StructuredOutputFailure


class _FakeProvider(LLMProvider):
    """Records-canned-response fake provider for testing."""

    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self._last_user_content: str = ""
        self._last_system_prompt: str = ""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def supports_images(self) -> bool:
        return False

    async def generate(self, **kwargs) -> str:
        self._last_user_content = kwargs.get("user_content", "")
        self._last_system_prompt = kwargs.get("system_prompt", "")
        if self._call_count >= len(self._responses):
            raise RuntimeError("Test fake exhausted canned responses")
        result = self._responses[self._call_count]
        self._call_count += 1
        return result

    async def embed(self, text: str, **kwargs) -> list[float]:
        return [0.0]

    async def embed_batch(self, texts, **kwargs) -> list[list[float]]:
        return [[0.0] for _ in texts]


class _Person(BaseModel):
    name: str
    age: int


@pytest.mark.asyncio
async def test_structured_output_returns_validated_model() -> None:
    provider = _FakeProvider(['{"name": "Alice", "age": 30}'])
    result = await StructuredOutput(_Person).generate(
        provider=provider,
        system_prompt="You are a helper.",
        user_content="Give me a person.",
    )
    assert isinstance(result, _Person)
    assert result.name == "Alice"
    assert result.age == 30
    assert provider._call_count == 1


@pytest.mark.asyncio
async def test_structured_output_strips_markdown_fences() -> None:
    fenced = '```json\n{"name":"Bob","age":40}\n```'
    provider = _FakeProvider([fenced])
    result = await StructuredOutput(_Person).generate(
        provider=provider,
        system_prompt="sys",
        user_content="user",
    )
    assert result.name == "Bob"
    assert result.age == 40


@pytest.mark.asyncio
async def test_structured_output_retries_on_invalid_json() -> None:
    provider = _FakeProvider(["not json", '{"name":"Carol","age":50}'])
    result = await StructuredOutput(_Person).generate(
        provider=provider,
        system_prompt="sys",
        user_content="user",
    )
    assert result.name == "Carol"
    assert result.age == 50
    assert provider._call_count == 2
    # Second call's user_content should include the JSON parse retry hint
    assert "not valid JSON" in provider._last_user_content
    assert "Parse error" in provider._last_user_content


@pytest.mark.asyncio
async def test_structured_output_retries_on_validation_failure() -> None:
    provider = _FakeProvider(
        ['{"name":"Dave"}', '{"name":"Eve","age":25}']
    )
    result = await StructuredOutput(_Person).generate(
        provider=provider,
        system_prompt="sys",
        user_content="user",
    )
    assert result.name == "Eve"
    assert result.age == 25
    assert provider._call_count == 2
    # Second call's user_content should include the validation retry hint
    assert "failed validation" in provider._last_user_content


@pytest.mark.asyncio
async def test_structured_output_raises_after_max_attempts() -> None:
    provider = _FakeProvider(["bad", "still bad", "nope"])
    with pytest.raises(StructuredOutputFailure) as exc_info:
        await StructuredOutput(_Person).generate(
            provider=provider,
            system_prompt="sys",
            user_content="user",
            max_attempts=3,
        )
    err = exc_info.value
    assert err.attempts == 3
    assert err.last_raw_output == "nope"
    assert "JSON parse error" in err.last_error or "Validation error" in err.last_error
    assert provider._call_count == 3


@pytest.mark.asyncio
async def test_structured_output_max_attempts_must_be_positive() -> None:
    provider = _FakeProvider(['{"name":"X","age":1}'])
    so = StructuredOutput(_Person)
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        await so.generate(
            provider=provider,
            system_prompt="sys",
            user_content="user",
            max_attempts=0,
        )


@pytest.mark.asyncio
async def test_structured_output_appends_schema_to_system_prompt() -> None:
    provider = _FakeProvider(['{"name":"Y","age":2}'])
    original_system = "You are a careful assistant."
    await StructuredOutput(_Person).generate(
        provider=provider,
        system_prompt=original_system,
        user_content="user",
    )
    captured = provider._last_system_prompt
    # Original system content preserved
    assert original_system in captured
    # Schema instructions appended
    assert "JSON" in captured
    assert "schema" in captured.lower()
    # Pydantic schema content (field names) included
    assert "name" in captured
    assert "age" in captured


def test_structured_output_no_live_calls() -> None:
    """Sanity: this module must not import live HTTP provider clients.

    The fact that every other test uses _FakeProvider is the real proof;
    this no-op test simply imports the helper module to confirm it loads
    without pulling in httpx-bound live clients at import time.
    """
    from townlight_core.llm import structured as _structured  # noqa: F401

    assert _structured.StructuredOutput is StructuredOutput
    assert _structured.StructuredOutputFailure is StructuredOutputFailure
