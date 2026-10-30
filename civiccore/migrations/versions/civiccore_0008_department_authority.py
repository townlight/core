# SPDX-License-Identifier: AGPL-3.0-only
"""Append-only department grant ledger for the shared Core authority.

Additive only: no existing table, row or consumer path is changed. One row per grant/revoke
*event*, keyed by ``(scope_id, subject, department_id, sequence)``, so the active entitlement is
always the highest sequence and a revoked grant stays readable as history. PostgreSQL refuses
UPDATE and DELETE, so a revoked grant cannot be silently un-revoked by editing a row.
Downgrade is deliberately a no-op: dropping the ledger would erase who was allowed to read
which department, so recovery is restore-from-backup.
"""

from alembic import op

revision = "civiccore_0008_authority"
down_revision = "civiccore_0007_module_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS civiccore_department_grant_events (
        scope_id varchar(64) NOT NULL CHECK (length(btrim(scope_id)) > 0),
        subject varchar(320) NOT NULL CHECK (length(btrim(subject)) > 0),
        department_id uuid NOT NULL,
        sequence integer NOT NULL CHECK (sequence >= 1),
        action varchar(10) NOT NULL CHECK (action IN ('grant','revoke')),
        roles text[] NOT NULL DEFAULT ARRAY[]::text[],
        recorded_by varchar(128) NOT NULL CHECK (length(btrim(recorded_by)) > 0),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        content_sha256 char(64) NOT NULL,
        CONSTRAINT civiccore_department_grant_events_pkey
            PRIMARY KEY (scope_id, subject, department_id, sequence),
        CONSTRAINT civiccore_department_grant_roles_shape
            CHECK ((action = 'grant' AND cardinality(roles) >= 1)
                OR (action = 'revoke' AND cardinality(roles) = 0))
    )"""
    )
    # The active-state read path is one DISTINCT ON per (scope, subject): this index serves it
    # without scanning every retained event of the whole ledger.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_civiccore_department_grant_active "
        "ON civiccore_department_grant_events (scope_id, subject, department_id, sequence DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_civiccore_department_grant_department "
        "ON civiccore_department_grant_events (scope_id, department_id)"
    )
    op.execute(
        """CREATE OR REPLACE FUNCTION civiccore_department_grant_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'civiccore department grants are append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$"""
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_civiccore_department_grant_append_only "
        "ON civiccore_department_grant_events"
    )
    op.execute(
        """CREATE TRIGGER trg_civiccore_department_grant_append_only
        BEFORE UPDATE OR DELETE ON civiccore_department_grant_events
        FOR EACH ROW EXECUTE FUNCTION civiccore_department_grant_append_only()"""
    )
    # Scope isolation is structural: every row carries its scope, and the composite primary key
    # makes a (scope, subject, department, sequence) identity unambiguous. A grant in one scope
    # is therefore never selected by a query for another scope.
    # department_id is deliberately not a foreign key to public.departments: the ledger is
    # deployment-scoped, Core does not own the city org chart, and a deleted department row must
    # not erase the authority history that allowed earlier access.


def downgrade() -> None:
    """Preserve the grant ledger; recover through backup/restore rather than deletion."""
    pass
