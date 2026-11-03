"""TownlightCore migration 0002 — Phase 2 LLM extraction: prompt_templates schema evolution.

Context — Phase 2 LLM extraction:
    TownlightCore v0.1.0 (baseline 0001) already contains both LLM-related tables:

    * ``model_registry`` — fully Phase-2-ready as extracted from TownlightRecords HEAD 019.
      No columns need to be added or altered; this migration leaves it untouched.

    * ``prompt_templates`` — present in the baseline but needs schema evolution to
      support per-consumer-app override resolution. This migration performs that
      evolution in-place (ALTER, not CREATE).

Why ALTER not CREATE:
    Both tables were captured verbatim from TownlightRecords HEAD 019 by the baseline
    migration (townlight_core_0001_baseline_v1). They therefore already exist in any
    database that has run 0001. This migration extends ``prompt_templates``; it does
    not recreate it. Running against a fresh database after 0001 is the normal path;
    running against a database already at a partially-evolved state is also safe
    (all five steps are individually idempotent).

The 5 evolution steps (all idempotent):
    1. Rename ``name`` → ``template_name`` (VARCHAR 200).
       The baseline carried a ``name`` column; the canonical LLM-extraction spec
       calls this ``template_name`` to distinguish it from other "name"-style
       columns in the database.

    2. Add ``consumer_app VARCHAR(100) NOT NULL DEFAULT 'townlight_core'``.
       Identifies which consuming application owns a template row. Defaults to
       'townlight_core' for the shared kernel. Records-AI side migration bacfills rows
       that belong to 'townlight_records' (Step 5 of the Phase 2 sprint).

    3. Add ``is_override BOOLEAN NOT NULL DEFAULT false``.
       Flag indicating whether a row is a consumer-app override of a townlight_core
       canonical template rather than a canonical template itself.

    4. Drop old unique constraint ``prompt_templates_name_key``.
       The baseline created a single-column UNIQUE on ``name``; once ``name`` is
       renamed to ``template_name`` and two new columns arrive, the correct
       uniqueness boundary changes. This constraint is replaced by step 5.

    5. Add composite unique constraint ``uq_prompt_templates_app_name_version``
       on (``consumer_app``, ``template_name``, ``version``).
       Ensures each (app, template name, version) triple is unique — the intended
       uniqueness invariant after Phase 2 extraction.

model_registry note:
    ``model_registry`` already has all Phase 2 columns from the baseline (see
    0001 module docstring for the full column list). No action is taken here.

Data migration note:
    Existing ``prompt_templates`` rows will default ``consumer_app`` to
    'townlight_core' and ``is_override`` to False. The TownlightRecords-side migration
    handles backfilling rows that logically belong to 'townlight_records'
    (Phase 2 sprint Step 5). No data migration is performed in this file.

Idempotency guarantees:
    Every step uses a guard helper from ``townlight_core.migrations.guards``:
    * idempotent_alter_column   — no-op if the old column name is absent
    * idempotent_add_column     — no-op if the column already exists
    * idempotent_drop_constraint — no-op if the constraint is absent
    * idempotent_create_unique_constraint — no-op if the constraint already exists

    This makes the migration safe to re-run after partial execution or against
    a database already at this schema state.

Downgrade:
    No-op by design — same reasoning as 0001. The renamed column and new
    columns are already referenced by downstream townlight_records migrations.
    Use point-in-time restore or drop/recreate the database instead.
"""

from __future__ import annotations

import sqlalchemy as sa

from townlight_core.migrations.guards import (
    idempotent_add_column,
    idempotent_alter_column,
    idempotent_create_unique_constraint,
    idempotent_drop_constraint,
)


# Alembic identifiers --------------------------------------------------------

revision = "townlight_core_0002"
down_revision = "townlight_core_0001"
branch_labels = None
depends_on = None


# Migration ------------------------------------------------------------------


def upgrade() -> None:
    """Evolve prompt_templates for Phase 2 LLM extraction.

    Applies 5 idempotent steps in order:
        1. Rename name -> template_name
        2. Add consumer_app column
        3. Add is_override column
        4. Drop old single-column unique constraint prompt_templates_name_key
        5. Add composite unique constraint uq_prompt_templates_app_name_version
    """
    # 1. Rename name -> template_name
    idempotent_alter_column(
        "prompt_templates",
        "name",
        new_column_name="template_name",
        existing_type=sa.String(200),
    )

    # 2. Add consumer_app VARCHAR(100) NOT NULL DEFAULT 'townlight_core'
    idempotent_add_column(
        "prompt_templates",
        sa.Column("consumer_app", sa.String(100), nullable=False, server_default="townlight_core"),
    )

    # 3. Add is_override BOOLEAN NOT NULL DEFAULT false
    idempotent_add_column(
        "prompt_templates",
        sa.Column("is_override", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 4. Drop old single-column unique constraint (replaced by composite below)
    idempotent_drop_constraint(
        "prompt_templates_name_key",
        "prompt_templates",
        type_="unique",
    )

    # 5. Add composite unique constraint on (consumer_app, template_name, version)
    idempotent_create_unique_constraint(
        "uq_prompt_templates_app_name_version",
        "prompt_templates",
        ["consumer_app", "template_name", "version"],
    )


def downgrade() -> None:
    """No-op.

    The renamed column (template_name) and new columns (consumer_app,
    is_override) are already referenced by downstream townlight_records
    migrations. Reversing this migration would break those dependencies.
    Use database-level restore instead.
    """
    # Intentional no-op. See module docstring.
    return None
