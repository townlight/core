"""Contract tests for TownlightCore-owned suite staff session tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import townlight_core.auth.suite_session as suite_session_module
from townlight_core.auth.suite_session import (
    SuiteSessionConfigError,
    SuiteSessionPrincipal,
    issue_suite_session_token,
    revoke_suite_session,
    validate_suite_session_token,
)


def test_suite_session_token_validates_role_claims_and_rejects_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOWNLIGHT_CORE_SUITE_SESSION_SECRET", "test-secret-with-enough-entropy")
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    token = issue_suite_session_token(
        subject="admin@example.gov",
        roles=frozenset({"records_admin", "clerk_admin", "code_admin"}),
        session_id="suite-session-123",
        expires_at=expires_at,
    )

    principal = validate_suite_session_token(
        token,
        required_roles=frozenset({"records_admin"}),
    )

    assert principal == SuiteSessionPrincipal(
        subject="admin@example.gov",
        roles=frozenset({"records_admin", "clerk_admin", "code_admin"}),
        session_id="suite-session-123",
    )

    revoke_suite_session("suite-session-123")

    with pytest.raises(PermissionError, match="revoked"):
        validate_suite_session_token(token, required_roles=frozenset({"records_admin"}))


def test_suite_session_secret_is_required_with_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TOWNLIGHT_CORE_SUITE_SESSION_SECRET", raising=False)

    with pytest.raises(SuiteSessionConfigError, match="TOWNLIGHT_CORE_SUITE_SESSION_SECRET"):
        issue_suite_session_token(
            subject="admin@example.gov",
            roles=frozenset({"records_admin"}),
            session_id="suite-session-missing-secret",
        )


def test_suite_session_revocation_file_survives_process_local_cache_reset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("TOWNLIGHT_CORE_SUITE_SESSION_SECRET", "test-secret-with-enough-entropy")
    revocation_path = tmp_path / "suite-session-revocations.json"
    monkeypatch.setenv("TOWNLIGHT_CORE_SUITE_SESSION_REVOCATION_FILE", str(revocation_path))
    token = issue_suite_session_token(
        subject="admin@example.gov",
        roles=frozenset({"records_admin"}),
        session_id="suite-session-shared-revocation",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )

    revoke_suite_session("suite-session-shared-revocation")
    suite_session_module._REVOKED_SESSION_IDS.clear()

    with pytest.raises(PermissionError, match="revoked"):
        validate_suite_session_token(token, required_roles=frozenset({"records_admin"}))
