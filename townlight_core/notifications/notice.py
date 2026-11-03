"""Shared notice deadline and compliance helpers for Townlight modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


SPECIAL_NOTICE_TYPES = {"special", "emergency"}


@dataclass(frozen=True)
class DeadlinePlan:
    """Deterministic notice deadline reminders without legal determinations."""

    notice_type: str
    event_date: date
    publish_by: date
    reminders: tuple[str, ...]
    staff_review_required: bool


@dataclass(frozen=True)
class NoticeComplianceWarning:
    """Actionable warning describing a notice-compliance gap."""

    code: str
    message: str
    fix: str

    def public_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "fix": self.fix}


@dataclass(frozen=True)
class NoticeComplianceResult:
    """Result of checking whether a meeting notice is ready to publish."""

    meeting_id: str
    notice_type: str
    scheduled_start: datetime
    posted_at: datetime
    minimum_notice_hours: int
    deadline_at: datetime
    statutory_basis: str | None
    approved_by: str | None
    compliant: bool
    http_status: int
    warnings: tuple[NoticeComplianceWarning, ...]

    def public_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "notice_type": self.notice_type,
            "scheduled_start": self.scheduled_start.isoformat(),
            "posted_at": self.posted_at.isoformat(),
            "minimum_notice_hours": self.minimum_notice_hours,
            "deadline_at": self.deadline_at.isoformat(),
            "statutory_basis": self.statutory_basis,
            "approved_by": self.approved_by,
            "compliant": self.compliant,
            "warnings": [warning.public_dict() for warning in self.warnings],
        }


def build_deadline_plan(*, notice_type: str, event_date: date, lead_days: int = 10) -> DeadlinePlan:
    """Build deterministic review reminders for a notice event."""

    publish_by = event_date - timedelta(days=lead_days)
    reminders = (
        f"{publish_by - timedelta(days=14)}: confirm statutory authority and publication channel.",
        f"{publish_by - timedelta(days=7)}: route draft copy for clerk/legal review.",
        f"{publish_by}: publish or file proof of publication deadline.",
        f"{event_date}: verify final notice packet before hearing/opening/action.",
    )
    return DeadlinePlan(
        notice_type=notice_type.strip() or "general notice",
        event_date=event_date,
        publish_by=publish_by,
        reminders=reminders,
        staff_review_required=True,
    )


def evaluate_notice_compliance(
    *,
    meeting_id: str,
    notice_type: str,
    scheduled_start: datetime,
    posted_at: datetime,
    minimum_notice_hours: int,
    statutory_basis: str | None,
    approved_by: str | None,
) -> NoticeComplianceResult:
    """Evaluate notice timing and approval guardrails for a scheduled event."""

    normalized_notice_type = notice_type.strip().lower()
    deadline_at = scheduled_start - timedelta(hours=minimum_notice_hours)
    warnings: list[NoticeComplianceWarning] = []

    if normalized_notice_type in SPECIAL_NOTICE_TYPES and not statutory_basis:
        warnings.append(
            NoticeComplianceWarning(
                code="missing_statutory_basis",
                message="Special and emergency notices require a statutory basis.",
                fix="Add the statutory basis authorizing this meeting type before posting public notice.",
            )
        )

    if posted_at > deadline_at:
        warnings.append(
            NoticeComplianceWarning(
                code="notice_deadline_missed",
                message="Notice was posted after the required deadline.",
                fix="Move the meeting, document the legal exception, or obtain attorney/clerk approval before posting.",
            )
        )

    if not approved_by:
        warnings.append(
            NoticeComplianceWarning(
                code="human_approval_required",
                message="Public notice posting requires a named clerk or authorized approver.",
                fix="Provide approved_by before posting public notice.",
            )
        )

    return NoticeComplianceResult(
        meeting_id=meeting_id,
        notice_type=normalized_notice_type,
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=minimum_notice_hours,
        deadline_at=deadline_at,
        statutory_basis=statutory_basis,
        approved_by=approved_by,
        compliant=not warnings,
        http_status=_status_for_warnings(warnings),
        warnings=tuple(warnings),
    )


def _status_for_warnings(warnings: list[NoticeComplianceWarning]) -> int:
    if not warnings:
        return 200
    if warnings[0].code == "human_approval_required":
        return 403
    return 422


__all__ = [
    "DeadlinePlan",
    "NoticeComplianceResult",
    "NoticeComplianceWarning",
    "SPECIAL_NOTICE_TYPES",
    "build_deadline_plan",
    "evaluate_notice_compliance",
]
