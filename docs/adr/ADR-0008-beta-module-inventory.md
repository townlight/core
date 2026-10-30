# ADR-0008: Beta installed-module inventory and recommendations

Status: Implemented in the private beta candidate; release, packaging and installed-city
acceptance pending
Date: 2026-10-27
Supersedes: ADR-0001 and ADR-0004 only for the tested installed-module inventory and
recommendation contract below

## Context

ADR-0001 deferred `civiccore.catalog` wholesale, and ADR-0004 resumed only the municipal systems
catalog. That left the installed-module half of CORE-08 open: nothing in Core persisted which
module packages a deployment scope had, and nothing offered an operator a next step. The
Windows-local shell already resolves modules through `civiccore.platform.build_module_registry`
with manifest admission, minimum Core versions, dependency minimums, transitive blocking and
required-cycle detection, so a second resolver would create two authorities.

Two further hazards shaped this decision. First, the systems catalog is *not* a module inventory:
`system_catalog` rows are vendor reference data, and treating them as install evidence would
invent installations that never happened. Second, a "recommendation" surface invites fabricated
discovery — probing servers, listing packages, or letting a model guess what a city runs.

## Decision

Add `civiccore.platform.inventory` plus the additive migration `civiccore_0007_module_inventory`.

* **Declared, not discovered.** A scope's inventory is only ever what a caller supplied with an
  attributed identity. No scanning, network access, package enumeration or runtime action exists
  in the module. "Available" packages are an explicit caller argument, and omitting it claims
  nothing.
* **Persisted and append-only.** One header row per `(scope_id, revision)` and one entry row per
  declared module, with the full manifest stored as `jsonb`. `expected_revision` is a
  compare-and-append guard and an advisory lock serialises per scope, so a stale writer cannot
  overwrite a newer declaration. A PostgreSQL trigger refuses `UPDATE`/`DELETE`; downgrade is a
  deliberate no-op.
* **Scoped, not global.** `scope_id` is caller-supplied. Core does not enumerate, authenticate or
  invent scopes. Scope isolation is structural through composite keys and the FK; the same module
  package may be declared installed by two scopes independently.
* **One resolver.** Every compatibility answer comes from the shipped
  `build_module_registry`, using the persisted manifests. There is no second dependency walker,
  cycle detector or version comparator in this module.
* **Advice separated from evidence.** Each recommendation carries `basis` (`installed` or
  `available`) and resolver text. A module that is admitted produces no recommendation at all.
  Nothing here asserts that a package is present, running, healthy, licensed or accepted.
* **Unknown ids refused.** `require_installed` raises `UnknownModuleError` rather than ignoring an
  id the scope never declared.

No public HTTP API or CLI is added: the actual clause asks for a persisted inventory and
recommendations, and the shipped consumers already own authentication and their own routes.

## Consequences

- Records and other consumers can persist and read a scoped inventory with real revision history
  instead of local, undocumented lists.
- An operator sees an explicit, honest next step per module, and no suggestion at all for a
  module the declared set already admits.
- The systems catalog and the module inventory stay distinct; a catalog row can no longer be
  mistaken for an installed module.
- Historical ADR-0001 and ADR-0004 remain preserved. The ADR-0001 downstream-consumption rule
  still applies because this candidate is not released.
- Not closed here: reviewed per-city module commissioning, installer/umbrella registration, a
  package artifact proof chain, download/update orchestration, a Core HTTP surface, consumer
  wiring in Records or the desktop shell, and any release or installed-city acceptance.

## Verification

No-database contract tests: `tests/test_module_inventory.py` (17 tests) — admission, scope
validation, duplicate refusal, fingerprint stability, installed/enabled separation,
unknown-id refusal, per-action determinism, ordering and the no-fabrication boundary.

Real PostgreSQL: `work/beta-foundations/module-inventory-01/harness.py` starts one disposable
owned cluster from `work/station-boundary/postgres/bin`, applies the real Core chain to head
`civiccore_0007_module_inventory`, and asserts nine checks — migration head and tables alongside
existing Core tables, append/idempotency/supersession, refusal of conflict/stale/backfill/gap/
invalid scope, unknown-module refusal against the persisted row set, scope isolation and two
scopes declaring one package independently, database-level `UPDATE`/`DELETE` refusal,
deterministic resolver-derived recommendations including an `upgrade-core` case, exactly one
winner from three concurrent writers of one next revision, and inventory/history/fingerprint
survival across a cluster stop/start with the recovered revision still gating the next append.
The cluster is stopped by the same process and no task-owned `postgres.exe` remains.

Receipts: `outputs/beta-plan/core-module-inventory-01/{checks.json,evidence.json,source-hashes.json}`
and this increment's `README.md`.
