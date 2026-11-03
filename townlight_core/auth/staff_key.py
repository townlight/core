"""Shared staff API-key gate for lightweight module staff routes."""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Callable

from fastapi import Header, HTTPException

from townlight_core.auth.bearer import AuthenticatedPrincipal


def _role_header_for_staff_key_header(header: str) -> str:
    if header.endswith("-Staff-Key"):
        return f"{header[:-len('-Staff-Key')]}-Role"
    return f"{header}-Role"


def staff_key_gate(env_var: str, header: str) -> Callable[..., AuthenticatedPrincipal]:
    """Return a FastAPI dependency that gates staff routes with one shared contract.

    The dependency preserves the existing Townlight module convention:
    ``X-CivicFoo-Role: staff`` plus ``X-CivicFoo-Staff-Key: <secret>``.
    """

    role_header = _role_header_for_staff_key_header(header)

    def require_staff_key(
        role: str | None = Header(default=None, alias=role_header),
        staff_key: str | None = Header(default=None, alias=header),
    ) -> AuthenticatedPrincipal:
        expected_key = os.environ.get(env_var)
        if expected_key is None or not expected_key:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Staff API key auth is not configured.",
                    "fix": f"Set {env_var} before using staff-only routes.",
                },
            )

        if role != "staff":
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Staff role required.",
                    "fix": f"Send {role_header}: staff with trusted staff requests.",
                },
            )

        if staff_key is None or not hmac.compare_digest(
            staff_key.encode("utf-8"),
            expected_key.encode("utf-8"),
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Staff API key is missing or invalid.",
                    "fix": f"Send {header} with the configured staff API key.",
                },
            )

        return AuthenticatedPrincipal(
            token_fingerprint=hashlib.sha256(staff_key.encode("utf-8")).hexdigest()[:12],
            roles=frozenset({"staff"}),
            auth_method="staff_key",
        )

    return require_staff_key


__all__ = ["staff_key_gate"]
