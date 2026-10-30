# ADR-0007: Resume module scaffolding for the beta candidate

Status: Implemented and migration-verified in the private beta candidate; release and downstream dependency pending
Date: 2026-10-27
Supersedes: ADR-0003 only for the tested generator described below

## Context

ADR-0003 deferred `civiccore.scaffold` and left the namespace as a documented placeholder:
"no downstream module may import ... a placeholder namespace until that namespace ships in a
versioned CivicCore release artifact." That deferral text stays in force and is preserved
verbatim; this ADR is the resumption record, the same way ADR-0004 resumed the catalog.

The beta acceptance register still lists `C1.scaffold` ("Generated module boots against
supported auth/migrations; no working insecure defaults") and `CORE-10` as implementation-needed.
The owner's current instruction is to close that gap with the smallest working generator that
conforms to Core's *existing* contracts, not to design a plugin framework.

## Decision

`civiccore.scaffold` now ships one generator, reachable as a library
(`plan_module_project`, `generate_module_project`, `ModuleSpec`) and as a CLI
(`python -m civiccore.scaffold generate|plan`).

The generator emits one complete module project with:

* `pyproject.toml` declaring `license = "AGPL-3.0-only"` and a `civiccore>=` floor;
* `src/<package>/manifest.json`, shaped so the **shipped** `civiccore.platform.ModuleManifest`
  and `validate_windows_local_manifest()` accept it; the generator re-validates its own output
  before returning a plan, so a template drift cannot silently emit an invalid module;
* `src/<package>/app.py`, a minimal FastAPI staff surface whose only auth dependency is the
  shipped `civiccore.auth.authorize_bearer_roles`. It fails closed: **503** until the operator
  sets `<PACKAGE>_TOKEN_ROLES`, then 401 for a missing or unknown token, 200 only for a
  configured role. No default token, role or password is compiled in;
* `migrations/` — an Alembic environment that owns **only** the module's own schema and
  delegates the Core chain to `civiccore.migrations.runner.upgrade_to_head`, plus one additive
  baseline revision;
* `tests/test_<package>_contract.py`, `docs/module.md`, `README.md`, `.gitignore`.

**Every identity is derived from `module_id`.** Package name, import path, env-var name,
default permission key, route prefix, manifest filename and migration revision are computed,
never supplied independently, so a caller cannot produce a self-inconsistent project.

Deliberate boundaries:

* **Refusal, not sanitisation.** `module_id` must match Core's existing `MODULE_ID_PATTERN`;
  reserved ids (`civiccore`, `tests`, `docs`, `app`, `migrations`, ...), Python keywords and
  stdlib module names are refused with `InvalidModuleSpecError`. `../escape` is an error, not
  `escape`.
* **No overwrite, ever.** `generate_module_project` refuses an existing project directory
  (`TargetExistsError`) or a non-directory at that path (`UnsafeTargetError`); it never merges.
  A partial failure rolls back only what that call created.
* **Containment checked, not assumed.** Every planned relative path is rejected before writing
  if it is absolute, parented, drive-qualified or shell-separated (`PathContainmentError`), the
  resolved parent must equal the requested target directory, and each write re-checks that its
  resolved destination is inside the project root.
* **No new runtime, provider, framework or network.** Generated code imports only Core,
  FastAPI and the stdlib. The generator makes no network call, installs nothing, starts no
  service, writes no global setting and emits no credential.
* **No reimplementation of Core.** The manifest is Core's model; auth is Core's helper;
  migrations are Alembic plus one additive revision. There is no second registry, settings
  store or permission engine in the template.

## Consequences

* The `C1.scaffold` / `CORE-10` "working generator" clause now has an implementation and
  isolated evidence (`outputs/beta-plan/core-scaffold-01/`).
* The **downstream consumption rule is unchanged**: consumers must still not depend on
  `civiccore.scaffold` from a released artifact, because this candidate is not released and no
  compatibility-matrix entry names it. `tests/test_placeholder_adrs.py` asserts both the
  historical deferral text and this ADR.
* The generated project is a skeleton. Core does not ship an installer, an umbrella host or a
  module marketplace; a generated module still needs the umbrella owner to install, register
  and supervise it.

## Migration verification and template defects found

`work/beta-foundations/scaffold-01/pg-acceptance/harness.py` applies Core's real chain to head
(`civiccore_0006_rule_history`) and then the generated module's own chain on one disposable,
owned PostgreSQL 17 cluster, and asserts the module revision, its exclusive schema, Core's
unchanged tables and revision, re-run idempotency, restart durability and a clean
downgrade/re-upgrade. That run found two real template defects, both now fixed and covered by
a regression assertion in `tests/test_scaffold.py`:

* `migrations/env.py` configured `version_table_schema` without creating the schema, so a
  fresh database failed with `psycopg2.errors.InvalidSchemaName`. It now creates the schema
  before configuring the context.
* The baseline `downgrade` dropped the module schema while Alembic's version table still
  lived in it, failing with `DependentObjectsStillExist`. It now drops only the tables the
  revision created.

Still open, and not implied by this ADR: generated modules for real products, a `CivicSuite`
suite-registration writer, module settings UI, generated CI workflow files, a *generated*
per-module PostgreSQL integration test shipped inside the project template, scaffold of
non-Python surfaces, and any release/packaging of this namespace. Packaging the new source
into a versioned artifact remains a separate authorized step.

Evidence: `tests/test_scaffold.py` (26 tests; the targeted suite reports 50 passed and 1
host-limited skip, the skip being a Windows-privilege symlink check) plus the existing
placeholder, module-registry, platform-contract, public-API and smoke regressions; the
synthetic generated project in `work/beta-foundations/scaffold-01/`; the disposable
PostgreSQL acceptance in `work/beta-foundations/scaffold-01/pg-acceptance/`; receipts in
`outputs/beta-plan/core-scaffold-01/`.
