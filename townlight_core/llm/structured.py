"""Provider-agnostic structured output helper for LLM calls.

Wraps a provider's generate() with JSON parsing + Pydantic validation +
retry-on-malformed loop. Returns a validated Pydantic model instance or
raises StructuredOutputFailure after exhausting retries.

Provider-agnostic by design: works with any LLMProvider implementation
(Ollama, OpenAI, Anthropic, or any third-party @register_provider).
"""
from __future__ import annotations

import json
import logging
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from townlight_core.llm.providers.base import LLMProvider

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

DEFAULT_MAX_ATTEMPTS = 3


class StructuredOutputFailure(Exception):
    """Raised when StructuredOutput exhausts retries without a valid result.

    Attributes:
        attempts: Number of provider calls made before giving up.
        last_raw_output: Last raw string the provider returned.
        last_error: Last validation/parse error encountered.
    """

    def __init__(
        self,
        *,
        attempts: int,
        last_raw_output: str,
        last_error: str,
    ) -> None:
        self.attempts = attempts
        self.last_raw_output = last_raw_output
        self.last_error = last_error
        super().__init__(
            f"StructuredOutput failed after {attempts} attempt(s). "
            f"Last error: {last_error}. "
            f"Last raw output (truncated): {last_raw_output[:500]!r}"
        )


class StructuredOutput(Generic[ModelT]):
    """Wrap a Pydantic model class for validated LLM output.

    Usage:
        result: MyModel = await StructuredOutput(MyModel).generate(
            provider=my_provider,
            system_prompt="...",
            user_content="...",
            model="gpt-4o-mini",
            max_attempts=3,
        )
    """

    def __init__(self, model_cls: type[ModelT]) -> None:
        self.model_cls = model_cls

    def _schema_instructions(self) -> str:
        """JSON-schema description appended to the system prompt."""
        try:
            schema = self.model_cls.model_json_schema()
        except Exception:
            schema = {}
        return (
            "\n\nReturn your answer as a single JSON object that conforms exactly "
            "to this JSON schema. Output ONLY the JSON object - no markdown fences, "
            "no commentary, no preamble.\n"
            f"Schema:\n{json.dumps(schema, indent=2)}"
        )

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Strip common ```json ... ``` markdown fencing if present."""
        text = text.strip()
        if text.startswith("```"):
            # Remove leading fence (```json, ```, etc.)
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            # Remove trailing fence
            if text.endswith("```"):
                text = text[:-3]
        return text.strip()

    async def generate(
        self,
        *,
        provider: LLMProvider,
        system_prompt: str,
        user_content: str,
        model: str | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        timeout: float = 120.0,
    ) -> ModelT:
        """Generate validated structured output with retry-on-malformed.

        Raises:
            StructuredOutputFailure: After max_attempts unsuccessful tries.
            ValueError: If max_attempts < 1.
        """
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

        full_system = system_prompt + self._schema_instructions()
        retry_context = ""
        last_raw = ""
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            user_with_retry = user_content + retry_context
            raw = await provider.generate(
                system_prompt=full_system,
                user_content=user_with_retry,
                model=model,
                timeout=timeout,
            )
            last_raw = raw

            # Parse JSON
            stripped = self._strip_fences(raw)
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(
                    "StructuredOutput attempt %d/%d: JSON parse failed: %s",
                    attempt,
                    max_attempts,
                    e,
                )
                retry_context = (
                    f"\n\nYour previous response was not valid JSON. "
                    f"Parse error: {e}. Return only a valid JSON object."
                )
                continue

            # Validate against Pydantic model
            try:
                return self.model_cls.model_validate(parsed)
            except ValidationError as e:
                last_error = f"Validation error: {e}"
                logger.warning(
                    "StructuredOutput attempt %d/%d: validation failed: %s",
                    attempt,
                    max_attempts,
                    e,
                )
                retry_context = (
                    f"\n\nYour previous response failed validation. "
                    f"Errors: {e.errors()}. Return only a valid JSON object."
                )
                continue

        raise StructuredOutputFailure(
            attempts=max_attempts,
            last_raw_output=last_raw,
            last_error=last_error,
        )


__all__ = [
    "StructuredOutput",
    "StructuredOutputFailure",
    "DEFAULT_MAX_ATTEMPTS",
]
