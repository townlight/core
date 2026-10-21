"""Storage-neutral local task contracts for Townlight modules."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskStatus = Literal["queued", "running", "succeeded", "retry_wait", "failed", "cancelled"]


class TaskRetryPolicy(BaseModel):
    """Retry settings for local durable task queues."""

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=3, ge=1)
    base_delay_seconds: int = Field(default=30, ge=0)
    max_delay_seconds: int = Field(default=3600, ge=0)


class LocalTaskEnvelope(BaseModel):
    """Storage-neutral task record for module-owned persistence."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    module_id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    task_type: str = Field(min_length=1)
    status: TaskStatus = "queued"
    payload: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = Field(default=0, ge=0)
    queued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    available_at: datetime | None = None
    last_error: str | None = Field(default=None, min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1)
    audit_subject_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_retry_state(self) -> LocalTaskEnvelope:
        if self.status == "retry_wait" and self.available_at is None:
            raise ValueError("retry_wait tasks must include available_at")
        if self.status == "failed" and not self.last_error:
            raise ValueError("failed tasks must include last_error")
        return self


class LocalTaskResult(BaseModel):
    """Result returned after recording a local task attempt."""

    model_config = ConfigDict(extra="forbid")

    task: LocalTaskEnvelope
    message: str
    retry_at: datetime | None = None


class TaskQueueSummary(BaseModel):
    """Counts and operator copy for a module task queue."""

    model_config = ConfigDict(extra="forbid")

    total: int
    counts: dict[str, int]
    blocked: bool
    message: str


def next_retry_at(
    attempt_count: int,
    failed_at: datetime,
    *,
    policy: TaskRetryPolicy | None = None,
) -> datetime | None:
    """Return the next retry time after a failed attempt, or None when exhausted."""

    active_policy = policy or TaskRetryPolicy()
    if attempt_count >= active_policy.max_attempts:
        return None
    delay = active_policy.base_delay_seconds * (2 ** max(0, attempt_count - 1))
    delay = min(delay, active_policy.max_delay_seconds)
    return failed_at + timedelta(seconds=delay)


def can_run_task(task: LocalTaskEnvelope, *, now: datetime | None = None) -> bool:
    """Return True when a queued or retry-wait task can be claimed."""

    current_time = now or datetime.now(UTC)
    if task.status == "queued":
        return True
    if task.status == "retry_wait" and task.available_at is not None:
        return task.available_at <= current_time
    return False


def record_task_attempt(
    task: LocalTaskEnvelope,
    *,
    success: bool,
    now: datetime | None = None,
    error: str | None = None,
    policy: TaskRetryPolicy | None = None,
) -> LocalTaskResult:
    """Return an updated task envelope after one local worker attempt."""

    current_time = now or datetime.now(UTC)
    attempt_count = task.attempt_count + 1
    if success:
        updated = task.model_copy(
            update={
                "status": "succeeded",
                "attempt_count": attempt_count,
                "available_at": None,
                "last_error": None,
            }
        )
        return LocalTaskResult(task=updated, message="Task completed successfully.")

    if not error:
        raise ValueError("error is required when recording a failed task attempt")

    retry_at = next_retry_at(attempt_count, current_time, policy=policy)
    if retry_at is None:
        updated = task.model_copy(
            update={
                "status": "failed",
                "attempt_count": attempt_count,
                "available_at": None,
                "last_error": error,
            }
        )
        return LocalTaskResult(task=updated, message="Task failed and retries are exhausted.")

    updated = task.model_copy(
        update={
            "status": "retry_wait",
            "attempt_count": attempt_count,
            "available_at": retry_at,
            "last_error": error,
        }
    )
    return LocalTaskResult(task=updated, message="Task failed and is waiting to retry.", retry_at=retry_at)


def summarize_task_queue(tasks: list[LocalTaskEnvelope]) -> TaskQueueSummary:
    """Return counts and operator copy for a queue view."""

    counts = Counter(task.status for task in tasks)
    blocked = bool(counts.get("failed"))
    if blocked:
        message = "One or more local tasks failed and need review."
    elif counts.get("retry_wait"):
        message = "Some local tasks are waiting to retry."
    elif counts.get("running") or counts.get("queued"):
        message = "Local tasks are active."
    else:
        message = "No local task issues are reported."

    return TaskQueueSummary(
        total=len(tasks),
        counts=dict(sorted(counts.items())),
        blocked=blocked,
        message=message,
    )
