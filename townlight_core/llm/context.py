"""Context manager for townlight_core LLM services.

Townlight Core context handling shared with Townlight Records.
Covers token-budget math, prompt-injection defense, and prompt assembly
for any provider plugged into townlight_core.

Adaptation notes (vs. records-ai):
- ``get_active_model_context_window()`` is intentionally NOT ported here.
  Per ADR-0004, that lookup is a registry-service concern and lives in
  ``townlight_core/llm/registry/service.py``. This module stays free of DB
  imports and is safe to use in pure unit-test contexts.
- ``count_tokens(text, model)`` is a thin, provider-aware wrapper around
  the chars/4 heuristic. A future v0.3.0 candidate is provider-specific
  tokenizers (e.g. ``tiktoken`` for OpenAI). The default implementation
  intentionally matches ``estimate_tokens(text)``.

Per ADR-0004 §1.5: token counting here is context-window math only —
NO cost tracking, NO budget enforcement, NO spend ceilings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_CONTEXT_WINDOW = _DEFAULT_CONTEXT_WINDOW


@dataclass
class TokenBudget:
    """Token budget allocation for an LLM call."""

    system_instruction: int = 500
    request_context: int = 500
    retrieved_chunks: int = 5000
    exemption_rules: int = 500
    output_reservation: int = 1500
    safety_margin: int = 192

    @property
    def total(self) -> int:
        return (
            self.system_instruction
            + self.request_context
            + self.retrieved_chunks
            + self.exemption_rules
            + self.output_reservation
            + self.safety_margin
        )


@dataclass
class ContextBlock:
    """A block of content with its role and estimated token count."""

    role: str  # system, request, chunk, rule, instruction
    content: str
    estimated_tokens: int = 0

    def __post_init__(self) -> None:
        if self.estimated_tokens == 0:
            # Rough estimate: 1 token ~ 4 characters for English text
            self.estimated_tokens = max(1, len(self.content) // 4)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~ 4 characters."""
    return max(1, len(text) // 4)


def count_tokens(text: str, model: str | None = None) -> int:
    """Provider-aware token count.

    Currently delegates to :func:`estimate_tokens` regardless of ``model``.
    This is the documented default per ADR-0004 §1.5; provider-specific
    implementations (e.g. ``tiktoken`` for OpenAI models) can override this
    in a future release without changing the public signature.
    """
    return estimate_tokens(text)


# ── Prompt Injection Defense ──────────────────────────────────────────────────

# Patterns that attempt to override system instructions or inject new roles
_ROLE_OVERRIDE_PATTERNS = re.compile(
    r"(?:ignore\s+(?:previous|above|all)\s+instructions"
    r"|you\s+are\s+now\s+(?:a|an|the)\b"
    r"|forget\s+(?:everything|your|all)\s+(?:previous|prior)"
    r"|disregard\s+(?:previous|above|all|your)[\s\w]*(?:instructions|rules|guidelines)"
    r"|new\s+instructions?\s*:"
    r"|override\s+(?:system|safety|previous)"
    r"|act\s+as\s+(?:a|an|if)\b"
    r"|pretend\s+(?:you\s+are|to\s+be)"
    r"|from\s+now\s+on\s+you\s+(?:are|will|must|should))",
    re.IGNORECASE,
)

# Delimiter injection patterns that try to break out of content boundaries
_DELIMITER_PATTERNS = re.compile(
    r"<\|(?:system|user|assistant|im_start|im_end|endoftext)[|>]"
    r"|```\s*(?:system|instructions?|override)"
    r"|\[INST\]|\[/INST\]"
    r"|<<\s*SYS\s*>>|<<\s*/SYS\s*>>"
    r"|<\s*/?(?:system|instruction|prompt)\s*>",
    re.IGNORECASE,
)

# Excessive repetition (common jailbreak technique)
_REPETITION_PATTERN = re.compile(r"(.{10,}?)\1{4,}")


def sanitize_for_llm(text: str) -> str:
    """Sanitize document content before inclusion in LLM prompts.

    Strips or neutralizes patterns that could manipulate LLM behavior:
    - Role override phrases ("ignore previous instructions", "you are now", etc.)
    - Delimiter injection (<|system|>, [INST], <<SYS>>, etc.)
    - Excessive repetition (repeated strings used to overwhelm context)

    This is a defense-in-depth measure. It does not guarantee safety against
    all adversarial inputs, but raises the bar significantly against known
    prompt injection techniques found in documents.
    """
    if not text:
        return text

    # Replace role override attempts with a neutralized marker
    sanitized = _ROLE_OVERRIDE_PATTERNS.sub("[CONTENT FILTERED]", text)

    # Replace delimiter injection attempts
    sanitized = _DELIMITER_PATTERNS.sub("[CONTENT FILTERED]", sanitized)

    # Collapse excessive repetition to a single instance + note
    sanitized = _REPETITION_PATTERN.sub(
        lambda m: m.group(1) + " [REPEATED CONTENT TRUNCATED]", sanitized
    )

    return sanitized


def assemble_context(
    system_prompt: str,
    request_context: str | None = None,
    chunks: list[str] | None = None,
    exemption_rules: list[str] | None = None,
    budget: TokenBudget | None = None,
    max_context_tokens: int | None = None,
) -> list[ContextBlock]:
    """Assemble context blocks within token budget.

    Prioritizes: system > request > top-k chunks > exemption rules.
    Chunks are added in order until budget is exhausted.
    """
    if budget is None:
        budget = TokenBudget()

    if max_context_tokens:
        # Scale budget proportionally to model context window
        scale = max_context_tokens / budget.total
        budget = TokenBudget(
            system_instruction=int(budget.system_instruction * scale),
            request_context=int(budget.request_context * scale),
            retrieved_chunks=int(budget.retrieved_chunks * scale),
            exemption_rules=int(budget.exemption_rules * scale),
            output_reservation=int(budget.output_reservation * scale),
            safety_margin=int(budget.safety_margin * scale),
        )

    blocks: list[ContextBlock] = []
    tokens_used = 0

    # 1. System instruction (always included)
    sys_block = ContextBlock("system", system_prompt)
    if sys_block.estimated_tokens <= budget.system_instruction:
        blocks.append(sys_block)
        tokens_used += sys_block.estimated_tokens

    # 2. Request context
    if request_context:
        req_block = ContextBlock("request", request_context)
        if req_block.estimated_tokens <= budget.request_context:
            blocks.append(req_block)
            tokens_used += req_block.estimated_tokens

    # 3. Retrieved chunks (top-k that fit)
    # Chunks come from document content — sanitize before LLM inclusion
    if chunks:
        chunk_budget = budget.retrieved_chunks
        for chunk_text in chunks:
            block = ContextBlock("chunk", sanitize_for_llm(chunk_text))
            if block.estimated_tokens <= chunk_budget:
                blocks.append(block)
                chunk_budget -= block.estimated_tokens
                tokens_used += block.estimated_tokens
            else:
                break  # Budget exhausted

    # 4. Exemption rules
    # Rules are admin-configured but sanitize defensively
    if exemption_rules:
        rule_budget = budget.exemption_rules
        for rule_text in exemption_rules:
            block = ContextBlock("rule", sanitize_for_llm(rule_text))
            if block.estimated_tokens <= rule_budget:
                blocks.append(block)
                rule_budget -= block.estimated_tokens
                tokens_used += block.estimated_tokens

    return blocks


def blocks_to_prompt(blocks: list[ContextBlock]) -> str:
    """Convert context blocks to a single prompt string."""
    sections = []
    for block in blocks:
        if block.role == "system":
            sections.append(block.content)
        elif block.role == "request":
            sections.append(f"\n--- Request Context ---\n{block.content}")
        elif block.role == "chunk":
            sections.append(f"\n--- Document Excerpt ---\n{block.content}")
        elif block.role == "rule":
            sections.append(f"\n--- Exemption Rule ---\n{block.content}")
    return "\n".join(sections)


__all__ = [
    "TokenBudget",
    "ContextBlock",
    "estimate_tokens",
    "count_tokens",
    "sanitize_for_llm",
    "assemble_context",
    "blocks_to_prompt",
    "DEFAULT_CONTEXT_WINDOW",
]
