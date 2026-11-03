"""Negative contract tests for TownlightCore-owned suite staff session tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def test_suite_session_rejects_expired_and_wrong_signature_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from townlight_core.auth.suite_session import (
        issue_suite_session_token,
        validate_suite_session_token,
    )

    monkeypatch.setenv("TOWNLIGHT_CORE_SUITE_SESSION_SECRET", "first-test-secret")
    expired_token = issue_suite_session_token(
        subject="operator@example.gov",
        roles=frozenset({"records_admin"}),
        session_id="expired-session",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(PermissionError, match="expired|expire"):
        validate_suite_session_token(
            expired_token,
            required_roles=frozenset({"records_admin"}),
        )

    valid_token = issue_suite_session_token(
        subject="operator@example.gov",
        roles=frozenset({"records_admin"}),
        session_id="wrong-secret-session",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    monkeypatch.setenv("TOWNLIGHT_CORE_SUITE_SESSION_SECRET", "second-test-secret")

    with pytest.raises(PermissionError, match="signature|invalid"):
        validate_suite_session_token(
            valid_token,
            required_roles=frozenset({"records_admin"}),
        )
