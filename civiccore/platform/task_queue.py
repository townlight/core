"""PostgreSQL-backed local task queue for Townlight desktop runtimes."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from civiccore.db import Base
from civiccore.platform.tasks import (
    LocalTaskEnvelope,
    TaskRetryPolicy,
    record_task_attempt,
)

TaskHandler = Callable[[LocalTaskEnvelope], object | Awaitable[object]]


class LocalTask(Base):
    """Durable local task row used by the Windows local runtime."""

    __tablename__ = "civiccore_local_tasks"

    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(64), index=True)
    task_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="queued")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    audit_subject_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


def task_row_to_envelope(row: LocalTask) -> LocalTaskEnvelope:
    """Convert an ORM row into the public task contract."""

    return LocalTaskEnvelope(
        task_id=row.task_id,
        module_id=row.module_id,
        task_type=row.task_type,
        status=row.status,  # type: ignore[arg-type]
        payload=row.payload or {},
        attempt_count=row.attempt_count,
        queued_at=row.queued_at,
        available_at=row.available_at,
        last_error=row.last_error,
        idempotency_key=row.idempotency_key,
        audit_subject_id=row.audit_subject_id,
    )


async def enqueue_local_task(
    session: AsyncSession,
    task: LocalTaskEnvelope,
) -> LocalTaskEnvelope:
    """Insert a task unless its idempotency key already exists."""

    if task.idempotency_key:
        existing = await session.scalar(
            select(LocalTask).where(LocalTask.idempotency_key == task.idempotency_key)
        )
        if existing is not None:
            return task_row_to_envelope(existing)

    row = LocalTask(
        task_id=task.task_id,
        module_id=task.module_id,
        task_type=task.task_type,
        status=task.status,
        payload=task.payload,
        attempt_count=task.attempt_count,
        queued_at=task.queued_at,
        available_at=task.available_at,
        last_error=task.last_error,
        idempotency_key=task.idempotency_key,
        audit_subject_id=task.audit_subject_id,
    )
    session.add(row)
    await session.flush()
    return task_row_to_envelope(row)


async def claim_next_local_task(
    session: AsyncSession,
    *,
    module_id: str | None = None,
    now: datetime | None = None,
) -> LocalTaskEnvelope | None:
    """Claim the next queued or due retry task."""

    current_time = now or datetime.now(UTC)
    query = (
        select(LocalTask)
        .where(
            (LocalTask.status == "queued")
            | ((LocalTask.status == "retry_wait") & (LocalTask.available_at <= current_time))
        )
        .order_by(LocalTask.queued_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if module_id is not None:
        query = query.where(LocalTask.module_id == module_id)

    row = await session.scalar(query)
    if row is None:
        return None

    row.status = "running"
    row.available_at = None
    await session.flush()
    return task_row_to_envelope(row)


async def complete_local_task(session: AsyncSession, task_id: str) -> LocalTaskEnvelope:
    """Mark a claimed task as succeeded."""

    row = await _get_task_row(session, task_id)
    row.status = "succeeded"
    row.last_error = None
    row.available_at = None
    await session.flush()
    return task_row_to_envelope(row)


async def fail_local_task(
    session: AsyncSession,
    task_id: str,
    *,
    error: str,
    now: datetime | None = None,
    policy: TaskRetryPolicy | None = None,
) -> LocalTaskEnvelope:
    """Record a failed attempt and either schedule retry or exhaust the task."""

    row = await _get_task_row(session, task_id)
    result = record_task_attempt(
        task_row_to_envelope(row),
        success=False,
        error=error,
        now=now,
        policy=policy,
    )
    _apply_envelope(row, result.task)
    await session.flush()
    return task_row_to_envelope(row)


async def run_one_local_task(
    session: AsyncSession,
    *,
    handlers: dict[str, TaskHandler],
    module_id: str | None = None,
    now: datetime | None = None,
    retry_policy: TaskRetryPolicy | None = None,
) -> LocalTaskEnvelope | None:
    """Claim and run one task with a registered in-process handler."""

    task = await claim_next_local_task(session, module_id=module_id, now=now)
    if task is None:
        return None

    handler = handlers.get(task.task_type)
    if handler is None:
        return await fail_local_task(
            session,
            task.task_id,
            error=f"No handler registered for task type {task.task_type!r}.",
            now=now,
            policy=retry_policy,
        )

    try:
        result = handler(task)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # pragma: no cover - exact handler failures are module-owned
        return await fail_local_task(
            session,
            task.task_id,
            error=str(exc),
            now=now,
            policy=retry_policy,
        )
    return await complete_local_task(session, task.task_id)


async def _get_task_row(session: AsyncSession, task_id: str) -> LocalTask:
    row = await session.get(LocalTask, task_id)
    if row is None:
        raise LookupError(f"local task not found: {task_id}")
    return row


def _apply_envelope(row: LocalTask, envelope: LocalTaskEnvelope) -> None:
    row.status = envelope.status
    row.payload = envelope.payload
    row.attempt_count = envelope.attempt_count
    row.available_at = envelope.available_at
    row.last_error = envelope.last_error
    row.idempotency_key = envelope.idempotency_key
    row.audit_subject_id = envelope.audit_subject_id
