"""Contract tests for immutable cited rule-version history (no database needed).

The persisted behaviour (append-only, jurisdiction isolation, deterministic retrieval,
concurrent append) is exercised against a real PostgreSQL instance by
``work/beta-foundations/rule-history-01/harness.py``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from civiccore.exemptions import Rule, evaluate
from civiccore.exemptions.history import (
    COVERAGE_DECLARATIONS,
    RuleHistoryError,
    RuleVersionInput,
    _require_state_code,
)


def payload(**changes):
    values = dict(
        rule_id=uuid4(),
        state_code="co",
        version=1,
        category="Synthetic fixture records",
        rule_type="keyword",
        rule_definition="confidential, trade secret",
        citation_text="Synthetic fixture statute 1-1-101 (not a real citation)",
        citation_url="https://example.invalid/fixture/1-1-101",
        effective_from=date(2026, 1, 1),
        retrieved_at=datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
        coverage_declaration="synthetic-fixture",
    )
    return values | changes


def test_version_input_normalizes_jurisdiction_and_is_frozen():
    item = RuleVersionInput.model_validate(payload())
    assert item.state_code == "CO"
    with pytest.raises(ValidationError):
        item.state_code = "TX"


def test_fingerprint_is_deterministic_and_content_bound():
    rule_id = uuid4()
    first = RuleVersionInput.model_validate(payload(rule_id=rule_id))
    same = RuleVersionInput.model_validate(payload(rule_id=rule_id))
    changed = RuleVersionInput.model_validate(payload(rule_id=rule_id, version=2))
    assert first.fingerprint() == same.fingerprint()
    assert first.fingerprint() != changed.fingerprint()
    assert len(first.fingerprint()) == 64


@pytest.mark.parametrize("changes", [{"state_code": "COL"}, {"state_code": "C1"}, {"version": 0}])
def test_invalid_jurisdiction_or_version_refuses_construction(changes):
    with pytest.raises(ValidationError):
        RuleVersionInput.model_validate(payload(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"rule_type": "llm_prompt"},
        {"coverage_declaration": "official-legal-coverage"},
        {"coverage_declaration": "all-50-states"},
        {"citation_text": "   "},
        {"rule_type": "regex", "rule_definition": "["},
        {"rule_definition": " , "},
        {"citation_url": "file:///synthetic/fixture.txt"},
    ],
)
def test_rejects_unsupported_type_coverage_citation_and_pattern(changes):
    with pytest.raises(ValidationError):
        RuleVersionInput.model_validate(payload(**changes))


def test_incomplete_scan_error_is_not_converted_to_empty():
    from civiccore.exemptions import RuleEvaluationError

    with pytest.raises(ValidationError) as caught:
        RuleVersionInput.model_validate(payload(rule_type="regex", rule_definition="(a+)+$"))
    # The evaluator's incomplete-scan error is surfaced, not swallowed or turned into "no matches".
    assert isinstance(caught.value.errors()[0]["ctx"]["error"], RuleEvaluationError)


def test_coverage_declarations_exclude_official_legal_coverage():
    assert set(COVERAGE_DECLARATIONS) == {"synthetic-fixture", "tenant-supplied"}


def test_as_rule_feeds_the_single_shared_evaluator_with_exact_version():
    item = RuleVersionInput.model_validate(payload(version=4))
    version = type(
        "V",
        (),
        {
            "rule_id": item.rule_id,
            "state_code": item.state_code,
            "version": item.version,
            "category": item.category,
            "rule_type": item.rule_type,
            "rule_definition": item.rule_definition,
            "as_rule": lambda self: Rule(
                id=item.rule_id,
                state_code=item.state_code,
                category=item.category,
                rule_type=item.rule_type,
                definition=item.rule_definition,
                version=item.version,
            ),
        },
    )()
    flags = evaluate("synthetic CONFIDENTIAL fixture text", "CO", rules=[version.as_rule()])
    match = next(f for f in flags if f.rule_id == item.rule_id)
    assert match.rule_version == 4
    assert match.category == "Synthetic fixture records"


@pytest.mark.parametrize("value", ["", "  ", "USA", "1", None])
def test_retrieval_requires_explicit_two_letter_jurisdiction(value):
    with pytest.raises(RuleHistoryError):
        _require_state_code(value)
