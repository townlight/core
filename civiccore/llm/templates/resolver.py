"""Prompt template resolution per ADR-0004 §7 (3-step algorithm).

Step 1 — App DB override:
    Look for an active row in prompt_templates with consumer_app=<requesting app>,
    template_name=<requested>, is_override=true, is_active=true.
    Highest version wins. DB overrides win over code overrides so that
    operators can hot-fix prompts in production without redeploy.

Step 2 — App code-level override:
    Look up (consumer_app, template_name) in OVERRIDE_REGISTRY (in-memory map
    populated at import time via @register_template_override). Code overrides
    beat civiccore defaults so that consumer apps can ship Python-level
    defaults that supersede civiccore's defaults when no DB override exists.

Step 3 — Townlight Core DB default:
    Fall back to consumer_app='civiccore', template_name=<requested>,
    is_override=false, is_active=true. Highest version wins.

Step 4 — Missing:
    Raise PromptTemplateNotFoundError. No silent default.

When consumer_app == 'civiccore', steps 1 AND 2 are skipped — civiccore can't
override its own template; it owns the default.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from civiccore.llm.templates.exceptions import PromptTemplateNotFoundError
from civiccore.llm.templates.models import PromptTemplate
from civiccore.llm.templates.overrides import OVERRIDE_REGISTRY

CIVICCORE_DEFAULT_APP = "civiccore"


async def resolve_template(
    session: AsyncSession,
    *,
    template_name: str,
    consumer_app: str,
) -> PromptTemplate:
    """Resolve a prompt template per the 3-step override algorithm.

    Args:
        session: Active SQLAlchemy AsyncSession.
        template_name: Logical template name (e.g., "exemption_review.system").
        consumer_app: Requesting application namespace (e.g., "civicrecords-ai").
            When set to "civiccore", steps 1 and 2 are skipped (no self-override).

    Returns:
        The resolved PromptTemplate ORM row (or in-memory instance for code overrides).

    Raises:
        PromptTemplateNotFoundError: When no DB app override, code override, or
            civiccore default is found. The error names both fields and tells
            the caller how to add the missing template.
    """
    # Step 1: App-specific DB override (skip if requester is civiccore itself)
    if consumer_app != CIVICCORE_DEFAULT_APP:
        stmt = (
            select(PromptTemplate)
            .where(
                PromptTemplate.consumer_app == consumer_app,
                PromptTemplate.template_name == template_name,
                PromptTemplate.is_override.is_(True),
                PromptTemplate.is_active.is_(True),
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            return row

        # Step 2: App code-level override (in-memory registry).
        # Skipped for consumer_app='civiccore' along with step 1.
        code_override = OVERRIDE_REGISTRY.get((consumer_app, template_name))
        if code_override is not None:
            return code_override

    # Step 3: CivicCore default
    stmt = (
        select(PromptTemplate)
        .where(
            PromptTemplate.consumer_app == CIVICCORE_DEFAULT_APP,
            PromptTemplate.template_name == template_name,
            PromptTemplate.is_override.is_(False),
            PromptTemplate.is_active.is_(True),
        )
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    # Step 4: Missing
    raise PromptTemplateNotFoundError(
        template_name=template_name,
        consumer_app=consumer_app,
    )


__all__ = ["resolve_template", "CIVICCORE_DEFAULT_APP"]
