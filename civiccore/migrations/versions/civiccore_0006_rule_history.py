# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable, cited jurisdiction-rule version history.

Additive only: the consumer-owned ``exemption_rules`` working table is untouched, so
existing consumers keep their current rows and code path. History rows are keyed by
``(rule_id, version)`` and protected by triggers that refuse UPDATE/DELETE and refuse
rebinding a rule id to a second jurisdiction. Deleting cited history would destroy the
provenance a prior scan relied on, so rollback is restore-from-backup, not DROP.
"""

from alembic import op

revision = "civiccore_0006_rule_history"
down_revision = "civiccore_0005_job_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS civiccore_rule_versions (
        rule_id uuid NOT NULL,
        state_code varchar(2) NOT NULL,
        version integer NOT NULL CHECK (version >= 1),
        category varchar(100) NOT NULL CHECK (length(btrim(category)) > 0),
        rule_type varchar(20) NOT NULL CHECK (rule_type IN ('regex','keyword')),
        rule_definition text NOT NULL CHECK (length(rule_definition) > 0),
        citation_text varchar(1000) NOT NULL CHECK (length(btrim(citation_text)) > 0),
        citation_url varchar(2000),
        effective_from date,
        retrieved_at timestamptz NOT NULL,
        coverage_declaration varchar(32) NOT NULL
            CHECK (coverage_declaration IN ('synthetic-fixture','tenant-supplied')),
        content_sha256 char(64) NOT NULL,
        recorded_by varchar(128) NOT NULL CHECK (length(btrim(recorded_by)) > 0),
        recorded_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT civiccore_rule_versions_pkey PRIMARY KEY (rule_id, version),
        CONSTRAINT civiccore_rule_versions_jurisdiction_key UNIQUE (rule_id, state_code, version),
        CONSTRAINT civiccore_rule_versions_state_code_ck
            CHECK (state_code = upper(state_code) AND length(state_code) = 2)
    )"""
    )
    # Deterministic current-version and per-jurisdiction listing.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_civiccore_rule_versions_state_category "
        "ON civiccore_rule_versions (state_code, category, version DESC)"
    )
    op.execute(
        """CREATE OR REPLACE FUNCTION civiccore_rule_versions_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'civiccore rule version history is append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$"""
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_civiccore_rule_versions_append_only ON civiccore_rule_versions"
    )
    op.execute(
        """CREATE TRIGGER trg_civiccore_rule_versions_append_only
        BEFORE UPDATE OR DELETE ON civiccore_rule_versions
        FOR EACH ROW EXECUTE FUNCTION civiccore_rule_versions_append_only()"""
    )
    # A rule id belongs to exactly one jurisdiction; a later insert cannot migrate it.
    op.execute(
        """CREATE OR REPLACE FUNCTION civiccore_rule_versions_single_jurisdiction()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM civiccore_rule_versions
                WHERE rule_id = NEW.rule_id AND state_code <> NEW.state_code
            ) THEN
                RAISE EXCEPTION 'rule % already belongs to another jurisdiction', NEW.rule_id
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END;
        $$"""
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_civiccore_rule_versions_jurisdiction "
        "ON civiccore_rule_versions"
    )
    op.execute(
        """CREATE TRIGGER trg_civiccore_rule_versions_jurisdiction
        BEFORE INSERT ON civiccore_rule_versions
        FOR EACH ROW EXECUTE FUNCTION civiccore_rule_versions_single_jurisdiction()"""
    )


def downgrade() -> None:
    """Preserve cited history; recover through backup/restore rather than deletion."""
    pass
