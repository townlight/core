"""Shared platform health projection for local Townlight surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlatformHealthStatus = Literal["ok", "needs_setup", "degraded", "blocked"]
_STATUS_RANK: dict[PlatformHealthStatus, int] = {
    "ok": 0,
    "needs_setup": 1,
    "degraded": 2,
    "blocked": 3,
}


class PlatformHealthCheck(BaseModel):
    """One health check result suitable for staff/admin health screens."""

    model_config = ConfigDict(extra="forbid")

    component: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: PlatformHealthStatus
    message: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    blocking: bool = False
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    admin_detail: str | None = Field(default=None, min_length=1)


class PlatformHealthSummary(BaseModel):
    """Aggregated health status for the umbrella shell."""

    model_config = ConfigDict(extra="forbid")

    status: PlatformHealthStatus
    checks: list[PlatformHealthCheck]
    next_action: str
    staff_message: str
    admin_message: str
    blocked_components: list[str]
    degraded_components: list[str]

    @property
    def is_release_blocked(self) -> bool:
        return self.status == "blocked" or bool(self.blocked_components)


def summarize_platform_health(checks: list[PlatformHealthCheck]) -> PlatformHealthSummary:
    """Return the worst health status plus plain-English action copy."""

    if not checks:
        return PlatformHealthSummary(
            status="needs_setup",
            checks=[],
            next_action="Run first-run setup so Townlight can verify the local services.",
            staff_message="Townlight has not completed setup yet.",
            admin_message="No platform health checks have reported.",
            blocked_components=[],
            degraded_components=[],
        )

    worst = max((check.status for check in checks), key=lambda status: _STATUS_RANK[status])
    action_source = next(
        (
            check
            for check in checks
            if check.blocking or check.status in {"blocked", "needs_setup", "degraded"}
        ),
        checks[0],
    )
    blocked = [
        check.component for check in checks if check.blocking or check.status == "blocked"
    ]
    degraded = [check.component for check in checks if check.status == "degraded"]

    if blocked:
        staff_message = "Townlight needs attention before affected workflows can continue."
    elif worst == "degraded":
        staff_message = "Townlight is running, but one or more background checks need attention."
    elif worst == "needs_setup":
        staff_message = "Townlight needs setup before all workflows are available."
    else:
        staff_message = "Townlight is healthy."

    return PlatformHealthSummary(
        status=worst,
        checks=checks,
        next_action=action_source.next_action,
        staff_message=staff_message,
        admin_message=_admin_message(checks),
        blocked_components=blocked,
        degraded_components=degraded,
    )


def _admin_message(checks: list[PlatformHealthCheck]) -> str:
    details = [check.admin_detail for check in checks if check.admin_detail]
    if details:
        return " ".join(details)
    return "All reported checks are available in the local health center."
