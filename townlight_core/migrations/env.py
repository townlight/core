"""Alembic env for townlight_core. Reads the connection from Config.attributes['connection'] when invoked by runner.py (the normal path). Falls back to DATABASE_URL env var when invoked standalone."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Tolerate the minimal alembic.ini which intentionally omits [loggers]/[handlers]/[formatters].
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except KeyError:
        # No logging sections configured; skip Python logging setup.
        pass

VERSION_TABLE = "alembic_version_townlight_core"
target_metadata = None  # v0.1 baseline is raw-SQL; no ORM metadata yet.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout / script without a DB connection."""
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Two sub-modes:
      - Connection supplied by caller via `config.attributes["connection"]`
        (the normal path: records' env.py hands us its live connection through
        `runner.upgrade_to_head`). We do not dispose the connection; the caller
        owns its lifecycle.
      - Standalone CLI (`alembic upgrade head`): no attached connection, so
        build an engine from `DATABASE_URL` (or the ini's `sqlalchemy.url`) and
        run migrations against it.
    """
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # Standalone path: no connection was passed in.
    url = os.environ.get("DATABASE_URL")
    ini_section = config.get_section(config.config_ini_section) or {}
    if url:
        ini_section["sqlalchemy.url"] = url

    engine = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
