# SPDX-License-Identifier: AGPL-3.0-only
"""Attributable immutable municipal catalog imports; existing rows stay intact."""

from alembic import op

revision = "civiccore_0004_catalog"
down_revision = "civiccore_0003_local_task_queue"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS civiccore_catalog_imports (
        version varchar(20) PRIMARY KEY,
        source_sha256 varchar(64) NOT NULL,
        entry_count integer NOT NULL CHECK (entry_count >= 0),
        actor_id varchar(128) NOT NULL,
        imported_at timestamptz NOT NULL DEFAULT now()
    )""")


def downgrade():
    """Preserve catalog history; recover through backup/restore rather than deletion."""
    pass
