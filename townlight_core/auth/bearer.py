"""Minimal bearer-token role checks for downstream FastAPI services."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Represents the caller that satisfied a bearer-token role check."""

    token_fingerprint: str | None
    roles: frozenset[str]
    auth_method: str = "bearer"
    subject: str | None = None
    provider: str | None = None


def parse_token_role_map(raw_value: str, *, env_var: str) -> dict[str, frozenset[str]]:
    """Parse a JSON object mapping bearer tokens to one or more roles."""

    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{env_var} must be valid JSON mapping bearer tokens to roles."
        ) from exc

    if not isinstance(data, dict) or not data:
        raise ValueError(
            f"{env_var} must be a non-empty JSON object mapping bearer tokens to roles."
        )

    parsed: dict[str, frozenset[str]] = {}
    for token, raw_roles in data.items():
        if not isinstance(token, str) or not token.strip():
            raise ValueError(f"{env_var} contains an empty or non-string bearer token key.")

        if isinstance(raw_roles, str):
            roles = [role.strip() for role in raw_roles.split(",")]
        elif isinstance(raw_roles, list) and all(isinstance(role, str) for role in raw_roles):
            roles = [role.strip() for role in raw_roles]
        else:
            raise ValueError(
                f"{env_var} token entries must be a role string or a list of role strings."
            )

        normalized = frozenset(role.lower() for role in roles if role)
        if not normalized:
            raise ValueError(f"{env_var} token entries must include at least one role.")
        parsed[token] = normalized

    return parsed


def authorize_bearer_roles(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    service_name: str,
    feature_name: str,
    token_roles_env_var: str,
    allowed_roles: Iterable[str],
) -> AuthenticatedPrincipal:
    """Validate an incoming bearer token against configured allowed roles."""

    raw_config = os.environ.get(token_roles_env_var)
    if raw_config is None or not raw_config.strip():
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"{service_name} {feature_name} auth is not configured.",
                "fix": (
                    f"Set {token_roles_env_var} to a JSON object mapping bearer tokens "
                    f"to one or more roles before exposing {feature_name}."
                ),
            },
        )

    try:
        configured_tokens = parse_token_role_map(raw_config, env_var=token_roles_env_var)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"{service_name} {feature_name} auth configuration is invalid.",
                "fix": str(exc),
            },
        ) from exc

    normalized_allowed = frozenset(role.strip().lower() for role in allowed_roles if role.strip())
    if not normalized_allowed:
        raise ValueError("allowed_roles must contain at least one non-empty role.")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Bearer token required.",
                "fix": (
                    "Send an Authorization header in the form "
                    "'Bearer <token>' using a token with one of the allowed roles."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_roles = configured_tokens.get(credentials.credentials)
    if token_roles is None:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Bearer token not recognized.",
                "fix": (
                    f"Use a token configured in {token_roles_env_var} with one of these roles: "
                    f"{', '.join(sorted(normalized_allowed))}."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_roles.isdisjoint(normalized_allowed):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Bearer token lacks an allowed role.",
                "fix": (
                    "Grant the token one of these roles or use a different token: "
                    f"{', '.join(sorted(normalized_allowed))}."
                ),
                "required_roles": sorted(normalized_allowed),
            },
        )

    return AuthenticatedPrincipal(
        token_fingerprint=hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()[:12],
        roles=token_roles,
        auth_method="bearer",
    )


def resolve_optional_bearer_roles(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    service_name: str,
    feature_name: str,
    token_roles_env_var: str,
    allowed_roles: Iterable[str],
) -> AuthenticatedPrincipal | None:
    """Return an authenticated principal when a bearer token is present.

    Mixed public/staff endpoints can use this helper to keep anonymous access
    available while upgrading privileged results to the shared bearer-token
    contract when callers present Authorization headers.
    """

    if credentials is None:
        return None

    return authorize_bearer_roles(
        credentials,
        service_name=service_name,
        feature_name=feature_name,
        token_roles_env_var=token_roles_env_var,
        allowed_roles=allowed_roles,
    )
