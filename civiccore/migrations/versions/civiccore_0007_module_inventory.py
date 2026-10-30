# SPDX-License-Identifier: AGPL-3.0-only
"""Append-only, scope-keyed installed-module inventory.

Additive only: no existing table, row or consumer path is changed. One header row per
``(scope_id, revision)`` plus one entry row per declared module; revisions are never rewritten
because a later revision supersedes the earlier declaration while the earlier declaration stays
retrievable. Downgrade is deliberately a no-op: dropping the inventory would erase which modules
a scope declared installed, so recovery is restore-from-backup.
"""

from alembic import op

revision = "civiccore_0007_module_inventory"
down_revision = "civiccore_0006_rule_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS civiccore_module_inventory (
        scope_id varchar(64) NOT NULL CHECK (length(btrim(scope_id)) > 0),
        revision integer NOT NULL CHECK (revision >= 1),
        profile varchar(20) NOT NULL CHECK (profile IN ('windows_local','server','developer')),
        civiccore_version varchar(40) NOT NULL CHECK (length(btrim(civiccore_version)) > 0),
        content_sha256 char(64) NOT NULL,
        recorded_by varchar(128) NOT NULL CHECK (length(btrim(recorded_by)) > 0),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT civiccore_module_inventory_pkey PRIMARY KEY (scope_id, revision)
    )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS civiccore_module_inventory_entries (
        scope_id varchar(64) NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        module_id varchar(64) NOT NULL CHECK (length(btrim(module_id)) > 0),
        version varchar(40) NOT NULL CHECK (length(btrim(version)) > 0),
        enabled boolean NOT NULL,
        manifest jsonb NOT NULL,
        CONSTRAINT civiccore_module_inventory_entries_pkey
            PRIMARY KEY (scope_id, revision, module_id),
        CONSTRAINT civiccore_module_inventory_entries_scope_fk
            FOREIGN KEY (scope_id, revision)
            REFERENCES civiccore_module_inventory (scope_id, revision)
    )"""
    )
    # Deterministic scope listing without a sequential scan of every revision.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_civiccore_module_inventory_scope "
        "ON civiccore_module_inventory (scope_id, revision DESC)"
    )
    op.execute(
        """CREATE OR REPLACE FUNCTION civiccore_module_inventory_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'civiccore module inventory is append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$"""
    )
    for table in ("civiccore_module_inventory", "civiccore_module_inventory_entries"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.execute(
            f"""CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION civiccore_module_inventory_append_only()"""
        )
    # Scope isolation comes from the composite primary key and the (scope_id, revision)
    # foreign key: a revision's entries cannot be read or joined across scopes, while the same
    # module package may still be declared installed independently by another deployment scope.


def downgrade() -> None:
    """Preserve declared inventory; recover through backup/restore rather than deletion."""
    pass
