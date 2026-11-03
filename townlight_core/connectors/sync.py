"""Storage-neutral live connector sync primitives.

These helpers intentionally avoid ORM models, credentials, schedulers, and
vendor adapters. Downstream modules keep those product-specific pieces while
sharing one retry/circuit-breaker contract and one operator-facing health model.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal, TypeVar

import httpx
from townlight_core.scheduling import compute_next_sync_at

logger = logging.getLogger(__name__)

T = TypeVar("T")
SyncHealthStatus = Literal["healthy", "degraded", "circuit_open"]


@dataclass(frozen=True)
class SyncRetryPolicy:
    """HTTP retry policy for live vendor connector calls."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    jitter_factor: float = 0.2
    max_backoff_seconds: float = 30.0
    retry_after_cap_seconds: float = 600.0


class SyncRetryExhausted(Exception):
    """Raised when a retryable connector call exhausts the configured policy."""


@dataclass(frozen=True)
class SyncCircuitPolicy:
    """Circuit-breaker thresholds shared by live connector consumers."""

    full_failure_threshold: int = 5
    grace_period_failure_threshold: int = 2
    grace_period_reason: str = "grace_period"


@dataclass(frozen=True)
class SyncCircuitState:
    """Storage-neutral state needed to compute live-sync health."""

    connector: str
    source_name: str = "connector source"
    consecutive_failure_count: int = 0
    active_failure_count: int = 0
    sync_paused: bool = False
    sync_paused_at: datetime | None = None
    sync_paused_reason: str | None = None
    last_sync_status: str | None = None
    last_error_at: datetime | None = None

    @property
    def health_status(self) -> SyncHealthStatus:
        return compute_sync_health_status(self)


@dataclass(frozen=True)
class SyncRunResult:
    """Normalized result summary for one connector sync run."""

    records_discovered: int
    records_succeeded: int
    records_failed: int
    retries_attempted: int = 0
    error_summary: str | None = None

    @property
    def attempted_count(self) -> int:
        return self.records_discovered + self.retries_attempted

    @property
    def any_success(self) -> bool:
        return self.records_succeeded > 0

    @property
    def any_failure(self) -> bool:
        return self.records_failed > 0


@dataclass(frozen=True)
class SyncOperatorStatus:
    """Actionable health copy that can be rendered directly in module UIs."""

    connector: str
    source_name: str
    health_status: SyncHealthStatus
    consecutive_failure_count: int
    active_failure_count: int
    sync_paused: bool
    sync_paused_reason: str | None
    message: str
    fix: str

    def public_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "connector": self.connector,
            "source_name": self.source_name,
            "health_status": self.health_status,
            "consecutive_failure_count": self.consecutive_failure_count,
            "active_failure_count": self.active_failure_count,
            "sync_paused": self.sync_paused,
            "sync_paused_reason": self.sync_paused_reason,
            "message": self.message,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class SyncSourceStatus:
    """Storage-neutral status projection for module connector source lists."""

    connector: str
    source_name: str
    health_status: SyncHealthStatus
    consecutive_failure_count: int
    active_failure_count: int
    sync_paused: bool
    sync_paused_reason: str | None
    last_sync_status: str | None
    next_sync_at: datetime | None
    message: str
    fix: str

    def public_dict(self) -> dict[str, str | int | bool | datetime | None]:
        return {
            "connector": self.connector,
            "source_name": self.source_name,
            "health_status": self.health_status,
            "consecutive_failure_count": self.consecutive_failure_count,
            "active_failure_count": self.active_failure_count,
            "sync_paused": self.sync_paused,
            "sync_paused_reason": self.sync_paused_reason,
            "last_sync_status": self.last_sync_status,
            "next_sync_at": self.next_sync_at,
            "message": self.message,
            "fix": self.fix,
        }


def compute_retry_delay(
    attempt: int,
    *,
    retry_after_seconds: float | None = None,
    policy: SyncRetryPolicy | None = None,
    random_value: float | None = None,
) -> float | None:
    """Return the delay for a retry attempt, or ``None`` when policy says stop."""

    active_policy = policy or SyncRetryPolicy()
    if attempt < 0:
        raise ValueError("attempt must be zero or greater.")
    if retry_after_seconds is not None:
        return max(0.0, min(retry_after_seconds, active_policy.retry_after_cap_seconds))
    else:
        delay = active_policy.base_delay_seconds * (2**attempt)
        if delay > active_policy.max_backoff_seconds:
            return None

    jitter_source = random.random() if random_value is None else random_value
    jitter = delay * active_policy.jitter_factor * (2 * jitter_source - 1)
    return max(0.0, delay + jitter)


async def with_http_retry(
    action: Callable[[], Awaitable[httpx.Response]],
    *,
    policy: SyncRetryPolicy | None = None,
    bypass_retry: bool = False,
    sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
) -> httpx.Response:
    """Execute an async HTTP action with retry on ``429``, ``5xx``, and connection failures."""

    active_policy = policy or SyncRetryPolicy()
    if bypass_retry:
        return await action()

    last_exc: Exception | None = None
    for attempt in range(active_policy.max_attempts):
        try:
            response = await action()
            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                delay = compute_retry_delay(
                    attempt,
                    retry_after_seconds=retry_after,
                    policy=active_policy,
                )
                if delay is None or attempt == active_policy.max_attempts - 1:
                    raise SyncRetryExhausted(
                        f"Rate limited after {attempt + 1} attempt(s); Retry-After={retry_after}"
                    )
                logger.warning(
                    "Rate limited (429), retrying in %.1fs (attempt %d/%d)",
                    delay,
                    attempt + 1,
                    active_policy.max_attempts,
                )
                await sleep(delay)
                continue
            if response.status_code >= 500:
                delay = compute_retry_delay(attempt, policy=active_policy)
                if delay is None or attempt == active_policy.max_attempts - 1:
                    raise SyncRetryExhausted(
                        f"Server error {response.status_code} after {attempt + 1} attempt(s)"
                    )
                logger.warning(
                    "Server error %d, retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    delay,
                    attempt + 1,
                    active_policy.max_attempts,
                )
                await sleep(delay)
                continue
            return response
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            delay = compute_retry_delay(attempt, policy=active_policy)
            if delay is None or attempt == active_policy.max_attempts - 1:
                raise SyncRetryExhausted(
                    f"Connection error after {attempt + 1} attempt(s): {exc}"
                ) from exc
            logger.warning("Connection error, retrying in %.1fs: %s", delay, exc)
            await sleep(delay)

    raise SyncRetryExhausted(f"Exhausted {active_policy.max_attempts} attempts") from last_exc


def apply_sync_run_result(
    state: SyncCircuitState,
    result: SyncRunResult,
    *,
    now: datetime | None = None,
    policy: SyncCircuitPolicy | None = None,
) -> SyncCircuitState:
    """Apply one run result using the shared Townlight circuit-breaker pattern."""

    active_policy = policy or SyncCircuitPolicy()
    current_time = now or datetime.now(UTC)
    if result.attempted_count == 0 and not result.any_failure:
        return replace(state, last_sync_status="success")

    if result.any_success:
        return replace(
            state,
            consecutive_failure_count=0,
            sync_paused=False,
            sync_paused_at=None,
            sync_paused_reason=None
            if state.sync_paused_reason == active_policy.grace_period_reason
            else state.sync_paused_reason,
            last_sync_status="partial" if result.any_failure else "success",
        )

    if result.any_failure:
        failure_count = state.consecutive_failure_count + 1
        threshold = (
            active_policy.grace_period_failure_threshold
            if state.sync_paused_reason == active_policy.grace_period_reason
            else active_policy.full_failure_threshold
        )
        if failure_count >= threshold:
            return replace(
                state,
                consecutive_failure_count=failure_count,
                sync_paused=True,
                sync_paused_at=current_time,
                sync_paused_reason=f"Circuit open after {failure_count} consecutive full-run failures.",
                last_sync_status="failed",
                last_error_at=current_time,
            )
        return replace(
            state,
            consecutive_failure_count=failure_count,
            last_sync_status="failed",
            last_error_at=current_time,
        )

    return replace(state, last_sync_status="success")


def compute_sync_health_status(state: SyncCircuitState) -> SyncHealthStatus:
    if state.sync_paused:
        return "circuit_open"
    if state.consecutive_failure_count > 0 or state.active_failure_count > 0:
        return "degraded"
    return "healthy"


def build_sync_operator_status(
    state: SyncCircuitState,
    *,
    policy: SyncCircuitPolicy | None = None,
) -> SyncOperatorStatus:
    """Return actionable operator copy for current live-sync state."""

    active_policy = policy or SyncCircuitPolicy()
    health = compute_sync_health_status(state)
    if health == "circuit_open":
        message = f"{state.source_name} live sync is paused because the circuit breaker is open."
        fix = (
            "Review the latest run errors, correct the vendor credentials or endpoint, "
            "run a one-time readiness check, then unpause the source."
        )
    elif health == "degraded":
        message = f"{state.source_name} live sync is degraded."
        fix = (
            "Review active failures and confirm the next scheduled sync can reach the vendor "
            f"endpoint; the circuit opens after {active_policy.full_failure_threshold} "
            "consecutive full-run failures."
        )
    else:
        message = f"{state.source_name} live sync is healthy."
        fix = "No action needed. Continue monitoring scheduled run logs."
    return SyncOperatorStatus(
        connector=state.connector,
        source_name=state.source_name,
        health_status=health,
        consecutive_failure_count=state.consecutive_failure_count,
        active_failure_count=state.active_failure_count,
        sync_paused=state.sync_paused,
        sync_paused_reason=state.sync_paused_reason,
        message=message,
        fix=fix,
    )


def build_sync_source_status(
    state: SyncCircuitState,
    *,
    sync_schedule: str | None = None,
    schedule_enabled: bool = True,
    last_sync_at: datetime | None = None,
    policy: SyncCircuitPolicy | None = None,
) -> SyncSourceStatus:
    """Return shared source-list health, pause, and next-run projection.

    Product modules own persistence and authorization. Townlight Core owns the
    repeated semantics: circuit-open beats degraded, active failures degrade
    health, paused sources do not advertise a next scheduled run, and operator
    copy always includes a fix path.
    """

    operator = build_sync_operator_status(state, policy=policy)
    next_sync_at = None
    if sync_schedule and schedule_enabled and not state.sync_paused:
        next_sync_at = compute_next_sync_at(sync_schedule, last_sync_at)
    return SyncSourceStatus(
        connector=operator.connector,
        source_name=operator.source_name,
        health_status=operator.health_status,
        consecutive_failure_count=operator.consecutive_failure_count,
        active_failure_count=operator.active_failure_count,
        sync_paused=operator.sync_paused,
        sync_paused_reason=operator.sync_paused_reason,
        last_sync_status=state.last_sync_status,
        next_sync_at=next_sync_at,
        message=operator.message,
        fix=operator.fix,
    )


def _parse_retry_after(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None
