"""Authentication helpers for Townlight FastAPI services.

``civiccore.auth`` verifies credentials (bearer tokens, trusted proxy headers, staff keys and
suite sessions). ``civiccore.auth.department_scope`` is the separate *authorization* contract:
it consumes an already-authenticated principal and refuses by default unless a persisted,
server-side department grant admits the request.
"""

from civiccore.auth.bearer import (
    AuthenticatedPrincipal,
    authorize_bearer_roles,
    parse_token_role_map,
    resolve_optional_bearer_roles,
)
from civiccore.auth.department_scope import (
    AuthorityProvenanceError,
    DepartmentAccessDenied,
    DepartmentAuthority,
    DepartmentAuthorityError,
    DepartmentEntitlement,
    DepartmentGrant,
    DepartmentGrantError,
    GrantOutcome,
    active_department_grants,
    authorize_export,
    department_grant_history,
    record_department_grant,
    resolve_department_authority,
    revoke_department_grant,
    scope_model_context_chunks,
    scope_search_results,
    TRUSTED_AUTH_METHODS,
)
from civiccore.auth.staff_key import staff_key_gate
from civiccore.auth.suite_session import (
    SuiteSessionConfigError,
    SuiteSessionPrincipal,
    issue_suite_session_token,
    revoke_suite_session,
    validate_suite_session_token,
)
from civiccore.auth.trusted_headers import (
    authorize_trusted_header_roles,
    enforce_trusted_proxy_source,
    load_trusted_header_auth_config,
    parse_header_role_list,
    resolve_optional_trusted_header_roles,
    TrustedHeaderAuthConfig,
)

__all__ = [
    "AuthenticatedPrincipal",
    "AuthorityProvenanceError",
    "DepartmentAccessDenied",
    "DepartmentAuthority",
    "DepartmentAuthorityError",
    "DepartmentEntitlement",
    "DepartmentGrant",
    "DepartmentGrantError",
    "GrantOutcome",
    "SuiteSessionConfigError",
    "SuiteSessionPrincipal",
    "TRUSTED_AUTH_METHODS",
    "active_department_grants",
    "authorize_bearer_roles",
    "authorize_export",
    "authorize_trusted_header_roles",
    "department_grant_history",
    "enforce_trusted_proxy_source",
    "issue_suite_session_token",
    "load_trusted_header_auth_config",
    "parse_header_role_list",
    "parse_token_role_map",
    "record_department_grant",
    "resolve_department_authority",
    "resolve_optional_bearer_roles",
    "resolve_optional_trusted_header_roles",
    "revoke_department_grant",
    "revoke_suite_session",
    "scope_model_context_chunks",
    "scope_search_results",
    "staff_key_gate",
    "TrustedHeaderAuthConfig",
    "validate_suite_session_token",
]
