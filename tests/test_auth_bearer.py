from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from civiccore.auth import (
    AuthenticatedPrincipal,
    authorize_bearer_roles,
    enforce_trusted_proxy_source,
    load_trusted_header_auth_config,
    authorize_trusted_header_roles,
    parse_header_role_list,
    parse_token_role_map,
    resolve_optional_bearer_roles,
    resolve_optional_trusted_header_roles,
    staff_key_gate,
    TrustedHeaderAuthConfig,
)


def test_parse_token_role_map_accepts_string_and_list_roles() -> None:
    parsed = parse_token_role_map(
        '{"reader-token": "workpaper_reader, budget_admin", "admin-token": ["records_admin"]}',
        env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
    )

    assert parsed == {
        "reader-token": frozenset({"workpaper_reader", "budget_admin"}),
        "admin-token": frozenset({"records_admin"}),
    }


def test_parse_token_role_map_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_token_role_map("{not-json}", env_var="CIVIC_TEST_AUTH_TOKEN_ROLES")


def test_authorize_bearer_roles_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CIVIC_TEST_AUTH_TOKEN_ROLES", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        authorize_bearer_roles(
            None,
            service_name="Townlight Budget",
            feature_name="persisted workpaper retrieval",
            token_roles_env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
            allowed_roles={"workpaper_reader"},
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["message"] == (
        "Townlight Budget persisted workpaper retrieval auth is not configured."
    )
    assert "Set CIVIC_TEST_AUTH_TOKEN_ROLES" in exc_info.value.detail["fix"]


def test_authorize_bearer_roles_rejects_missing_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVIC_TEST_AUTH_TOKEN_ROLES", '{"reader-token": ["workpaper_reader"]}')

    with pytest.raises(HTTPException) as exc_info:
        authorize_bearer_roles(
            None,
            service_name="Townlight Budget",
            feature_name="persisted workpaper retrieval",
            token_roles_env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
            allowed_roles={"workpaper_reader"},
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    assert exc_info.value.detail["message"] == "Bearer token required."


def test_authorize_bearer_roles_rejects_unmapped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVIC_TEST_AUTH_TOKEN_ROLES", '{"reader-token": ["workpaper_reader"]}')

    with pytest.raises(HTTPException) as exc_info:
        authorize_bearer_roles(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="unknown-token"),
            service_name="Townlight Budget",
            feature_name="persisted workpaper retrieval",
            token_roles_env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
            allowed_roles={"workpaper_reader"},
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["message"] == "Bearer token not recognized."


def test_authorize_bearer_roles_rejects_token_without_allowed_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVIC_TEST_AUTH_TOKEN_ROLES", '{"reader-token": ["budget_viewer"]}')

    with pytest.raises(HTTPException) as exc_info:
        authorize_bearer_roles(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="reader-token"),
            service_name="Townlight Budget",
            feature_name="persisted workpaper retrieval",
            token_roles_env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
            allowed_roles={"workpaper_reader"},
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["message"] == "Bearer token lacks an allowed role."
    assert exc_info.value.detail["required_roles"] == ["workpaper_reader"]
    assert "token_roles" not in exc_info.value.detail


def test_authorize_bearer_roles_returns_principal_for_allowed_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CIVIC_TEST_AUTH_TOKEN_ROLES",
        '{"reader-token": ["workpaper_reader", "budget_admin"]}',
    )

    principal = authorize_bearer_roles(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="reader-token"),
        service_name="Townlight Budget",
        feature_name="persisted workpaper retrieval",
        token_roles_env_var="CIVIC_TEST_AUTH_TOKEN_ROLES",
        allowed_roles={"workpaper_reader"},
    )

    assert isinstance(principal, AuthenticatedPrincipal)
    assert principal.roles == frozenset({"workpaper_reader", "budget_admin"})


def test_resolve_optional_bearer_roles_allows_anonymous_callers_without_config() -> None:
    principal = resolve_optional_bearer_roles(
        None,
        service_name="CivicClerk",
        feature_name="archive search staff access",
        token_roles_env_var="CIVICCLERK_AUTH_TOKEN_ROLES",
        allowed_roles={"archive_reader"},
    )

    assert principal is None


def test_resolve_optional_bearer_roles_returns_principal_for_configured_staff_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CIVICCLERK_AUTH_TOKEN_ROLES",
        '{"staff-token": ["archive_reader", "clerk_admin"]}',
    )

    principal = resolve_optional_bearer_roles(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="staff-token"),
        service_name="CivicClerk",
        feature_name="archive search staff access",
        token_roles_env_var="CIVICCLERK_AUTH_TOKEN_ROLES",
        allowed_roles={"archive_reader"},
    )

    assert isinstance(principal, AuthenticatedPrincipal)
    assert principal.roles == frozenset({"archive_reader", "clerk_admin"})


def test_resolve_optional_bearer_roles_rejects_present_token_without_allowed_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CIVICCLERK_AUTH_TOKEN_ROLES",
        '{"staff-token": ["meeting_editor"]}',
    )

    with pytest.raises(HTTPException) as exc_info:
        resolve_optional_bearer_roles(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="staff-token"),
            service_name="CivicClerk",
            feature_name="archive search staff access",
            token_roles_env_var="CIVICCLERK_AUTH_TOKEN_ROLES",
            allowed_roles={"archive_reader"},
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["required_roles"] == ["archive_reader"]


def test_parse_header_role_list_normalizes_comma_delimited_roles() -> None:
    parsed = parse_header_role_list(
        " Clerk_Admin, meeting_editor , city_attorney ",
        header_name="X-Civic-Roles",
    )

    assert parsed == frozenset({"clerk_admin", "meeting_editor", "city_attorney"})


def test_authorize_trusted_header_roles_requires_principal_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_trusted_header_roles(
            {"X-Civic-Roles": "clerk_admin"},
            service_name="CivicClerk",
            feature_name="staff workflow access",
            principal_header_name="X-Civic-Principal",
            roles_header_name="X-Civic-Roles",
            allowed_roles={"clerk_admin"},
            provider_name="Entra ID proxy",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["message"] == "Trusted identity header missing."
    assert "X-Civic-Principal" in exc_info.value.detail["fix"]
    assert "CivicClerk" in exc_info.value.detail["fix"]
    assert "staff workflow access" in exc_info.value.detail["fix"]


def test_authorize_trusted_header_roles_requires_role_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_trusted_header_roles(
            {"X-Civic-Principal": "clerk@example.gov"},
            service_name="CivicClerk",
            feature_name="staff workflow access",
            principal_header_name="X-Civic-Principal",
            roles_header_name="X-Civic-Roles",
            allowed_roles={"clerk_admin"},
            provider_name="Entra ID proxy",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["message"] == "Trusted role header missing."
    assert "X-Civic-Roles" in exc_info.value.detail["fix"]
    assert "CivicClerk" in exc_info.value.detail["fix"]
    assert "staff workflow access" in exc_info.value.detail["fix"]


def test_authorize_trusted_header_roles_rejects_underprivileged_identity() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_trusted_header_roles(
            {
                "X-Civic-Principal": "clerk@example.gov",
                "X-Civic-Roles": "records_viewer",
            },
            service_name="CivicClerk",
            feature_name="staff workflow access",
            principal_header_name="X-Civic-Principal",
            roles_header_name="X-Civic-Roles",
            allowed_roles={"clerk_admin", "meeting_editor"},
            provider_name="Entra ID proxy",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["message"] == "Trusted identity lacks an allowed role."
    assert exc_info.value.detail["required_roles"] == ["clerk_admin", "meeting_editor"]
    assert "principal" not in exc_info.value.detail
    assert "principal_roles" not in exc_info.value.detail
    assert "CivicClerk" in exc_info.value.detail["fix"]
    assert "staff workflow access" in exc_info.value.detail["fix"]


def test_authorize_trusted_header_roles_returns_principal() -> None:
    principal = authorize_trusted_header_roles(
        {
            "X-Civic-Principal": "clerk@example.gov",
            "X-Civic-Roles": "meeting_editor, clerk_admin",
        },
        service_name="CivicClerk",
        feature_name="staff workflow access",
        principal_header_name="X-Civic-Principal",
        roles_header_name="X-Civic-Roles",
        allowed_roles={"clerk_admin"},
        provider_name="Entra ID proxy",
    )

    assert isinstance(principal, AuthenticatedPrincipal)
    assert principal.auth_method == "trusted_header"
    assert principal.subject == "clerk@example.gov"
    assert principal.provider == "Entra ID proxy"
    assert principal.roles == frozenset({"clerk_admin", "meeting_editor"})
    assert principal.token_fingerprint


def test_resolve_optional_trusted_header_roles_allows_anonymous_callers() -> None:
    principal = resolve_optional_trusted_header_roles(
        {},
        service_name="CivicClerk",
        feature_name="staff workflow access",
        principal_header_name="X-Civic-Principal",
        roles_header_name="X-Civic-Roles",
        allowed_roles={"clerk_admin"},
        provider_name="Entra ID proxy",
    )

    assert principal is None


def test_resolve_optional_trusted_header_roles_returns_principal_when_present() -> None:
    principal = resolve_optional_trusted_header_roles(
        {
            "X-Civic-Principal": "clerk@example.gov",
            "X-Civic-Roles": "clerk_admin",
        },
        service_name="CivicClerk",
        feature_name="staff workflow access",
        principal_header_name="X-Civic-Principal",
        roles_header_name="X-Civic-Roles",
        allowed_roles={"clerk_admin"},
        provider_name="Entra ID proxy",
    )

    assert isinstance(principal, AuthenticatedPrincipal)
    assert principal.subject == "clerk@example.gov"


def test_load_trusted_header_auth_config_trims_values_and_parses_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_SSO_PROVIDER", " Entra ID proxy ")
    monkeypatch.setenv("TEST_SSO_PRINCIPAL_HEADER", " X-Staff-Email ")
    monkeypatch.setenv("TEST_SSO_ROLES_HEADER", " X-Staff-Roles ")
    monkeypatch.setenv("TEST_SSO_TRUSTED_PROXIES", "10.0.0.0/24, 192.168.1.8/32 ")

    config = load_trusted_header_auth_config(
        provider_env_var="TEST_SSO_PROVIDER",
        provider_default="trusted reverse proxy",
        principal_header_env_var="TEST_SSO_PRINCIPAL_HEADER",
        principal_header_default="X-Civic-Principal",
        roles_header_env_var="TEST_SSO_ROLES_HEADER",
        roles_header_default="X-Civic-Roles",
        trusted_proxy_env_var="TEST_SSO_TRUSTED_PROXIES",
    )

    assert config == TrustedHeaderAuthConfig(
        provider_name="Entra ID proxy",
        principal_header_name="X-Staff-Email",
        roles_header_name="X-Staff-Roles",
        trusted_proxy_cidrs=("10.0.0.0/24", "192.168.1.8/32"),
    )


def test_load_trusted_header_auth_config_falls_back_to_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_SSO_PROVIDER", raising=False)
    monkeypatch.delenv("TEST_SSO_PRINCIPAL_HEADER", raising=False)
    monkeypatch.delenv("TEST_SSO_ROLES_HEADER", raising=False)
    monkeypatch.delenv("TEST_SSO_TRUSTED_PROXIES", raising=False)

    config = load_trusted_header_auth_config(
        provider_env_var="TEST_SSO_PROVIDER",
        provider_default="trusted reverse proxy",
        principal_header_env_var="TEST_SSO_PRINCIPAL_HEADER",
        principal_header_default="X-Civic-Principal",
        roles_header_env_var="TEST_SSO_ROLES_HEADER",
        roles_header_default="X-Civic-Roles",
        trusted_proxy_env_var="TEST_SSO_TRUSTED_PROXIES",
    )

    assert config.provider_name == "trusted reverse proxy"
    assert config.principal_header_name == "X-Civic-Principal"
    assert config.roles_header_name == "X-Civic-Roles"
    assert config.trusted_proxy_cidrs == ()


def test_enforce_trusted_proxy_source_requires_allowlist() -> None:
    config = TrustedHeaderAuthConfig(
        provider_name="Entra ID proxy",
        principal_header_name="X-Staff-Email",
        roles_header_name="X-Staff-Roles",
        trusted_proxy_cidrs=(),
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_trusted_proxy_source(
            "127.0.0.1",
            service_name="CivicClerk",
            feature_name="staff workflow access",
            config=config,
            trusted_proxy_env_var="CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES",
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["message"] == "Trusted-header proxy allowlist is missing."
    assert "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES" in exc_info.value.detail["fix"]


def test_enforce_trusted_proxy_source_rejects_invalid_allowlist() -> None:
    config = TrustedHeaderAuthConfig(
        provider_name="Entra ID proxy",
        principal_header_name="X-Staff-Email",
        roles_header_name="X-Staff-Roles",
        trusted_proxy_cidrs=("not-a-cidr",),
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_trusted_proxy_source(
            "127.0.0.1",
            service_name="CivicClerk",
            feature_name="staff workflow access",
            config=config,
            trusted_proxy_env_var="CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES",
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["message"] == "Trusted-header proxy allowlist is invalid."
    assert "not-a-cidr" in exc_info.value.detail["fix"]


def test_enforce_trusted_proxy_source_rejects_untrusted_host() -> None:
    config = TrustedHeaderAuthConfig(
        provider_name="Entra ID proxy",
        principal_header_name="X-Staff-Email",
        roles_header_name="X-Staff-Roles",
        trusted_proxy_cidrs=("10.20.30.0/24",),
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_trusted_proxy_source(
            "203.0.113.22",
            service_name="CivicClerk",
            feature_name="staff workflow access",
            config=config,
            trusted_proxy_env_var="CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES",
        )

    assert exc_info.value.status_code == 403
    assert (
        exc_info.value.detail["message"] == "Trusted staff headers were not received from an approved proxy."
    )
    assert "client_host" not in exc_info.value.detail
    assert "trusted_proxy_cidrs" not in exc_info.value.detail


def test_enforce_trusted_proxy_source_accepts_allowed_host() -> None:
    config = TrustedHeaderAuthConfig(
        provider_name="Entra ID proxy",
        principal_header_name="X-Staff-Email",
        roles_header_name="X-Staff-Roles",
        trusted_proxy_cidrs=("10.20.30.0/24",),
    )

    enforce_trusted_proxy_source(
        "10.20.30.40",
        service_name="CivicClerk",
        feature_name="staff workflow access",
        config=config,
        trusted_proxy_env_var="CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES",
    )


def test_staff_key_gate_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CIVIC_TEST_STAFF_API_KEY", raising=False)
    dependency = staff_key_gate("CIVIC_TEST_STAFF_API_KEY", "X-CivicTest-Staff-Key")

    with pytest.raises(HTTPException) as exc_info:
        dependency(role="staff", staff_key="secret")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["message"] == "Staff API key auth is not configured."
    assert "Set CIVIC_TEST_STAFF_API_KEY" in exc_info.value.detail["fix"]


def test_staff_key_gate_rejects_wrong_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIVIC_TEST_STAFF_API_KEY", "secret")
    dependency = staff_key_gate("CIVIC_TEST_STAFF_API_KEY", "X-CivicTest-Staff-Key")

    with pytest.raises(HTTPException) as exc_info:
        dependency(role="resident", staff_key="secret")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["message"] == "Staff role required."
    assert "X-CivicTest-Role: staff" in exc_info.value.detail["fix"]


def test_staff_key_gate_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIVIC_TEST_STAFF_API_KEY", "secret")
    dependency = staff_key_gate("CIVIC_TEST_STAFF_API_KEY", "X-CivicTest-Staff-Key")

    with pytest.raises(HTTPException) as exc_info:
        dependency(role="staff", staff_key="wrong")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["message"] == "Staff API key is missing or invalid."
    assert "X-CivicTest-Staff-Key" in exc_info.value.detail["fix"]


def test_staff_key_gate_returns_principal_for_valid_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVIC_TEST_STAFF_API_KEY", "secret")
    dependency = staff_key_gate("CIVIC_TEST_STAFF_API_KEY", "X-CivicTest-Staff-Key")

    principal = dependency(role="staff", staff_key="secret")

    assert principal == AuthenticatedPrincipal(
        token_fingerprint="2bb80d537b1d",
        roles=frozenset({"staff"}),
        auth_method="staff_key",
    )


def test_staff_key_gate_uses_constant_time_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bytes, bytes]] = []

    def fake_compare_digest(left: bytes, right: bytes) -> bool:
        calls.append((left, right))
        return False

    monkeypatch.setenv("CIVIC_TEST_STAFF_API_KEY", "secret")
    monkeypatch.setattr("civiccore.auth.staff_key.hmac.compare_digest", fake_compare_digest)
    dependency = staff_key_gate("CIVIC_TEST_STAFF_API_KEY", "X-CivicTest-Staff-Key")

    with pytest.raises(HTTPException):
        dependency(role="staff", staff_key="wrong")

    assert calls == [(b"wrong", b"secret")]
