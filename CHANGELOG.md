# Changelog

All notable changes to **civiccore** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

CivicCore is the shared platform package for the
[CivicSuite](https://github.com/CivicSuite/civicsuite) open-source
municipal operations suite. Per the CivicCore Extraction Spec section 16,
breaking changes to the public API surface (Appendix A of that spec) ship
as MAJOR releases; new symbols or backward-compatible behavior ship as
MINOR; bug fixes ship as PATCH.

## [1.2.1] - 2026-07-04

### Added
- Published the `civiccore_0003_local_task_queue` Alembic migration and the
  Windows-local platform contracts (PostgreSQL-backed local task queue/worker)
  as an installable release. This code was already on `main` and bundled by the
  CivicSuite Windows Local installer, but the v1.2.0 wheel predates it — so
  downstream modules whose tests expect migration head
  `civiccore_0003_local_task_queue` (e.g. civicclerk's alembic-upgrade test)
  could not pass against the published package. v1.2.1 closes that gap.

### Notes
- No breaking API changes; consumers on the v1.2.0 line upgrade in place.

## [1.2.0] - 2026-05-22

### Added
- Lifted the shared document-ingestion pipeline into `civiccore.ingest`,
  including file parser dispatch for PDF, DOCX, XLSX, CSV, EML, HTML, and text,
  sentence-aware chunking, local Ollama embedding helpers, and SQLAlchemy ORM
  models for the baseline `data_sources`, `documents`, and `document_chunks`
  pgvector schema.
- Added public `register_handler()`, `ingest_file()`, and `ingest_bytes()`
  entry points so downstream modules can ingest source documents through the
  CivicCore-owned pipeline instead of rebuilding module-local parser and vector
  storage paths.
- Added a Longmont Code of Ordinances PDF proof showing a 12.4 MB municipal
  code corpus parsed with `chunk_size=900` / `chunk_overlap=90` into 1,789
  persisted chunks with 1,789 768-dimensional Ollama embeddings; CivicCode PR
  #61 adds a committed dual-run proof script that reproduces this count and the
  CivicCode `500/50` count through the same CivicCore `ingest_file()` path.

## [1.1.0] - 2026-05-11

### Added
- Added `civiccore.auth.staff_key_gate(env_var, header)`, a shared FastAPI
  dependency factory for lightweight module staff routes.
- The helper preserves the existing `X-Civic*-Role: staff` plus
  `X-Civic*-Staff-Key` contract while centralizing staff-key comparison with
  `hmac.compare_digest`.
- Closes audit punch-list D2 and B3 for the shared CivicCore primitive.

## [1.0.1] - 2026-05-10

### Security Hardening
- Removed diagnostic role and caller details from CivicCore auth error
  payloads in `civiccore/auth/bearer.py` and
  `civiccore/auth/trusted_headers.py`.
- Removed these error-payload fields: `token_roles`, `principal`,
  `principal_roles`, `client_host`, and `trusted_proxy_cidrs`.
- Rationale source: `docs/audits/civiccore-audit-full-2026-05-07.md`.
- Operator note: if your monitoring or downstream tests assert these field
  names in CivicCore auth error responses, update them before bumping the pin.

### Changed
- Cut the CivicCore recovery patch from the post-`v1.0` recovery line, keeping
  the published platform label honest while preserving the audit-fix commit
  and provisional-status evidence.

### Changed
- Marked the published `v1.0` line as provisional during suite-wide release
  recovery instead of advertising it as production/stable.
- Updated the release verification script to prefer native Unix `python3`
  before Windows launchers so WSL evidence exercises Linux Python.

## [1.0.0] - 2026-05-05

### Added
- Added the CO-9 CivicCore v1.0 closeout report tying together release
  authorization, attested releases, retrofit decisions, placeholder ADRs,
  freeze-line tag, cleanroom evidence, procurement pack, and audit gate.
- Added the final `v1.0` SBOM to the CO-8 procurement evidence pack and
  extended regression coverage so the pack verifies both pre-release and final
  release package inventories.
- Added the CO-8 CivicCore procurement evidence pack with a signed threat
  model, generated SBOM inputs for `v0.22.1`, `civiccore-m1-freeze`, and the
  v1.0 release-candidate and final release trees, dependency license manifest,
  incident drills, patch cadence evidence, sovereignty proof, claims registry,
  and worked install-and-verify commands.
- Added the CO-7 placeholder ADRs and freeze-readiness evidence for the
  `civiccore.catalog`, `civiccore.exemptions`, and `civiccore.scaffold`
  deferrals.
- Added the CO-6 CivicCore cleanroom harness with a pinned Docker base image,
  no-cache build orchestrator, live `v0.22.1` Sigstore/SHA256 verification
  paths, offline runtime proof, signed evidence manifests, and CI artifact
  upload.
- Added `docs/ops/co-4-cross-module-retrofit-report.md` as the CivicCore
  closeout index for the merged CivicRecords AI, CivicClerk, and CivicCode
  Tier 1 retrofit ledgers.
- Published `docs/ops/civiccore-tier1-retrofit-ledger.md` and its structured
  JSON source so every live CivicCore release tag is explicitly marked either
  as the `v0.22.1` attested baseline or as pre-gate/no-attestation historical
  release material.
- Added `scripts/check-tier1-ledger.py` and regression coverage for the CO-3
  ledger so future release-surface edits cannot silently leave CivicCore tags
  unledgered.

### Changed
- Promoted package metadata, smoke tests, README, text README, user manual, and
  docs landing page to the `1.0.0` package / `v1.0` release surface.
- Release workflow notes now point auditors to the procurement evidence pack,
  historical-provenance policy, closeout report, SHA256SUMS path, Sigstore
  verification command, and `scripts/verify-release-provenance.py` command.
- Promoted `docs/ops/historical-provenance.md` from draft disclosure to
  operative policy with the dated `v0.22.1` baseline, live attestation URL,
  retrofit evidence, release verification result, and no-historical-asset-edit
  boundary.
- README, text README, user manual, and docs landing page now distinguish
  `v1.0` as the current downstream productization release from `v0.22.1` as
  the first attested baseline.

## [0.22.1] - 2026-05-05

### Added
- `civiccore.release_provenance` now provides the canonical CivicSuite
  release-provenance gate for the Sigstore attestation trust model, including
  GitHub-backed tag-ref/target-commit checks, exact per-repo/per-tag workflow
  identity validation, artifact hash validation, and adversarial fixture
  execution.
- `docs/ops/release-attestation.schema.json` locks
  `release-attestation.json` schema version 1 before the first attested
  release-class operation.
- Release-signing runbook now documents the GitHub tag-signing ceiling, the
  Sigstore/cosign attestation model, failure modes for trust-root rotation,
  transparency-log availability, workflow identity drift, offline verification,
  and the bootstrap trust problem.
- Draft historical provenance disclosure records the boundary between
  GitHub-native historical releases and future Sigstore-attested releases.
- Release workflow now installs cosign, generates and signs
  `release-attestation.json`, verifies the attestation before publication, and
  uploads the attestation plus bundle alongside wheel, sdist, and checksums.

### Fixed
- Release workflow now writes GitHub Release notes from a generated Markdown
  file so the workflow remains valid YAML before the first attested baseline
  tag is published.
- Test coverage now parses every GitHub workflow file to catch release-workflow
  YAML regressions before tag-push release operations.
- Release publication now passes explicit downloaded artifact paths to
  `gh release create` so the nested artifact directory is not uploaded as a
  release asset.

## [0.22.0] - 2026-05-03

### Added
- `civiccore.connectors.SyncSourceStatus` and `build_sync_source_status()` now
  provide a storage-neutral source-list projection for downstream connector
  workspaces. The helper combines CivicCore circuit health, active failure
  counts, pause state, last status, actionable operator copy, and next scheduled
  run calculation without importing any module ORM models.
- Package-root exports and the release-gate clean-venv smoke now include the new
  source-status projection so CivicRecords AI, CivicClerk, and future modules can
  consume one shared health/next-run contract instead of hand-computing it per
  router.

## [0.21.0] - 2026-05-02

### Added
- `civiccore.scheduling` now ships shared cron schedule validation helpers:
  `min_interval_minutes()`, `validate_cron_expression()`, and
  `compute_next_sync_at()`.
- Package-root exports expose the scheduling helpers so downstream modules can
  block too-frequent background schedules consistently without copying the
  CivicRecords AI cron utility.
- Release docs now identify scheduling as a shipped helper namespace while
  keeping scheduler runtimes and task queues module-owned.

## [0.20.0] - 2026-05-02

### Added
- `civiccore.security` now ships shared startup config validation helpers for
  placeholder detection, CSV env parsing, generic secret length/default checks,
  Fernet key validation, and common-password rejection so modules do not carry
  one-off bootstrap hardening rules.

## [0.19.0] - 2026-05-02

### Added
- `civiccore.connectors.plan_vendor_delta_request()` now ships the shared
  connector-specific delta cursor planning contract for Legistar, Granicus,
  PrimeGov, and NovusAGENDA live-sync consumers.
- `civiccore.testing.mock_city` now ships reusable no-network Brookfield
  mock-city contracts for supported agenda vendors, municipal OIDC staff auth,
  and backup-retention/off-host readiness so future modules can prove those
  seams without contacting vendors, identity providers, or storage services.

## [0.18.1] - 2026-05-02

### Fixed
- `civiccore.connectors.compute_retry_delay()` now preserves the proven
  CivicRecords AI `Retry-After` behavior: honor valid header values exactly,
  cap oversized values at 600 seconds by default, and do not add jitter to
  server-directed `Retry-After` sleeps.

## [0.18.0] - 2026-05-02

### Added
- `civiccore.connectors.SyncCircuitState`, `SyncRunResult`, and
  `apply_sync_run_result()` now ship the storage-neutral CivicRecords AI
  live-sync circuit-breaker pattern for downstream modules.
- `civiccore.connectors.SyncCircuitPolicy` and
  `build_sync_operator_status()` now provide configurable thresholds and
  actionable operator copy for healthy, degraded, and circuit-open sync states.
- `civiccore.connectors.SyncRetryPolicy`, `compute_retry_delay()`,
  `with_http_retry()`, and `SyncRetryExhausted` now ship a shared async HTTP
  retry helper for `429`, `5xx`, timeout, and connection-error paths.
- Package-root exports now expose the sync primitives so CivicRecords AI,
  CivicClerk, and future modules can consume one shared implementation.

## [0.17.0] - 2026-05-01

### Added
- `civiccore.audit.PersistedAuditLogEntry` now ships a storage-neutral view of
  legacy database-backed audit rows so modules can verify retained audit logs
  without owning duplicate hash-chain math.
- `civiccore.audit.compute_persisted_audit_hash()` now preserves the
  CivicRecords AI legacy `previous_hash|timestamp|actor_id|action|details`
  SHA-256 formula for existing deployed audit rows.
- `civiccore.audit.verify_persisted_audit_chain()` now verifies persisted
  audit rows with archived-log support, including actionable mismatch messages
  that identify the failing row and position.
- Package-root exports now expose the persisted audit-log helpers so
  CivicRecords AI and CivicClerk can consume one shared implementation.

## [0.16.0] - 2026-04-29

### Added
- `civiccore.auth.TrustedHeaderAuthConfig` now ships a shared trusted-header
  configuration contract so downstream modules can load provider labels,
  principal/roles header names, and proxy CIDR allowlists without bespoke env
  parsing.
- `civiccore.auth.load_trusted_header_auth_config()` now ships shared
  environment-backed trusted-header config loading for reverse-proxy SSO
  bridges.
- `civiccore.auth.enforce_trusted_proxy_source()` now ships shared actionable
  source-boundary enforcement for trusted-header deployments so downstream
  modules can require approved proxy CIDRs without carrying service-local copy.

### Changed
- Trusted-header auth tests now cover shared config loading plus missing,
  invalid, rejected, and accepted proxy-source paths.

## [0.14.1] - 2026-04-29

### Fixed
- `civiccore.auth.authorize_trusted_header_roles()` now uses the caller-provided
  `service_name` and `feature_name` when building actionable fix text so
  downstream modules do not leak `CivicClerk`-specific guidance in shared
  auth failures.

### Changed
- Trusted-header auth tests now assert service-aware error-copy paths for
  missing principal headers, missing role headers, and underprivileged
  identities.

## [0.15.0] - 2026-04-29

### Added
- `civiccore.security.normalize_trusted_proxy_cidrs()` now ships a shared
  CIDR parser for reverse-proxy trust boundaries so downstream modules can
  validate trusted-header deployments without carrying bespoke network parsing.
- `civiccore.security.is_trusted_proxy_ip()` now ships a shared source-IP
  matcher for reverse-proxy CIDR allowlists, making trusted-header auth
  contracts enforceable instead of purely documentary.

### Changed
- README, package metadata, and release surfaces now describe `civiccore.security`
  as the shared home for both connector host validation and trusted-proxy
  boundary checks.

## [0.14.0] - 2026-04-29

### Added
- `civiccore.auth.authorize_trusted_header_roles()` now ships a shared
  reverse-proxy SSO bridge contract for downstream FastAPI services that
  receive asserted principal and role headers from a trusted municipal IdP
  front door instead of handling first-party login directly.
- `civiccore.auth.resolve_optional_trusted_header_roles()` now lets mixed
  public/staff routes stay anonymous until a trusted proxy actually injects
  identity headers.
- `civiccore.auth.parse_header_role_list()` now ships a shared comma-delimited
  role-header parser with actionable error handling for misconfigured proxy
  role assertions.

### Changed
- `AuthenticatedPrincipal` now records the auth method plus optional subject
  and provider metadata so downstream modules can describe bearer-token and
  trusted-header sessions through one stable contract.
- README, package metadata, and release surfaces now describe
  `civiccore.auth` as a shipped small-auth helper namespace for bearer-token
  and trusted-header reverse-proxy bridges.

## [0.13.0] - 2026-04-29

### Added
- `civiccore.ingest.DiscoveredRecord`, `FetchedDocument`,
  `HealthStatus`, and `HealthCheckResult` now ship the first shared
  connector discovery/fetch contract so consumers can reuse one ingest-facing
  record surface instead of carrying private copies of the same dataclasses.
- `civiccore.ingest.SourceMaterial`, `CitedSentence`,
  `CitationValidationError`, and `validate_cited_sentences()` now ship a
  storage-neutral cited-source validation contract for generated drafts and
  other document-derived workflows that must prove every sentence cites known
  source material.
- Package-root exports now include the shared ingest contracts so downstream
  modules can adopt them from the stable `civiccore` public API.

### Changed
- README, package metadata, and release surfaces now describe
  `civiccore.ingest` as a shipped helper namespace for contracts, not a
  placeholder-only package.

## [0.12.0] - 2026-04-29

### Added
- `civiccore.security.validate_url_host()` now ships a shared connector-host
  validation helper that blocks loopback, RFC1918, link-local, and localhost
  targets by default while supporting narrow exact-host allowlists for
  intentional on-prem endpoints.
- `civiccore.security.extract_odbc_host()` and
  `validate_odbc_connection_string()` now ship a fail-closed shared contract
  for ODBC host parsing and blocked-range enforcement.
- `civiccore.security.encrypt_json()`, `decrypt_json()`, and
  `is_encrypted()` now ship a shared encrypted JSON envelope contract for
  secret-bearing connector/config payloads that need at-rest protection.
- Package-root exports now include the shared security primitives so
  downstream modules can consume them from the stable `civiccore` public API.

### Changed
- README, package metadata, and release surfaces now describe
  `civiccore.security` as a shipped helper namespace.

## [0.11.0] - 2026-04-29

### Added
- `civiccore.onboarding.parse_profile_answer()` now ships a shared
  storage-neutral answer-normalization helper for interview-style
  onboarding flows so downstream modules can reuse one yes/no parsing
  and text-trimming contract.
- `civiccore.onboarding.compute_onboarding_status()` now ships the
  shared `not_started` / `in_progress` / `complete` lifecycle contract
  for tracked city-profile onboarding state.
- `civiccore.onboarding.completed_profile_fields()` and
  `next_profile_prompt()` now ship a skip-aware field-walk contract for
  modules that need deterministic onboarding interview progression
  without taking a dependency on one product's router implementation.
- `civiccore.onboarding.OnboardingField`,
  `OnboardingProgress`, and `DEFAULT_PROFILE_FIELDS` now ship the
  default CivicSuite bootstrap-profile question order for storage-neutral
  onboarding helpers.
- `civiccore.notifications.build_deadline_plan()` now ships a shared
  deterministic notice-deadline planning contract so downstream modules
  can reuse one publish-by/reminder surface instead of reimplementing
  lead-time math per module.
- `civiccore.notifications.evaluate_notice_compliance()` now ships a
  shared publication-readiness helper with actionable warning codes for
  missing statutory basis, missed deadlines, and missing human approval.
- `civiccore.notifications.NoticeComplianceResult` and
  `NoticeComplianceWarning` now ship a reusable notice warning/result
  contract for mixed public/staff workflows that need operator-facing
  fix paths.
- `civiccore.connectors.import_meeting_payload()` now ships a shared
  local-first normalization helper for supported agenda-platform export
  payloads so downstream modules can reuse one deterministic import
  contract instead of reimplementing payload mapping and provenance
  logic per module.
- `civiccore.connectors.ImportedMeeting` and `ImportedAgendaItem` now
  ship a shared normalized payload surface with source provenance
  metadata for local connector imports.
- `civiccore.connectors.ConnectorImportError` now ships actionable
  `message`/`fix` validation errors for malformed or unsupported local
  connector payloads.
- `civiccore.search.normalize_search_text()` and
  `normalize_search_query()` now ship a deterministic shared
  normalization surface for current CivicSuite consumers that need
  case-insensitive, whitespace-stable text matching without pulling in a
  database or embedding runtime.
- `civiccore.search.search_text_matches_query()` now ships a tiny shared
  substring-matching helper so mixed public/staff consumer routes can
  reuse one query-normalization contract instead of reimplementing it
  per module.
- `civiccore.search.reciprocal_rank_fusion()` now ships a generic hybrid
  ranking helper for consumers that need to merge semantic and lexical
  search results without extracting a full search engine.
- `civiccore.search.normalize_access_value()`,
  `normalize_access_values()`, `roles_grant_access()`,
  `access_level_allows()`, and `filter_records_by_access_level()` now
  ship shared permission-aware search/access helpers so downstream
  modules can reuse one normalized role/tier visibility contract
  instead of reimplementing closed-session or privileged-access checks.
- `civiccore.verification.validate_release_browser_evidence()` validates
  content-bound browser QA release manifests so downstream modules can
  prove that desktop/mobile screenshots still match the current rendered
  page source across Windows and Linux checkouts.
- `civiccore.verification.normalized_text_sha256()` hashes UTF-8 text
  with normalized newlines so cross-platform browser QA evidence does
  not fail purely because of line-ending differences.

### Changed
- README and onboarding placeholder docs now describe
  `civiccore.onboarding` as shipping shared onboarding-profile helpers
  while keeping full web onboarding flows in the planned bucket.
- README and connector placeholder docs now describe
  `civiccore.connectors` as shipping both offline manifest schemas and
  local-first import helpers for supported agenda-platform payloads.
- README and placeholder docs now describe `civiccore.notifications` as
  a partially shipped helper namespace instead of a future-only
  delivery placeholder.
- README and placeholder docs now describe `civiccore.search` as a
  partially shipped helper namespace instead of a future-only placeholder
  package.
- README and verification placeholder docs now describe
  `civiccore.verification` as a partially shipped helper namespace
  instead of a reserved future-only package.
- Package metadata and release verification now target the upcoming
  `0.11.0` minor line so the shared search-access helper additions do
  not retroactively change the published `0.10.0`
  contract.

## [0.6.0] - 2026-04-29

### Added
- `civiccore.verification.validate_release_browser_evidence()` validates
  content-bound browser QA release manifests so downstream modules can
  prove that desktop/mobile screenshots still match the current rendered
  page source across Windows and Linux checkouts.
- `civiccore.verification.normalized_text_sha256()` hashes UTF-8 text
  with normalized newlines so cross-platform browser QA evidence does
  not fail purely because of line-ending differences.

### Changed
- README and verification placeholder docs now describe
  `civiccore.verification` as a partially shipped helper namespace
  instead of a reserved future-only package.
- Package metadata and release verification now target the upcoming
  `0.6.0` minor line so the first shipped verification helper does not
  retroactively change the published `0.5.0` contract.

## [0.5.0] - 2026-04-29

### Added
- `civiccore.auth` now ships a minimal bearer-token role helper for
  downstream FastAPI services that need actionable `401`/`403`/`503`
  protection on non-public internal routes without introducing a full
  identity-provider stack.
- `civiccore.auth.resolve_optional_bearer_roles()` now supports mixed
  public/staff endpoints that should keep anonymous access available
  while upgrading privileged results to the shared bearer-token role
  contract when callers present Authorization headers.

### Changed
- README and auth placeholder docs now describe `civiccore.auth` as a
  shipped helper namespace instead of a reserved future-only package.
- Package metadata and release verification now target the upcoming
  `0.5.0` minor line so the optional mixed-route auth helper does not
  retroactively change the published `0.4.0` contract.

## [0.3.0] - 2026-04-28

This release adds the shared offline primitives needed for CivicSuite's first
production-depth municipal workflows. It is backward-compatible with v0.2.0
and does not introduce auth/RBAC, live connector sync, document ingestion,
search indexing, notification delivery, or vendor write-back.

### Added
- `civiccore.audit`: storage-neutral hash-chained audit primitives
  (`AuditActor`, `AuditSubject`, `AuditEvent`, `AuditHashChain`) for downstream
  modules that need tamper-evident local audit trails.
- `civiccore.provenance`: source/provenance metadata contracts
  (`SourceKind`, `SourceReference`, `CitationTarget`, `DocumentMetadata`,
  `ProvenanceBundle`) for citations, source manifests, and export metadata.
- `civiccore.connectors`: offline import/export manifest schemas
  (`ImportManifest`, `ExportManifest`, `ManifestFile`, `validate_manifest`)
  with path, size, and SHA-256 validation.
- `civiccore.exports`: static export-bundle helpers (`ExportBundle`,
  `BundleFile`, `write_manifest`, `build_sha256sums`, `validate_bundle`) for
  reproducible offline bundles.
- `civiccore.city_profile`: local city/deployment configuration models
  (`CityProfile`, `DepartmentProfile`, `DeploymentProfile`,
  `ModuleEnablement`, `load_city_profile`) with JSON support and optional YAML
  loading when PyYAML is installed.
- Package-root exports for the v0.3.0 primitives, plus public API smoke tests
  proving shipped symbols are exposed and planned symbols are not accidentally
  promoted.

## [0.2.0] - 2026-04-25

This release ships the `civiccore.llm` module — provider abstraction
(Ollama / OpenAI / Anthropic), prompt template engine with a 3-step
override resolver, model registry service + admin router, context
utilities with prompt-injection defense, structured-output helper, and the
full public `civiccore.llm` import surface.

### Added
- `civiccore_0002_llm` migration: evolves `prompt_templates` for Phase 2 override-resolution columns (`template_name` rename, `consumer_app`, `is_override`); adds `idempotent_drop_constraint` guard helper
- `civiccore.llm.registry`: `ModelRegistry` ORM + Pydantic schemas (`ModelRegistryCreate`, `ModelRegistryRead`, `ModelRegistryUpdate`)
- `civiccore.llm.templates`: `PromptTemplate` ORM + Pydantic schemas (`PromptTemplateCreate`, `PromptTemplateRead`, `PromptTemplateUpdate`)
- `civiccore.db.Base`: shared SQLAlchemy declarative base for civiccore ORM models
- `civiccore.llm.providers`: pluggable provider abstraction.
  - `LLMProvider` ABC with `generate`, `embed`, `embed_batch`, `name`, `supports_images` (per ADR-0004 §6).
  - Decorator-based registry: `@register_provider`, `get_provider`, `list_providers`.
  - Built-in providers: `OllamaProvider` (uses httpx, default model `gemma4:e4b`), `OpenAIProvider` (optional extra `civiccore[openai]`), `AnthropicProvider` (optional extra `civiccore[anthropic]`; embeddings raise `NotImplementedError` since Anthropic has no native embed endpoint).
  - Optional cloud SDKs: install `openai` or `anthropic` directly (e.g. `pip install openai`); the `civiccore[openai]` and `civiccore[anthropic]` extras shorthand becomes available once civiccore is published to PyPI.
- `civiccore.llm.templates`: rendering and override resolution (Step 3c).
  - `render_template(template, variables)` returns a `RenderedPrompt` dataclass with `system` / `user` / `template_name` / `consumer_app` / `version`.
  - `resolve_template(session, *, template_name, consumer_app)` async helper implements the 3-step resolution per ADR-0004 §7: app DB override (consumer_app + is_override=true + is_active + highest version) → app code-level override (`OVERRIDE_REGISTRY`) → civiccore default (consumer_app='civiccore' + is_override=false + is_active + highest version) → `PromptTemplateNotFoundError`.
  - New exceptions: `PromptTemplateError` (base), `PromptTemplateNotFoundError`, `PromptTemplateRenderError` (names the missing variable).
  - Uses stdlib `string.Template` per ADR-0004 (no Jinja2; `$name` syntax avoids JSON-brace collisions).
- `civiccore.llm` (Step 3d): finalized public API surface for downstream consumption.
  - Context utilities ported from records-ai: `TokenBudget`, `ContextBlock`, `estimate_tokens`, `count_tokens`, `sanitize_for_llm` (3-pattern prompt-injection defense), `assemble_context`, `blocks_to_prompt`, `DEFAULT_CONTEXT_WINDOW=8192`.
  - `civiccore.llm.structured`: `StructuredOutput[ModelT]` Pydantic-validated LLM-call helper with retry-on-malformed (default 3 attempts); `StructuredOutputFailure` exception. Provider-agnostic.
  - `civiccore.llm.registry.service`: async `get_active_model`, `require_active_model` (raises `MissingModelError`), `get_active_model_context_window` (defaults to 8192). Library-friendly: takes `AsyncSession` parameter, no hardcoded session_maker.
  - `civiccore.llm.registry.router`: FastAPI APIRouter for ModelRegistry admin CRUD (list / get / post / patch / delete). Mountable; consumers override `get_session` dependency.
  - Single import surface: `from civiccore.llm import ...` exposes the full public API for records-ai Step 5 consumption.
- Per ADR-0004 §3: NO cost tracking, NO spend logging, NO `llm_call_log` table introduced. Token budgeting is context-window math only.
- **Audit fix (RESOLVER-001):** template resolver upgraded from 2-step to 3-step per ADR-0004 §7. Added `civiccore.llm.templates.overrides` module with `OVERRIDE_REGISTRY`, `register_template_override`, and `unregister_template_override`. Resolution order is now: app DB override → app code-level override → civiccore DB default → `PromptTemplateNotFoundError`. DB overrides win over code overrides (operators retain production hot-fix capability).
- **Audit fix (PROVIDER-CONFIG-001):** added Pydantic config schemas (`OllamaConfig`, `OpenAIConfig`, `AnthropicConfig`) and `civiccore.llm.factory.build_provider(name, config)` per ADR-0004 §6. Validates config type matches the registered provider before construction. Direct provider constructor calls remain supported for backwards compatibility.

## [0.1.0] - 2026-04-24

### Added
- Initial package skeleton with empty subpackages for the 14 subsystems
  specified in CivicCore Extraction Spec Appendix B: `auth`, `audit`,
  `llm`, `ingest`, `search`, `connectors`, `notifications`, `onboarding`,
  `catalog`, `exemptions`, `verification`, `models`, `migrations`, and
  `scaffold`.
- `pyproject.toml` with shared dependency pins matching
  civicrecords-ai/backend/pyproject.toml (FastAPI, SQLAlchemy, Alembic,
  fastapi-users, pgvector, redis, celery, pydantic, uvicorn, ollama-stack
  ingest libs, etc.). Python `>=3.11` to support modules that have not yet
  moved to 3.12.
- Smoke test asserting `import civiccore` succeeds and the package exports
  the release version.
- Apache 2.0 `LICENSE`, `README.md`, `CONTRIBUTING.md`, `.gitignore`, and
  placeholder `civiccore-ui/` npm package directory.
- `civiccore.migrations.guards` — idempotent wrappers for table, column,
  index, foreign-key, unique-constraint, and check-constraint creation,
  plus `has_table`.
- `civiccore.migrations.runner` — `upgrade_to_head()` and
  `current_revision(connection)` entry points for consuming modules'
  Alembic env.py wiring.
- `civiccore/migrations/alembic.ini` + `civiccore/migrations/env.py` —
  civiccore's own Alembic wiring (`alembic_version_civiccore` version table
  to avoid collision with consuming modules).
- `civiccore_0001_baseline_v1` migration — idempotent snapshot of the 16
  civiccore-owned shared tables at CivicRecords AI HEAD
  `019_encrypt_connection_config`, per ADR-0003.
- `tests/test_baseline_idempotency.py` — pytest asserting the baseline runs
  clean on an empty DB and is a no-op against an already-populated DB.
- `.github/workflows/ci.yml` — CI workflow on `pull_request`/`push` to
  `main` running smoke + baseline idempotency tests.
- `.github/workflows/release.yml` — tag-driven build that publishes a
  versioned wheel and source distribution to GitHub Releases so downstream
  apps can depend on a release artifact instead of a Git SHA pin.

### Changed
- License switched from MIT to Apache License 2.0 to match
  civicrecords-ai.
- `docs/index.html` landing page added to satisfy the project's pre-push
  documentation gate.
- README, CONTRIBUTING, pyproject.toml, and CHANGELOG: stale
  `scottconverse/civiccore` and `scottconverse/civicsuite` URLs corrected
  to `CivicSuite/civiccore` and `CivicSuite/civicsuite`.
- Hardened the tag-driven release workflow so it runs
  `scripts/verify-release.sh` before publishing GitHub release artifacts.
- Release artifacts now include `SHA256SUMS.txt` so downstream modules can
  verify the wheel and source distribution they consume.
- `scripts/verify-release.sh` now creates a clean virtualenv, installs the
  freshly built wheel, asserts the exact package version, and smoke-imports the
  migration runner before a release can pass.
- `tests/test_smoke.py` now asserts the exact `0.1.0` release version instead
  of accepting any `0.1.x` prefix.
