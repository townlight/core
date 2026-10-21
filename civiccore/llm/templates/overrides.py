"""Code-level template overrides per ADR-0004 §7.

Consumer apps (records-ai, civicclerk) can register Python-shipped default
overrides at module import time via @register_template_override. These take
precedence over civiccore defaults but are subordinate to operator-installed
DB overrides (so production hot-fixes still win).

Resolution order (per ADR-0004 §7):
1. App DB override (consumer_app, is_override=true, is_active, highest version)
2. App code-level override (this module's OVERRIDE_REGISTRY)
3. Townlight Core DB default (consumer_app="civiccore", is_override=false, is_active, highest version)
4. PromptTemplateNotFoundError
"""
from __future__ import annotations

from civiccore.llm.templates.models import PromptTemplate

# Keyed by (consumer_app, template_name); value is a fully-formed PromptTemplate
# instance (not a Pydantic schema — the resolver returns ORM rows uniformly).
OVERRIDE_REGISTRY: dict[tuple[str, str], PromptTemplate] = {}


def register_template_override(
    *,
    consumer_app: str,
    template_name: str,
    template: PromptTemplate,
) -> None:
    """Register an in-memory code-level override.

    The supplied `template` is returned as-is by `resolve_template` when the
    caller's `(consumer_app, template_name)` matches and no DB app override is
    found. Subsequent calls with the same key REPLACE the prior registration
    (last-import-wins; consistent with how Python module-level overrides work
    on re-import in tests).

    Args:
        consumer_app: Namespace key (e.g., "civicrecords-ai", "civicclerk").
            Should not be "civiccore" — civiccore defaults belong in the DB.
        template_name: Logical template name (e.g., "exemption_review.system").
        template: Fully-formed PromptTemplate instance. The caller is
            responsible for setting `template_name`, `consumer_app`,
            `system_prompt`, `user_prompt_template`, and any other fields the
            renderer needs. The instance does not need to be persisted to the DB.
    """
    OVERRIDE_REGISTRY[(consumer_app, template_name)] = template


def unregister_template_override(*, consumer_app: str, template_name: str) -> None:
    """Remove a code-level override. Useful for tests; safe if not registered."""
    OVERRIDE_REGISTRY.pop((consumer_app, template_name), None)


__all__ = [
    "OVERRIDE_REGISTRY",
    "register_template_override",
    "unregister_template_override",
]
