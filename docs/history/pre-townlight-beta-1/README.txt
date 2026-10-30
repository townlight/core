# Townlight Core

**The shared foundation beneath municipal work.**

Core supplies Python contracts and shared services used by the other seven products. Staff normally encounter it through Setup, Settings and System Health rather than a separate Core workspace.

## Use this product

- [Current user manual](USER-MANUAL.md): installed workflow, roles, sources, review, export, recovery and limits.
- [Product landing page](https://townlight.github.io/products/core/).
- [Overall eight-product manual](https://github.com/townlight/townlight/blob/main/USER-MANUAL.md) and [feature/integration assessment](https://github.com/townlight/townlight/blob/main/docs/assessment/feature-and-integration-review.md).
- [Signed composition and acceptance](https://github.com/townlight/townlight/releases/tag/townlight-records-meetings-code-zoning-planning-permitting-inspections-v1.7.0-beta.1): Core 1.2.1, bundled in accepted desktop compositions.

All seven products consume Core. The module owns its business permissions and workflow; Core does not automatically connect every pair of products.

## Release scope

The shared catalog and shared exemption engine are private beta candidates recorded by ADR-0004 and ADR-0005. `civiccore.scaffold` now ships a working module generator in the same private candidate (ADR-0007), which resumes the ADR-0003 placeholder deferral for that generator only; ADR-0003 stays the historical record and the downstream-dependency rule is unchanged, so no module may depend on the namespace until a versioned artifact and a compatibility-matrix entry name it. Search helpers are not a complete centrally hosted search service. Full user administration, business exemptions and public portals remain consumer responsibilities.

Documentation reviewed 2026-10-26. Installed acceptance, source/API implementation and future requirements are different evidence. Code is AGPL-3.0-only with the repository’s public institution exception where applicable; documentation is CC BY 4.0. See the repository license files.

## Historical repository reference

The earlier README below is retained for package history and contributor commands. Older maturity/version statements describe that historical reference and are superseded by the current operating guide and linked release evidence.

<a id="civiccore"></a>

# Townlight Core

Shared platform package for the
[Townlight](https://github.com/townlight/townlight) open-source
municipal operations suite.

## What this is

Townlight Core is the Python package every Townlight module depends on for
shared platform plumbing. **What ships today:** the migration runner plus
`civiccore_0001_baseline_v1` shared-schema baseline, a shared SQLAlchemy
declarative `Base`, the `civiccore.llm` module, hash-chained audit
primitives, source/provenance metadata contracts, offline import/export
manifest schemas, static export-bundle helpers, local city profile
configuration, small auth helpers for downstream FastAPI services,
including mixed public/staff routes that should stay anonymous by
default while unlocking privileged results for authorized callers,
browser-evidence verification helpers for current-facing release pages,
small shared search helpers for deterministic text matching, generic
permission-aware access checks, hybrid ranking fusion, and local-first connector import helpers for
agenda-platform payload normalization with actionable error contracts and
source provenance, storage-neutral live connector sync retry/circuit-breaker
primitives with actionable operator health copy and shared source-list status
projection, connector delta request
planning, reusable mock-city proof contracts for vendor, municipal IdP, and
backup-retention readiness, shared ingest contracts for connector discovery/fetch
records and cited-source validation, shared document ingestion for PDF, DOCX,
XLSX, CSV, EML, HTML, and text files with sentence-aware chunking, local Ollama
embeddings, and pgvector-backed `documents` / `document_chunks` storage, plus
shared notice deadline planning and publication compliance helpers with
actionable warning codes, plus shared
cron schedule validation helpers for module background jobs.

**Still planned extraction targets (placeholder packages exist; not yet
implemented today):** `civiccore.exemptions`
(50-state public-records exemption engine). `civiccore.scaffold` is no longer a
placeholder: the private 1.3.0.dev1 candidate ships the generator described in
`docs/scaffold.md` and ADR-0007, with an acceptance run against a disposable synthetic
PostgreSQL cluster. `civiccore.ingest` now ships reusable
discovery/fetch contracts, cited-source validation helpers, and the shared
document ingestion pipeline. It does not ship a worker scheduler/runtime.
`civiccore.onboarding` now ships storage-neutral
profile interview helpers, but not a web onboarding UI or persistence
router. `civiccore.search` now ships normalization and
fusion helpers, but not a full search engine or indexer.
`civiccore.notifications` now ships notice deadline and compliance
helpers, but not delivery queues or outbound notification orchestration.
`civiccore.platform` now ships the Windows-local desktop contracts for module
manifests, install-profile validation, operator health summaries, durable local
task envelopes, backup/restore manifests, and installer/runtime action results.
It also ships the PostgreSQL-backed `civiccore_local_tasks` migration, async
queue helpers, and `python -m civiccore.tasks.worker` entry point for the local
desktop worker. Product modules still own task handlers and UI, while Townlight Core
owns shared validation, queue state, retry semantics, and plain-English
operator state.
`civiccore.verification` now ships the first release-evidence helper
surface, while sovereignty verification remains future work.
`civiccore.connectors` now also ships shared local-payload import
normalization helpers, live-sync retry/circuit-breaker primitives, and source-list
status projection helpers for supported agenda platforms, while
`civiccore.security` now ships shared connector-host validation,
startup config validation, and encrypted JSON envelope helpers for secret-bearing config.
`civiccore.scheduling` now ships storage-neutral cron validation and next-run
helpers, but not a scheduler runtime or task queue. Credential
orchestration, vendor-specific network adapters, and vendor write-back remain unshipped.
`civiccore.release_provenance` now uses the attestation trust model for release
verification: Git tags are treated as release pointers, while
`release-attestation.json` plus its Sigstore/cosign bundle are the verifiable
trust artifacts. The exact workflow identity is pinned per repo and per tag;
org-wide wildcard identities are not accepted.
The CO-7 placeholder ADRs in [`docs/adr/index.md`](docs/adr/index.md) record
the deferral rationale, target phase, and downstream consumption rule for the
reserved placeholder namespaces. Unshipped namespaces are reserved for future
Phase work and must not be relied on by downstream modules until they ship.

## Status

**v1.2.1 is the current Townlight Core downstream productization line.** It carries
the shared document-ingestion pipeline used by the city-core release train,
the CO-7 freeze-line trust anchor, the CO-8 procurement evidence pack, and the
CO-9 closeout trail for modules that need a procurement-grade platform pin.
`v0.22.1` remains the first attested baseline release. This line carries the
canonical Sigstore release-provenance helper, versioned attestation schema,
fixture-driven gate, and tag-driven release workflow that signs and verifies
`release-attestation.json` before publication, plus the shared
connector source-list status projection that combines circuit health, active
failure counts, pause state, actionable operator copy, and next-run calculation
for module workspaces on top of shared cron schedule validation helpers for
module background jobs on top of shared
startup config validation helpers for placeholder detection, CSV env parsing,
generic secret checks, Fernet key validation, and common-password rejection,
on top of shared vendor delta request planning plus reusable no-network
mock-city proof contracts for agenda vendors, municipal OIDC, and backup
retention/off-host storage, on top of shared live connector sync retry/circuit-breaker primitives,
including run-result normalization, operator health copy, retry delay policy, and async HTTP retry,
on top of shared Windows-local module/runtime contracts for the desktop shell,
including no-Docker/no-WSL manifest validation, plain-English health summaries,
PostgreSQL-backed local task queue helpers, and backup/restore checksum
manifests, on top of shared persisted audit-log hash and verification helpers for
database-backed module audit rows on top of shared trusted-header auth config
loading and proxy-source enforcement helpers on top of shipped
trusted-header auth helpers on top of shipped
`civiccore.ingest` discovery/fetch, cited-source validation, and document-ingestion pipeline on top of shipped
`civiccore.security` connector host-validation, startup config validation, and encrypted-config helpers on top of shipped
`civiccore.onboarding` profile interview helpers on top of shipped
`civiccore.notifications` notice deadline planning and publication
compliance helpers on top of the shipped `civiccore.connectors`
local-first import helpers, the shipped `civiccore.search` helper
surface for deterministic text matching, permission-aware access checks,
and reciprocal-rank-fusion, the
shipped `civiccore.verification` release-evidence helpers, the shipped
`civiccore.auth` optional bearer resolver for mixed public/staff
endpoints, and the shared audit, provenance, manifest, export-bundle,
and city profile primitives needed for the first production-depth
Townlight workflows.
`v0.2.0` shipped the `civiccore.llm` module:
provider abstraction (Ollama / OpenAI / Anthropic), prompt template engine
with a 3-step override resolver, model registry service + admin router,
context utilities with prompt-injection defense, and a Pydantic-validated
structured-output helper. `v0.1.0` was the Phase 1 baseline (migration
runner, idempotent guards, and the `civiccore_0001_baseline_v1`
shared-schema baseline extracted from Townlight Records).

## Architecture

### Shipped vs placeholder

![civiccore extraction map](docs/diagrams/civiccore-extraction-map.svg)

### Migration order (consumer chain)

![Migration order](docs/diagrams/migration-order.svg)

### LLM provider abstraction

![Provider abstraction](docs/diagrams/provider-abstraction.svg)

## Install

From the current GitHub release wheel (`v1.2.1`):

```bash
pip install https://github.com/CivicSuite/civiccore/releases/download/v1.2.1/civiccore-1.2.1-py3-none-any.whl
```

Each GitHub release also publishes `SHA256SUMS.txt` alongside the wheel and
sdist. Verify the checksum before promoting a release artifact into a downstream
module or internal package mirror.

### Release Provenance

Townlight Core now carries the canonical Townlight release-provenance gate in
`civiccore.release_provenance`. The gate exists because GitHub release pages can
show the target commit as "Verified" even when the release tag is lightweight or
the annotated tag object is unsigned. Treat the release-page badge as a commit
signal only; use `scripts/verify-release-provenance.py` and
`docs/ops/release-signing.md` for release-tag provenance.

`v1.2.1` is the current published downstream productization line. It adds the
shared document-ingestion pipeline used by the city-core release train. The
original `v1.0` release remains historical and superseded. `v0.22.1` remains
the first attested baseline release, and `civiccore-m1-freeze` remains the
CO-7 freeze-line tag downstream modules use as their initial trust anchor.
`v0.22.0` and earlier Townlight Core releases predate the Sigstore attestation
baseline and are retained for historical installs only. Their Tier 1 status is published in
[`docs/ops/civiccore-tier1-retrofit-ledger.md`](docs/ops/civiccore-tier1-retrofit-ledger.md).
The operative historical disclosure is published in
[`docs/ops/historical-provenance.md`](docs/ops/historical-provenance.md).
Outside auditors can reproduce the release gate and public install-and-verify
paths with the CO-6 cleanroom harness in
[`docs/ops/cleanroom-harness.md`](docs/ops/cleanroom-harness.md).
The CO-8 procurement evidence pack in
[`docs/evidence/co8-civiccore-procurement-evidence-pack/index.md`](docs/evidence/co8-civiccore-procurement-evidence-pack/index.md)
links the threat model, SBOMs, license manifest, incident drills,
sovereignty proof, patch cadence, claims registry, and worked install-and-verify
commands that an outside auditor needs to evaluate the v1.0 release gate. The
current recovery status is tracked in
[`docs/release-recovery-status.md`](docs/release-recovery-status.md).
The CO-9 closeout report in
[`docs/ops/co-9-civiccore-v1-closeout.md`](docs/ops/co-9-civiccore-v1-closeout.md)
maps the release authorization, attested releases, freeze-line tag, retrofit
decisions, placeholder ADRs, cleanroom evidence, and final audit gate.
Do not promote any pre-baseline release as the corrected provenance baseline
unless a future additive attestation is explicitly authorized, published, and
recorded in that ledger.

For development from a clone:

```bash
git clone https://github.com/CivicSuite/civiccore.git
cd civiccore
pip install -e .[dev]
```

PyPI publication can come later; Townlight Core is distributed as versioned
GitHub release artifacts so Townlight Records can stop depending on a Git SHA pin.
The tag-driven release workflow runs `scripts/verify-release.sh` before
publishing so the shipped artifact has already passed pytest, ruff,
docs/version checks, a local build, and a clean-virtualenv wheel-install smoke
test.

## LLM providers

Townlight Core exposes a pluggable LLM provider abstraction for downstream apps. Three providers ship built-in:

```python
from civiccore.llm.providers import (
    LLMProvider,         # ABC
    register_provider,   # decorator for adding new providers
    get_provider,        # construct a provider by name
    list_providers,      # introspection
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
)

# Built-in usage
provider = get_provider("ollama", base_url="http://localhost:11434")
text = await provider.generate(system_prompt="...", user_content="...")
```

Optional cloud-provider SDKs are needed only if you instantiate the corresponding provider:

```bash
# Direct install (works today, including GitHub wheel installs):
pip install openai      # required for OpenAIProvider
pip install anthropic   # required for AnthropicProvider

# Extras shorthand (works once civiccore is published to PyPI):
pip install civiccore[openai]
pip install civiccore[anthropic]
```

Ollama needs no extra (uses httpx, already a base dependency).

Third-party providers register via the public decorator without modifying civiccore source:

```python
from civiccore.llm.providers import LLMProvider, register_provider

@register_provider("my_provider")
class MyProvider(LLMProvider):
    ...
```

## LLM templates

Townlight Core exposes a prompt-template rendering and override-resolution layer for downstream apps.

```python
from civiccore.llm.templates import (
    PromptTemplate,             # ORM
    PromptTemplateCreate,       # Pydantic schemas
    PromptTemplateRead,
    RenderedPrompt,             # render() result dataclass
    render_template,            # string.Template renderer
    resolve_template,           # async DB resolver (3-step: app DB → code-level → civiccore default)
    CIVICCORE_DEFAULT_APP,      # "civiccore" namespace constant
    PromptTemplateError,        # exceptions
    PromptTemplateNotFoundError,
    PromptTemplateRenderError,
)
```

### Resolution order

`resolve_template(session, template_name=..., consumer_app=...)` returns the active `PromptTemplate` row using:

1. **App DB override** — `consumer_app=<requesting app>`, `is_override=True`, `is_active=True`, highest `version`.
2. **App code-level override** — in-memory `OVERRIDE_REGISTRY` populated via `register_template_override` (per ADR-0004 §7). DB overrides win over code overrides so operators retain production hot-fix capability.
3. **Townlight Core default** — `consumer_app="civiccore"`, `is_override=False`, `is_active=True`, highest `version`.
4. Otherwise raises `PromptTemplateNotFoundError`.

Callers passing `consumer_app="civiccore"` skip both override steps (1 and 2) and resolve directly to the civiccore default.

### Rendering

`render_template(template, {"key": "value", ...})` substitutes `string.Template` placeholders (`$key` or `${key}`). Missing variables raise `PromptTemplateRenderError` naming the missing key.

## LLM context utilities and structured output

Townlight Core exposes context-budgeting and structured-output helpers at the package root:

```python
from civiccore.llm import (
    TokenBudget, ContextBlock,
    estimate_tokens, count_tokens, sanitize_for_llm,
    assemble_context, blocks_to_prompt, DEFAULT_CONTEXT_WINDOW,
    StructuredOutput, StructuredOutputFailure,
)

# Token-budgeted prompt assembly with prompt-injection defense
blocks = assemble_context(
    system_prompt="You are a helpful assistant.",
    chunks=[document_text],
    max_context_tokens=4096,
)
prompt = blocks_to_prompt(blocks)

# Pydantic-validated structured output with retry-on-malformed
class ExtractedFields(BaseModel):
    name: str
    confidence: float

result = await StructuredOutput(ExtractedFields).generate(
    provider=get_provider("ollama"),
    system_prompt="Extract fields from the document.",
    user_content=document_text,
    max_attempts=3,
)
```

Per ADR-0004: token counting is context-window math; no cost tracking, no spend limits.

## Audit, provenance, manifests, exports, and city profiles

The current Townlight Core development line adds storage-neutral primitives
for production-depth municipal workflows:

```python
from civiccore import (
    AuditActor, AuditSubject, AuditHashChain,
    PersistedAuditLogEntry, compute_persisted_audit_hash,
    verify_persisted_audit_chain,
    SourceReference, SourceKind, CitationTarget, ProvenanceBundle,
    ImportManifest, ExportManifest, ManifestFile, validate_manifest,
    ExportBundle, BundleFile, write_manifest, build_sha256sums, validate_bundle,
    CityProfile, load_city_profile,
)

chain = AuditHashChain()
chain.record_event(
    actor=AuditActor(actor_id="clerk-1", actor_type="staff"),
    action="packet_exported",
    subject=AuditSubject(subject_id="meeting-42", subject_type="meeting"),
    source_module="civicclerk",
)
assert chain.verify()

entry_hash = compute_persisted_audit_hash(
    previous_hash="0" * 64,
    timestamp="2026-05-01T12:00:00+00:00",
    actor_id="records-admin",
    action="request_created",
    details={"request_id": "RR-1001"},
)
assert verify_persisted_audit_chain([
    PersistedAuditLogEntry(
        previous_hash="0" * 64,
        entry_hash=entry_hash,
        timestamp="2026-05-01T12:00:00+00:00",
        actor_id="records-admin",
        action="request_created",
        details={"request_id": "RR-1001"},
    )
])[0]
```

These APIs are deliberately offline-first. They do not provide JWT
issuance, SSO, user directories, credential storage, vendor-specific network
adapters, worker execution, legal determinations, or vendor write-back.

## Windows-local platform contracts

`civiccore.platform` exposes the shared contracts and queue helpers the
Townlight Windows desktop shell uses to keep future modules pluggable without
making clerks learn infrastructure:

```python
from civiccore.platform import (
    ModuleManifest,
    build_module_registry,
    PlatformHealthCheck,
    summarize_platform_health,
    LocalTaskEnvelope,
    enqueue_local_task,
    claim_next_local_task,
    record_task_attempt,
    run_one_local_task,
    build_backup_manifest,
    plan_restore,
)
```

For the `windows_local` install profile, module manifests cannot require
Docker, WSL, Linux shell setup, or a terminal-only operator path. Townlight Core also
ships task envelopes, a durable PostgreSQL task table, async queue helpers, and
a worker CLI so downstream modules share retry, health, checksum, and
restore-safety semantics while registering their own task handlers.

## Document ingestion

`civiccore.ingest` owns the shared document-ingestion path for downstream
modules. It exposes parser dispatch plus `register_handler()`, `ingest_file()`,
and `ingest_bytes()` entry points; stores parsed files in the baseline
`documents` table; writes sentence-aware chunks to `document_chunks`; and
persists 768-dimensional local Ollama embeddings through pgvector.

```python
from pathlib import Path

from civiccore.ingest import DataSource, SourceType, ingest_file

source = DataSource(
    name="Longmont Code of Ordinances proof corpus",
    source_type=SourceType.FILE_SYSTEM,
    connection_config={"path": "longmont-code-corpus"},
    created_by=operator_id,
)
session.add(source)
await session.commit()

document = await ingest_file(
    session=session,
    file_path=Path("longmont-code-corpus/Longmont, CO Code of Ordinances.pdf"),
    source_id=source.id,
    chunk_size=900,
    chunk_overlap=90,
)
```

The local Longmont proof in
[`docs/qa/civiccore-longmont-ingest-proof-2026-05-21.md`](docs/qa/civiccore-longmont-ingest-proof-2026-05-21.md)
parsed the 12.4 MB Longmont Code of Ordinances PDF into 1,789 persisted chunks
and wrote 1,789 768-dimensional `nomic-embed-text` embeddings.

## Live connector sync primitives

Townlight Core ships the storage-neutral pieces of the Townlight Records sync pattern
so every Townlight module can share one retry and circuit-breaker contract
without inheriting product-specific tables, credentials, or vendor adapters.

```python
from civiccore.connectors import (
    SyncCircuitState,
    SyncRunResult,
    apply_sync_run_result,
    build_sync_operator_status,
    build_sync_source_status,
)

state = SyncCircuitState(connector="legistar", source_name="Legistar production")
state = apply_sync_run_result(
    state,
    SyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
)
status = build_sync_operator_status(state)
assert status.public_dict()["health_status"] == "degraded"
source_status = build_sync_source_status(state, sync_schedule="*/15 * * * *")
assert source_status.public_dict()["active_failure_count"] == 0
```

The shared circuit opens after five consecutive full-run failures by default,
or after two failures when the source is in a configured grace period. Modules
still own their ORM rows, scheduler, credential store, vendor-specific fetch
logic, and UI, but they should use this shared state machine, operator copy, and
source-list projection instead of reimplementing it.

## Auth helper

`civiccore.auth` now exposes small auth helpers for downstream FastAPI
services that need to protect non-public internal endpoints or support
mixed public/staff routes without taking on a full first-party
identity-provider dependency. That surface now includes shared
trusted-header config loading and proxy-source enforcement helpers in
addition to bearer-token, trusted-header, and staff-key role checks.

```python
from fastapi import Depends
from fastapi.security import HTTPBearer

from civiccore.auth import (
    authorize_bearer_roles,
    authorize_trusted_header_roles,
    resolve_optional_bearer_roles,
    staff_key_gate,
)

bearer = HTTPBearer(auto_error=False)

def read_workpaper(credentials = Depends(bearer)) -> dict[str, str]:
    authorize_bearer_roles(
        credentials,
        service_name="CivicBudget",
        feature_name="persisted workpaper retrieval",
        token_roles_env_var="CIVICBUDGET_AUTH_TOKEN_ROLES",
        allowed_roles={"workpaper_reader", "budget_admin"},
    )
    return {"status": "ok"}


def search_archive(credentials = Depends(bearer)) -> dict[str, bool]:
    principal = resolve_optional_bearer_roles(
        credentials,
        service_name="CivicClerk",
        feature_name="archive search staff access",
        token_roles_env_var="CIVICCLERK_AUTH_TOKEN_ROLES",
        allowed_roles={"archive_reader", "clerk_admin", "city_attorney"},
    )
    return {"include_closed": principal is not None}


def require_proxy_assertion(request) -> dict[str, str]:
    principal = authorize_trusted_header_roles(
        request.headers,
        service_name="CivicClerk",
        feature_name="staff workflow access",
        principal_header_name="X-Forwarded-Email",
        roles_header_name="X-Forwarded-Roles",
        allowed_roles={"clerk_admin", "meeting_editor"},
        provider_name="Entra ID proxy",
    )
    return {"subject": principal.subject or "unknown"}


require_staff_key = staff_key_gate(
    "CIVICGRANTS_STAFF_API_KEY",
    "X-CivicGrants-Staff-Key",
)

def create_grant_case(_principal = Depends(require_staff_key)) -> dict[str, str]:
    return {"status": "accepted"}
```

Set `CIVICBUDGET_AUTH_TOKEN_ROLES` to a JSON object that maps bearer
tokens to role strings or role lists:

```json
{
  "demo-reader-token": ["workpaper_reader"],
  "budget-admin-token": "workpaper_reader,budget_admin"
}
```

If the bearer-token config is missing or malformed, Townlight Core raises an
actionable `503`; missing or invalid bearer headers return `401`; tokens
without an allowed role return `403`. Trusted-header helpers return
actionable `401` and `403` responses when the proxy assertion is missing,
malformed, or underprivileged. The optional resolvers return `None` for
anonymous callers, which lets public endpoints stay public until a caller
actually presents a bearer token or arrives through a trusted proxy.
`staff_key_gate()` preserves the existing Townlight module convention of
`X-Civic*-Role: staff` plus `X-Civic*-Staff-Key`, fails closed when the
configured environment variable is missing, and compares submitted keys with
`hmac.compare_digest`.

## Onboarding helper

`civiccore.onboarding` now ships shared storage-neutral helpers for
interview-style city-profile onboarding flows:

```python
from civiccore.onboarding import (
    DEFAULT_PROFILE_FIELDS,
    compute_onboarding_status,
    next_profile_prompt,
    parse_profile_answer,
)

parsed = parse_profile_answer("has_dedicated_it", "yes")
status = compute_onboarding_status({"city_name": "Sampleville"})
progress = next_profile_prompt(
    {"city_name": "Sampleville"},
    skipped_fields=("state",),
)
assert parsed is True
assert status == "in_progress"
assert progress.next_field == "county"
```

This ships the field order, skip-aware next-question selection, text
trimming, and yes/no normalization contract. Full web onboarding flows,
router integration, and persistence orchestration remain future work.

## Scheduling helper

`civiccore.scheduling` exposes the shared cron expression contract used by
module background jobs. `civiccore.platform` exposes the local task envelope,
PostgreSQL queue helpers, and retry contract. Modules keep their own task
handlers, but should reuse these helpers so one-minute accidental or adversarial
schedules and task retry behavior are handled consistently across Townlight.

```python
from civiccore.scheduling import compute_next_sync_at, validate_cron_expression

validate_cron_expression("*/5 * * * *")
next_run = compute_next_sync_at("0 2 * * *", last_sync_at=None)
```

## Verification helper

`civiccore.verification` now ships a small browser-evidence helper for
current-facing release pages. It binds a release screenshot manifest to
the normalized content hash of a rendered source file, which keeps
browser QA evidence honest across Windows and Linux checkouts.

```python
from pathlib import Path

from civiccore.verification import validate_release_browser_evidence

result = validate_release_browser_evidence(
    repo_root=Path("."),
    manifest_path=Path("docs/browser-qa/release-evidence.json"),
    expected_version="0.1.2",
)
print(result.reviewed_at)
```

## Public API surface

`civiccore.llm` exposes a single import surface for downstream apps:

```python
from civiccore.llm import (
    # Providers
    LLMProvider, register_provider, get_provider, list_providers,
    OllamaProvider, OpenAIProvider, AnthropicProvider,
    # Templates
    PromptTemplate, PromptTemplateCreate, PromptTemplateRead,
    RenderedPrompt, render_template, resolve_template,
    CIVICCORE_DEFAULT_APP, PromptTemplateError,
    PromptTemplateNotFoundError, PromptTemplateRenderError,
    # Model registry
    ModelRegistry, ModelRegistryCreate, ModelRegistryRead, ModelRegistryUpdate,
    model_registry_router, MissingModelError, ModelRegistryServiceError,
    get_active_model, require_active_model, get_active_model_context_window,
    # Context utilities
    TokenBudget, ContextBlock, estimate_tokens, count_tokens, sanitize_for_llm,
    assemble_context, blocks_to_prompt, DEFAULT_CONTEXT_WINDOW,
    # Structured output
    StructuredOutput, StructuredOutputFailure, DEFAULT_MAX_ATTEMPTS,
)
```

The full enumerated list — stable across the v0.x series per the spec's
semver policy — is also published in **Appendix A of the Townlight Core
Extraction Spec** in
[townlight/townlight](https://github.com/townlight/townlight).

## Compatibility

Every Townlight module's README declares its Townlight Core dependency contract.
Current v0.1.0 module foundations pin older civiccore lines. Production-depth
consumers should move only to the released Townlight Core version recorded in their
compatibility matrix.
The suite-wide compatibility matrix — which
module versions work with which Townlight Core versions — is maintained at
[CivicSuite/civicsuite/docs/compatibility/](https://github.com/townlight/townlight/tree/main/docs/compatibility).

## License

Code: AGPL-3.0-only. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), including the decision tree for
where to file a bug across the Townlight multi-repo layout.

## Private beta foundation candidate

The shared systems catalog now has a tested Records consumer; see [catalog contract](docs/catalog-beta.md) and [superseding ADR](docs/adr/ADR-0004-beta-shared-catalog.md). Broader installed-module catalog/recommendations remain open. Shared jobs now carry renewable claim leases, cancellation attribution and stale-result fencing; see [job contract](docs/job-leases.md). These are private candidate changes, not a published release or installed-city acceptance.

Core now owns the deterministic Records PII/regex/keyword evaluator, with compatibility imports and explicit incomplete-scan errors; see [scope and remaining rule work](docs/adr/ADR-0005-beta-exemption-evaluation.md). Module admission validates Core and required dependency versions, transitive blocks and cycles. Admission describes compatibility, not observed runtime health. The private candidate removes the Public Institution Exception; [license history](docs/licensing/README.md) preserves earlier grants.
