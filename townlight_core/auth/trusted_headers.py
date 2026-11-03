"""Trusted-header auth helpers for reverse-proxy SSO deployments."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from fastapi import HTTPException

from townlight_core.auth.bearer import AuthenticatedPrincipal
from townlight_core.security import is_trusted_proxy_ip, normalize_trusted_proxy_cidrs


@dataclass(frozen=True)
class TrustedHeaderAuthConfig:
    """Service-specific trusted-header auth settings loaded from env/defaults."""

    provider_name: str
    principal_header_name: str
    roles_header_name: str
    trusted_proxy_cidrs: tuple[str, ...]


def parse_header_role_list(raw_value: str, *, header_name: str) -> frozenset[str]:
    """Parse a comma-delimited header value into normalized roles."""

    roles = frozenset(role.strip().lower() for role in raw_value.split(",") if role.strip())
    if not roles:
        raise ValueError(f"{header_name} must include at least one non-empty role.")
    return roles


def _lookup_header(headers: Mapping[str, str], header_name: str) -> str | None:
    target = header_name.strip().lower()
    for key, value in headers.items():
        if key.strip().lower() == target:
            candidate = value.strip()
            return candidate or None
    return None


def load_trusted_header_auth_config(
    *,
    provider_env_var: str,
    provider_default: str,
    principal_header_env_var: str,
    principal_header_default: str,
    roles_header_env_var: str,
    roles_header_default: str,
    trusted_proxy_env_var: str,
) -> TrustedHeaderAuthConfig:
    """Load trusted-header auth settings from environment-backed service config."""

    provider_name = os.environ.get(provider_env_var, provider_default).strip() or provider_default
    principal_header_name = (
        os.environ.get(principal_header_env_var, principal_header_default).strip()
        or principal_header_default
    )
    roles_header_name = (
        os.environ.get(roles_header_env_var, roles_header_default).strip() or roles_header_default
    )
    trusted_proxy_cidrs = tuple(
        candidate.strip()
        for candidate in os.environ.get(trusted_proxy_env_var, "").split(",")
        if candidate.strip()
    )
    return TrustedHeaderAuthConfig(
        provider_name=provider_name,
        principal_header_name=principal_header_name,
        roles_header_name=roles_header_name,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


def enforce_trusted_proxy_source(
    client_host: str | None,
    *,
    service_name: str,
    feature_name: str,
    config: TrustedHeaderAuthConfig,
    trusted_proxy_env_var: str,
) -> None:
    """Require trusted headers to arrive from a configured reverse-proxy allowlist."""

    if not config.trusted_proxy_cidrs:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Trusted-header proxy allowlist is missing.",
                "fix": (
                    f"Set {trusted_proxy_env_var} to the reverse-proxy CIDR list "
                    f"allowed to inject {service_name} {feature_name} identity headers, for example "
                    "'10.0.0.0/24,192.168.1.8/32'."
                ),
            },
        )

    try:
        normalize_trusted_proxy_cidrs(config.trusted_proxy_cidrs)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Trusted-header proxy allowlist is invalid.",
                "fix": f"{trusted_proxy_env_var}: {exc}",
            },
        ) from exc

    if not is_trusted_proxy_ip(client_host, config.trusted_proxy_cidrs):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Trusted staff headers were not received from an approved proxy.",
                "fix": (
                    f"Route {service_name} {feature_name} requests through a reverse proxy inside "
                    f"{trusted_proxy_env_var} and strip client-supplied copies of "
                    f"{config.principal_header_name} and {config.roles_header_name} before they reach "
                    f"{service_name}."
                ),
            },
        )


def authorize_trusted_header_roles(
    headers: Mapping[str, str],
    *,
    service_name: str,
    feature_name: str,
    principal_header_name: str,
    roles_header_name: str,
    allowed_roles: Iterable[str],
    provider_name: str = "trusted reverse proxy",
) -> AuthenticatedPrincipal:
    """Validate an asserted principal + roles from a trusted proxy/header bridge."""

    normalized_allowed = frozenset(role.strip().lower() for role in allowed_roles if role.strip())
    if not normalized_allowed:
        raise ValueError("allowed_roles must contain at least one non-empty role.")

    subject = _lookup_header(headers, principal_header_name)
    if subject is None:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Trusted identity header missing.",
                "fix": (
                    f"Authenticate through the configured {provider_name} flow so it injects "
                    f"{principal_header_name} before {service_name} handles {feature_name}."
                ),
            },
        )

    raw_roles = _lookup_header(headers, roles_header_name)
    if raw_roles is None:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Trusted role header missing.",
                "fix": (
                    f"Configure the trusted proxy to inject {roles_header_name} with one of these "
                    f"roles for {service_name} {feature_name}: {', '.join(sorted(normalized_allowed))}."
                ),
            },
        )

    try:
        header_roles = parse_header_role_list(raw_roles, header_name=roles_header_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Trusted role header is invalid.",
                "fix": f"{service_name} {feature_name}: {exc}",
            },
        ) from exc

    if header_roles.isdisjoint(normalized_allowed):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Trusted identity lacks an allowed role.",
                "fix": (
                    "Grant the signed-in staff account one of these roles or adjust the "
                    f"{provider_name} role mapping for {service_name} {feature_name}: "
                    f"{', '.join(sorted(normalized_allowed))}."
                ),
                "required_roles": sorted(normalized_allowed),
            },
        )

    return AuthenticatedPrincipal(
        token_fingerprint=hashlib.sha256(subject.encode("utf-8")).hexdigest()[:12],
        roles=header_roles,
        auth_method="trusted_header",
        subject=subject,
        provider=provider_name,
    )


def resolve_optional_trusted_header_roles(
    headers: Mapping[str, str],
    *,
    service_name: str,
    feature_name: str,
    principal_header_name: str,
    roles_header_name: str,
    allowed_roles: Iterable[str],
    provider_name: str = "trusted reverse proxy",
) -> AuthenticatedPrincipal | None:
    """Return an authenticated principal only when trusted headers are present."""

    if _lookup_header(headers, principal_header_name) is None:
        return None

    return authorize_trusted_header_roles(
        headers,
        service_name=service_name,
        feature_name=feature_name,
        principal_header_name=principal_header_name,
        roles_header_name=roles_header_name,
        allowed_roles=allowed_roles,
        provider_name=provider_name,
    )
