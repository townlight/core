"""TownlightCore baseline v1 — shared schema extracted from TownlightRecords HEAD 019.

This baseline captures the 16 shared tables that constitute the TownlightCore
kernel. It is the single source of truth for kernel schema going forward;
downstream applications (e.g., TownlightRecords) should rebase onto this baseline
and stop re-declaring shared tables in their own migrations.

Provenance:
    Dumped from TownlightRecords alembic HEAD ``019_encrypt_connection_config``
    via ``pg_dump --schema-only --no-owner --no-privileges --no-comments``
    against ``townlight_records_test`` on PostgreSQL 17.9.

Dependencies captured (SHARED -> SHARED only):
    users.department_id          -> departments.id
    city_profile.updated_by      -> users.id
    data_sources.created_by      -> users.id
    exemption_rules.created_by   -> users.id
    notification_templates.created_by -> users.id
    prompt_templates.created_by  -> users.id
    prompt_templates.model_id    -> model_registry.id
    service_accounts.created_by  -> users.id
    documents.source_id          -> data_sources.id
    document_chunks.document_id  -> documents.id
    sync_failures.dismissed_by   -> users.id
    sync_failures.source_id      -> data_sources.id
    sync_run_log.source_id       -> data_sources.id

No shared->records-only FKs were present in the source dump; none were
dropped during extraction.

Idempotency:
    Each table DDL chunk executes only when ``has_table(t)`` returns False.
    This lets the baseline co-exist with a database that already carries
    the shared tables from a prior records-side migration.

Downgrade:
    No-op by design. A baseline migration defines the floor of supported
    schema; reversing it would drop tables that both townlight_core and
    downstream apps depend on. Use point-in-time restore or drop the
    database instead.
"""

from __future__ import annotations

from alembic import op

from townlight_core.migrations.guards import has_table


# Alembic identifiers --------------------------------------------------------

revision = "townlight_core_0001"
down_revision = None
branch_labels = None
depends_on = None


# Ordered list of shared tables (parents before children per FK analysis) ----

_SHARED_TABLE_ORDER: list[str] = [
    "audit_log",
    "model_registry",
    "connector_templates",
    "departments",
    "system_catalog",
    "users",
    "city_profile",
    "data_sources",
    "exemption_rules",
    "notification_templates",
    "prompt_templates",
    "service_accounts",
    "documents",
    "sync_failures",
    "sync_run_log",
    "document_chunks",
]


# Per-table DDL chunks extracted from pg_dump ------------------------------
#
# Each entry bundles, for a single table:
#   - CREATE SEQUENCE (if the table owns one, e.g. serial PKs)
#   - CREATE TABLE
#   - ALTER SEQUENCE ... OWNED BY
#   - ALTER TABLE ... ALTER COLUMN ... SET DEFAULT nextval(...)
#   - ALTER TABLE ... ADD CONSTRAINT (PRIMARY KEY / UNIQUE)
#   - CREATE INDEX
#   - ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY (only shared->shared)
#
# Executed verbatim via ``op.execute`` so the DDL matches TownlightRecords HEAD 019
# byte-for-byte where practical.

_TABLE_DDL: dict[str, str] = {
    "audit_log": """
CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.audit_log (
    id integer NOT NULL,
    prev_hash character varying(64) DEFAULT '0000000000000000000000000000000000000000000000000000000000000000'::character varying NOT NULL,
    entry_hash character varying(64) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    user_id uuid,
    action character varying(100) NOT NULL,
    resource_type character varying(100) NOT NULL,
    resource_id character varying(255),
    details jsonb,
    ai_generated boolean DEFAULT false NOT NULL
);
ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;
ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);
ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);
CREATE INDEX ix_audit_log_action ON public.audit_log USING btree (action);
CREATE INDEX ix_audit_log_entry_hash ON public.audit_log USING btree (entry_hash);
CREATE INDEX ix_audit_log_resource_type ON public.audit_log USING btree (resource_type);
CREATE INDEX ix_audit_log_timestamp ON public.audit_log USING btree ("timestamp");
CREATE INDEX ix_audit_log_user_id ON public.audit_log USING btree (user_id);
CREATE INDEX ix_audit_log_user_timestamp ON public.audit_log USING btree (user_id, "timestamp");
""",

    "model_registry": """
CREATE SEQUENCE public.model_registry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.model_registry (
    id integer NOT NULL,
    model_name character varying(255) NOT NULL,
    model_version character varying(100),
    parameter_count character varying(50),
    license character varying(100),
    model_card_url text,
    is_active boolean DEFAULT false NOT NULL,
    added_at timestamp with time zone DEFAULT now(),
    context_window_size integer,
    supports_ner boolean DEFAULT false NOT NULL,
    supports_vision boolean DEFAULT false NOT NULL
);
ALTER SEQUENCE public.model_registry_id_seq OWNED BY public.model_registry.id;
ALTER TABLE ONLY public.model_registry ALTER COLUMN id SET DEFAULT nextval('public.model_registry_id_seq'::regclass);
ALTER TABLE ONLY public.model_registry
    ADD CONSTRAINT model_registry_pkey PRIMARY KEY (id);
""",

    "connector_templates": """
CREATE SEQUENCE public.connector_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.connector_templates (
    id integer NOT NULL,
    vendor_name character varying(200) NOT NULL,
    protocol character varying(50) NOT NULL,
    auth_method character varying(50) NOT NULL,
    config_schema jsonb NOT NULL,
    default_sync_schedule character varying(50),
    default_rate_limit integer,
    redaction_tier integer NOT NULL,
    setup_instructions text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    catalog_version character varying(20) NOT NULL
);
ALTER SEQUENCE public.connector_templates_id_seq OWNED BY public.connector_templates.id;
ALTER TABLE ONLY public.connector_templates ALTER COLUMN id SET DEFAULT nextval('public.connector_templates_id_seq'::regclass);
ALTER TABLE ONLY public.connector_templates
    ADD CONSTRAINT connector_templates_pkey PRIMARY KEY (id);
""",

    "departments": """
CREATE TABLE public.departments (
    id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(20) NOT NULL,
    contact_email character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_code_key UNIQUE (code);
ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);
""",

    "system_catalog": """
CREATE SEQUENCE public.system_catalog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE TABLE public.system_catalog (
    id integer NOT NULL,
    domain character varying(100) NOT NULL,
    function character varying(200) NOT NULL,
    vendor_name character varying(200) NOT NULL,
    vendor_version character varying(50),
    access_protocol character varying(50) NOT NULL,
    data_shape character varying(50) NOT NULL,
    common_record_types jsonb NOT NULL,
    redaction_tier integer NOT NULL,
    discovery_hints jsonb NOT NULL,
    connector_template_id integer,
    catalog_version character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER SEQUENCE public.system_catalog_id_seq OWNED BY public.system_catalog.id;
ALTER TABLE ONLY public.system_catalog ALTER COLUMN id SET DEFAULT nextval('public.system_catalog_id_seq'::regclass);
ALTER TABLE ONLY public.system_catalog
    ADD CONSTRAINT system_catalog_pkey PRIMARY KEY (id);
""",

    "users": """
CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    hashed_password character varying(1024) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_superuser boolean DEFAULT false NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    full_name character varying DEFAULT ''::character varying NOT NULL,
    role public.user_role DEFAULT 'staff'::public.user_role NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_login timestamp with time zone,
    department_id uuid
);
ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);
CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);
ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_department FOREIGN KEY (department_id) REFERENCES public.departments(id);
""",

    "city_profile": """
CREATE TABLE public.city_profile (
    id uuid NOT NULL,
    city_name character varying(200) NOT NULL,
    state character varying(2),
    county character varying(200),
    population_band character varying(50),
    email_platform character varying(50),
    has_dedicated_it boolean,
    monthly_request_volume character varying(20),
    onboarding_status character varying(20) NOT NULL,
    profile_data jsonb NOT NULL,
    gap_map jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by uuid
);
ALTER TABLE ONLY public.city_profile
    ADD CONSTRAINT city_profile_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.city_profile
    ADD CONSTRAINT city_profile_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;
""",

    "data_sources": """
CREATE TABLE public.data_sources (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    source_type public.source_type NOT NULL,
    connection_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_ingestion_at timestamp with time zone,
    discovered_source_id uuid,
    connector_template_id integer,
    sync_schedule character varying(50),
    last_sync_at timestamp with time zone,
    last_sync_status character varying(20),
    health_status character varying(20),
    schema_hash character varying(64),
    last_sync_cursor character varying,
    schedule_enabled boolean DEFAULT true NOT NULL,
    consecutive_failure_count integer DEFAULT 0 NOT NULL,
    last_error_message character varying(500),
    last_error_at timestamp with time zone,
    sync_paused boolean DEFAULT false NOT NULL,
    sync_paused_at timestamp with time zone,
    sync_paused_reason character varying(200),
    retry_batch_size integer,
    retry_time_limit_seconds integer,
    CONSTRAINT chk_sync_schedule_nonempty CHECK (((sync_schedule IS NULL) OR (length(TRIM(BOTH FROM sync_schedule)) > 0)))
);
ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_name_key UNIQUE (name);
ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);
""",

    "exemption_rules": """
CREATE TABLE public.exemption_rules (
    id uuid NOT NULL,
    state_code character varying(2) NOT NULL,
    category character varying(100) NOT NULL,
    rule_type public.rule_type NOT NULL,
    rule_definition text NOT NULL,
    description text,
    enabled boolean DEFAULT true NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    version integer DEFAULT 1 NOT NULL
);
ALTER TABLE ONLY public.exemption_rules
    ADD CONSTRAINT exemption_rules_pkey PRIMARY KEY (id);
CREATE INDEX ix_exemption_rules_category ON public.exemption_rules USING btree (category);
CREATE INDEX ix_exemption_rules_state ON public.exemption_rules USING btree (state_code);
ALTER TABLE ONLY public.exemption_rules
    ADD CONSTRAINT exemption_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);
""",

    "notification_templates": """
CREATE TABLE public.notification_templates (
    id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    channel character varying(20) NOT NULL,
    subject_template character varying(500) NOT NULL,
    body_template text NOT NULL,
    is_active boolean NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT notification_templates_event_type_key UNIQUE (event_type);
ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT notification_templates_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT notification_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;
""",

    "prompt_templates": """
CREATE TABLE public.prompt_templates (
    id uuid NOT NULL,
    name character varying(200) NOT NULL,
    purpose character varying(50) NOT NULL,
    system_prompt text NOT NULL,
    user_prompt_template text NOT NULL,
    token_budget jsonb NOT NULL,
    model_id integer,
    version integer NOT NULL,
    is_active boolean NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_name_key UNIQUE (name);
ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model_registry(id) ON DELETE SET NULL;
""",

    "service_accounts": """
CREATE TABLE public.service_accounts (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    api_key_hash character varying(255) NOT NULL,
    role public.user_role DEFAULT 'read_only'::public.user_role NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT true NOT NULL
);
ALTER TABLE ONLY public.service_accounts
    ADD CONSTRAINT service_accounts_name_key UNIQUE (name);
ALTER TABLE ONLY public.service_accounts
    ADD CONSTRAINT service_accounts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.service_accounts
    ADD CONSTRAINT service_accounts_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);
""",

    "documents": """
CREATE TABLE public.documents (
    id uuid NOT NULL,
    source_id uuid NOT NULL,
    source_path text NOT NULL,
    filename character varying(500) NOT NULL,
    file_type character varying(50) NOT NULL,
    file_hash character varying(64) NOT NULL,
    file_size integer DEFAULT 0 NOT NULL,
    ingestion_status public.ingestion_status DEFAULT 'pending'::public.ingestion_status NOT NULL,
    ingestion_error text,
    chunk_count integer DEFAULT 0 NOT NULL,
    ingested_at timestamp with time zone,
    metadata jsonb,
    display_name character varying(500),
    department_id uuid,
    redaction_status character varying(20) DEFAULT 'none'::character varying NOT NULL,
    derivative_path character varying(1000),
    original_locked boolean DEFAULT false NOT NULL,
    connector_type character varying(20),
    updated_at timestamp with time zone,
    CONSTRAINT chk_source_path_length CHECK (((source_path IS NULL) OR (length(source_path) <= 2048)))
);
ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
CREATE INDEX ix_documents_file_hash ON public.documents USING btree (file_hash);
CREATE INDEX ix_documents_source_hash ON public.documents USING btree (source_id, file_hash);
CREATE INDEX ix_documents_source_id ON public.documents USING btree (source_id);
CREATE UNIQUE INDEX uq_documents_binary_hash ON public.documents USING btree (source_id, file_hash) WHERE ((connector_type)::text <> ALL ((ARRAY['rest_api'::character varying, 'odbc'::character varying])::text[]));
CREATE UNIQUE INDEX uq_documents_structured_path ON public.documents USING btree (source_id, source_path) WHERE ((connector_type)::text = ANY ((ARRAY['rest_api'::character varying, 'odbc'::character varying])::text[]));
ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_sources(id);
""",

    "sync_failures": """
CREATE TABLE public.sync_failures (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id uuid NOT NULL,
    source_path text NOT NULL,
    error_message text,
    error_class character varying(200),
    http_status_code integer,
    retry_count integer DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'retrying'::character varying NOT NULL,
    first_failed_at timestamp with time zone DEFAULT now() NOT NULL,
    last_retried_at timestamp with time zone,
    resolved_at timestamp with time zone,
    dismissed_at timestamp with time zone,
    dismissed_by uuid
);
ALTER TABLE ONLY public.sync_failures
    ADD CONSTRAINT sync_failures_pkey PRIMARY KEY (id);
CREATE INDEX ix_sync_failures_created ON public.sync_failures USING btree (first_failed_at);
CREATE INDEX ix_sync_failures_source_status ON public.sync_failures USING btree (source_id, status);
ALTER TABLE ONLY public.sync_failures
    ADD CONSTRAINT sync_failures_dismissed_by_fkey FOREIGN KEY (dismissed_by) REFERENCES public.users(id);
ALTER TABLE ONLY public.sync_failures
    ADD CONSTRAINT sync_failures_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_sources(id) ON DELETE CASCADE;
""",

    "sync_run_log": """
CREATE TABLE public.sync_run_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    status character varying(20),
    records_attempted integer DEFAULT 0,
    records_succeeded integer DEFAULT 0,
    records_failed integer DEFAULT 0,
    error_summary text
);
ALTER TABLE ONLY public.sync_run_log
    ADD CONSTRAINT sync_run_log_pkey PRIMARY KEY (id);
CREATE INDEX ix_sync_run_log_source ON public.sync_run_log USING btree (source_id, started_at);
ALTER TABLE ONLY public.sync_run_log
    ADD CONSTRAINT sync_run_log_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_sources(id) ON DELETE CASCADE;
""",

    "document_chunks": """
CREATE TABLE public.document_chunks (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    content_text text NOT NULL,
    embedding public.vector(768),
    token_count integer DEFAULT 0 NOT NULL,
    page_number integer,
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content_text)) STORED
);
ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);
CREATE INDEX ix_chunks_doc_index ON public.document_chunks USING btree (document_id, chunk_index);
CREATE INDEX ix_chunks_embedding_hnsw ON public.document_chunks USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');
CREATE INDEX ix_chunks_tsvector ON public.document_chunks USING gin (content_tsvector);
CREATE INDEX ix_document_chunks_document_id ON public.document_chunks USING btree (document_id);
ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
""",

}


# Extensions and enum types captured from pg_dump ---------------------------

_REQUIRED_EXTENSIONS: list[str] = [
    "vector",  # pgvector; required by document_chunks.embedding
]

# Enum types referenced by shared-table columns. Records-only enums
# (flag_status, inclusion_status, request_status) stay records-side.
_SHARED_ENUM_DDL: dict[str, str] = {
    "user_role": (
        "CREATE TYPE public.user_role AS ENUM "
        "('admin', 'staff', 'reviewer', 'read_only', 'liaison', 'public')"
    ),
    "source_type": (
        "CREATE TYPE public.source_type AS ENUM "
        "('manual_drop', 'file_system', 'rest_api', 'odbc')"
    ),
    "ingestion_status": (
        "CREATE TYPE public.ingestion_status AS ENUM "
        "('pending', 'processing', 'completed', 'failed')"
    ),
    "rule_type": (
        "CREATE TYPE public.rule_type AS ENUM "
        "('regex', 'keyword', 'llm_prompt')"
    ),
}


def _type_exists(conn, name: str) -> bool:
    """Return True if a PostgreSQL type with this name exists in any schema."""
    from sqlalchemy import text

    return (
        conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = :n LIMIT 1"),
            {"n": name},
        ).scalar()
        is not None
    )


def _split_statements(ddl: str) -> list[str]:
    """Split a multi-statement SQL chunk on `;` boundaries.

    Required because asyncpg refuses multi-statement prepared statements
    ("cannot insert multiple commands into a prepared statement"). We pass
    statements to op.execute one at a time so any underlying driver works.

    Assumes no semicolons inside string literals — safe for the pg_dump-emitted
    DDL captured here (no DEFAULT 'foo;bar' or similar). Validated against
    the baseline's contents: no embedded semicolons in any literal.
    """
    return [stmt.strip() for stmt in ddl.split(";") if stmt.strip()]


def upgrade() -> None:
    """Idempotently bring the database up to the townlight_core baseline.

    Runs in three phases:
        1. Ensure required extensions exist (``vector`` for pgvector).
        2. Ensure the 4 shared enum types exist (``user_role``,
           ``source_type``, ``ingestion_status``, ``rule_type``).
        3. Create the 16 shared tables in dependency order, skipping any
           that already exist.

    Safe to run against:
        * A fresh database (all extensions, enums, tables are created).
        * A records-side database already at HEAD 019 (everything skipped).
        * Any partial intermediate state (each element independently guarded).
    """
    conn = op.get_bind()

    # 1. Extensions — CREATE EXTENSION supports IF NOT EXISTS natively
    for ext in _REQUIRED_EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}"')

    # 2. Enums — PostgreSQL has no CREATE TYPE IF NOT EXISTS; check pg_type
    for enum_name, ddl in _SHARED_ENUM_DDL.items():
        if not _type_exists(conn, enum_name):
            op.execute(ddl)

    # 3. Tables — ordered, guarded, statements emitted one at a time
    #    (asyncpg cannot handle multi-statement chunks).
    for table in _SHARED_TABLE_ORDER:
        if has_table(table):
            continue
        for statement in _split_statements(_TABLE_DDL[table]):
            op.execute(statement)


def downgrade() -> None:
    """No-op.

    A baseline cannot be meaningfully downgraded: the 16 shared tables are
    the kernel contract and are likely referenced by downstream migrations
    that are not visible from here. Use database-level restore instead.
    """
    # Intentional no-op. See module docstring.
    return None
