# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic review suggestions, never an automatic disclosure decision.

The caller owns authorization, rule selection and review. Jurisdiction
completeness and legal correctness are not inferred from a match.

Citation and version retention live in :mod:`civiccore.exemptions.history`, which
appends immutable cited rule versions and returns ``Rule`` objects for exactly the
persisted version via ``RuleVersion.as_rule()``. That module adds history around
this single evaluator; it is not a second rule engine and it never declares a
jurisdiction's rules complete or official.
"""

from dataclasses import dataclass
from uuid import UUID
import time
import regex
from .patterns import scan_text


class RuleEvaluationError(ValueError):
    """The scan is incomplete; a caller must not report 'no exemptions found'."""


@dataclass(frozen=True)
class Rule:
    id: UUID
    state_code: str
    category: str
    rule_type: str
    definition: str
    version: int


@dataclass
class FlagResult:
    category: str
    matched_text: str
    confidence: float
    rule_id: UUID | None = None
    rule_type: str = "regex"
    rule_version: int | None = None


# Bounded synthetic probe used only to admit a rule pattern for storage. It is
# never returned as a match and never stands in for a real document scan.
_PROBE_TEXT = "a" * 2000 + "!"


def validate_rule_pattern(pattern: str) -> None:
    """Refuse an invalid or catastrophically backtracking pattern before storage.

    The shared evaluator is lazy: ``finditer`` on empty text never compiles, so a
    scan-based check would accept ``"["``. This compiles explicitly and then runs
    one bounded probe under the same time limit the real scan uses.
    """
    if not pattern or len(pattern) > 8000:
        raise RuleEvaluationError("Rule pattern is empty or exceeds the input limit")
    try:
        regex.compile(pattern, regex.IGNORECASE)
        for _ in regex.finditer(pattern, _PROBE_TEXT, regex.IGNORECASE, timeout=0.05):
            pass
    except (regex.error, TimeoutError) as exc:
        raise RuleEvaluationError("Rule pattern is invalid or exceeded its time limit") from exc


def scan_text_with_regex(text: str, pattern: str) -> list[str]:
    """Bound runtime and return whole matches even for grouped expressions."""
    if len(text) > 1_000_000 or len(pattern) > 8000:
        raise RuleEvaluationError("Rule scan exceeds the input limit")
    try:
        matches = []
        for match in regex.finditer(pattern, text, regex.IGNORECASE, timeout=0.05):
            if len(matches) >= 10000:
                raise RuleEvaluationError("Rule scan exceeds the match limit")
            if match.end() > match.start():
                matches.append(match.group(0))
        return matches
    except (regex.error, TimeoutError) as exc:
        raise RuleEvaluationError("Rule pattern is invalid or exceeded its time limit") from exc


def scan_text_with_keywords(text: str, keywords: str) -> list[str]:
    if len(text) > 1_000_000 or len(keywords) > 8000:
        raise RuleEvaluationError("Rule scan exceeds the input limit")
    matches = []
    lowered = text.lower()
    for keyword in keywords.split(","):
        keyword = keyword.strip().lower()
        if keyword and keyword in lowered:
            index = lowered.index(keyword)
            matches.append(text[max(0, index - 30) : index + len(keyword) + 30].strip())
    return matches


def scan_chunk_builtin(text: str, state_code: str | None = None) -> list[FlagResult]:
    if len(text) > 1_000_000:
        raise RuleEvaluationError("Rule scan exceeds the input limit")
    return [
        FlagResult(m.category, m.matched_text[:200], m.confidence)
        for m in scan_text(text, state_code)
    ]


def evaluate(text: str, jurisdiction: str | None, *, rules=()) -> list[FlagResult]:
    """Evaluate supplied active rules and universal PII suggestions.

    No implicit state default or built-in claim of 50-state legal coverage.
    Unsupported rules require a separate reviewer in the application.
    """
    flags = scan_chunk_builtin(text, jurisdiction)
    rules = tuple(rules)
    if len(rules) > 1000:
        raise RuleEvaluationError("Rule set exceeds the supported limit")
    deadline = time.monotonic() + 2.0
    for rule in rules:
        if time.monotonic() > deadline:
            raise RuleEvaluationError("Rule set exceeded its time limit")
        if not jurisdiction or rule.state_code.upper() != jurisdiction.upper():
            raise RuleEvaluationError("Rule jurisdiction does not match the requested scan")
        if rule.version < 1:
            raise RuleEvaluationError("Rule version is required")
        if rule.rule_type == "regex":
            matches = scan_text_with_regex(text, rule.definition)
        elif rule.rule_type == "keyword":
            matches = scan_text_with_keywords(text, rule.definition)
        else:
            raise RuleEvaluationError("Rule requires a separate supported review method")
        flags.extend(
            FlagResult(rule.category, match[:200], 0.8, rule.id, rule.rule_type, rule.version)
            for match in matches
        )
    return flags


__all__ = [
    "Rule",
    "FlagResult",
    "RuleEvaluationError",
    "evaluate",
    "scan_text_with_regex",
    "scan_text_with_keywords",
    "scan_chunk_builtin",
    "validate_rule_pattern",
]
