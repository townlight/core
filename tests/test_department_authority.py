# SPDX-License-Identifier: AGPL-3.0-only
"""Contract tests for the deny-by-default department authority.

No database is required here: these cover provenance, deny-by-default, scope isolation, role
intersection and the search/export/model-context adapters. The persisted ledger, concurrent
sequence assignment, revocation and restart behaviour are exercised against a real PostgreSQL
cluster by ``work/beta-foundations/core-authority-01/harness.py``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from civiccore.auth import AuthenticatedPrincipal
from civiccore.auth.department_scope import (
    TRUSTED_AUTH_METHODS,
    AuthorityProvenanceError,
    DepartmentAccessDenied,
    DepartmentAuthority,
    DepartmentGrant,
    DepartmentGrantError,
    authorize_export,
    resolve_department_authority,
    scope_model_context_chunks,
    scope_search_results,
)
from civiccore.llm.context import assemble_context

SCOPE = "city-a"
OTHER_SCOPE = "city-b"
CLERK = uuid.uuid4()
PUBLIC_WORKS = uuid.uuid4()
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def principal(
    *, subject="clerk@example.gov", roles=("clerk_admin",), method="bearer", provider="entra-id"
):
    return AuthenticatedPrincipal(
        token_fingerprint="deadbeefcafe",
        roles=frozenset(roles),
        auth_method=method,
        subject=subject,
        provider=provider,
    )


def grant(
    department_id=CLERK,
    *,
    subject="clerk@example.gov",
    scope=SCOPE,
    sequence=1,
    action="grant",
    roles=("clerk_admin",),
    recorded_by="fixture-admin",
):
    return DepartmentGrant(
        scope_id=scope,
        subject=subject,
        department_id=department_id,
        sequence=sequence,
        action=action,
        roles=tuple(roles),
        recorded_by=recorded_by,
        recorded_at=NOW,
        content_sha256="0" * 64,
    )


def resolve(**kwargs):
    kwargs.setdefault("principal", principal())
    kwargs.setdefault("scope_id", SCOPE)
    kwargs.setdefault("grants", (grant(),))
    kwargs.setdefault("now", NOW)
    return resolve_department_authority(**kwargs)


# ── provenance: no caller-supplied department claim can become authority ─────────────


def test_authority_cannot_be_constructed_by_a_caller():
    with pytest.raises(AuthorityProvenanceError):
        DepartmentAuthority(
            scope_id=SCOPE,
            subject="clerk@example.gov",
            auth_method="bearer",
            provider=None,
            roles=frozenset({"clerk_admin"}),
            entitlements=(),
            resolved_at=NOW,
            grants_digest="0" * 64,
        )


def test_resolver_refuses_an_unauthenticated_principal():
    anonymous = AuthenticatedPrincipal(token_fingerprint=None, roles=frozenset())
    with pytest.raises(AuthorityProvenanceError):
        resolve(principal=anonymous)


def test_resolver_refuses_an_identity_source_outside_the_trusted_methods():
    with pytest.raises(AuthorityProvenanceError):
        resolve(principal=principal(method="x_department_header"))


class _DeactivatedPrincipal:
    """Extended principal stand-in: a consumer that disables an identity in its own store.

    ``AuthenticatedPrincipal`` has no ``is_active`` field, so a deployment that tracks
    deactivation passes an object that also exposes one; the resolver must honour it.
    """

    token_fingerprint = "x"
    roles = frozenset({"clerk_admin"})
    auth_method = "bearer"
    subject = "clerk@example.gov"
    provider = "entra-id"
    is_active = False


def test_resolver_refuses_a_deactivated_principal():
    with pytest.raises(AuthorityProvenanceError):
        resolve(principal=_DeactivatedPrincipal())


def test_every_trusted_identity_method_is_accepted():
    for method in TRUSTED_AUTH_METHODS:
        authority = resolve(principal=principal(method=method))
        assert authority.auth_method == method
        assert authority.department_ids == {CLERK}


def test_resolver_refuses_a_malformed_deployment_scope():
    with pytest.raises(AuthorityProvenanceError):
        resolve(scope_id="City A")


# ── deny by default ───────────────────────────────────────────────────────────────────


def test_no_persisted_grant_means_no_departments_and_no_access():
    authority = resolve(grants=())
    assert authority.entitlements == ()
    with pytest.raises(DepartmentAccessDenied) as denied:
        authority.require(CLERK, action="search")
    assert denied.value.reason == "no-active-grant"


def test_a_grant_for_another_department_does_not_leak_across():
    authority = resolve(grants=(grant(PUBLIC_WORKS),))
    with pytest.raises(DepartmentAccessDenied) as denied:
        authority.require(CLERK, action="search")
    assert denied.value.reason == "department-not-granted"
    assert authority.permits(PUBLIC_WORKS) is True
    assert authority.permits(CLERK) is False


def test_a_grant_for_another_subject_is_ignored():
    authority = resolve(grants=(grant(subject="someone-else@example.gov"),))
    assert authority.entitlements == ()
    assert authority.permits(CLERK) is False


def test_a_grant_in_another_scope_is_ignored():
    authority = resolve(grants=(grant(scope=OTHER_SCOPE),))
    assert authority.scope_id == SCOPE
    assert authority.entitlements == ()
    assert authority.permits(CLERK) is False


def test_role_intersection_is_required():
    # The department grant admits clerk_admin only; this principal holds meeting_editor.
    authority = resolve(
        principal=principal(roles=("meeting_editor",)), grants=(grant(),)
    )
    assert authority.entitlements == ()
    assert authority.permits(CLERK) is False


def test_a_required_role_outside_the_department_grant_is_refused():
    authority = resolve()
    assert authority.permits(CLERK) is True
    with pytest.raises(DepartmentAccessDenied) as denied:
        authority.require(CLERK, roles=("city_attorney",), action="export")
    assert denied.value.reason == "role-not-granted"


def test_extra_principal_roles_do_not_widen_a_department_grant():
    authority = resolve(
        principal=principal(roles=("clerk_admin", "city_attorney")),
        grants=(grant(roles=("clerk_admin",)),),
    )
    assert authority.roles_in(CLERK) == frozenset({"clerk_admin"})
    assert authority.permits(CLERK, roles=("clerk_admin",)) is True
    assert authority.permits(CLERK, roles=("city_attorney",)) is False


def test_requested_departments_can_only_narrow():
    authority = resolve(requested_departments=[CLERK])
    assert authority.department_ids == {CLERK}
    with pytest.raises(DepartmentAccessDenied):
        resolve(requested_departments=[CLERK, PUBLIC_WORKS])


# ── revocation is expressed as a later event, never as a deleted row ─────────────────


def test_a_later_revoke_event_removes_the_entitlement():
    events = (grant(sequence=1), grant(sequence=2, action="revoke", roles=()))
    authority = resolve(grants=events)
    assert authority.entitlements == ()
    with pytest.raises(DepartmentAccessDenied):
        authority.require(CLERK, action="search")


def test_a_regrant_after_revoke_restores_the_entitlement():
    events = (
        grant(sequence=1),
        grant(sequence=2, action="revoke", roles=()),
        grant(sequence=3),
    )
    authority = resolve(grants=events)
    assert authority.department_ids == {CLERK}


def test_a_stale_lower_sequence_event_cannot_override_a_newer_one():
    # Out-of-order input must not let an old grant win over a newer revoke.
    events = (grant(sequence=3, action="revoke", roles=()), grant(sequence=1))
    authority = resolve(grants=events)
    assert authority.entitlements == ()


def test_a_grant_event_without_roles_is_refused_at_construction():
    with pytest.raises(ValueError):
        grant(roles=())


# ── two departments, two subjects: the acceptance shape ──────────────────────────────


def test_two_departments_and_a_revoked_staff_member():
    clerk = resolve(
        principal=principal(subject="clerk@example.gov", roles=("clerk_admin",)),
        grants=(
            grant(CLERK, subject="clerk@example.gov", roles=("clerk_admin",)),
            grant(PUBLIC_WORKS, subject="clerk@example.gov", roles=("clerk_admin",)),
        ),
    )
    works = resolve(
        principal=principal(subject="works@example.gov", roles=("works_editor",)),
        grants=(
            grant(PUBLIC_WORKS, subject="works@example.gov", roles=("works_editor",)),
        ),
    )
    revoked = resolve(
        principal=principal(subject="former@example.gov", roles=("clerk_admin",)),
        grants=(
            grant(CLERK, subject="former@example.gov", sequence=1, roles=("clerk_admin",)),
            grant(CLERK, subject="former@example.gov", sequence=2, action="revoke", roles=()),
        ),
    )

    assert clerk.department_ids == {CLERK, PUBLIC_WORKS}
    assert works.department_ids == {PUBLIC_WORKS}
    assert works.permits(CLERK) is False
    assert revoked.department_ids == frozenset()
    assert revoked.permits(CLERK) is False


# ── consumer adapters reuse the shipped search helpers and context builder ───────────


RECORDS = [
    {"id": "clerk-1", "department": CLERK, "text": "Council packet draft"},
    {"id": "works-1", "department": PUBLIC_WORKS, "text": "Sidewalk repair bid"},
    {"id": "unbound-1", "department": None, "text": "Unowned scan"},
]


def department_of(record):
    return record["department"]


def test_search_scope_drops_other_departments_and_unbound_records():
    works = resolve(
        principal=principal(subject="works@example.gov", roles=("works_editor",)),
        grants=(grant(PUBLIC_WORKS, subject="works@example.gov", roles=("works_editor",)),),
    )
    visible = scope_search_results(works, RECORDS, department_for=department_of)
    assert [row["id"] for row in visible] == ["works-1"]
    assert all("clerk" not in row["id"] for row in visible)


def test_search_scope_denies_everything_without_a_grant():
    authority = resolve(grants=())
    assert scope_search_results(authority, RECORDS, department_for=department_of) == []


def test_export_is_refused_across_departments():
    works = resolve(
        principal=principal(subject="works@example.gov", roles=("works_editor",)),
        grants=(grant(PUBLIC_WORKS, subject="works@example.gov", roles=("works_editor",)),),
    )
    assertion = authorize_export(works, department_id=PUBLIC_WORKS, purpose="export")
    assert assertion.department_id == PUBLIC_WORKS
    with pytest.raises(DepartmentAccessDenied):
        authorize_export(works, department_id=CLERK, purpose="export")


def test_model_context_only_receives_permitted_chunk_text():
    works = resolve(
        principal=principal(subject="works@example.gov", roles=("works_editor",)),
        grants=(grant(PUBLIC_WORKS, subject="works@example.gov", roles=("works_editor",)),),
    )
    pairs = [(record, record["text"]) for record in RECORDS]
    chunks = scope_model_context_chunks(works, pairs, department_for=department_of)
    assert chunks == ["Sidewalk repair bid"]

    prompt = assemble_context(
        "You are a records assistant.", "Summarize the visible items.", chunks=chunks
    )
    text = " ".join(block.content for block in prompt)
    assert "Sidewalk repair bid" in text
    assert "Council packet draft" not in text
    assert "Unowned scan" not in text


def test_receipt_is_bounded_and_does_not_leak_the_subject():
    receipt = resolve().receipt()
    assert "clerk@example.gov" not in receipt["subject_fingerprint"]
    assert receipt["provenance"] == "persisted-grant"
    assert receipt["departments"] == [str(CLERK)]
    assert len(receipt["subject_fingerprint"]) == 12


# ── grant ledger write guards (no database needed) ───────────────────────────────────


@pytest.mark.parametrize("scope", ["City A", "", "9lives", "a" * 65])
def test_grant_writes_refuse_a_malformed_scope(scope):
    import asyncio

    from civiccore.auth.department_scope import active_department_grants, record_department_grant

    async def write():
        # ``session=None`` is never touched: the scope is validated before any query.
        await record_department_grant(
            session=None,
            scope_id=scope,
            subject="clerk@example.gov",
            department_id=CLERK,
            roles=("clerk_admin",),
            recorded_by="fixture-admin",
        )

    async def read():
        await active_department_grants(session=None, scope_id=scope, subject="clerk@example.gov")

    for call in (write, read):
        with pytest.raises(DepartmentGrantError):
            asyncio.run(call())


def test_grant_event_fingerprint_is_stable_and_content_bound():
    first = grant()
    second = grant()
    assert first.fingerprint() == second.fingerprint()
    assert grant(roles=("works_editor",)).fingerprint() != first.fingerprint()
