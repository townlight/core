# SPDX-License-Identifier: AGPL-3.0-only
"""Deny-by-default, department-scoped shared authority for Core consumers.

What this module is
-------------------
One authority object answers exactly one question for every Core consumer: *may this
authenticated subject see or export this department's material in this deployment scope, and
with which roles?* Search results/snippets/facets, export bundles and model context all pass
through the same object, so there is no second permission engine and no per-consumer guess.

What this module is not
-----------------------
It is not an identity provider and it does not authenticate anyone. Credential verification
stays in the shipped helpers (:mod:`civiccore.auth.bearer`,
:mod:`civiccore.auth.trusted_headers`, :mod:`civiccore.auth.staff_key`,
:mod:`civiccore.auth.suite_session`). This module consumes the *already authenticated*
principal those helpers return.

The trust boundary (read this before adding a caller)
----------------------------------------------------
The only admissible source of a department claim is the persisted, server-side grant ledger
``civiccore_department_grant_events`` read through :func:`active_department_grants` and keyed by
``(scope_id, subject, department_id)``. A department named in a request body, query string,
cookie, HTTP header, environment variable, JWT custom claim or model output is **not** a grant:
:func:`resolve_department_authority` has no parameter that accepts one, and
:class:`DepartmentAuthority` cannot be constructed without the resolver's private provenance
token. Adding a \"caller says it belongs to department X\" path would be a privilege escalation
hole, not a feature.

Deny by default
---------------
Every failure mode denies: no authenticated subject, an identity source outside
:data:`TRUSTED_AUTH_METHODS`, an inactive principal, no persisted grant, a grant for a
different department, an empty role intersection, or an explicitly requested department the
subject does not hold. There is no fallback to \"public\", \"all departments\", or
\"inherit from another scope\".

Scope and non-claims
--------------------
``scope_id`` is a caller-supplied deployment/tenant scope (for example a city profile
identifier); Core does not invent or enumerate one, and a grant in one scope is invisible in
another. Core does not assert that a role name maps to a real job function, that a department
row matches a city's org chart, or that a consumer applied this authority correctly. Records,
Meetings and the other products still own their own routes, review workflows and legal
decisions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from civiccore.search import normalize_access_values, roles_grant_access

__all__ = [
    "DepartmentAuthorityError",
    "AuthorityProvenanceError",
    "DepartmentAccessDenied",
    "DepartmentGrantError",
    "DepartmentGrant",
    "DepartmentEntitlement",
    "DepartmentAuthority",
    "GrantOutcome",
    "resolve_department_authority",
    "record_department_grant",
    "revoke_department_grant",
    "active_department_grants",
    "department_grant_history",
    "scope_search_results",
    "authorize_export",
    "scope_model_context_chunks",
    "TRUSTED_AUTH_METHODS",
    "GRANT_TABLE",
    "SCOPE_PATTERN",
]

GRANT_TABLE = "civiccore_department_grant_events"

#: Identity sources produced by a credential check inside the service or by a proxy that is
#: verified separately (``enforce_trusted_proxy_source``). Anything else — including a raw
#: header/claim name a caller invented — is refused.
TRUSTED_AUTH_METHODS = ("bearer", "trusted_header", "staff_key", "suite_session")

SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")

GrantAction = Literal["grant", "revoke"]

# Sentinel that only this module can reach: proves an authority came from the resolver.
_RESOLVED = object()

_REASON_DETAIL = {
    "unauthenticated": "No authenticated subject was supplied by a credential helper.",
    "untrusted-identity-source": "The identity source is not one of the trusted auth methods.",
    "inactive-principal": "The authenticated principal is inactive or revoked.",
    "invalid-scope": "The deployment scope identifier is malformed.",
    "no-active-grant": "No active persisted department grant exists for this subject.",
    "department-not-granted": "The requested department is not granted to this subject.",
    "role-not-granted": "The subject holds no role this department grant admits.",
}


class DepartmentAuthorityError(ValueError):
    """Base class: the authority was refused and nothing was disclosed."""


class AuthorityProvenanceError(DepartmentAuthorityError):
    """The identity behind the request is absent, untrusted or inactive."""


class DepartmentAccessDenied(DepartmentAuthorityError):
    """Deny-by-default refusal carrying a stable machine-readable reason code."""

    def __init__(self, reason: str, *, action: str) -> None:
        self.reason = reason
        self.action = action
        detail = _REASON_DETAIL.get(reason, "Access refused.")
        super().__init__(f"{action} denied ({reason}): {detail}")


class DepartmentGrantError(DepartmentAuthorityError):
    """A grant/revoke write was refused and no event row was added."""


def _require_scope(scope_id: str) -> str:
    value = scope_id.strip() if isinstance(scope_id, str) else ""
    if not SCOPE_PATTERN.match(value):
        raise DepartmentGrantError(
            "scope_id must match ^[a-z][a-z0-9._-]{1,63}$ (for example 'city-a')"
        )
    return value


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class DepartmentGrant(BaseModel):
    """One persisted grant/revoke event for a subject in one scope and department.

    Rows are append-only: a ``revoke`` event does not delete the earlier ``grant`` event, it
    supersedes it. ``sequence`` is monotonic per ``(scope_id, subject, department_id)`` so the
    active state is always the highest-sequence event.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    scope_id: str = Field(min_length=2, max_length=64)
    subject: str = Field(min_length=1, max_length=320)
    department_id: UUID
    sequence: int = Field(ge=1)
    action: GrantAction
    roles: tuple[str, ...] = ()
    recorded_by: str = Field(min_length=1, max_length=128)
    recorded_at: AwareDatetime
    content_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("scope_id")
    @classmethod
    def _scope(cls, value: str) -> str:
        if not SCOPE_PATTERN.match(value):
            raise ValueError("scope_id must match ^[a-z][a-z0-9._-]{1,63}$")
        return value

    @field_validator("roles")
    @classmethod
    def _roles_normalized(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(normalize_access_values(value)))

    @field_validator("content_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("content_sha256 must be a lowercase sha-256 hex digest")
        return value

    @model_validator(mode="after")
    def _action_shape(self) -> DepartmentGrant:
        if self.action == "grant" and not self.roles:
            raise ValueError("a grant event must name at least one role")
        return self

    def payload(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "subject": self.subject,
            "department_id": str(self.department_id),
            "sequence": self.sequence,
            "action": self.action,
            "roles": list(self.roles),
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at.isoformat(),
        }

    def fingerprint(self) -> str:
        return _fingerprint(self.payload())


@dataclass(frozen=True)
class DepartmentEntitlement:
    """A department this subject may reach, with the roles granted there."""

    department_id: UUID
    roles: frozenset[str]
    granted_by: str
    granted_at: datetime


@dataclass(frozen=True)
class DepartmentAuthority:
    """The only object Core consumers may use to scope search, exports and model context.

    Instances are produced by :func:`resolve_department_authority`. Direct construction raises
    :class:`AuthorityProvenanceError`, because a hand-built authority would be exactly the
    \"trust the caller's department claim\" hole this contract exists to close.
    """

    scope_id: str
    subject: str
    auth_method: str
    provider: str | None
    roles: frozenset[str]
    entitlements: tuple[DepartmentEntitlement, ...]
    resolved_at: datetime
    grants_digest: str
    provenance: Literal["persisted-grant"] = "persisted-grant"
    _token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _RESOLVED:
            raise AuthorityProvenanceError(
                "DepartmentAuthority must be produced by resolve_department_authority from "
                "persisted server-side grants; a caller-supplied department claim is not "
                "authority"
            )
        if not SCOPE_PATTERN.match(self.scope_id):
            raise AuthorityProvenanceError("invalid-scope")
        if not self.subject.strip():
            raise AuthorityProvenanceError("unauthenticated")
        if self.auth_method not in TRUSTED_AUTH_METHODS:
            raise AuthorityProvenanceError("untrusted-identity-source")

    # -- read-only inspection -----------------------------------------------------------
    @property
    def department_ids(self) -> frozenset[UUID]:
        return frozenset(item.department_id for item in self.entitlements)

    def roles_in(self, department_id: UUID) -> frozenset[str]:
        for item in self.entitlements:
            if item.department_id == department_id:
                return item.roles
        return frozenset()

    def permits(self, department_id: UUID, *, roles: Iterable[str] = ()) -> bool:
        """Return True only when this subject holds the department and an admitted role."""

        granted = self.roles_in(department_id)
        if not granted:
            return False
        if not roles:
            return True
        return roles_grant_access(self.roles, allowed_roles=granted) and roles_grant_access(
            roles, allowed_roles=granted
        )

    def require(
        self, department_id: UUID, *, roles: Iterable[str] = (), action: str
    ) -> DepartmentEntitlement:
        """Raise :class:`DepartmentAccessDenied` unless the department is reachable."""

        if not self.entitlements:
            raise DepartmentAccessDenied("no-active-grant", action=action)
        if department_id not in self.department_ids:
            raise DepartmentAccessDenied("department-not-granted", action=action)
        if not self.permits(department_id, roles=roles):
            raise DepartmentAccessDenied("role-not-granted", action=action)
        for item in self.entitlements:
            if item.department_id == department_id:
                return item
        raise DepartmentAccessDenied("department-not-granted", action=action)

    def receipt(self) -> dict[str, Any]:
        """Bounded, non-secret description suitable for logs and evidence."""

        return {
            "scope_id": self.scope_id,
            "subject_fingerprint": hashlib.sha256(self.subject.encode("utf-8")).hexdigest()[:12],
            "auth_method": self.auth_method,
            "provider": self.provider,
            "roles": sorted(self.roles),
            "departments": sorted(str(item.department_id) for item in self.entitlements),
            "grants_digest": self.grants_digest,
            "resolved_at": self.resolved_at.isoformat(),
            "provenance": self.provenance,
        }


def _principal_fields(principal: Any) -> tuple[str | None, frozenset[str], str | None]:
    """Read identity from a shipped auth result without importing its private internals."""

    subject = getattr(principal, "subject", None)
    roles = getattr(principal, "roles", None)
    method = getattr(principal, "auth_method", None)
    normalized_roles = normalize_access_values(roles) if roles else frozenset()
    return (
        subject.strip() if isinstance(subject, str) and subject.strip() else None,
        frozenset(normalized_roles),
        method.strip().lower() if isinstance(method, str) and method.strip() else None,
    )


def _active_entitlements(
    *,
    scope_id: str,
    subject: str,
    grants: Sequence[DepartmentGrant],
    principal_roles: frozenset[str],
) -> tuple[DepartmentEntitlement, ...]:
    latest: dict[UUID, DepartmentGrant] = {}
    for grant in grants:
        if grant.scope_id != scope_id or grant.subject != subject:
            # A caller mixing scopes or subjects cannot widen its own view.
            continue
        current = latest.get(grant.department_id)
        if current is None or grant.sequence > current.sequence:
            latest[grant.department_id] = grant

    entitlements: list[DepartmentEntitlement] = []
    for department_id, event in sorted(latest.items(), key=lambda item: str(item[0])):
        if event.action != "grant":
            continue
        inherited = principal_roles & normalize_access_values(event.roles)
        if not inherited:
            continue
        entitlements.append(
            DepartmentEntitlement(
                department_id=department_id,
                roles=frozenset(sorted(inherited)),
                granted_by=event.recorded_by,
                granted_at=event.recorded_at,
            )
        )
    return tuple(entitlements)


def resolve_department_authority(
    *,
    principal: Any,
    scope_id: str,
    grants: Iterable[DepartmentGrant],
    requested_departments: Iterable[UUID] | None = None,
    now: datetime | None = None,
) -> DepartmentAuthority:
    """Build the deny-by-default authority for one already-authenticated principal.

    ``grants`` must be the persisted, server-side rows for this scope and subject (normally
    :func:`active_department_grants`). ``requested_departments`` is the optional set of
    departments the caller *asks* for; it can only narrow the result and every requested
    department must be granted, otherwise the whole resolution is refused.
    """

    subject, principal_roles, auth_method = _principal_fields(principal)
    if subject is None:
        raise AuthorityProvenanceError("unauthenticated")
    if auth_method not in TRUSTED_AUTH_METHODS:
        raise AuthorityProvenanceError("untrusted-identity-source")
    is_active = getattr(principal, "is_active", True)
    if is_active is False:
        raise AuthorityProvenanceError("inactive-principal")
    try:
        scope = _require_scope(scope_id)
    except DepartmentGrantError as exc:
        raise AuthorityProvenanceError("invalid-scope") from exc

    effective_now = now or datetime.now(UTC)
    if effective_now.tzinfo is None:
        raise AuthorityProvenanceError("resolved_at must be timezone-aware")

    materialized = tuple(grants)
    entitlements = _active_entitlements(
        scope_id=scope,
        subject=subject,
        grants=materialized,
        principal_roles=principal_roles,
    )
    authority = DepartmentAuthority(
        scope_id=scope,
        subject=subject,
        auth_method=auth_method,
        provider=getattr(principal, "provider", None),
        roles=principal_roles,
        entitlements=entitlements,
        resolved_at=effective_now,
        grants_digest=_fingerprint(
            [event.fingerprint() for event in sorted(materialized, key=lambda e: (
                str(e.department_id), e.sequence
            ))]
        ),
        _token=_RESOLVED,
    )

    if requested_departments is not None:
        for department_id in requested_departments:
            authority.require(department_id, action="resolve requested department")
    return authority


# ── persisted grant ledger ─────────────────────────────────────────────────────────────


def _grant_payload(
    *, scope_id: str, subject: str, department_id: UUID, sequence: int, action: str,
    roles: Sequence[str], recorded_by: str,
) -> dict[str, Any]:
    return {
        "scope_id": scope_id,
        "subject": subject,
        "department_id": str(department_id),
        "sequence": sequence,
        "action": action,
        "roles": sorted(roles),
        "recorded_by": recorded_by,
    }


@dataclass(frozen=True)
class GrantOutcome:
    """Result of an append attempt. ``inserted`` is False for an exact repeat."""

    grant: DepartmentGrant
    inserted: bool


async def _append_event(
    session: AsyncSession,
    *,
    scope_id: str,
    subject: str,
    department_id: UUID,
    action: GrantAction,
    roles: Sequence[str],
    recorded_by: str,
) -> GrantOutcome:
    if not isinstance(recorded_by, str) or not recorded_by.strip() or len(recorded_by) > 128:
        raise DepartmentGrantError("An attributed recorder identity is required")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 320:
        raise DepartmentGrantError("An authenticated subject is required")
    subject = subject.strip()
    normalized_roles = tuple(sorted(normalize_access_values(roles)))
    if action == "grant" and not normalized_roles:
        raise DepartmentGrantError("A grant must name at least one role")
    if action == "revoke" and normalized_roles:
        raise DepartmentGrantError("A revoke event must not carry roles")

    # Serialize per (scope, subject, department): sequence assignment must be total.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"civiccore.department_authority:{scope_id}:{subject}:{department_id}"},
    )
    latest = (
        (
            await session.execute(
                text(
                    f"SELECT sequence, action, roles, content_sha256 FROM {GRANT_TABLE} "
                    "WHERE scope_id=:scope AND subject=:subject AND department_id=:dept "
                    "ORDER BY sequence DESC LIMIT 1"
                ),
                {"scope": scope_id, "subject": subject, "dept": department_id},
            )
        )
        .mappings()
        .first()
    )
    next_sequence = (latest["sequence"] + 1) if latest else 1

    payload = _grant_payload(
        scope_id=scope_id,
        subject=subject,
        department_id=department_id,
        sequence=next_sequence,
        action=action,
        roles=normalized_roles,
        recorded_by=recorded_by,
    )
    digest = _fingerprint(payload)
    same_target = (
        latest is not None
        and latest["action"] == action
        and tuple(sorted(latest["roles"] or ())) == normalized_roles
    )
    if action == "grant" and same_target:
        # Exact repeat of the active grant: idempotent, original actor/time preserved.
        row = await session.execute(
            text(
                f"SELECT * FROM {GRANT_TABLE} WHERE scope_id=:scope AND subject=:subject "
                "AND department_id=:dept AND sequence=:seq"
            ),
            {
                "scope": scope_id,
                "subject": subject,
                "dept": department_id,
                "seq": latest["sequence"],
            },
        )
        return GrantOutcome(grant=_row_to_grant(row.mappings().one()), inserted=False)
    if action == "revoke" and (latest is None or latest["action"] == "revoke"):
        raise DepartmentGrantError("No active grant to revoke for this department")

    await session.execute(
        text(
            f"INSERT INTO {GRANT_TABLE} (scope_id, subject, department_id, sequence, action, "
            "roles, recorded_by, recorded_at, content_sha256) VALUES (:scope, :subject, :dept, "
            ":seq, :action, :roles, :by, now(), :digest)"
        ),
        {
            "scope": scope_id,
            "subject": subject,
            "dept": department_id,
            "seq": next_sequence,
            "action": action,
            "roles": list(normalized_roles),
            "by": recorded_by.strip(),
            "digest": digest,
        },
    )
    row = await session.execute(
        text(
            f"SELECT * FROM {GRANT_TABLE} WHERE scope_id=:scope AND subject=:subject "
            "AND department_id=:dept AND sequence=:seq"
        ),
        {"scope": scope_id, "subject": subject, "dept": department_id, "seq": next_sequence},
    )
    return GrantOutcome(grant=_row_to_grant(row.mappings().one()), inserted=True)


def _row_to_grant(row: Mapping[str, Any]) -> DepartmentGrant:
    return DepartmentGrant(
        scope_id=row["scope_id"],
        subject=row["subject"],
        department_id=row["department_id"],
        sequence=row["sequence"],
        action=row["action"],
        roles=tuple(row["roles"] or ()),
        recorded_by=row["recorded_by"],
        recorded_at=row["recorded_at"],
        content_sha256=row["content_sha256"],
    )


async def record_department_grant(
    session: AsyncSession,
    *,
    scope_id: str,
    subject: str,
    department_id: UUID,
    roles: Iterable[str],
    recorded_by: str,
) -> GrantOutcome:
    """Append a grant event for an already-authenticated subject. The caller commits.

    Authorization to *make* a grant belongs to the deployment's administration flow; this
    function only insists that the write is attributed and well formed. It never accepts a
    department claim from the subject being granted — the subject is identified by
    ``subject``, and the department must already exist.
    """

    scope = _require_scope(scope_id)
    return await _append_event(
        session,
        scope_id=scope,
        subject=subject,
        department_id=department_id,
        action="grant",
        roles=tuple(roles),
        recorded_by=recorded_by,
    )


async def revoke_department_grant(
    session: AsyncSession,
    *,
    scope_id: str,
    subject: str,
    department_id: UUID,
    recorded_by: str,
) -> GrantOutcome:
    """Append a revoke event; the prior grant stays readable as history. The caller commits."""

    scope = _require_scope(scope_id)
    return await _append_event(
        session,
        scope_id=scope,
        subject=subject,
        department_id=department_id,
        action="revoke",
        roles=(),
        recorded_by=recorded_by,
    )


async def active_department_grants(
    session: AsyncSession, *, scope_id: str, subject: str
) -> tuple[DepartmentGrant, ...]:
    """Return the highest-sequence event per department for one scope and subject.

    Scoped on both keys: rows for another scope or another subject are never returned. An
    unknown subject yields an empty tuple, which resolves to an authority that permits nothing.
    """

    scope = _require_scope(scope_id)
    if not isinstance(subject, str) or not subject.strip():
        raise DepartmentGrantError("An authenticated subject is required")
    rows = await session.execute(
        text(
            f"SELECT DISTINCT ON (department_id) * FROM {GRANT_TABLE} "
            "WHERE scope_id=:scope AND subject=:subject "
            "ORDER BY department_id, sequence DESC"
        ),
        {"scope": scope, "subject": subject.strip()},
    )
    return tuple(_row_to_grant(row) for row in rows.mappings())


async def department_grant_history(
    session: AsyncSession, *, scope_id: str, subject: str
) -> tuple[DepartmentGrant, ...]:
    """Return every retained event for one scope and subject, oldest first."""

    scope = _require_scope(scope_id)
    if not isinstance(subject, str) or not subject.strip():
        raise DepartmentGrantError("An authenticated subject is required")
    rows = await session.execute(
        text(
            f"SELECT * FROM {GRANT_TABLE} WHERE scope_id=:scope AND subject=:subject "
            "ORDER BY recorded_at, department_id, sequence"
        ),
        {"scope": scope, "subject": subject.strip()},
    )
    return tuple(_row_to_grant(row) for row in rows.mappings())


# ── consumer enforcement adapters (reuse the shipped search helpers) ──────────────────


def scope_search_results(
    authority: DepartmentAuthority,
    records: Iterable[Any],
    *,
    department_for: Any,
    required_roles: Iterable[str] = (),
) -> list[Any]:
    """Drop every result the authority may not see, before snippets or facets are built.

    ``department_for(record)`` returns the record's department id (or ``None`` when the record
    is not department-bound). An unbound record is filtered out: deny by default.
    """

    kept: list[Any] = []
    for record in records:
        department_id = department_for(record)
        if department_id is None:
            continue
        if authority.permits(department_id, roles=required_roles):
            kept.append(record)
    return kept


def authorize_export(
    authority: DepartmentAuthority,
    *,
    department_id: UUID,
    required_roles: Iterable[str] = (),
    purpose: str = "export",
) -> DepartmentEntitlement:
    """Refuse the export unless the authority covers the department and roles."""

    return authority.require(department_id, roles=required_roles, action=purpose)


def scope_model_context_chunks(
    authority: DepartmentAuthority,
    chunks: Iterable[tuple[Any, str]],
    *,
    department_for: Any,
) -> list[str]:
    """Return only chunk text the authority may send to a model.

    Chunks are ``(record, text)`` pairs. The returned list is the exact argument Core's existing
    :func:`civiccore.llm.context.assemble_context` accepts as ``chunks``, so no second context
    builder is introduced.
    """

    kept: list[str] = []
    for record, chunk_text in chunks:
        department_id = department_for(record)
        if department_id is None:
            continue
        if authority.permits(department_id):
            kept.append(chunk_text)
    return kept
