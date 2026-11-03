"""PostgreSQL-backed task queue tests for the Windows local runtime."""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from argparse import Namespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

testcontainers = pytest.importorskip(
    "testcontainers.postgres",
    reason="testcontainers[postgres] not installed; install dev extras to run queue tests",
)
PostgresContainer = testcontainers.PostgresContainer

from townlight_core.migrations.runner import upgrade_to_head  # noqa: E402
from townlight_core.platform import (  # noqa: E402
    LocalTask,
    LocalTaskEnvelope,
    TaskRetryPolicy,
    claim_next_local_task,
    complete_local_task,
    enqueue_local_task,
    fail_local_task,
    run_one_local_task,
)
from townlight_core.tasks import register_task_handler  # noqa: E402
from townlight_core.tasks.worker import _run_worker  # noqa: E402


def _docker_available() -> bool:
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
        return True
    except Exception:
        return False


@contextlib.contextmanager
def _database_url_env(pg_container):
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = pg_container.get_connection_url()
    try:
        yield
    finally:
        if old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_url


def _async_url(sync_url: str) -> str:
    if "+psycopg2" in sync_url:
        return sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg")
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_url


@pytest.fixture(scope="function")
def pg_container():
    if not _docker_available():
        pytest.skip("Docker daemon not reachable; queue tests require a PostgreSQL container.")
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest_asyncio.fixture(loop_scope="function")
async def session_factory(pg_container):
    with _database_url_env(pg_container):
        upgrade_to_head()

    engine = create_async_engine(_async_url(pg_container.get_connection_url()))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def session(session_factory):
    async with session_factory() as sess:
        yield sess


@pytest.mark.asyncio(loop_scope="function")
async def test_local_task_queue_enqueues_claims_and_completes(session) -> None:
    task = LocalTaskEnvelope(
        task_id="records-response-1",
        module_id="townlight_records",
        task_type="records_response_export",
        payload={"request_id": "RR-1001"},
        idempotency_key="RR-1001:response-export",
    )

    created = await enqueue_local_task(session, task)
    duplicate = await enqueue_local_task(session, task.model_copy(update={"task_id": "duplicate"}))
    claimed = await claim_next_local_task(session)
    completed = await complete_local_task(session, "records-response-1")
    await session.commit()

    persisted = await session.get(LocalTask, "records-response-1")
    assert created.task_id == "records-response-1"
    assert duplicate.task_id == "records-response-1"
    assert claimed is not None
    assert claimed.status == "running"
    assert completed.status == "succeeded"
    assert persisted is not None
    assert persisted.status == "succeeded"


@pytest.mark.asyncio(loop_scope="function")
async def test_local_task_queue_records_retry_state(session) -> None:
    task = LocalTaskEnvelope(
        task_id="records-search-1",
        module_id="townlight_records",
        task_type="records_search_index",
    )
    await enqueue_local_task(session, task)
    await claim_next_local_task(session)

    failed = await fail_local_task(
        session,
        "records-search-1",
        error="Local index unavailable",
        policy=TaskRetryPolicy(max_attempts=3, base_delay_seconds=1),
    )
    await session.commit()

    assert failed.status == "retry_wait"
    assert failed.attempt_count == 1
    assert failed.available_at is not None
    assert failed.last_error == "Local index unavailable"


@pytest.mark.asyncio(loop_scope="function")
async def test_run_one_local_task_uses_registered_handler(session) -> None:
    seen: list[str] = []
    await enqueue_local_task(
        session,
        LocalTaskEnvelope(
            task_id="records-review-1",
            module_id="townlight_records",
            task_type="records_review_packet",
        ),
    )

    async def handler(task: LocalTaskEnvelope) -> None:
        seen.append(task.task_id)

    completed = await run_one_local_task(session, handlers={"records_review_packet": handler})
    await session.commit()

    assert completed is not None
    assert completed.status == "succeeded"
    assert seen == ["records-review-1"]


@pytest.mark.asyncio(loop_scope="function")
async def test_worker_once_exits_when_queue_is_empty(pg_container) -> None:
    with _database_url_env(pg_container):
        upgrade_to_head()
        result = await _run_worker(
            Namespace(
                once=True,
                poll_seconds=0.01,
                max_attempts=1,
                base_delay_seconds=1,
                max_delay_seconds=1,
            )
        )

    assert result == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_worker_once_runs_registered_handler(pg_container, session_factory) -> None:
    seen: list[str] = []

    @register_task_handler("records_worker_registry_probe")
    async def handler(task: LocalTaskEnvelope) -> None:
        seen.append(task.task_id)

    async with session_factory() as sess:
        await enqueue_local_task(
            sess,
            LocalTaskEnvelope(
                task_id="records-worker-1",
                module_id="townlight_records",
                task_type="records_worker_registry_probe",
            ),
        )
        await sess.commit()

    with _database_url_env(pg_container):
        result = await _run_worker(
            Namespace(
                once=True,
                poll_seconds=0.01,
                max_attempts=1,
                base_delay_seconds=1,
                max_delay_seconds=1,
            )
        )

    async with session_factory() as sess:
        persisted = await sess.get(LocalTask, "records-worker-1")

    assert result == 0
    assert seen == ["records-worker-1"]
    assert persisted is not None
    assert persisted.status == "succeeded"
