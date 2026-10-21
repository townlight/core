"""Cron expression utilities for scheduled Townlight work."""

from __future__ import annotations

from datetime import datetime, timezone

from croniter import CroniterBadCronError, croniter

UTC = timezone.utc
DEFAULT_MIN_INTERVAL_MINUTES = 5
DEFAULT_SAMPLE_TICKS = 2016


def min_interval_minutes(
    expr: str,
    *,
    anchor: datetime | None = None,
    sample_ticks: int = DEFAULT_SAMPLE_TICKS,
) -> int:
    """Return the shortest interval, in whole minutes, across sampled cron firings.

    The default sample count covers one week at five-minute granularity. That catches
    adversarial schedules such as ``*/1 0 * * *`` that look sparse daily but fire
    every minute inside one hour.
    """

    active_anchor = anchor or datetime.now(UTC)
    try:
        iterator = croniter(expr, active_anchor)
    except (CroniterBadCronError, ValueError) as exc:
        raise ValueError(f"Invalid cron expression {expr!r}: {exc}") from exc

    previous = iterator.get_next(datetime)
    shortest_gap = float("inf")
    for _ in range(sample_ticks):
        current = iterator.get_next(datetime)
        gap = (current - previous).total_seconds() / 60
        shortest_gap = min(shortest_gap, gap)
        previous = current
    return int(shortest_gap)


def validate_cron_expression(
    expr: str,
    *,
    minimum_interval_minutes: int = DEFAULT_MIN_INTERVAL_MINUTES,
    anchor: datetime | None = None,
) -> None:
    """Validate a five-field cron expression and enforce a minimum interval."""

    active_anchor = anchor or datetime.now(UTC)
    try:
        croniter(expr, active_anchor)
    except (CroniterBadCronError, ValueError) as exc:
        raise ValueError(f"Invalid cron expression: {expr!r}. Use standard 5-field cron syntax.") from exc

    gap = min_interval_minutes(expr, anchor=active_anchor)
    if gap < minimum_interval_minutes:
        raise ValueError(
            "Schedule fires more frequently than every "
            f"{minimum_interval_minutes} minutes (minimum gap detected: {gap} min). "
            f"Minimum allowed interval is {minimum_interval_minutes} minutes."
        )


def compute_next_sync_at(sync_schedule: str | None, last_sync_at: datetime | None) -> datetime | None:
    """Compute the next scheduled run time from the last-sync anchor."""

    if not sync_schedule:
        return None
    anchor = last_sync_at or datetime(1970, 1, 1, tzinfo=UTC)
    return croniter(sync_schedule, anchor).get_next(datetime)


__all__ = [
    "UTC",
    "compute_next_sync_at",
    "min_interval_minutes",
    "validate_cron_expression",
]
