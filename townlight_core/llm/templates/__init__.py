"""Townlight Core LLM prompt template ORM, schemas, rendering, and resolution.

Phase 2 Step 3a added: PromptTemplate ORM + Pydantic schemas.
Phase 2 Step 3c added: rendering (string.Template engine) + override resolution.
"""
from __future__ import annotations

# Side-effect import: ensure ModelRegistry is registered with townlight_core.db.Base.metadata
# so SQLAlchemy can resolve PromptTemplate.model_id's FK("model_registry.id") at
# mapper configuration time. Without this, querying PromptTemplate from a session
# where only townlight_core.llm.templates was imported raises NoReferencedTableError.
from townlight_core.llm.registry.models import ModelRegistry  # noqa: F401

from townlight_core.llm.templates.engine import RenderedPrompt, render_template
from townlight_core.llm.templates.exceptions import (
    PromptTemplateError,
    PromptTemplateNotFoundError,
    PromptTemplateRenderError,
)
from townlight_core.llm.templates.models import PromptTemplate
from townlight_core.llm.templates.overrides import (
    OVERRIDE_REGISTRY,
    register_template_override,
    unregister_template_override,
)
from townlight_core.llm.templates.resolver import TOWNLIGHT_CORE_DEFAULT_APP, resolve_template
from townlight_core.llm.templates.schemas import (
    PromptTemplateCreate,
    PromptTemplateRead,
)

__all__ = [
    "OVERRIDE_REGISTRY",
    "register_template_override",
    "unregister_template_override",
    "PromptTemplate",
    "PromptTemplateCreate",
    "PromptTemplateRead",
    "RenderedPrompt",
    "render_template",
    "resolve_template",
    "TOWNLIGHT_CORE_DEFAULT_APP",
    "PromptTemplateError",
    "PromptTemplateNotFoundError",
    "PromptTemplateRenderError",
]
