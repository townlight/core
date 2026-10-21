Townlight Core
=========

Shared platform library for the Townlight open-source municipal operations
suite. https://github.com/townlight/townlight

What this is
------------

Townlight Core is the Python library every Townlight module depends on for shared
platform plumbing. It is not an end-user municipal app.

What ships in the current development line:

  - civiccore.migrations - migration runner with idempotent guards plus the
    civiccore_0001_baseline_v1 shared-schema baseline and civiccore_0002_llm.
  - civiccore.db - shared SQLAlchemy declarative Base.
  - civiccore.llm - providers, prompt templates, model registry, context
    utilities, and structured output.
  - civiccore.audit - hash-chained audit primitives plus persisted audit-log
    hash and verification helpers.
  - civiccore.provenance - source/provenance metadata contracts.
  - civiccore.connectors - offline import/export manifest schemas,
    local-first import helpers for supported agenda-platform payloads,
    vendor delta request planning, storage-neutral live-sync
    retry/circuit-breaker primitives, and source-list status projections.
  - civiccore.testing - no-network mock-city proof contracts for supported
    agenda vendors, municipal OIDC, and backup-retention/off-host readiness.
  - civiccore.security - connector host validation, startup config
    validation, and encrypted JSON envelope helpers for secret-bearing config.
  - civiccore.exports - static export-bundle manifest and checksum helpers.
  - civiccore.city_profile - local city/deployment configuration models.
  - civiccore.auth - bearer-token role helpers for protected or mixed
    public/staff FastAPI routes.
  - civiccore.verification - content-bound browser release-evidence helpers.
  - civiccore.search - deterministic text normalization, matching, and
    reciprocal-rank-fusion helpers.
  - civiccore.notifications - notice deadline planning and publication
    compliance helpers with actionable warning codes.
  - civiccore.scheduling - cron validation and next-run helpers for module
    background jobs.
  - civiccore.ingest - shared discovery/fetch contracts, cited-source
    validation helpers, and the document-ingestion pipeline for PDF, DOCX,
    XLSX, CSV, EML, HTML, and text files with sentence-aware chunking, local
    Ollama embeddings, and pgvector-backed documents/document_chunks storage.

Still planned extraction targets:

  civiccore.catalog, civiccore.exemptions, civiccore.scaffold.
  civiccore.onboarding now ships storage-neutral profile interview
  helpers, but not a web onboarding UI or persistence router.

Credential storage, vendor-specific network adapters, vendor write-back,
worker scheduler runtimes, notification delivery queues, and legal
determinations are still not shipped platform behaviors.

Status
------

v1.2.1 is the current Townlight Core downstream productization line. It carries the
shared document-ingestion pipeline used by the city-core release train, the
CO-7 freeze-line trust anchor, the CO-8 procurement evidence pack, and the
CO-9 closeout trail.
v0.22.1 remains the first attested baseline release. The
current line includes shared connector source-list status projection helpers, cron schedule validation helpers, startup config validation helpers, vendor delta planning,
reusable mock-city proof contracts, live connector sync retry/circuit-breaker
primitives, and persisted audit-log hash and verification helpers on top of
shared connector security/config helpers, onboarding profile helpers, auth helpers,
verification helpers, shared search helpers, local-first connector import
helpers, and notice deadline/compliance helpers on top of the audit,
provenance, manifest, export-bundle, city-profile, migration, and LLM
primitives. v0.2.0 shipped the
civiccore.llm module. v0.1.0 shipped the migration baseline.

Install
-------

From the current published GitHub release wheel:

    pip install https://github.com/CivicSuite/civiccore/releases/download/v1.2.1/civiccore-1.2.1-py3-none-any.whl

Townlight Core is distributed as versioned GitHub release artifacts (not on PyPI).
Each release publishes SHA256SUMS.txt alongside the wheel and sdist. Verify
checksums before promoting an artifact downstream. v1.2.1 is the current
published downstream productization line and includes the shared
document-ingestion pipeline used by the city-core release train. v0.22.0 and
earlier releases are retained for historical installs only.

For development from a clone:

    git clone https://github.com/CivicSuite/civiccore.git
    cd civiccore
    pip install -e .[dev]

Public API surface (high level)
-------------------------------

  civiccore.llm
    LLMProvider, register_provider, get_provider, list_providers
    OllamaProvider, OpenAIProvider, AnthropicProvider, build_provider
    PromptTemplate, RenderedPrompt, render_template, resolve_template
    ModelRegistry, model_registry_router, get_active_model
    TokenBudget, ContextBlock, assemble_context, blocks_to_prompt
    sanitize_for_llm, StructuredOutput, StructuredOutputFailure

  civiccore.audit
    AuditActor, AuditSubject, AuditEvent, AuditHashChain,
    PersistedAuditLogEntry, compute_persisted_audit_hash,
    verify_persisted_audit_chain

  civiccore.provenance
    SourceKind, SourceReference, CitationTarget, DocumentMetadata,
    ProvenanceBundle

  civiccore.connectors / civiccore.exports
    ConnectorImportError, ImportedAgendaItem, ImportedMeeting,
    SUPPORTED_CONNECTORS, import_meeting_payload,
    SyncCircuitPolicy, SyncCircuitState, SyncRunResult, SyncSourceStatus,
    apply_sync_run_result, build_sync_operator_status, build_sync_source_status,
    SyncRetryPolicy, with_http_retry,
    ImportManifest, ExportManifest, ManifestFile, validate_manifest,
    ExportBundle, BundleFile, write_manifest, build_sha256sums,
    validate_bundle

  civiccore.city_profile
    CityProfile, DepartmentProfile, DeploymentProfile, ModuleEnablement,
    load_city_profile

  civiccore.onboarding
    OnboardingField, OnboardingProgress, DEFAULT_PROFILE_FIELDS,
    parse_profile_answer, compute_onboarding_status,
    completed_profile_fields, next_profile_prompt

  civiccore.migrations / civiccore.db
    Migration runner, civiccore_0001_baseline_v1 shared schema, and Base

  civiccore.scheduling
    validate_cron_expression, min_interval_minutes, compute_next_sync_at

Compatibility
-------------

Current v0.1.0 module foundations still pin older civiccore lines.
Production-depth consumers should move only to the released Townlight Core version
recorded in their compatibility matrix.

The suite-wide compatibility matrix is maintained at:
https://github.com/townlight/townlight/tree/main/docs/compatibility

License
-------

Code: AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. See LICENSE and LICENSE-EXCEPTION.md.

Contributing
------------

See CONTRIBUTING.md, including the decision tree for where to file a bug
across the Townlight multi-repo layout.

Source
------

https://github.com/townlight/core
