from __future__ import annotations

from datetime import UTC, date, datetime

from townlight_core.notifications import build_deadline_plan, evaluate_notice_compliance


def test_build_deadline_plan_returns_publish_by_and_reminders() -> None:
    result = build_deadline_plan(
        notice_type="public hearing",
        event_date=date(2026, 6, 15),
        lead_days=14,
    )

    assert result.notice_type == "public hearing"
    assert result.publish_by.isoformat() == "2026-06-01"
    assert result.staff_review_required is True
    assert len(result.reminders) == 4
    assert "confirm statutory authority and publication channel" in result.reminders[0]


def test_evaluate_notice_compliance_requires_statutory_basis_for_special_notices() -> None:
    result = evaluate_notice_compliance(
        meeting_id="mtg-1",
        notice_type="special",
        scheduled_start=datetime(2026, 5, 10, 18, 0, tzinfo=UTC),
        posted_at=datetime(2026, 5, 8, 18, 0, tzinfo=UTC),
        minimum_notice_hours=24,
        statutory_basis=None,
        approved_by="Clerk",
    )

    assert result.http_status == 422
    assert result.warnings[0].code == "missing_statutory_basis"
    assert result.public_dict()["warnings"][0]["code"] == "missing_statutory_basis"


def test_evaluate_notice_compliance_requires_human_approval_before_posting() -> None:
    result = evaluate_notice_compliance(
        meeting_id="mtg-2",
        notice_type="regular",
        scheduled_start=datetime(2026, 5, 10, 18, 0, tzinfo=UTC),
        posted_at=datetime(2026, 5, 7, 17, 0, tzinfo=UTC),
        minimum_notice_hours=72,
        statutory_basis="C.R.S. 24-6-402",
        approved_by=None,
    )

    assert result.http_status == 403
    assert result.warnings[0].code == "human_approval_required"
