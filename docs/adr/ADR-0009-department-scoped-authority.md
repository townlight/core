# ADR-0009: Department-scoped shared authority

Status: Implemented in the private beta candidate; release, packaging and installed-city
acceptance pending
Date: 2026-10-27
Extends: ADR-0004/ADR-0006/ADR-0008 (additive; no historical ADR text is rewritten)

## Context

The `C1.authority` clause asks for "department-scoped identity/search/export/AI authorization"
and its exit evidence is that two departments and a revoked staff member demonstrate denied
reads, snippets, model context and exports.

Before this increment, the shipped candidate could not express that. A probe of the real package
(`work/beta-foundations/core-authority-01/gap-probe.json`) recorded four concrete gaps:

1. `AuthenticatedPrincipal` carries `roles`, `subject`, `provider` and `auth_method` — no
   department and no revocation state.
2. `civiccore.search.filter_records_by_access_level` takes `user_level`, `level_ranks` and
   `access_level_for`; there is no scope, department or tenant input at all.
3. `civiccore.exports` has no authorization step between the caller and the bundle.
4. `civiccore.llm.context.assemble_context` accepts any `chunks` the caller passes.

With that surface, the only way for a caller to be department-scoped was for it to *assert* its
own department in a header, claim or body — and the service had no way to tell an assertion from
an authorization. That is a privilege-escalation shape, not a missing feature.

## Decision

Add `civiccore.auth.department_scope` and the additive migration
`civiccore_0008_authority` (`civiccore_department_grant_events`).

* **Persisted provenance is the only authority.** A department claim is admissible only from the
  server-side grant ledger read through `active_department_grants`. The resolver has no
  parameter accepting a caller-supplied department, and `DepartmentAuthority` cannot be
  constructed outside the resolver (private sentinel; direct construction raises
  `AuthorityProvenanceError`).
* **Deny by default.** Seven named refusal reasons; unbound records are dropped rather than
  assumed readable; no "public"/"all"/"inherit" fallback.
* **Identity source allowlist.** Only `bearer`, `trusted_header`, `staff_key` and
  `suite_session` — the methods the shipped helpers produce — are accepted, so an invented
  `X-Department` style method is refused before any grant lookup.
* **Role intersection, not role union.** Extra roles a subject holds elsewhere never widen a
  department grant.
* **Scope is structural.** Every row carries `scope_id`, the primary key includes it, and the
  resolver re-checks `grant.scope_id == scope_id` so rows smuggled in from another scope cannot
  widen the result.
* **Append-only events.** `(scope_id, subject, department_id, sequence)` with a revoke expressed
  as a later event; triggers refuse `UPDATE`/`DELETE`; a `CHECK` enforces grant/revoke role
  shape; downgrade is a no-op.
* **One engine, reused.** Search scoping delegates to the shipped `roles_grant_access`, and model
  context returns a `chunks` list for the shipped `assemble_context`. No second permission
  engine and no second context builder is introduced.
* **No duplicate identity.** No new credential verifier, user table, SSO bridge or HTTP route.

## Consequences

- Records, Meetings and other consumers get a shared, tested gate instead of inventing per-app
  department checks, and a revocation is effective on the next resolution because nothing is
  cached.
- An administrative flow still has to authorize *who may grant*. Core deliberately does not
  decide that; it only insists the write is attributed and well formed.
- `department_id` is not a foreign key to `public.departments`: the ledger outlives org-chart
  edits.
- Not closed: a Core HTTP/CLI surface, per-city department commissioning, role-to-job-function
  mapping, search index/snippet/facet rendering, export rendering, consumer wiring in Records or
  other products, and any installed-city or legal acceptance.
- Historical ADR-0001/0003/0005/0006/0007/0008 text stays byte-identical; the ADR-0001
  downstream-consumption rule still applies because this candidate is not released.

## Verification

Contract tests: `tests/test_department_authority.py` (29 tests).

Real PostgreSQL: `work/beta-foundations/core-authority-01/harness.py` — one disposable owned
cluster, real Core chain to head `civiccore_0008_authority`, nine assertions: deny-by-default on
real rows plus untrusted identity source refusal; idempotent attributed grant; two departments
with distinct roles see only their own results/snippets/export while cross-department export and
an unowned record are refused; revocation effective immediately with retry refused; scope
isolation including cross-scope rows smuggled into a resolver call; database append-only and
`CHECK` guards; concurrent sequence assignment (3 distinct appends → 1,2,3 with one active row;
3 identical appends → one insert); restart survival with the recovered ledger still gating the
next sequence.

Defects this increment found and fixed: the initial migration revision id
`civiccore_0008_department_authority` (36 chars) exceeded Core's existing
`alembic_version_civiccore.version_num varchar(32)` and failed the real migration
(`StringDataRightTruncation`); it is now `civiccore_0008_authority`. A first draft of the auth
`__init__` rewrite dropped the pre-existing `revoke_suite_session` export while keeping its
import — a public-surface regression caught by `ruff` and restored.
