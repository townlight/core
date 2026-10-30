from uuid import uuid4
import pytest
from civiccore.exemptions import (
    Rule,
    RuleEvaluationError,
    evaluate,
    scan_text_with_regex,
    scan_text_with_keywords,
)


def rule(**changes):
    values = dict(
        id=uuid4(),
        state_code="CO",
        category="Fixture review",
        rule_type="keyword",
        definition="confidential",
        version=3,
    )
    return Rule(**(values | changes))


def test_real_pii_detector_and_keyword_suggestions_preserve_attribution():
    custom = rule()
    flags = evaluate("SSN 123-45-6789; confidential fixture", "CO", rules=[custom])
    assert any(f.category == "PII - SSN" for f in flags)
    match = next(f for f in flags if f.rule_id == custom.id)
    assert match.rule_version == 3 and match.confidence == 0.8


def test_grouped_regex_returns_text_and_never_tuple():
    assert scan_text_with_regex("reference AB-123", r"(AB)-(123)") == ["AB-123"]


def test_bad_or_expensive_pattern_is_incomplete_not_empty():
    with pytest.raises(RuleEvaluationError):
        scan_text_with_regex("fixture", "[")
    with pytest.raises(RuleEvaluationError):
        scan_text_with_regex("a" * 100000 + "!", "(a+)+$")


@pytest.mark.parametrize(
    "changes", [{"state_code": "TX"}, {"version": 0}, {"rule_type": "llm_prompt"}]
)
def test_incompatible_or_unsupported_rule_refuses_complete_scan(changes):
    with pytest.raises(RuleEvaluationError):
        evaluate("confidential", "CO", rules=[rule(**changes)])


def test_unknown_jurisdiction_does_not_claim_legal_coverage():
    assert evaluate("public meeting agenda", "XX") == []
    with pytest.raises(RuleEvaluationError):
        evaluate("confidential", None, rules=[rule()])


def test_keyword_context_preserves_legacy_behavior():
    assert scan_text_with_keywords("TRADE SECRET here", "trade secret") == ["TRADE SECRET here"]


def test_core_does_not_import_records():
    import sys

    assert "app.models.exemption" not in sys.modules
