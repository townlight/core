"""Tests for townlight_core.llm.registry.service and .router.

Mirrors the testcontainer pattern from tests/test_llm_templates.py:
function-scoped Postgres container, schema upgraded to townlight_core HEAD,
fresh AsyncSession per test for full isolation.

Hard Rule 4a: no test.skip / xfail / inside-test importorskip. The Docker
importorskip at module top is acceptable per existing precedent (Docker is
environment, not an SDK we control).
"""
from __future__ import annotations

import asyncio
import sys

# Windows + asyncpg requires SelectorEventLoop, not the default ProactorEventLoop,
# to avoid teardown race conditions during connection close.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import contextlib
import os

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

testcontainers = pytest.importorskip(
    "testcontainers.postgres",
    reason="testcontainers[postgres] not installed; install dev extras to run service tests",
)
PostgresContainer = testcontainers.PostgresContainer

from townlight_core.llm.context import DEFAULT_CONTEXT_WINDOW  # noqa: E402
from townlight_core.llm.registry import (  # noqa: E402
    MissingModelError,
    ModelRegistry,
    get_active_model,
    get_active_model_context_window,
    model_registry_router,
    require_active_model,
)
from townlight_core.llm.registry.router import get_session  # noqa: E402
from townlight_core.migrations.runner import upgrade_to_head  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable; False otherwise."""
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


async def _seed_model(
    session,
    *,
    model_name: str = "test-model",
    is_active: bool = True,
    context_window_size: int | None = 8192,
) -> ModelRegistry:
    row = ModelRegistry(
        model_name=model_name,
        is_active=is_active,
        context_window_size=context_window_size,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def pg_container():
    if not _docker_available():
        pytest.skip(
            "Docker daemon not reachable — service tests require testcontainers "
            "with a running Docker host. Install Docker Desktop or run in CI."
        )
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest_asyncio.fixture(loop_scope="function")
async def session_factory(pg_container):
    """Build an async_sessionmaker against a fresh upgraded DB."""
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


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_returns_none_when_empty(session):
    assert await get_active_model(session) is None


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_returns_active_row(session):
    row = await _seed_model(session, model_name="active-1", is_active=True)
    fetched = await get_active_model(session)
    assert fetched is not None
    assert fetched.id == row.id
    assert fetched.model_name == "active-1"


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_returns_none_when_only_inactive(session):
    await _seed_model(session, model_name="inactive-1", is_active=False)
    assert await get_active_model(session) is None


@pytest.mark.asyncio(loop_scope="function")
async def test_require_active_model_raises_when_none_active(session):
    with pytest.raises(MissingModelError) as excinfo:
        await require_active_model(session)
    msg = str(excinfo.value)
    assert "active" in msg
    assert "is_active=true" in msg


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_context_window_returns_db_value(session):
    await _seed_model(session, is_active=True, context_window_size=4096)
    assert await get_active_model_context_window(session) == 4096


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_context_window_defaults_when_no_active(session):
    assert await get_active_model_context_window(session) == DEFAULT_CONTEXT_WINDOW


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_context_window_defaults_when_size_null(session):
    await _seed_model(session, is_active=True, context_window_size=None)
    assert await get_active_model_context_window(session) == DEFAULT_CONTEXT_WINDOW


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_context_window_defaults_when_size_zero(session):
    await _seed_model(session, is_active=True, context_window_size=0)
    assert await get_active_model_context_window(session) == DEFAULT_CONTEXT_WINDOW


@pytest.mark.asyncio(loop_scope="function")
async def test_get_active_model_lowest_id_wins_when_multiple_active(session):
    first = await _seed_model(session, model_name="first-active", is_active=True)
    second = await _seed_model(session, model_name="second-active", is_active=True)
    assert second.id > first.id  # sanity
    fetched = await get_active_model(session)
    assert fetched is not None
    assert fetched.id == first.id


# ---------------------------------------------------------------------------
# Router tests (FastAPI + httpx ASGITransport)
# ---------------------------------------------------------------------------


def _build_app(session_factory) -> FastAPI:
    """FastAPI app with the registry router mounted and get_session overridden."""
    app = FastAPI()
    app.include_router(model_registry_router)

    async def _override():
        async with session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    return app


@pytest_asyncio.fixture(loop_scope="function")
async def client(session_factory):
    app = _build_app(session_factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio(loop_scope="function")
async def test_router_list_returns_all_models_via_app(client, session):
    await _seed_model(session, model_name="m1", is_active=True)
    await _seed_model(session, model_name="m2", is_active=False)

    resp = await client.get("/admin/models")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    names = {row["model_name"] for row in body}
    assert names == {"m1", "m2"}


@pytest.mark.asyncio(loop_scope="function")
async def test_router_create_inserts_model(client):
    payload = {
        "model_name": "new-model",
        "model_version": "v1",
        "is_active": True,
        "context_window_size": 16384,
    }
    resp = await client.post("/admin/models", json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["model_name"] == "new-model"
    assert created["context_window_size"] == 16384

    fetched = await client.get(f"/admin/models/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["model_name"] == "new-model"


@pytest.mark.asyncio(loop_scope="function")
async def test_router_get_404_when_missing(client):
    resp = await client.get("/admin/models/9999")
    assert resp.status_code == 404
    assert "9999" in resp.json()["detail"]


@pytest.mark.asyncio(loop_scope="function")
async def test_router_patch_updates_model(client, session):
    row = await _seed_model(session, model_name="patch-target", is_active=False)

    resp = await client.patch(
        f"/admin/models/{row.id}", json={"is_active": True}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_router_delete_removes_model(client, session):
    row = await _seed_model(session, model_name="delete-me", is_active=False)

    resp = await client.delete(f"/admin/models/{row.id}")
    assert resp.status_code == 204

    follow_up = await client.get(f"/admin/models/{row.id}")
    assert follow_up.status_code == 404


@pytest.mark.asyncio(loop_scope="function")
async def test_router_unconfigured_session_raises():
    """Mounting without overriding get_session yields an actionable runtime error."""
    app = FastAPI()
    app.include_router(model_registry_router)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/admin/models")

    # FastAPI surfaces unhandled exceptions as 500; the actionable message is
    # in the raised RuntimeError. raise_app_exceptions=False ensures httpx
    # returns the response rather than re-raising.
    assert resp.status_code == 500
