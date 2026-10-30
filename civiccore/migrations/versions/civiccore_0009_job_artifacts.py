# SPDX-License-Identifier: AGPL-3.0-only
"""Append-only, claim-bound artifact acceptance records for leased jobs.

Additive only: no existing queue table or consumer path is changed. One row per accepted
artifact, keyed by an opaque artifact id and bound to the producing job
(``task_id``, ``module_id``, ``task_type``, ``attempt_count``) and its ``claim_token``.
UPDATE and DELETE are refused by trigger, because an artifact acceptance is a receipt: the
history of which owner produced which bytes is not something a later writer may rewrite.
Downgrade is deliberately a no-op; recovery is restore-from-backup.
"""

from alembic import op

revision = "civiccore_0009_job_artifacts"
down_revision = "civiccore_0008_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS civiccore_job_artifacts (
        artifact_id varchar(64) PRIMARY KEY CHECK (length(artifact_id) = 32),
        task_id varchar(128) NOT NULL CHECK (length(btrim(task_id)) > 0),
        module_id varchar(64) NOT NULL CHECK (length(btrim(module_id)) > 0),
        task_type varchar(100) NOT NULL CHECK (length(btrim(task_type)) > 0),
        claim_token varchar(64) NOT NULL CHECK (length(btrim(claim_token)) > 0),
        attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
        artifact_name varchar(200) NOT NULL CHECK (length(btrim(artifact_name)) > 0),
        relative_path varchar(400) NOT NULL UNIQUE,
        artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
        artifact_bytes bigint NOT NULL CHECK (artifact_bytes >= 0),
        artifact_kind varchar(40) NOT NULL
            CHECK (artifact_kind IN ('text','chunks-json','media-metadata')),
        source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
        source_label varchar(200) NOT NULL CHECK (length(btrim(source_label)) > 0),
        recorded_by varchar(128) NOT NULL CHECK (length(btrim(recorded_by)) > 0),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT civiccore_job_artifacts_task_name_unique UNIQUE (task_id, artifact_name)
    )"""
    )
    # One claimed job cannot record the same relative path twice, and the queue's job
    # identity stays the fast lookup for a consumer assembling a job's receipts.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_civiccore_job_artifacts_task "
        "ON civiccore_job_artifacts (task_id, recorded_at)"
    )
    op.execute(
        """CREATE OR REPLACE FUNCTION civiccore_job_artifacts_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'civiccore job artifact receipts are append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$"""
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_civiccore_job_artifacts_append_only "
        "ON civiccore_job_artifacts"
    )
    op.execute(
        """CREATE TRIGGER trg_civiccore_job_artifacts_append_only
        BEFORE UPDATE OR DELETE ON civiccore_job_artifacts
        FOR EACH ROW EXECUTE FUNCTION civiccore_job_artifacts_append_only()"""
    )


def downgrade() -> None:
    """Preserve artifact acceptance receipts; recover through backup/restore."""

    return None
