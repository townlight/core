# Department-scoped shared authority

`civiccore.auth.department_scope` is Core's single authorization contract for department-scoped
material. It answers one question for every consumer: *may this already-authenticated subject
reach this department in this deployment scope, and with which roles?* Search results and
snippets, export bundles and model context all pass through the same object, so there is no
second permission engine and no per-consumer guess.

This contract is the executable part of the `C1.authority` clause ("department-scoped
identity/search/export/AI authorization"). It is **not** a complete identity administration or
search service (see [What this does not do](#what-this-does-not-do)).

## The trust boundary

The only admissible source of a department claim is the persisted, server-side grant ledger
`civiccore_department_grant_events`, read through `active_department_grants` and keyed by
`(scope_id, subject, department_id)`.

A department named in a request body, query string, cookie, HTTP header, environment variable,
JWT custom claim or model output is **not** a grant. `resolve_department_authority` has no
parameter that accepts one, and `DepartmentAuthority` cannot be constructed without the
resolver's private provenance token:

```python
from civiccore.auth import DepartmentAuthority
DepartmentAuthority(...)   # AuthorityProvenanceError: caller-supplied claims are not authority
```

Credential verification stays where it already lives: `civiccore.auth.bearer`,
`civiccore.auth.trusted_headers` (with `enforce_trusted_proxy_source` proving the proxy really
is the proxy), `civiccore.auth.staff_key` and `civiccore.auth.suite_session`. This module only
consumes the `AuthenticatedPrincipal` those helpers return, and only for the four identity
sources in `TRUSTED_AUTH_METHODS`.

## Deny by default

Every failure mode denies, with a stable reason code:

| Reason | When |
|---|---|
| `unauthenticated` | the principal carries no subject |
| `untrusted-identity-source` | `auth_method` is outside `TRUSTED_AUTH_METHODS` |
| `inactive-principal` | the principal exposes `is_active=False` |
| `invalid-scope` | `scope_id` is malformed |
| `no-active-grant` | the subject holds no active grant in this scope |
| `department-not-granted` | the requested department is not granted |
| `role-not-granted` | the role intersection is empty |

There is no fallback to "public", "all departments" or "inherit another scope". A record whose
owning department is unknown is filtered out of search and model context rather than assumed
readable.

## Roles

A grant names the roles it admits. The effective entitlement is the **intersection** of the
principal's roles and the grant's roles, so extra roles a subject happens to hold elsewhere never
widen a department grant. `permits(department_id, roles=...)` additionally requires any
caller-supplied required role to be inside that intersection.

## Append-only ledger

One row per grant/revoke *event*, primary key `(scope_id, subject, department_id, sequence)`.
The active entitlement is the highest sequence per department. Consequences:

- `record_department_grant` appends sequence N+1 or verifies an exact repeat (idempotent, keeps
  the original recorder and sequence).
- `revoke_department_grant` appends a roleless revoke event; the grant stays readable in
  `department_grant_history`. A second revoke of an already revoked department is refused.
- A stale, out-of-order event cannot override a newer one: the resolver picks the highest
  sequence, so smuggling an old grant into the call changes nothing.
- Sequence assignment is serialized per `(scope, subject, department)` with a transaction-scoped
  advisory lock; three concurrent writers produce sequences 1, 2, 3 and three identical writers
  produce exactly one insert.
- PostgreSQL refuses `UPDATE` and `DELETE` on the ledger, and a `CHECK` constraint refuses an
  unknown action, a roleless grant and a revoke that carries roles. Migration downgrade is a
  deliberate no-op: dropping the ledger would erase who was allowed to read which department, so
  recovery is restore-from-backup.

`department_id` is deliberately **not** a foreign key to `public.departments`. The ledger is
deployment-scoped, Core does not own a city's org chart, and deleting a department row must not
erase the authority history that allowed earlier access.

## Consumer adapters

Reusing the shipped helpers rather than adding new engines:

- `scope_search_results(authority, records, department_for=...)` — drops results before snippets
  or facets are built. Internally uses `civiccore.search.roles_grant_access`.
- `authorize_export(authority, department_id=..., purpose=...)` — the gate a static export bundle
  must pass before `civiccore.exports` writes anything.
- `scope_model_context_chunks(authority, chunks, department_for=...)` — returns the exact
  `chunks` list `civiccore.llm.context.assemble_context` accepts, so there is one context
  builder and one permission gate in front of it.

## What this does not do

- No HTTP API, CLI or route is added; consumers own their routes, sessions and error shapes.
- No identity administration: Core does not create users, verify passwords, provision SSO or
  decide who may *make* a grant. Authorizing an administrator to grant is the deployment's
  administration flow; this module only insists the write is attributed and well formed.
- No index, search service, snippet renderer, facet counter or export renderer.
- No claim that a role name maps to a real job function, that a department matches a city's org
  chart, or that every consumer actually applied the gate. Records, Meetings and the other
  products still own their review workflows and legal decisions.
- Permission *cache invalidation* is not needed here because nothing is cached: every resolution
  reads the current ledger, so a revocation takes effect on the next request.

## Verification

Contract tests (no database): `tests/test_department_authority.py`.

Real PostgreSQL: `work/beta-foundations/core-authority-01/harness.py` starts one disposable owned
cluster, applies the real Core chain to head `civiccore_0008_authority`, and asserts nine checks
covering deny-by-default on real rows, idempotent attributed grants, two-department isolation of
results/snippets/exports, immediate revocation with retained history, scope isolation, database
append-only/CHECK guards, concurrent sequence assignment, and restart survival.

## Compatibility

Purely additive: no existing table, function or export changed meaning. The pre-existing public
symbols of `civiccore.auth` remain exported, and the new names are added alongside them.
