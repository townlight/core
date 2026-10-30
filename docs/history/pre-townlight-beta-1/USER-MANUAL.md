# Townlight Core — User manual

## Private beta candidate — 29 October 2026

This guide now includes the local, unpublished corrected candidate. Use `Townlight-beta-corrected-private.msi`, version 1.6.0.1, SHA256 `98bcdef11ebdf5c767f620c904ff49f85115fde3b5c23f62703b111e645aaf86`. Historical public release links below identify earlier compositions; they are not the download instructions for this candidate. The current owned code is AGPL-3.0-only; retain third-party and historical notices.

For the full eight-module desktop choose **Townlight Inspections candidate** (`inspections-preview`) during normal first-run. This profile includes Core, Records, Meetings, Code, Zoning, Planning, Permitting and Inspections, plus supporting Notice and Access. Create the city profile and named administrator, sign in, choose backup storage, and use **Continue without local AI** for the deterministic staff workflows. Run Health Check, then Open Townlight. In System Health use **Finish Records Migration** to activate the canonical Python/PostgreSQL services. Add named staff through Settings. Station is provisioned separately; it does not replace or configure standalone CivicCast.

The private handoff contains the exact candidate identity, per-product receipt matrix and evidence limits. No city data or credentials were used. The tests drive the installed app's native commands and selected real UI controls; this is not a claim that every field, role, vendor or legal workflow has been tested. The source companion accompanying the MSI remains the source for the signed bytes; these later manual edits are a separate documentation companion.

### Core operator update

Settings creates named local staff accounts. Administrators own setup and maintenance; ordinary staff cannot administer users. Backup Now stops data writers. After backup, use Start to resume. Restore Latest Backup restores a verified snapshot and creates a safety backup; its normal result can be **Restore needs service start**. Follow **Start**, then **Check**. Do not interpret that intermediate status as a completed recovery before readback. Preserve previous installers/backups; this candidate has fresh-install acceptance, not an in-place upgrade certification.

Historical published baseline reviewed 2026-10-26; current private-candidate instructions above.

[Product page](https://townlight.github.io/products/core/) · [Overall manual](https://github.com/townlight/townlight/blob/main/USER-MANUAL.md) · [Requirements assessment](https://github.com/townlight/townlight/blob/main/docs/assessment/feature-and-integration-review.md)

## Purpose and audience

Core supplies Python contracts and shared services used by the other products. Staff normally encounter it through Setup, Settings and System Health rather than a separate Core workspace.

Primary operators: **IT and platform maintainers**. [Release and acceptance notes](https://github.com/townlight/townlight/releases/tag/townlight-records-meetings-code-zoning-planning-permitting-inspections-v1.7.0-beta.1).

## Before starting

Use the explicit product composition in the installed Townlight desktop. Sign in with the required local staff account, confirm System Health readiness and take a backup before maintenance. If a workspace is absent, inspect the profile and release identity before importing data. Optional AI is not needed for the accepted deterministic workflow. The procedures below use real saved sources; sample/demo web pages are not substitutes.

## Complete the workflow

### 1. Prepare a deployment

Choose the signed composition for the workflows needed. Keep the release acceptance, checksum and signing receipt with the installer. Package version, desktop version and the selected product profile are different identities; use the receipt rather than assuming they are equal.

### 2. Activate the local runtime

Complete the desktop administrator setup. Use the explicit activation and backed-up migration controls. System Health reports PostgreSQL, City workflow services, Task queue, optional Model runtime and document storage separately. Start dependencies before dependent services and wait for readiness, not merely a running PID.

### 3. Manage access

Create and use named local staff accounts through the desktop controls. Native session proof is mapped to persisted SQL identity. Never substitute an editable actor label, role header or staff key in a browser for an authenticated account.

### 4. Use shared ingestion

Import through the owning product. Core parses and normalizes supported material while the product records the original, permissions and citation. Core ingestion is implemented; it is not a central permission bypass or an automatic municipal data discovery service.

### 5. Use local AI deliberately

The optional model runtime and provider abstraction support configured consumers. Continue without local AI where offered. Model output is a draft; permission filtering, citations and human review still apply. No model download is necessary for the deterministic accepted land-use workflows.

### 6. Recover coherently

Create the desktop backup before migration or maintenance. Stop dependent City workflow services and Task queue before PostgreSQL maintenance. Use the canonical backup/restore controls; do not restore only one module table or write historical JSON back into a live SQL profile.

### 7. Diagnose a failure

Read System Health status, service logs and the support bundle. A dependency can be stopped, warming up, misconfigured or inaccessible; those conditions are distinct. Preserve data and the exact error before deciding a repair. Share a redacted bundle, not credentials or resident data.

## How this product connects

The other products consume Core contracts directly or through the Townlight runtime. The module owns its business permissions and workflow; Core does not automatically connect every pair of products.

## Boundaries and known gaps

The shared catalog and shared exemption engine are private beta candidates recorded by ADR-0004 and ADR-0005. `civiccore.scaffold` now ships a working module generator in the same private candidate (ADR-0007), which resumes the ADR-0003 placeholder deferral for that generator only; ADR-0003 stays the historical record and the downstream-dependency rule is unchanged, so no module may depend on the namespace until a versioned artifact and a compatibility-matrix entry name it. Search helpers are not a complete centrally hosted search service. Full user administration, business exemptions and public portals remain consumer responsibilities.

## Shared operating rules

Use the installed native desktop for the accepted workflow. Standalone package web pages, sample endpoints and developer API examples are different surfaces. A local Resident/Public view is not an internet deployment. Confirm the selected composition before looking for a workspace.

1. Keep named staff accounts and least privilege. Administrators manage setup; ordinary staff use their authorized workspace. Do not put credentials, unredacted evidence or resident data into public issues.
2. Preserve originals and their hashes. Import preview and confirmation are distinct actions. Treat fictional fixtures as fictional; they are not municipal authority.
3. Save before navigating away, closing or signing out. Unsaved drafts are not a durable record. On a conflict, reopen and reconcile; on an unknown result, inspect the saved record before repeating a write.
4. Review the exact revision and audience. A private packet and a public copy are different artifacts. Public text is explicitly edited/reviewed; changing a filename does not sanitize private content.
5. Keep source permission, version and hash checks. If a provider is stopped or a source becomes restricted, retain the draft, restore authorized access and deliberately reselect evidence. Never bypass the check or substitute a sample.
6. Approval, attachment, export and publication are separate actions. No cross-product attachment is an automatic records response, official permit, legal determination or enforcement decision.

## Installation, maintenance and recovery

For this private candidate use the exact installer and checksum above. Verify its publisher signature and handoff before installation; do not infer upgrade compatibility from its version. The public release references describe historical, separately identified compositions.

Complete Setup and normal runtime activation for the selected composition. Optional local AI can be deferred. Use System Health to distinguish stopped, starting, ready and failed dependencies. Wait for readiness before opening a dependent workspace. Use documented Retry controls after recovery; do not repeat business writes to refresh a stale screen.

Back up through the canonical desktop controls before migration or maintenance. Keep the coherent data, document and profile backup and its receipt in protected storage. A source export is not a full backup. Stop dependent services before PostgreSQL maintenance. Restore through the supported controls rather than editing SQL or restoring historical JSON into the active runtime. Uninstall can retain data; backup before uninstalling and inspect the chosen removal options. Never assume uninstall means data deletion.

For an error, retain the message, time, selected profile, installed version and operation; inspect System Health and relevant logs. Use a redacted support bundle. Do not delete the profile, run an arbitrary downgrade or repair prerequisites as a first response. If an installer requests a restart, save work and obtain the operator’s explicit restart decision before proceeding.

## Evidence and scope

The current normal-profile Sandbox acceptance covers first-run, named staff identity, the selected installed product workflows and coherent backup/restore. The handoff matrix links the exact raw receipts and distinguishes earlier unchanged source/media evidence. This is fresh-install acceptance of the identified private candidate; historical upgrades, every screen/role/vendor and city equipment are not certified. See the local beta handoff and current manual index; public documentation below is historical.


## Maintainer and API reference

The following source contracts support these instructions. The historical reference below retains older API/setup details for their original version; it does not override this operating guide or the release acceptance.

- [civiccore/search/__init__.py](https://github.com/townlight/core/tree/main/civiccore/search/__init__.py)
- [civiccore/ingest/pipeline.py](https://github.com/townlight/core/tree/main/civiccore/ingest/pipeline.py)
- [civiccore/platform](https://github.com/townlight/core/tree/main/civiccore/platform)
- [civiccore/catalog/__init__.py](https://github.com/townlight/core/tree/main/civiccore/catalog/__init__.py)
- [civiccore/exemptions/__init__.py](https://github.com/townlight/core/tree/main/civiccore/exemptions/__init__.py)
- [civiccore/scaffold/__init__.py](https://github.com/townlight/core/tree/main/civiccore/scaffold/__init__.py)
- [docs/adr/ADR-0001-defer-civiccore-catalog.md](https://github.com/townlight/core/tree/main/docs/adr/ADR-0001-defer-civiccore-catalog.md)
- [docs/adr/ADR-0002-defer-civiccore-exemptions.md](https://github.com/townlight/core/tree/main/docs/adr/ADR-0002-defer-civiccore-exemptions.md)
- [docs/adr/ADR-0003-defer-civiccore-scaffold.md](https://github.com/townlight/core/tree/main/docs/adr/ADR-0003-defer-civiccore-scaffold.md)


---

## Historical package/API reference

The material below is retained from the previous manual for historical and developer reference. Version, unreleased, sample, planned and installation claims below describe that earlier document, not current desktop release status. Use the current guide above for operation. Existing detailed API reference remains useful only for the matching package/version.

<a id="civiccore-user-manual"></a>

# Townlight Core User Manual

Version: v1.2.1 (current downstream productization line)
Repository: https://github.com/townlight/core
License: AGPL-3.0-only (see LICENSE)

This manual has three audiences:

1. **Non-technical evaluators** - what Townlight Core is and why it matters.
2. **IT and module developers** - how to install it and consume the public API.
3. **Architecture reviewers** - what ships today, what is planned, and how the library fits into the Townlight stack.

---

## 1. Non-Technical Overview

<a id="what-civiccore-is"></a>

### What Townlight Core Is

Townlight Core is the shared platform library underneath Townlight. It is the common
Python package that Townlight modules use for migrations, LLM plumbing,
provenance metadata, audit-chain primitives, export manifests, and local city
configuration.

It is **not** an app a clerk or resident logs into. End users interact with
module applications such as Townlight Records or Townlight Meetings. Townlight Core is the
shared foundation those applications import.

### What the current development line ships

- `civiccore.migrations` - migration runner, idempotent guards, and the shared
  schema baseline.
- `civiccore.db` - shared SQLAlchemy declarative `Base`.
- `civiccore.llm` - provider registry, prompt templates, model registry,
  context utilities, and structured-output helpers.
- `civiccore.audit` - hash-chained audit primitives for tamper-evident local
  event streams plus legacy-compatible persisted audit-log verification
  helpers.
- `civiccore.provenance` - source, citation, document, and provenance metadata
  contracts.
- `civiccore.connectors` - offline import/export manifest schemas,
  local-first import helpers for supported agenda-platform payloads, and
  storage-neutral live-sync retry/circuit-breaker primitives plus vendor
  delta request planning and source-list status projection.
- `civiccore.testing` - no-network mock-city proof contracts for supported
  agenda vendors, municipal OIDC, and backup-retention/off-host readiness.
- `civiccore.exports` - static export-bundle manifest and checksum helpers.
- `civiccore.city_profile` - local city/deployment configuration models.
- `civiccore.auth` - bearer-token role helpers, staff-key route gates, and
  trusted-header config/source-boundary helpers for protected or mixed
  public/staff FastAPI routes.
- `civiccore.verification` - content-bound browser release-evidence helpers.
- `civiccore.search` - deterministic text normalization, matching, and
  reciprocal-rank-fusion helpers.
- `civiccore.notifications` - notice deadline planning and publication
  compliance helpers with actionable warning codes.
- `civiccore.onboarding` - storage-neutral onboarding profile field order,
  answer parsing, completion-state, and next-question helpers.
- `civiccore.scheduling` - storage-neutral cron validation and next-run
  helpers for module background jobs.
- `civiccore.ingest` - shared discovery/fetch contracts, cited-source
  validation helpers, and document ingestion for PDF, DOCX, XLSX, CSV, EML,
  HTML, and text files with sentence-aware chunking, local Ollama embeddings,
  and pgvector-backed `documents` / `document_chunks` storage.

### What the current development line does not ship yet

The following namespaces remain planned extraction targets:
`civiccore.catalog` and `civiccore.exemptions`. `civiccore.scaffold` now ships a
working module generator in the private 1.3.0.dev1 candidate (ADR-0007), and a
generated module has been migrated on a disposable synthetic PostgreSQL cluster;
the namespace is still unreleased, so no module may depend on it.

`civiccore.onboarding` now ships shared profile interview helpers, but
full web onboarding flows and persistence orchestration are still not
shipped platform behavior.

Credential storage, vendor-specific network adapters, vendor write-back,
worker scheduler runtimes, notification delivery queues, and legal
determinations are also not shipped platform behaviors. Downstream modules must
not promote those behaviors as shipped Townlight Core capability.

### Why Municipal Teams Should Care

- **Sovereignty:** Local-first defaults keep cities in control of their data and
  infrastructure.
- **Reuse without coupling:** Each Townlight module depends on the same
  versioned primitives rather than copying logic.
- **Auditability:** Shared contracts for provenance, export bundles, and audit
  chains make compliance evidence more consistent across modules.

---

## 2. Technical Guide for IT and Module Developers

### Install from a Release Wheel

Townlight Core is distributed as GitHub release artifacts, not PyPI packages:

```bash
pip install https://github.com/CivicSuite/civiccore/releases/download/v1.2.1/civiccore-1.2.1-py3-none-any.whl
```

Each release publishes `SHA256SUMS.txt` next to the wheel and source
distribution. Verify checksums before promoting a release artifact:

```bash
curl -L -o SHA256SUMS.txt \
  https://github.com/CivicSuite/civiccore/releases/download/v1.2.1/SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

`v1.2.1` is the current published downstream productization line and includes
the shared document-ingestion pipeline used by the city-core release train.
`v0.22.1` is the first
Townlight Core release with a Sigstore-signed
`release-attestation.json` and bundle. Earlier Townlight Core releases are retained
for historical installs only and must not be treated as provenance baselines
unless a future additive attestation is explicitly authorized, published, and
recorded in `docs/ops/civiccore-tier1-retrofit-ledger.md`.

For local development:

```bash
git clone https://github.com/CivicSuite/civiccore.git
cd civiccore
pip install -e .[dev]
```

### Use LLM Providers

```python
from civiccore.llm import get_provider

provider = get_provider("ollama", base_url="http://localhost:11434")
text = await provider.generate(
    system_prompt="You summarize municipal records.",
    user_content="Summarize this request: ...",
)
```

Ollama uses the base dependency set. OpenAI and Anthropic require their SDKs
only if those providers are instantiated:

```bash
pip install openai
pip install anthropic
```

### Use Prompt Templates

```python
from civiccore.llm import render_template, resolve_template

template = await resolve_template(
    session,
    template_name="extract_request_fields",
    consumer_app="records-ai",
)
rendered = render_template(template, {"document_text": document_text})
```

The resolver checks app DB overrides first, code-level overrides second, and
Townlight Core defaults third. Missing variables produce actionable render errors.

### Use Audit, Provenance, Manifest, Export, and City Profile Primitives

```python
from civiccore import (
    AuditActor,
    AuditHashChain,
    AuditSubject,
    CityProfile,
    ExportBundle,
    ImportManifest,
    PersistedAuditLogEntry,
    SourceReference,
    compute_persisted_audit_hash,
    validate_bundle,
    validate_manifest,
    verify_persisted_audit_chain,
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

These primitives are storage-neutral. They give downstream modules a consistent
contract without dictating where records are stored.

### Use Live Connector Sync Primitives

Use `civiccore.connectors` for the shared retry and circuit-breaker state
machine when a module pulls from a live vendor system. The module still owns
its scheduler, tables, credentials, and vendor-specific fetch adapter.

```python
from civiccore.connectors import (
    SyncCircuitState,
    SyncRunResult,
    apply_sync_run_result,
    build_sync_operator_status,
    build_sync_source_status,
)

state = SyncCircuitState(connector="granicus", source_name="Granicus production")
state = apply_sync_run_result(
    state,
    SyncRunResult(records_discovered=4, records_succeeded=3, records_failed=1),
)
status = build_sync_operator_status(state)
print(status.public_dict()["message"])
source_status = build_sync_source_status(state, sync_schedule="0 2 * * *")
print(source_status.public_dict()["next_sync_at"])
```

Default behavior matches the Townlight Records pattern: healthy after successful
runs, degraded while failures remain, and circuit-open after five consecutive
full-run failures. Grace-period sources open after two full-run failures so
operators see the problem before scheduled pulls keep compounding it.
Use `build_sync_source_status()` for list/card views that need the same health
decision plus active failure counts, pause state, last status, actionable fix
copy, and next scheduled run.

### Run Migrations from a Consumer

Townlight Core migrations run before a downstream module's migrations. Consumer
modules use Townlight Core's migration runner and keep their own version table so
revision names do not collide.

The release gate verifies the Townlight Core migration chain, including
`civiccore_0001_baseline_v1` and `civiccore_0002_llm`.

---

## 3. Architecture Reference

### Shipped vs Planned

![Townlight Core extraction map](docs/diagrams/civiccore-extraction-map.svg)

Shipped implementation in the current development line:

```text
civiccore/
  audit/        hash-chained audit primitives and persisted audit-log helpers
  city_profile/ local city/deployment configuration models
  connectors/   offline manifests, local-first import helpers, live-sync primitives
  db/           shared SQLAlchemy declarative Base
  exports/      static export-bundle helpers
  ingest/       shared contracts, cited-source validation, document ingestion,
                sentence-aware chunking, and pgvector embedding storage
  llm/          providers, templates, registry, context, structured output
  migrations/   migration runner and shared schema baseline
  notifications/ notice deadline + compliance helpers
  onboarding/   shared onboarding profile field-order/progress helpers
  scheduling/   cron validation and next-run helpers
  provenance/   source/citation/provenance metadata contracts
```

Still planned namespaces:

```text
civiccore/
  catalog/       future catalog primitives
  exemptions/    future 50-state public-records exemption engine
  notifications/ delivery queues and outbound orchestration remain future work
  onboarding/    future web onboarding UI/persistence flows
  scheduling/    scheduler runtime and task queue remain module-owned
  scaffold/      working module generator (private 1.3.0.dev1 candidate; ADR-0007),
                 not a released namespace
  verification/  future sovereignty verification
```

### Migration Order

![Migration order](docs/diagrams/migration-order.svg)

Consumer applications run Townlight Core migrations first, then their own module
migrations. Separate Alembic version tables prevent revision-name collisions.

### LLM Provider Abstraction

![Provider abstraction](docs/diagrams/provider-abstraction.svg)

The provider abstraction keeps local Ollama as the sovereignty-first default
while allowing explicitly configured cloud providers where a city authorizes
them.

### Compatibility

Current v0.1.0 module foundations still pin older civiccore lines.
Production-depth consumers should move only to the released Townlight Core version
recorded in their compatibility matrix.

The suite-wide matrix lives at:
https://github.com/townlight/townlight/tree/main/docs/compatibility

---

## Appendix: Where to File Issues

- Townlight Core bug: https://github.com/townlight/core/issues
- Suite-wide design issue: https://github.com/townlight/townlight/issues
- Security issue: follow `SECURITY.md`; do not file publicly.

The decision tree in `CONTRIBUTING.md` has the full routing rules.
