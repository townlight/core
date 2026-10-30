"""Idempotency test for civiccore_0001_baseline_v1. Blocks Phase 1 Part A PR merge per ADR-0003 §5."""

from __future__ import annotations

import contextlib
import os

import pytest
import sqlalchemy as sa

# Skip the whole module gracefully if testcontainers or Docker are unavailable.
# Rationale: these tests require a live ephemeral Postgres and cannot be
# faked with a stub. When the runner lacks Docker, we record the skip reason
# rather than failing — CI image provisions Docker; dev machines may not.
testcontainers = pytest.importorskip(
    "testcontainers.postgres",
    reason="testcontainers[postgres] not installed; install dev extras to run idempotency tests",
)
PostgresContainer = testcontainers.PostgresContainer

from civiccore.migrations.runner import current_revision, upgrade_to_head  # noqa: E402
from civiccore.migrations.versions.civiccore_0001_baseline_v1 import (  # noqa: E402
    _SHARED_TABLE_ORDER,
)

EXPECTED_HEAD = "civiccore_0009_job_artifacts"


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable; False otherwise.

    testcontainers spins up via the Docker SDK, which raises ``DockerException``
    when the daemon is unreachable. We probe once at fixture setup so that
    dev machines without Docker get a clear skip rather than a stack trace.
    """
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def pg_container():
    """Ephemeral Postgres 17 + pgvector container shared across this module's tests.

    Uses the same ``pgvector/pgvector:pg17`` image as CivicRecords' docker-compose
    stack so the extension stanza in the baseline migration (``CREATE EXTENSION
    IF NOT EXISTS vector``) can succeed. Plain ``postgres:17`` lacks the
    pgvector control file and would fail the ``document_chunks`` table DDL.

    Skips the whole module if Docker is not available on the runner.
    """
    if not _docker_available():
        pytest.skip(
            "Docker daemon not reachable — idempotency tests require testcontainers "
            "with a running Docker host. Install Docker Desktop or run in CI."
        )
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest.fixture
def engine(pg_container):
    """Fresh SQLAlchemy engine against the ephemeral container.

    A new engine per test gives each test a clean transactional context;
    the container itself is reused across the module for speed.
    """
    url = pg_container.get_connection_url()
    # testcontainers returns a psycopg2 URL; normalize to psycopg2 driver form
    # SQLAlchemy understands without requiring asyncpg here.
    eng = sa.create_engine(url, future=True)
    try:
        yield eng
    finally:
        eng.dispose()


@contextlib.contextmanager
def _database_url_env(pg_container):
    """Set DATABASE_URL to the testcontainer URL for the scope of the block.

    Civiccore's runner opens its own connection from DATABASE_URL (see
    ``upgrade_to_head`` docstring re: nested EnvironmentContext fix), so the
    test must export the testcontainer URL before invoking it. Restores the
    prior value (or unsets) on exit so tests don't leak environment state.
    """
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = pg_container.get_connection_url()
    try:
        yield
    finally:
        if old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_url


def _snapshot_schema(connection: sa.Connection) -> list[tuple[str, list[str]]]:
    """Capture (table_name, sorted column_names) for every shared table present.

    Sorted for stable comparison across runs; structure is a plain list of
    tuples so equality is exact.
    """
    inspector = sa.inspect(connection)
    existing = set(inspector.get_table_names())
    snapshot: list[tuple[str, list[str]]] = []
    for table in _SHARED_TABLE_ORDER:
        if table not in existing:
            continue
        cols = sorted(col["name"] for col in inspector.get_columns(table))
        snapshot.append((table, cols))
    return sorted(snapshot, key=lambda row: row[0])


def test_baseline_runs_clean_on_empty_db(engine, pg_container):
    """Baseline migration creates all 16 shared tables and stamps HEAD on an empty DB."""
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        existing = set(inspector.get_table_names())
        missing = [t for t in _SHARED_TABLE_ORDER if t not in existing]
        assert not missing, (
            f"Baseline did not create expected shared tables: {missing}. "
            f"Found tables: {sorted(existing)}"
        )
        assert current_revision(connection) == EXPECTED_HEAD


def test_baseline_is_idempotent(engine, pg_container):
    """Re-running the baseline against an already-populated DB is a no-op.

    Proves the ``idempotent_*`` op wrappers (see ``civiccore.migrations.guards``)
    skip existing objects rather than destructively recreating them — which
    is what makes the extracted civiccore baseline safe to ship alongside
    already-deployed civicrecords databases (ADR-0003 §3).
    """
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        first_snapshot = _snapshot_schema(connection)
        assert current_revision(connection) == EXPECTED_HEAD

    # Second upgrade on the same engine — must not raise, must not mutate schema.
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        second_snapshot = _snapshot_schema(connection)
        assert current_revision(connection) == EXPECTED_HEAD

    assert first_snapshot == second_snapshot, (
        "Schema changed between first and second baseline runs — baseline is not idempotent.\n"
        f"First:  {first_snapshot}\n"
        f"Second: {second_snapshot}"
    )
