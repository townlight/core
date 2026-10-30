# SPDX-License-Identifier: AGPL-3.0-only
"""ADR-0009 must record the authority contract without rewriting earlier ADRs.

Mirrors how ADR-0007 and ADR-0008 handled their deferrals: the historical ADR text stays
byte-identical and the new ADR states both the decision and what it does not close.
"""

from __future__ import annotations

from pathlib import Path

import civiccore.auth.department_scope as authority


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_authority_adr_records_the_trust_boundary_and_non_claims() -> None:
    current = (REPO_ROOT / "docs/adr/ADR-0009-department-scoped-authority.md").read_text(
        encoding="utf-8"
    )

    assert "Implemented in the private beta candidate" in current
    assert "not released" in current
    # The trust boundary is the point of the ADR and must stay stated.
    assert "civiccore_department_grant_events" in current
    assert "privil" in current.lower()  # the escalation shape it prevents
    assert "active_department_grants" in current
    assert "deny by default" in current.lower()
    assert "intersection" in current.lower()
    assert "append-only" in current
    assert "does not" in current.lower()
    # It must not claim more than was tested.
    assert "Core HTTP/CLI surface" in current


def test_historical_adr_text_is_preserved() -> None:
    for name in (
        "ADR-0001-defer-civiccore-catalog.md",
        "ADR-0004-beta-shared-catalog.md",
        "ADR-0006-rule-version-history.md",
        "ADR-0008-beta-module-inventory.md",
    ):
        text = (REPO_ROOT / "docs" / "adr" / name).read_text(encoding="utf-8")
        assert "Status:" in text, name

    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")
    assert "ADR-0009-department-scoped-authority.md" in index
    assert "ADR-0001-defer-civiccore-catalog.md" in index
    assert "ADR-0008-beta-module-inventory.md" in index


def test_authority_module_documents_the_non_claims_it_must_uphold() -> None:
    docstring = " ".join((authority.__doc__ or "").split())

    assert "not an identity provider" in docstring
    assert "trust boundary" in docstring.lower()
    assert "persisted, server-side grant ledger" in docstring
    assert "privilege escalation" in docstring
    assert "Deny by default" in docstring
    assert "does not invent or enumerate" in docstring


def test_authority_contract_is_importable_from_the_auth_namespace() -> None:
    import civiccore.auth as auth

    for name in (
        "DepartmentAuthority",
        "DepartmentAuthorityError",
        "DepartmentAccessDenied",
        "DepartmentEntitlement",
        "DepartmentGrant",
        "DepartmentGrantError",
        "AuthorityProvenanceError",
        "GrantOutcome",
        "TRUSTED_AUTH_METHODS",
        "active_department_grants",
        "authorize_export",
        "department_grant_history",
        "record_department_grant",
        "resolve_department_authority",
        "revoke_department_grant",
        "scope_model_context_chunks",
        "scope_search_results",
    ):
        assert name in auth.__all__, name
        assert getattr(auth, name) is not None, name

    # Pre-existing auth exports must survive this additive increment.
    for name in (
        "AuthenticatedPrincipal",
        "authorize_bearer_roles",
        "authorize_trusted_header_roles",
        "enforce_trusted_proxy_source",
        "issue_suite_session_token",
        "revoke_suite_session",
        "staff_key_gate",
        "validate_suite_session_token",
    ):
        assert name in auth.__all__, name
