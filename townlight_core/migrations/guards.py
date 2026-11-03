"""Idempotent Alembic operation helpers. These wrap alembic.op.* calls with 'skip if already exists' semantics so townlight_core's baseline migration and records' 14 guarded migrations can all be re-run against a database that already contains the shared schema."""

from __future__ import annotations

from typing import Any

import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.engine import Inspector


def _inspector() -> Inspector:
    """Return a fresh SQLAlchemy Inspector bound to the current Alembic connection."""
    return sa.inspect(op.get_bind())


def idempotent_create_table(name: str, *columns: Any, **kwargs: Any) -> None:
    """op.create_table that no-ops if the table already exists.

    Used by townlight_core's baseline migration and by guarded records migrations that
    create shared tables (e.g. `users`, `data_sources`). If the table is already
    present in the database, the create is skipped; otherwise it proceeds normally.
    """
    inspector = _inspector()
    if inspector.has_table(name):
        return
    op.create_table(name, *columns, **kwargs)


def idempotent_add_column(table: str, column: Any, **kwargs: Any) -> None:
    """op.add_column that no-ops if the column already exists.

    If the target table itself does not exist, returns silently — the upstream
    migration (or townlight_core baseline) is responsible for creating it. If the
    table exists and the column is already present, skip. Otherwise add it.
    """
    inspector = _inspector()
    if not inspector.has_table(table):
        # Upstream migration will handle table creation; nothing to add to.
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column.name in existing:
        return
    op.add_column(table, column, **kwargs)


def idempotent_alter_column(
    table: str,
    column: str,
    *,
    existing_type: Any = None,
    nullable: bool | None = None,
    server_default: Any = None,
    new_column_name: str | None = None,
    **kwargs: Any,
) -> None:
    """op.alter_column that introspects current state before applying.

    Applies the alter only when a concrete difference is detected:
      - `nullable` is specified AND the current column's nullable != requested, OR
      - `new_column_name` is specified AND it differs from `column`.

    `existing_type` and `server_default` are passed through to `op.alter_column`
    but are NOT used as the diff trigger — type/default deep-comparison is too
    brittle across dialects. Those alters are the caller's responsibility to
    schedule once by migration history; this guard exists to absorb repeat runs.

    If the table or column does not exist, returns silently.
    """
    inspector = _inspector()
    if not inspector.has_table(table):
        return

    cols = {col["name"]: col for col in inspector.get_columns(table)}
    current = cols.get(column)
    if current is None:
        return

    should_apply = False
    if nullable is not None and bool(current.get("nullable")) != bool(nullable):
        should_apply = True
    if new_column_name is not None and new_column_name != column:
        should_apply = True

    if not should_apply:
        return

    alter_kwargs: dict[str, Any] = dict(kwargs)
    if existing_type is not None:
        alter_kwargs["existing_type"] = existing_type
    if nullable is not None:
        alter_kwargs["nullable"] = nullable
    if server_default is not None:
        alter_kwargs["server_default"] = server_default
    if new_column_name is not None:
        alter_kwargs["new_column_name"] = new_column_name

    op.alter_column(table, column, **alter_kwargs)


def idempotent_create_index(
    name: str,
    table: str,
    columns: list[str | Any],
    *,
    unique: bool = False,
    **kwargs: Any,
) -> None:
    """op.create_index that no-ops if an index with this name already exists on the table.

    Used by guarded records migrations whose ``op.create_index`` calls target shared
    tables that townlight_core's baseline migration already populated with indexes
    (per pg_dump-derived DDL). If the named index is already present, skip the
    create; otherwise create it normally.
    """
    inspector = _inspector()
    if not inspector.has_table(table):
        # Upstream migration will create the table; nothing to index against yet.
        return
    existing = {idx["name"] for idx in inspector.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns, unique=unique, **kwargs)


def idempotent_create_foreign_key(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs: Any,
) -> None:
    """op.create_foreign_key that no-ops if a constraint with this name already exists.

    Checks via Inspector.get_foreign_keys against the source table.
    """
    inspector = _inspector()
    if not inspector.has_table(source_table):
        return
    existing = {fk["name"] for fk in inspector.get_foreign_keys(source_table) if fk.get("name")}
    if constraint_name in existing:
        return
    op.create_foreign_key(
        constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs
    )


def idempotent_create_unique_constraint(
    constraint_name: str,
    table: str,
    columns: list[str],
    **kwargs: Any,
) -> None:
    """op.create_unique_constraint that no-ops if the constraint already exists."""
    inspector = _inspector()
    if not inspector.has_table(table):
        return
    existing = {uc["name"] for uc in inspector.get_unique_constraints(table) if uc.get("name")}
    if constraint_name in existing:
        return
    op.create_unique_constraint(constraint_name, table, columns, **kwargs)


def idempotent_create_check_constraint(
    constraint_name: str,
    table: str,
    condition: str,
    **kwargs: Any,
) -> None:
    """op.create_check_constraint that no-ops if the constraint already exists."""
    inspector = _inspector()
    if not inspector.has_table(table):
        return
    existing = {cc["name"] for cc in inspector.get_check_constraints(table) if cc.get("name")}
    if constraint_name in existing:
        return
    op.create_check_constraint(constraint_name, table, condition, **kwargs)


def idempotent_drop_constraint(
    constraint_name: str,
    table: str,
    *,
    type_: str = "unique",
) -> None:
    """Drop a named constraint, no-op if the constraint or table does not exist.

    Supports type_='unique' (checks get_unique_constraints) and
    type_='foreignkey' (checks get_foreign_keys). For other type_ values,
    delegates directly to op.drop_constraint — caller is responsible for
    guarding those cases.

    Used by townlight_core_0002_llm to idempotently drop the old
    prompt_templates_name_key UNIQUE constraint before adding the
    replacement composite unique constraint.
    """
    inspector = _inspector()
    if not inspector.has_table(table):
        return
    if type_ == "unique":
        existing = {uc["name"] for uc in inspector.get_unique_constraints(table) if uc.get("name")}
        if constraint_name not in existing:
            return
    elif type_ == "foreignkey":
        existing = {fk["name"] for fk in inspector.get_foreign_keys(table) if fk.get("name")}
        if constraint_name not in existing:
            return
    op.drop_constraint(constraint_name, table, type_=type_)


def has_table(name: str) -> bool:
    """Thin public wrapper returning whether the named table exists in the current DB."""
    return _inspector().has_table(name)
