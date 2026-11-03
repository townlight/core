# SPDX-License-Identifier: AGPL-3.0-only
"""Fenced worker leases on the existing shared queue; no second job store."""

from alembic import op

revision = "townlight_core_0005"
down_revision = "townlight_core_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE townlight_core_local_tasks ADD COLUMN IF NOT EXISTS claim_token varchar(64)")
    op.execute(
        "ALTER TABLE townlight_core_local_tasks ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz"
    )
    op.execute(
        "ALTER TABLE townlight_core_local_tasks ADD COLUMN IF NOT EXISTS cancelled_by varchar(128)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_townlight_core_local_tasks_lease ON townlight_core_local_tasks (status,lease_expires_at)"
    )


def downgrade():
    pass  # Preserve jobs and cancellation history; restore a coherent backup.
