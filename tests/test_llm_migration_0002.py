"""Tests for civiccore_0002_llm migration.

Validates:
- New columns (template_name, consumer_app, is_override) exist after upgrade_to_head()
- Old column (name) no longer exists after migration
- New unique constraint uq_prompt_templates_app_name_version is in place
- Incremental upgrade path from 0001 through 0002 works correctly
- Migration remains idempotent when the full head chain is run twice
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

import pytest
import sqlalchemy as sa

testcontainers = pytest.importorskip(
    "testcontainers.postgres",
    reason="testcontainers[postgres] not installed; install dev extras to run migration tests",
)
PostgresContainer = testcontainers.PostgresContainer

import civiccore  # noqa: E402
from civiccore.migrations.runner import current_revision, upgrade_to_head  # noqa: E402
from civiccore.migrations.versions.civiccore_0001_baseline_v1 import (  # noqa: E402
    _SHARED_TABLE_ORDER,
)

EXPECTED_HEAD = "civiccore_0009_job_artifacts"

_ALEMBIC_INI = Path(civiccore.__file__).parent / "migrations" / "alembic.ini"


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable; False otherwise."""
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
def pg_container():
    """Ephemeral Postgres 17 + pgvector container shared across this module's tests."""
    if not _docker_available():
        pytest.skip(
            "Docker daemon not reachable — migration tests require testcontainers "
            "with a running Docker host. Install Docker Desktop or run in CI."
        )
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest.fixture
def engine(pg_container):
    """Fresh SQLAlchemy engine against the ephemeral container."""
    url = pg_container.get_connection_url()
    eng = sa.create_engine(url, future=True)
    try:
        yield eng
    finally:
        eng.dispose()


@contextlib.contextmanager
def _database_url_env(pg_container):
    """Set DATABASE_URL to the testcontainer URL for the scope of the block."""
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = pg_container.get_connection_url()
    try:
        yield
    finally:
        if old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_url


def _upgrade_to_revision(pg_container, revision: str) -> None:
    """Run Alembic upgrade to a specific revision (not necessarily head).

    Mirrors the runner's pattern but calls command.upgrade(cfg, revision)
    instead of "head", so tests can apply only part of the migration chain.
    """
    from alembic import command, config as alembic_config

    url = pg_container.get_connection_url()
    eng = sa.create_engine(url, future=True)
    try:
        cfg = alembic_config.Config(str(_ALEMBIC_INI))
        with eng.connect() as conn:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, revision)
            conn.commit()
    finally:
        eng.dispose()


def _snapshot_schema(connection: sa.Connection) -> list[tuple[str, list[str]]]:
    """Capture (table_name, sorted column_names) for every shared table present."""
    inspector = sa.inspect(connection)
    existing = set(inspector.get_table_names())
    snapshot: list[tuple[str, list[str]]] = []
    for table in _SHARED_TABLE_ORDER:
        if table not in existing:
            continue
        cols = sorted(col["name"] for col in inspector.get_columns(table))
        snapshot.append((table, cols))
    return sorted(snapshot, key=lambda row: row[0])


def test_0002_prompt_templates_has_new_columns(engine, pg_container):
    """After upgrade_to_head(), prompt_templates has the Phase 2 override columns.

    Verifies:
    - Current revision is the latest CivicCore head
    - template_name column exists (renamed from name)
    - consumer_app column exists
    - is_override column exists
    - old name column no longer exists
    - uq_prompt_templates_app_name_version unique constraint exists
    """
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        assert current_revision(connection) == EXPECTED_HEAD

        inspector = sa.inspect(connection)
        col_names = {col["name"] for col in inspector.get_columns("prompt_templates")}

        assert "template_name" in col_names, (
            f"Expected column 'template_name' in prompt_templates; found: {sorted(col_names)}"
        )
        assert "consumer_app" in col_names, (
            f"Expected column 'consumer_app' in prompt_templates; found: {sorted(col_names)}"
        )
        assert "is_override" in col_names, (
            f"Expected column 'is_override' in prompt_templates; found: {sorted(col_names)}"
        )
        assert "name" not in col_names, (
            f"Column 'name' should have been renamed to 'template_name' in 0002 migration; "
            f"still present in: {sorted(col_names)}"
        )

        unique_constraints = inspector.get_unique_constraints("prompt_templates")
        constraint_names = {uc["name"] for uc in unique_constraints}
        assert "uq_prompt_templates_app_name_version" in constraint_names, (
            f"Expected unique constraint 'uq_prompt_templates_app_name_version'; "
            f"found constraints: {sorted(constraint_names)}"
        )


def test_0002_upgrade_from_0001_baseline(pg_container):
    """Incremental upgrade from 0001 through 0002 transforms prompt_templates correctly.

    Step 1: Apply only civiccore_0001_baseline_v1 — verify old schema shape (name column).
    Step 2: Apply upgrade_to_head() — verify 0002 shape plus any later head migrations.
    """
    # Step 1: only 0001 applied
    _upgrade_to_revision(pg_container, "civiccore_0001_baseline_v1")

    url = pg_container.get_connection_url()
    eng = sa.create_engine(url, future=True)
    try:
        with eng.connect() as connection:
            inspector = sa.inspect(connection)
            col_names_0001 = {col["name"] for col in inspector.get_columns("prompt_templates")}

            assert "name" in col_names_0001, (
                f"After 0001, expected column 'name' in prompt_templates; found: {sorted(col_names_0001)}"
            )
            assert "template_name" not in col_names_0001, (
                f"After 0001 only, 'template_name' should not yet exist; found: {sorted(col_names_0001)}"
            )
            assert "consumer_app" not in col_names_0001, (
                f"After 0001 only, 'consumer_app' should not yet exist; found: {sorted(col_names_0001)}"
            )

        # Step 2: upgrade to head (0002 and later migrations applied)
        with _database_url_env(pg_container):
            upgrade_to_head()

        with eng.connect() as connection:
            inspector = sa.inspect(connection)
            col_names_0002 = {col["name"] for col in inspector.get_columns("prompt_templates")}

            assert "template_name" in col_names_0002, (
                f"After 0002, expected 'template_name'; found: {sorted(col_names_0002)}"
            )
            assert "consumer_app" in col_names_0002, (
                f"After 0002, expected 'consumer_app'; found: {sorted(col_names_0002)}"
            )
            assert "is_override" in col_names_0002, (
                f"After 0002, expected 'is_override'; found: {sorted(col_names_0002)}"
            )
            assert "name" not in col_names_0002, (
                f"After 0002, 'name' should have been renamed; still present in: {sorted(col_names_0002)}"
            )

            assert current_revision(connection) == EXPECTED_HEAD
    finally:
        eng.dispose()


def test_0002_is_idempotent(engine, pg_container):
    """Re-running upgrade_to_head() after the full head chain is already applied is a no-op.

    Proves idempotent guards in the 0002 migration skip existing objects
    rather than raising or mutating schema.
    """
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        first_snapshot = _snapshot_schema(connection)
        assert current_revision(connection) == EXPECTED_HEAD

    # Second upgrade on the same DB — must not raise, must not mutate schema.
    with _database_url_env(pg_container):
        upgrade_to_head()

    with engine.connect() as connection:
        second_snapshot = _snapshot_schema(connection)
        assert current_revision(connection) == EXPECTED_HEAD

    assert first_snapshot == second_snapshot, (
        "Schema changed between first and second 0002 runs — migration is not idempotent.\n"
        f"First:  {first_snapshot}\n"
        f"Second: {second_snapshot}"
    )
