"""TownlightCore migration 0003 - local task queue."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from townlight_core.migrations.guards import idempotent_create_index, idempotent_create_table


revision = "townlight_core_0003"
down_revision = "townlight_core_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "townlight_core_local_tasks",
        sa.Column("task_id", sa.String(128), primary_key=True),
        sa.Column("module_id", sa.String(64), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("audit_subject_id", sa.String(255), nullable=True),
    )
    idempotent_create_index("ix_townlight_core_local_tasks_module", "townlight_core_local_tasks", ["module_id"])
    idempotent_create_index("ix_townlight_core_local_tasks_status", "townlight_core_local_tasks", ["status"])
    idempotent_create_index("ix_townlight_core_local_tasks_type", "townlight_core_local_tasks", ["task_type"])


def downgrade() -> None:
    """No-op; local task queue data is preserved for point-in-time restore."""
    return None
